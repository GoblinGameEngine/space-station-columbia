extends Node3D
class_name VehicleStreamer

## Parked vehicles as records, built only near the player (the user, 2026-10-01: track what you can
## see and what you're directly connected to; load the rest as it's needed).
##
## A record is {id, make (Callable -> Node3D), xf (Transform3D), node (or null)}. Each frame a slice
## of the records is checked against the player: within `near` the vehicle is built (one a frame,
## inside a time budget), beyond `far` it is freed -- unless someone is in it, it's carrying
## people, or it's still moving -- and the record keeps where it was left. Far ones can show as an
## impostor (one MultiMesh for all of them: an aerostat's balloon seen across the ring).

@export var near := 180.0
@export var far := 230.0
@export var slice := 40              # records checked a frame
@export var budget_us := 3000

var records: Array = []
var player: Node3D
var impostor: Mesh                   # optional: drawn for the records that aren't built
var impostor_lift := Vector3.ZERO    # its offset in the record's frame
var _i := 0
var _mm: MultiMeshInstance3D
var _mm_dirty := true


func add(id: String, make: Callable, xf: Transform3D) -> void:
	records.append({"id": id, "make": make, "xf": xf, "node": null})
	_mm_dirty = true


func build_near(p: Vector3) -> void:
	## Now, all at once: the ones around the player's start (the load waits for these only).
	for r in records:
		if r.node == null and r.xf.origin.distance_to(p) < near:
			_build(r)


func live_count() -> int:
	var n := 0
	for r in records:
		if r.node != null:
			n += 1
	return n


func _process(_delta: float) -> void:
	if player == null or records.is_empty():
		return
	var t0 := Time.get_ticks_usec()
	var p := player.global_position
	var built := false
	for k in mini(slice, records.size()):
		var r: Dictionary = records[_i]
		_i = (_i + 1) % records.size()
		var node = r.node
		if node != null and not is_instance_valid(node):
			r.node = null
			node = null
		if node == null:
			if not built and r.xf.origin.distance_to(p) < near and Time.get_ticks_usec() - t0 < budget_us:
				_build(r)
				built = true
		else:
			var n3 := node as Node3D
			if n3.global_position.distance_to(p) > far and not _in_use(n3):
				r.xf = n3.global_transform
				n3.queue_free()
				r.node = null
				_mm_dirty = true
	if _mm_dirty and impostor != null:
		_redraw_impostors()


func _build(r: Dictionary) -> void:
	var n: Node3D = (r.make as Callable).call()
	n.name = r.id
	add_child(n)
	n.global_transform = r.xf
	r.node = n
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
	for r in records:
		if r.node == null:
			xs.append((r.xf as Transform3D) * Transform3D(Basis(), impostor_lift))
	_mm.multimesh.instance_count = xs.size()
	for i in xs.size():
		_mm.multimesh.set_instance_transform(i, xs[i])
