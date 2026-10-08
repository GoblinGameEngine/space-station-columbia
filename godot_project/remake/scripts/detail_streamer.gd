extends Node
class_name RemakeDetailStreamer

## Buildings near the player, in two tiers.  Records come from RemakeLodClusters.build(..., full=false):
## {id, model, root, lod1, k, landmark, xform, parent, key2}, and cells: key2 -> {node (its merged LOD2 mesh), recs}.
##
## LOD1 (an ordinary building's exterior): the 1:1 world has ~50,000 buildings (2026-10-07), too many to keep
## in the scene, so an ordinary building has no nodes until its cell's LOD2 mesh comes within CELL_AHEAD m of
## handing over to it (the mesh's own visibility range begin); then its LOD1 goes in, one model load at a time
## on a worker thread and LOD1_BUDGET_USEC of instancing a frame, with the cell mesh as its visibility parent.
## CELL_DROP m farther out the cell's LOD1s are freed again.  Landmarks keep their whole chain all the time.
##
## LOD0 (the complete glb: interiors, doors, lights, collision): each check (every 0.5 s) wants every building
## of an active cell (and every landmark) within LOAD_MARGIN m of where its full model starts to show
## (lod0_end(k)); a wanted building's glb loads on a background thread (MAX_INFLIGHT at a time) and goes in
## one a frame, its RemakeBuilding with the range [0, lod0_end(k)] and its LOD1 starting there.  FREE_MARGIN m
## past it the building is freed and its LOD1 draws from 0 m again.

const LOAD_MARGIN := 60.0
const FREE_MARGIN := 100.0
const MAX_INFLIGHT := 2
const CELL_AHEAD := 80.0
const CELL_DROP := 160.0
const LOD1_BUDGET_USEC := 3000
const LOD1_INFLIGHT := 4

var target: Node3D
var records: Array = []
var _loaded := {}                    # record index -> RemakeBuilding
var _inflight := {}                  # record index -> path
var _t := 0.0
var _cells: Array = []               # [{node, recs, begin, on}]
var _active := {}                    # record index -> true: its LOD1 is in (or always: landmarks)
var _lod1_queue: Array = []          # record indices waiting for their LOD1
var _lod1_scenes := {}               # model -> PackedScene
var _lod1_users := {}                # model -> records using it
var _lod1_loading := {}              # model -> path
# the merged LOD2 / LOD3 cells, a band of the ring at a time round the player (RemakeLodClusters.band_path)
var parent_node: Node3D              # where the cells' meshes go
var far_side: Node                   # RemakeFarSide: they're registered with it as they go in
const KEEP_R := 2300.0               # m of s each way whose bands are kept (the far side is an image past FLAT_ARC)
var _banded := false
var _cell_by_key := {}               # key2 -> cell
var _sb_nodes := {}                  # band -> [MeshInstance3D]
var _sb_task := {}                   # band -> worker task
var _sb_res := {}                    # band -> BakedMeshes waiting to go in
var _sb_loaded := {}                 # band -> true once its cells are in
var _sb_t := 0.0
var bake_mode := false               # (FarsideBake: the merged cells drawn at every distance, no LOD1 / LOD0 streamed)


func setup(p_target: Node3D, p_records: Array, p_cells := {}) -> void:
	target = p_target
	records = p_records
	for i in records.size():
		if records[i].lod1 != null:
			_active[i] = true
	_banded = ResourceLoader.exists(RemakeLodClusters.band_path(0)) or ResourceLoader.exists(RemakeLodClusters.band_path(1))
	for key in p_cells:
		var c: Dictionary = p_cells[key]
		var begin := INF
		if c.node != null:
			var mi := c.node as MeshInstance3D
			begin = mi.visibility_range_begin + mi.visibility_range_begin_margin
		var cell := {"node": c.node, "recs": c.recs, "begin": begin, "on": false, "key": key,
			"band": RemakeLodClusters.band_of_s(float((key as Vector2i).x) * RemakeLodClusters.CELL2 + 0.5)}
		_cells.append(cell)
		_cell_by_key[key] = cell


