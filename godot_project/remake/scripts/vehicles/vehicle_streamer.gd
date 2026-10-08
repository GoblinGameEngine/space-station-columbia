extends Node3D
class_name VehicleStreamer

## Parked vehicles as records, built only near the player (the user, 2026-10-01: track what you can
## see and what you're directly connected to; load the rest as it's needed).
##
## A record is an id, a maker (Callable -> Node3D) and where it stands. The records round the player (a grid of GCELL
## cells) are looked at a few times a second: within `near` the vehicle is built (one a frame, inside a time budget),
## beyond `far` it is freed -- unless someone is in it, it's carrying people, or it's still moving -- and the record
## keeps where it was left. Far ones can show as an impostor (one MultiMesh for all of them: an aerostat's balloon
## seen across the ring).
##
## The records are packed (22,000 bicycles were a Dictionary each, ~100 MB with the ground heights worked out at load,
## and a slice of 40 a frame took 9 s to reach one by a player who'd just arrived -- 2026-10-08). With ground = true
## a record's height is the ground's, worked out when it's built.

@export var near := 180.0
@export var far := 230.0
@export var slice := 40              # (unused: kept for the callers that set it)
@export var budget_us := 3000

const GCELL := 100.0
const LOOK_EVERY := 0.25

var player: Node3D
var impostor: Mesh                   # optional: drawn for the records that aren't built
var impostor_lift := Vector3.ZERO    # its offset in the record's frame
var _ids := PackedStringArray()
var _mk := PackedInt32Array()        # record -> its maker in _makers
var _makers: Array[Callable] = []
var _xf := PackedFloat32Array()      # 12 a record: the basis' columns, the origin
var _ground := PackedByteArray()     # 1: stand it on the ground when it's built
var _grid := {}                      # Vector2i(s cell, x cell) -> PackedInt32Array of records
var _nodes := {}                     # record -> its built node
var _want: Array[int] = []           # records to build, nearest last
var _look := 0.0
var _mm: MultiMeshInstance3D
var _mm_dirty := true


func add(id: String, make: Callable, xf: Transform3D, ground := false) -> void:
	var i := _ids.size()
	_ids.append(id)
	var m := _makers.find(make)
	if m < 0:
		m = _makers.size()
		_makers.append(make)
	_mk.append(m)
	_set_xf(i, xf)
	_ground.append(1 if ground else 0)
	var key := _cell_of(xf.origin)
	var a: PackedInt32Array = _grid.get(key, PackedInt32Array())
	a.append(i)
	_grid[key] = a
	_mm_dirty = true


func count() -> int:
	return _ids.size()


func record(i: int) -> Dictionary:
	## {id, node (or null), xf}
	return {"id": _ids[i], "node": _nodes.get(i), "xf": _xform(i)}


func _set_xf(i: int, xf: Transform3D) -> void:
	var o := i * 12
	if _xf.size() < o + 12:
		_xf.resize(o + 12)
	var b := xf.basis
	for k in 3:
		_xf[o + k] = b.x[k]
		_xf[o + 3 + k] = b.y[k]
		_xf[o + 6 + k] = b.z[k]
		_xf[o + 9 + k] = xf.origin[k]


func _xform(i: int) -> Transform3D:
	var o := i * 12
	return Transform3D(Vector3(_xf[o], _xf[o + 1], _xf[o + 2]), Vector3(_xf[o + 3], _xf[o + 4], _xf[o + 5]),
		Vector3(_xf[o + 6], _xf[o + 7], _xf[o + 8]), Vector3(_xf[o + 9], _xf[o + 10], _xf[o + 11]))


func _origin(i: int) -> Vector3:
	var o := i * 12 + 9
	return Vector3(_xf[o], _xf[o + 1], _xf[o + 2])


static func _cell_of(p: Vector3) -> Vector2i:
	return Vector2i(floori(fposmod(StationGeo.s_of(p), StationGeo.CIRC) / GCELL), floori(p.x / GCELL))


func _near_records(p: Vector3, r: float) -> Array[int]:
	## the records within r of p, nearest last
	var c := _cell_of(p)
	var ns := ceili(StationGeo.CIRC / GCELL)
	var reach := ceili(r / GCELL)
	var got: Array = []
	for i in range(-reach, reach + 1):
		for j in range(-reach, reach + 1):
			for k in _grid.get(Vector2i(posmod(c.x + i, ns), c.y + j), PackedInt32Array()):
				var d := _origin(k).distance_to(p)
				if d < r:
					got.append([d, k])
	got.sort()
	got.reverse()
	var out: Array[int] = []
	for g in got:
		out.append(g[1])
	return out


func build_near(p: Vector3) -> void:
	## Now, all at once: the ones around the player's start (the load waits for these only).
	for i in _near_records(p, near):
		if not _nodes.has(i):
			_build(i)


func live_count() -> int:
	return _nodes.size()


func _process(delta: float) -> void:
	if player == null or _ids.is_empty():
		return
	var p := player.global_position
	_look -= delta
	if _look <= 0.0:
		_look = LOOK_EVERY
		_want = _near_records(p, near)
		for i in _nodes.keys():
			var n3 = _nodes[i]
			if not is_instance_valid(n3):
				_nodes.erase(i)
				continue
			if (n3 as Node3D).global_position.distance_to(p) > far and not _in_use(n3):
				_set_xf(i, (n3 as Node3D).global_transform)
				_ground[i] = 0
				(n3 as Node3D).queue_free()
				_nodes.erase(i)
				_mm_dirty = true
	var t0 := Time.get_ticks_usec()
	while not _want.is_empty() and Time.get_ticks_usec() - t0 < budget_us:
		var i: int = _want.pop_back()
		if not _nodes.has(i):
			_build(i)
			break                                          # (one a frame)
	if _mm_dirty and impostor != null:
		_redraw_impostors()


func _build(i: int) -> void:
	var n: Node3D = _makers[_mk[i]].call()
	n.name = _ids[i]
	add_child(n)
	var xf := _xform(i)
	if _ground[i] == 1:
		var s := StationGeo.s_of(xf.origin)
		xf.origin = StationGeo.point(s, xf.origin.x, MapTerrain.elevation(s, xf.origin.x))
	n.global_transform = xf
	_nodes[i] = n
	_mm_dirty = true


static func _in_use(n: Node3D) -> bool:
	if n.get("pilot") != null:
		return true
	var riders = n.get("_riders")
	if riders is Array and not (riders as Array).is_empty():
		return true
	if n is RigidBody3D and not (n as RigidBody3D).freeze and (n as RigidBody3D).linear_velocity.length() > 0.5:
		return true
	return false


func _redraw_impostors() -> void:
	_mm_dirty = false
	if _mm == null:
		_mm = MultiMeshInstance3D.new()
		_mm.name = "Impostors"
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = impostor
		_mm.multimesh = mm
		add_child(_mm)
	var xs: Array = []
	for i in _ids.size():
		if not _nodes.has(i):
			xs.append(_xform(i) * Transform3D(Basis(), impostor_lift))
	_mm.multimesh.instance_count = xs.size()
	for i in xs.size():
		_mm.multimesh.set_instance_transform(i, xs[i])
