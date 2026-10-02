extends Node3D
class_name TramJoint

## The articulation between two tram sections: a covered walkway people can cross while the tram
## runs or stands. Multi-point, as real low-floor trams are: an articulation ring (a short module on
## the turntable, with the walkway through it) between two accordion bellows, one to each section's
## portal flange. The ring sits midway and turns half the bend, so each bellows takes half of it -- one
## bellows alone could not: at a 14 m turning loop the sections meet at ~40 degrees and their inside
## corners passed through each other (the user, 2026-10-01: "missing the accordion section necessary
## for the multi point articulation"). The sections steer for themselves (both their axles); the joint
## only follows.

const RINGS := 8                     # folds per bellows
const AROUND := 28
const HALF_W := 1.18                 # the bellows' half width / height round the portal
const Z0 := 0.42
const Z1 := 2.86
const WALK_HW := 0.70                # the walkway's half width inside
const RING_HALF := 0.20              # the articulation ring's half length (along the walkway)
const PORTAL_HW := 0.66              # its opening (the walkway through it)
const PORTAL_Z0 := 0.55
const PORTAL_Z1 := 2.64

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
var _ring_mat := StandardMaterial3D.new()
var _dirty := true                   # the sections moved since the bellows was drawn
var _built := false
var _rel := Transform3D()             # b's portal in a's frame, when the bellows was last built
var _ring := PackedVector3Array()     # the bellows' cross-section (unit folds)


func setup(p_a: TramSection, p_b: TramSection) -> void:
	a = p_a
	b = p_b
	name = "Joint_%s_%s" % [a.name, b.name]
	_mat.albedo_color = Color(0.12, 0.12, 0.13)
	_mat.roughness = 0.9
	_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	_ring_mat.albedo_color = Color(0.86, 0.84, 0.76)
	_ring_mat.roughness = 0.5
	_ring_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	_mi.mesh = _mesh
	_mi.top_level = true
	_mi.visibility_range_end = TramSection.LOD_FAR      # (seen as far as the sections are: no gap between them from afar)
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
	_plate.visibility_range_end = 45.0
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
	## Each physics tick: the walkway's floor, walls and roof follow the sections; the bellows is
	## redrawn on the next frame, if anyone is near enough to see it (_process).
	var e := ends()
	var ta: Transform3D = e[0]
	var tb: Transform3D = e[1]
	var qa := ta.basis.get_rotation_quaternion()
	var qb := tb.basis.get_rotation_quaternion()
	_dirty = true
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


func _process(_delta: float) -> void:
	if not _dirty:
		return
	var cam := get_viewport().get_camera_3d()
	if cam == null or cam.global_position.distance_to(a.global_position) > _mi.visibility_range_end + 10.0:
		_mi.visible = false                              # (the sections' far models close their ends)
		return
	_mi.visible = true
	_dirty = false
	_bellows()


func _bellows() -> void:
	## Drawn in the front portal's frame: its shape depends only on how the two portals sit to each
	## other, so on straight track (or a steady curve) it's only moved, not rebuilt.
	var e := ends()
	var ta: Transform3D = e[0]
	var tb: Transform3D = e[1]
	_mi.global_transform = ta
	var rel := ta.affine_inverse() * tb
	var q_rel := rel.basis.get_rotation_quaternion()
	if _built and rel.origin.distance_to(_rel.origin) < 0.01 and q_rel.angle_to(_rel.basis.get_rotation_quaternion()) < 0.003:
		return
	_built = true
	_rel = rel
	if _ring.is_empty():
		for i in AROUND:
			var ang := TAU * i / AROUND
			var c := cos(ang)
			var sn := sin(ang)
			_ring.append(Vector3(signf(c) * pow(absf(c), 0.25) * HALF_W, signf(sn) * pow(absf(sn), 0.25) * (Z1 - Z0) / 2, 0.0))
	# the articulation ring: midway, turned half the bend
	var m := Transform3D(Basis(Quaternion.IDENTITY.slerp(q_rel, 0.5)), rel.origin * 0.5)
	var m_front := m * Transform3D(Basis(), Vector3(0, 0, -RING_HALF))
	var m_back := m * Transform3D(Basis(), Vector3(0, 0, RING_HALF))
	var verts := PackedVector3Array()
	var norms := PackedVector3Array()
	_fold(Transform3D.IDENTITY, m_front, verts, norms)
	_fold(m_back, rel, verts, norms)
	_mesh.clear_surfaces()
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = norms
	_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	_mesh.surface_set_material(0, _mat)
	var rv := PackedVector3Array()
	var rn := PackedVector3Array()
	_collar(m_front, m_back, rv, rn)
	var arr2 := []
	arr2.resize(Mesh.ARRAY_MAX)
	arr2[Mesh.ARRAY_VERTEX] = rv
	arr2[Mesh.ARRAY_NORMAL] = rn
	_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr2)
	_mesh.surface_set_material(1, _ring_mat)