func lod1_count() -> int:
	return _active.size()


func lod1_pending() -> int:
	## LOD1s wanted but not in yet (the loading screen waits for the ones round the player)
	return _lod1_queue.size() + (1 if bands_pending() else 0) if _checked else 1


func _process(delta: float) -> void:
	if _banded and parent_node != null:
		_stream_bands(delta)
	_finish_lod1()
	# finish background loads -- one into the world a frame (a building's full model takes 8-30 ms to put in)
	var attached := false
	for i in _inflight.keys():
		var path: String = _inflight[i]
		var st := ResourceLoader.load_threaded_get_status(path)
		if st == ResourceLoader.THREAD_LOAD_LOADED:
			if attached:
				continue
			attached = true
			_inflight.erase(i)
			_attach(i, ResourceLoader.load_threaded_get(path))
		elif st == ResourceLoader.THREAD_LOAD_FAILED or st == ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
			_inflight.erase(i)
	_t -= delta
	if _t > 0.0 or target == null:
		return
	_t = 0.5
	if bake_mode:
		_checked = true
		return
	var p := target.global_position
	_check_cells(p)
	_checked = true
	var want := []
	for i in _active.keys():
		var r: Dictionary = records[i]
		var d := p.distance_to((r.xform as Transform3D).origin)
		# loaded from LOAD_MARGIN m before it's drawn, freed FREE_MARGIN m past (it was 180-270 m for a model drawn to
		# 60-90 m: Calder's 300 full buildings in the scene at once, their nodes, doors, lights and colliders)
		var d0 := RemakeLodClusters.lod0_end(float(r.k))
		if d < d0 + LOAD_MARGIN:
			want.append([d, i])
		elif _loaded.has(i) and d > d0 + FREE_MARGIN:
			_release(i)
	want.sort_custom(func(a, b): return a[0] < b[0])
	for w in want:
		var i: int = w[1]
		if _loaded.has(i) or _inflight.has(i) or records[i].lod1 == null:
			continue
		if _inflight.size() >= MAX_INFLIGHT:
			break
		var path := "res://remake/buildings/%s.glb" % records[i].get("model", records[i].id)
		if ResourceLoader.load_threaded_request(path) == OK:
			_inflight[i] = path


func _check_cells(p: Vector3) -> void:
	# a cell's LOD1s go in CELL_AHEAD m before its merged mesh hands over to them, out CELL_DROP m farther
	for c in _cells:
		var d := 0.0
		if _banded and not _sb_loaded.has(c.band):
			continue                                         # (its band isn't in: far off)
		if c.node == null and c.get("nomesh", false):
			# no merged mesh of its own: by its first building, from where a mesh would have handed over
			d = p.distance_to(records[c.recs[0]].xform.origin)
			c.begin = RemakeLodClusters.D2 + 110.0
		elif c.node != null:
			d = p.distance_to((c.node as MeshInstance3D).global_transform * (c.node as MeshInstance3D).get_aabb().get_center())
		if not c.on and d < c.begin + CELL_AHEAD:
			c.on = true
			for i in c.recs:
				_lod1_queue.append(i)
		elif c.on and d > c.begin + CELL_DROP:
			c.on = false
			for i in c.recs:
				_drop_lod1(i)
	# nearest first
	if _lod1_queue.size() > 1:
		_lod1_queue.sort_custom(func(a, b): return p.distance_squared_to(records[a].xform.origin) < p.distance_squared_to(records[b].xform.origin))


