extends RefCounted
class_name NpcProps

## Hand props for authored clips (npc_clips.json "props"): small procedural meshes on a PropL/PropR
## bone, in that bone's rest frame -- the hand hanging down (-y), the palm facing in, the thumb
## forward (-z).  A held handle runs along z through the fist; the working end of a tool is at +z
## (the little-finger side, down when the thumb is up).  Sizes are fractions of height T, so a
## child's cup is a child's cup.

const TWO_HANDED := ["broom", "hoe"]   # aimed from the holding hand through the other each frame
const COLORS := {"wood": Color("#8a6040"), "dark": Color("#3c3a3a"), "clay": Color("#c9b69a"),
	"paper": Color("#ece6d4"), "metal": Color("#9aa0a4"), "straw": Color("#c8a85a"),
	"apple": Color("#b8412e"), "screen": Color("#2c4a5a")}


static func make(kind: String, T: float, side: String) -> Node3D:
	var root := Node3D.new()
	root.name = "Prop_" + kind
	var s := T / 1.7                                   # built at an adult's scale, then fitted
	match kind:
		"cup":
			_part(root, _cyl(0.04, 0.035, 0.09), "clay", Vector3(0, 0, -0.01), Vector3(-90, 0, 0))
		"apple":
			_part(root, _sphere(0.04), "apple", Vector3(0, -0.01, 0))
		"paper":
			_part(root, _box(0.004, 0.3, 0.22), "paper", Vector3(0, -0.1, 0.03))
		"pda":
			_part(root, _box(0.012, 0.13, 0.075), "dark", Vector3(0, -0.02, 0))
			_part(root, _box(0.002, 0.1, 0.06), "screen", Vector3(-0.007, -0.02, 0))
		"spoon":
			# held like a pencil: down out of the fist, the bowl in the pot
			_part(root, _cyl(0.007, 0.007, 0.32), "wood", Vector3(0, -0.1, 0))
			_part(root, _sphere(0.025), "wood", Vector3(0, -0.26, 0))
		"hammer":
			_part(root, _cyl(0.013, 0.013, 0.3), "wood", Vector3(0, 0, -0.08), Vector3(90, 0, 0))
			_part(root, _box(0.035, 0.12, 0.035), "metal", Vector3(0, 0, -0.22))
		"broom":
			_part(root, _cyl(0.013, 0.013, 1.2), "wood", Vector3(0, 0, 0.35), Vector3(90, 0, 0))
			_part(root, _cyl(0.11, 0.03, 0.3), "straw", Vector3(0, 0, 1.05), Vector3(90, 0, 0))
		"hoe":
			_part(root, _cyl(0.014, 0.014, 1.25), "wood", Vector3(0, 0, 0.5), Vector3(90, 0, 0))
			_part(root, _box(0.18, 0.12, 0.01), "metal", Vector3(0, -0.05, 1.1), Vector3(-30, 0, 0))
		_:
			push_warning("NpcProps: no prop '%s'" % kind)
	root.scale = Vector3.ONE * s
	if side == "L":
		root.scale.x = -root.scale.x
	return root


static func _part(root: Node3D, mesh: Mesh, col: String, pos: Vector3, rot := Vector3.ZERO) -> void:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	var m := StandardMaterial3D.new()
	m.albedo_color = COLORS[col]
	m.roughness = 0.9
	mi.material_override = m
	mi.position = pos
	mi.rotation_degrees = rot
	root.add_child(mi)


static func _cyl(top: float, bottom: float, h: float) -> CylinderMesh:
	var c := CylinderMesh.new()
	c.top_radius = top
	c.bottom_radius = bottom
	c.height = h
	c.radial_segments = 12
	c.rings = 1
	return c


static func _sphere(r: float) -> SphereMesh:
	var sp := SphereMesh.new()
	sp.radius = r
	sp.height = r * 2.0
	sp.radial_segments = 12
	sp.rings = 6
	return sp


static func _box(x: float, y: float, z: float) -> BoxMesh:
	var b := BoxMesh.new()
	b.size = Vector3(x, y, z)
	return b
