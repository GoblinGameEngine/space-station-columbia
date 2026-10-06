extends Node
class_name RemakeDetailStreamer

## Full detail (LOD0: the complete glb with interiors, doors, lights and collision) only near the
## player.  Records come from RemakeLodClusters.build(..., full=false): {id, root, lod1, k}.  Each
## check (every 0.5 s) wants every building within LOAD_MARGIN m of where its full model starts to
## show (lod0_end(k)); a wanted building's glb loads on a background thread (MAX_INFLIGHT at a time)
## and goes into the world one a frame, its RemakeBuilding with the range [0, lod0_end(k)] and its LOD1
## starting there.  FREE_MARGIN m past it the building is freed and its LOD1 draws from 0 m again.

const LOAD_MARGIN := 60.0
const FREE_MARGIN := 100.0
const MAX_INFLIGHT := 2

var target: Node3D
var records: Array = []
var _loaded := {}                    # record index -> RemakeBuilding
var _inflight := {}                  # record index -> path
var _t := 0.0


func setup(p_target: Node3D, p_records: Array) -> void:
	target = p_target
	records = p_records


func _process(delta: float) -> void:
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
	var want := []
	for i in records.size():
		var r: Dictionary = records[i]
		var d := p.distance_to((r.root as Node3D).global_position)
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
		if _loaded.has(i) or _inflight.has(i):
			continue
		if _inflight.size() >= MAX_INFLIGHT:
			break
		var path := "res://remake/buildings/%s.glb" % records[i].get("model", records[i].id)
		if ResourceLoader.load_threaded_request(path) == OK:
			_inflight[i] = path


func _attach(i: int, ps: PackedScene) -> void:
	if ps == null or _loaded.has(i):
		return
	var r: Dictionary = records[i]
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
	_set_lod1_begin(records[i].lod1, 0.0)


func _set_lod1_begin(n: Node, begin: float) -> void:
	var stack: Array[Node] = [n]
	while stack.size() > 0:
		var c: Node = stack.pop_back()
		stack.append_array(c.get_children())
		if c is GeometryInstance3D:
			(c as GeometryInstance3D).visibility_range_begin = begin
			(c as GeometryInstance3D).visibility_range_begin_margin = begin * RemakeLodClusters.MARGIN
