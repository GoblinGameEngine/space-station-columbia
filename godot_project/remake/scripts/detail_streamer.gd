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


func setup(p_target: Node3D, p_records: Array, p_cells := {}) -> void:
	target = p_target
	records = p_records
	for i in records.size():
		if records[i].lod1 != null:
			_active[i] = true
	for key in p_cells:
		var c: Dictionary = p_cells[key]
		var begin := INF
		if c.node != null:
			var mi := c.node as MeshInstance3D
			begin = mi.visibility_range_begin + mi.visibility_range_begin_margin
		_cells.append({"node": c.node, "recs": c.recs, "begin": begin, "on": false})


func lod1_count() -> int:
	return _active.size()


func lod1_pending() -> int:
	## LOD1s wanted but not in yet (the loading screen waits for the ones round the player)
	return _lod1_queue.size() if _checked else 1


func _process(delta: float) -> void:
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
		if c.node != null:
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