func _stream_bands(delta: float) -> void:
	## the merged cells of the bands within KEEP_R of the player in, the rest out
	for k in _sb_res.keys():
		var b: BakedMeshes = _sb_res[k]
		_sb_res.erase(k)
		var nodes := []
		var n3 := {}
		for i in b.keys.size():
			var key: Array = b.keys[i]
			if int(key[0]) == 3:
				var mi := RemakeLodClusters.lod3_node(b.meshes[i], key[1])
				if bake_mode:
					mi.visible = false                       # (the LOD2 cells are drawn instead)
				parent_node.add_child(mi)
				n3[key[1]] = mi
				nodes.append(mi)
		var with2 := {}
		for i in b.keys.size():
			var key: Array = b.keys[i]
			if int(key[0]) != 2:
				continue
			var mi := RemakeLodClusters.lod2_node(b.meshes[i], key[1])
			parent_node.add_child(mi)
			var p3: MeshInstance3D = n3.get(key[2])
			if bake_mode:
				mi.visibility_range_begin = 0.0
				mi.visibility_range_begin_margin = 0.0
			elif p3:
				mi.visibility_parent = mi.get_path_to(p3)
			nodes.append(mi)
			with2[key[1]] = true
			var c = _cell_by_key.get(key[1])
			if c != null:
				c.node = mi
				c.begin = mi.visibility_range_begin + mi.visibility_range_begin_margin
		for c in _cells:
			if c.band == k and not with2.has(c.key):
				c.nomesh = true
		if far_side:
			for mi in nodes:
				far_side.add_node(mi)
		_sb_nodes[k] = nodes
		_sb_loaded[k] = true
		return                                               # (a band a frame)
	_sb_t -= delta
	if _sb_t > 0.0 or target == null:
		return
	_sb_t = 0.5
	var sp := StationGeo.s_of(target.global_position)
	var want := {}
	var u := sp - KEEP_R
	while u <= sp + KEEP_R + RemakeLodClusters.STREAM_BAND:
		want[RemakeLodClusters.band_of_s(minf(u, sp + KEEP_R))] = true
		u += RemakeLodClusters.STREAM_BAND
	for k in _sb_loaded.keys():
		if want.has(k):
			continue
		for c in _cells:
			if c.band == k:
				if c.on:
					c.on = false
					for i in c.recs:
						_drop_lod1(i)
				c.node = null
		for mi in _sb_nodes.get(k, []):
			(mi as Node).queue_free()
		_sb_nodes.erase(k)
		_sb_loaded.erase(k)
		if far_side and far_side.has_method("prune"):
			far_side.prune()
	for k in _sb_task.keys():
		if WorkerThreadPool.is_task_completed(_sb_task[k]):
			WorkerThreadPool.wait_for_task_completion(_sb_task[k])
			_sb_task.erase(k)
	for k in want:
		if _sb_loaded.has(k) or _sb_task.has(k) or _sb_res.has(k):
			continue
		if not ResourceLoader.exists(RemakeLodClusters.band_path(k)):
			_sb_loaded[k] = true                         # (a band without buildings)
			continue
		_sb_task[k] = WorkerThreadPool.add_task(_load_sband.bind(k), false, "structures band %d" % k)


func _load_sband(k: int) -> void:
	var b := BakedMeshes.load_all(RemakeLodClusters.band_path(k))
	if b == null:
		return
	call_deferred("_sband_loaded", k, b)


func _sband_loaded(k: int, b: BakedMeshes) -> void:
	_sb_res[k] = b


func bands_pending() -> bool:
	return not _sb_task.is_empty() or not _sb_res.is_empty() or (_banded and _sb_loaded.is_empty())