func _fold(f0: Transform3D, f1: Transform3D, verts: PackedVector3Array, norms: PackedVector3Array) -> void:
	## One accordion bellows from frame f0 to f1 (both in the joint's drawing frame), folds alternating.
	var q0 := f0.basis.get_rotation_quaternion()
	var q1 := f1.basis.get_rotation_quaternion()
	var rings: Array = []
	for r in RINGS + 1:
		var t := float(r) / RINGS
		var xf := Transform3D(Basis(q0.slerp(q1, t)), f0.origin.lerp(f1.origin, t))
		var k := 1.0 if r % 2 == 0 or r == RINGS else 0.94
		var ring := PackedVector3Array()
		ring.resize(AROUND)
		for i in AROUND:
			ring[i] = xf * Vector3(_ring[i].x * k, (Z0 + Z1) / 2 + _ring[i].y * k, 0.0)
		rings.append(ring)
	for r in RINGS:
		var r0: PackedVector3Array = rings[r]
		var r1: PackedVector3Array = rings[r + 1]
		for i in AROUND:
			var i2 := (i + 1) % AROUND
			var n := ((r1[i] - r0[i]).cross(r0[i2] - r0[i])).normalized()
			for v in [r0[i], r1[i], r1[i2], r0[i], r1[i2], r0[i2]]:
				verts.append(v)
				norms.append(n)


func _collar(f0: Transform3D, f1: Transform3D, verts: PackedVector3Array, norms: PackedVector3Array) -> void:
	## The articulation ring: a short collar the bellows' size outside, the walkway's portal through it.
	var outer := PackedVector3Array()
	for i in AROUND:
		outer.append(Vector3(_ring[i].x * 1.02, (Z0 + Z1) / 2 + _ring[i].y * 1.02, 0.0))
	var inner: Array = []                                # the portal opening, sampled at the same angles
	for i in AROUND:
		var d := Vector2(_ring[i].x, _ring[i].y).normalized()
		var hx := PORTAL_HW
		var hy := (PORTAL_Z1 - PORTAL_Z0) / 2.0
		var t := minf(hx / maxf(absf(d.x), 1e-6), hy / maxf(absf(d.y), 1e-6))
		inner.append(Vector3(d.x * t, (PORTAL_Z0 + PORTAL_Z1) / 2.0 + d.y * t, 0.0))
	var faces := [[f0, -1.0], [f1, 1.0]]
	for fc in faces:
		var xf: Transform3D = fc[0]
		var n: Vector3 = xf.basis * Vector3(0, 0, fc[1])
		for i in AROUND:
			var i2 := (i + 1) % AROUND
			for v in [xf * outer[i], xf * outer[i2], xf * (inner[i2] as Vector3), xf * outer[i], xf * (inner[i2] as Vector3), xf * (inner[i] as Vector3)]:
				verts.append(v)
				norms.append(n)
	for i in AROUND:                                     # its outside band and its tunnel
		var i2 := (i + 1) % AROUND
		for band in [[outer[i], outer[i2], 1.0], [inner[i] as Vector3, inner[i2] as Vector3, -1.0]]:
			var p0: Vector3 = band[0]
			var p1: Vector3 = band[1]
			var q := [f0 * p0, f1 * p0, f1 * p1, f0 * p0, f1 * p1, f0 * p1]
			var n: Vector3 = ((q[1] as Vector3) - (q[0] as Vector3)).cross((q[2] as Vector3) - (q[0] as Vector3)).normalized() * float(band[2])
			for v in q:
				verts.append(v)
				norms.append(n)
