extends Node

## The road surface of each crossing's model (its deck, its culvert's crown, its embankment's
## crest) above the model's origin, where the road meets it at each end: tools/road_profile.py
## grades the road to meet it there.  Rays down onto the placed model's own collision, at the
## middle of its width, END_IN m in from each end.  The collision streams in near the player, so it
## takes the player to each crossing in turn.  From DevBridge (the world loaded):
##   var m = load("res://remake/tools/measure_crossings.gd").new(); root.add_child(m)   then m.done
## Writes remake/crossing_tops.json: {id: [top at the -z end, top at the +z end, top mid-span]}.

const END_IN := 0.6
const OUT := "res://remake/crossing_tops.json"


var done := false
var out := {}
var missing := []
var _todo: Array = []
var _wait := 0


func _ready() -> void:
	var pl: Array = JSON.parse_string(FileAccess.get_file_as_string("res://remake/placement.json")).structures
	_todo = pl.filter(func(e): return e.kind == "crossing")


func _physics_process(_delta: float) -> void:
	if done:
		return
	var p := get_tree().get_first_node_in_group("player") as Node3D
	if _wait > 0:
		_wait -= 1
		if _wait == 0:
			var e: Dictionary = _todo.pop_front()
			var xf := _xform(e)
			var lx: float = (e.fmin[0] + e.fmax[0]) * 0.5
			var tops := []
			for lz in [float(e.fmin[1]) + END_IN, float(e.fmax[1]) - END_IN, (float(e.fmin[1]) + float(e.fmax[1])) * 0.5]:
				tops.append(_top(p.get_world_3d().direct_space_state, xf, Vector3(lx, 0.0, lz), str(e.id)))
			if tops.has(NAN):
				missing.append(e.id)
			out[e.id] = tops
		return
	if _todo.is_empty():
		var f := FileAccess.open(OUT, FileAccess.WRITE)
		f.store_string(JSON.stringify(out, "", false))
		f.close()
		done = true
		return
	# stand beside the next one (well above, out of the way) and let its collision stream in
	var xf := _xform(_todo[0])
	p.global_position = xf.origin + xf.basis.y.normalized() * 30.0
	p.velocity = Vector3.ZERO
	_wait = 45


static func _xform(e: Dictionary) -> Transform3D:
	var s: float = e.s
	var x: float = e.x
	return Transform3D(StationGeo.basis(s, e.yaw), StationGeo.point(s, x, MapTerrain.pad_height(e.id)))


static func _top(space: PhysicsDirectSpaceState3D, xf: Transform3D, local: Vector3, id: String) -> float:
	## The height above the origin of the model's own surface at local (x, z): the highest hit on it
	## within 3 m of the origin's height (not a truss's top chord, not the ground beneath).
	var up := xf.basis.y.normalized()
	var p := xf * local
	var from := p + up * 3.0
	var ex: Array[RID] = []
	for attempt in 8:
		var q := PhysicsRayQueryParameters3D.create(from, p - up * 3.0)
		q.exclude = ex
		var hit := space.intersect_ray(q)
		if hit.is_empty():
			return NAN
		var c: Object = hit.collider
		if c is Node and str((c as Node).get_path()).contains("/World/" + id + "/"):
			return snappedf((hit.position - xf.origin).dot(up), 0.01)
		ex.append(hit.rid)
	return NAN