func _finish_lod1() -> void:
	var t0 := Time.get_ticks_usec()
	var budget := 60000 if StationGeo.loading else LOD1_BUDGET_USEC
	var keep := []
	for n in _lod1_queue.size():
		var i: int = _lod1_queue[n]
		if Time.get_ticks_usec() - t0 > budget:
			keep.append_array(_lod1_queue.slice(n))
			break
		var r: Dictionary = records[i]
		if r.lod1 != null or not _cell_on(r):
			continue
		var model: String = r.model
		if not _lod1_scenes.has(model):
			var path := "res://remake/buildings/%s.lod1.glb" % model
			if not _lod1_loading.has(model):
				if _lod1_loading.size() >= LOD1_INFLIGHT or not ResourceLoader.exists(path):
					if ResourceLoader.exists(path):
						keep.append(i)
					continue
				ResourceLoader.load_threaded_request(path)
				_lod1_loading[model] = path
			var st := ResourceLoader.load_threaded_get_status(path)
			if st == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
				keep.append(i)
				continue
			_lod1_loading.erase(model)
			if st != ResourceLoader.THREAD_LOAD_LOADED:
				continue
			_lod1_scenes[model] = ResourceLoader.load_threaded_get(path)
		_put_lod1(i)
	_lod1_queue = keep


var _cell_of := {}                   # key2 -> cell (built lazily)
var _checked := false                # the cells have been checked once


func _cell_on(r: Dictionary) -> bool:
	if _cell_of.is_empty():
		for c in _cells:
			for j in c.recs:
				_cell_of[records[j].key2] = c
	var c = _cell_of.get(r.key2)
	return c == null or c.on


func _put_lod1(i: int) -> void:
	var r: Dictionary = records[i]
	var model: String = r.model
	var root := Node3D.new()
	root.name = r.id
	root.transform = r.xform
	(r.parent as Node3D).add_child(root)
	var lod1: Node3D = (_lod1_scenes[model] as PackedScene).instantiate()
	root.add_child(lod1)
	RemakeBuilding.prepare_lod(lod1, "res://remake/buildings/%s.lod1.glb" % model)
	RemakeLodClusters._lod_bias(lod1, 1.0)
	RemakeLodClusters._ranges(lod1, 0.0, 0.0)
	var c = _cell_of.get(r.key2)
	if c != null and c.node != null:
		RemakeLodClusters._parent_all(lod1, c.node)
	r.root = root
	r.lod1 = lod1
	_active[i] = true
	_lod1_users[model] = _lod1_users.get(model, 0) + 1


func _drop_lod1(i: int) -> void:
	var r: Dictionary = records[i]
	if r.landmark or r.lod1 == null:
		return
	if _loaded.has(i):
		_loaded.erase(i)
	_inflight.erase(i)
	(r.root as Node).queue_free()
	r.root = null
	r.lod1 = null
	_active.erase(i)
	var model: String = r.model
	_lod1_users[model] = _lod1_users.get(model, 1) - 1
	if _lod1_users[model] <= 0:
		_lod1_users.erase(model)
		_lod1_scenes.erase(model)                    # (the model's meshes go when nothing uses them)


func _attach(i: int, ps: PackedScene) -> void:
	if ps == null or _loaded.has(i):
		return
	var r: Dictionary = records[i]
	if r.root == null:
		return
	var b := RemakeBuilding.new()
	(r.root as Node3D).add_child(b)
	b.load_building(ps)
	var d1: float = RemakeLodClusters.lod0_end(r.k)
	RemakeLodClusters._ranges(b, 0.0, d1)
	RemakeLodClusters._light_fade(b)
	_set_lod1_begin(r.lod1, d1)
	_loaded[i] = b


func _release(i: int) -> void:
	var b: Node = _loaded[i]
	_loaded.erase(i)
	b.queue_free()
	if records[i].lod1 != null:
		_set_lod1_begin(records[i].lod1, 0.0)


func _set_lod1_begin(n: Node, begin: float) -> void:
	var stack: Array[Node] = [n]
	while stack.size() > 0:
		var c: Node = stack.pop_back()
		stack.append_array(c.get_children())
		if c is GeometryInstance3D:
			(c as GeometryInstance3D).visibility_range_begin = begin
			(c as GeometryInstance3D).visibility_range_begin_margin = begin * RemakeLodClusters.MARGIN
