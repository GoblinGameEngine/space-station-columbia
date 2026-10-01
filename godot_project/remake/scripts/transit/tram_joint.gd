extends Node3D
class_name TramJoint

## The articulation between two tram sections: a covered walkway people can cross while the tram
## runs or stands. Each section's end has a portal (TramSection's endwall) and a rubber flange; the
## joint strings an accordion bellows between the two flanges (rebuilt every tick, so it bends and
## stretches with the turn), lays a turntable floor plate across the gap, and walls the walkway in.
## Two pivots -- one at each portal -- and the turntable between: the sections steer for themselves
## (both their axles), the joint only follows.

const RINGS := 10
const AROUND := 28
const HALF_W := 1.18                 # the bellows' half width / height round the portal
const Z0 := 0.42
const Z1 := 2.86
const WALK_HW := 0.70                # the walkway's half width inside

var a: TramSection                   # ahead
var b: TramSection                   # behind
var _mesh := ArrayMesh.new()
var _mi := MeshInstance3D.new()
var _plate := MeshInstance3D.new()
var _body := AnimatableBody3D.new()
var _floor := CollisionShape3D.new()
var _wall_l := CollisionShape3D.new()
var _wall_r := CollisionShape3D.new()
var _roof := CollisionShape3D.new()
var _mat := StandardMaterial3D.new()


func setup(p_a: TramSection, p_b: TramSection) -> void:
	a = p_a
	b = p_b
	name = "Joint_%s_%s" % [a.name, b.name]
	_mat.albedo_color = Color(0.12, 0.12, 0.13)
	_mat.roughness = 0.9
	_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	_mi.mesh = _mesh
	_mi.top_level = true
	add_child(_mi)
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.78
	cyl.bottom_radius = 0.78
	cyl.height = 0.05
	_plate.mesh = cyl
	var pm := StandardMaterial3D.new()
	pm.albedo_color = Color(0.55, 0.56, 0.58)
	pm.metallic = 0.8
	pm.roughness = 0.35
	_plate.material_override = pm
	_plate.top_level = true
	add_child(_plate)
	_body.sync_to_physics = true
	_body.collision_layer = 1 | RemakeGroundVehicle.HULL_LAYER
	_body.collision_mask = 0
	_body.top_level = true
	add_child(_body)
	for cs in [_floor, _wall_l, _wall_r, _roof]:
		cs.shape = BoxShape3D.new()
		_body.add_child(cs)


func ends() -> Array:
	## The two portal frames: a's back end, b's front end (each looking forward).
	var fa := float(TramSection.load_spec().half_length)
	var ta := a.global_transform * Transform3D(Basis(), Vector3(0, 0, fa + 0.03))
	var tb := b.global_transform * Transform3D(Basis(), Vector3(0, 0, -fa - 0.03))
	return [ta, tb]


func update() -> void:
	var e := ends()
	var ta: Transform3D = e[0]
	var tb: Transform3D = e[1]
	var qa := ta.basis.get_rotation_quaternion()
	var qb := tb.basis.get_rotation_quaternion()
	# the bellows: rings from a's flange to b's, folds alternating in and out
	var rings: Array = []
	for r in RINGS + 1:
		var t := float(r) / RINGS
		var xf := Transform3D(Basis(qa.slerp(qb, t)), ta.origin.lerp(tb.origin, t))
		var k := 1.0 if r % 2 == 0 or r == RINGS else 0.94
		var ring := PackedVector3Array()
		for i in AROUND:
			var ang := TAU * i / AROUND
			var c := cos(ang)
			var s := sin(ang)
			var x := signf(c) * pow(absf(c), 0.25) * HALF_W * k
			var y := (Z0 + Z1) / 2 + signf(s) * pow(absf(s), 0.25) * (Z1 - Z0) / 2 * k
			ring.append(xf * Vector3(x, y, 0))
		rings.append(ring)
	var verts := PackedVector3Array()
	var norms := PackedVector3Array()
	for r in RINGS:
		var r0: PackedVector3Array = rings[r]
		var r1: PackedVector3Array = rings[r + 1]
		for i in AROUND:
			var i2 := (i + 1) % AROUND
			var p := [r0[i], r1[i], r1[i2], r0[i], r1[i2], r0[i2]]
			var n := ((r1[i] - r0[i]).cross(r0[i2] - r0[i])).normalized()
			for v in p:
				verts.append(v)
				norms.append(n)
	_mesh.clear_surfaces()
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = norms
	_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	_mesh.surface_set_material(0, _mat)
	# the floor plate and the walkway's walls and roof, at the middle frame
	var mid := Transform3D(Basis(qa.slerp(qb, 0.5)), ta.origin.lerp(tb.origin, 0.5))
	var floor_y := float(TramSection.load_spec().floor_y)
	var gap := ta.origin.distance_to(tb.origin) + 0.9
	_plate.global_transform = mid * Transform3D(Basis(), Vector3(0, floor_y - 0.03, 0))
	_body.global_transform = mid
	(_floor.shape as BoxShape3D).size = Vector3(WALK_HW * 2 + 0.2, 0.06, gap)
	_floor.position = Vector3(0, floor_y - 0.03, 0)
	for pair in [[_wall_l, -1.0], [_wall_r, 1.0]]:
		var cs := pair[0] as CollisionShape3D
		(cs.shape as BoxShape3D).size = Vector3(0.08, 2.2, gap)
		cs.position = Vector3(pair[1] * (WALK_HW + 0.04), floor_y + 1.1, 0)
	(_roof.shape as BoxShape3D).size = Vector3(WALK_HW * 2 + 0.2, 0.08, gap)
	_roof.position = Vector3(0, float(TramSection.load_spec().portal.head) + 0.04, 0)
