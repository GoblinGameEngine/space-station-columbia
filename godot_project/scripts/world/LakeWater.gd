extends MeshInstance3D

# Summit Lake's surface animation -- explicitly NOT a shader and NOT any
# kind of water physics/simulation (the request ruled that out): just a
# slow, continuous UV-offset scroll on the existing tinted ripple texture
# (see build_neighborhood.py's build_lake()/gen_textures.py's
# water_detail.png) so the lake reads as gently moving instead of a
# static painted plane. One mesh, one material property nudged once a
# frame -- there's no per-frame cost here worth worrying about.
#
# Attached at runtime via set_script() (see LakeSetup.gd) rather than
# being the mesh's own script from the start, since this mesh comes in
# through the Blender/glTF import with no script of its own.

const SCROLL_SPEED := Vector2(0.015, 0.008)

var _material: StandardMaterial3D
var _uv_offset := Vector2.ZERO

static var _drivers := {}             # material instance id -> the one node that scrolls it

func _ready() -> void:
	var mat := get_active_material(0)
	if mat is StandardMaterial3D:
		_material = mat
		# the water meshes share their material: one of them scrolls it (96 did, every frame)
		var d = _drivers.get(mat.get_instance_id())
		if d != null and is_instance_valid(d) and d != self:
			set_process(false)
		else:
			_drivers[mat.get_instance_id()] = self

func _exit_tree() -> void:
	if _material and _drivers.get(_material.get_instance_id()) == self:
		_drivers.erase(_material.get_instance_id())

func _process(delta: float) -> void:
	if _material == null:
		return
	_uv_offset += SCROLL_SPEED * delta
	_material.uv1_offset = Vector3(_uv_offset.x, _uv_offset.y, 0.0)
