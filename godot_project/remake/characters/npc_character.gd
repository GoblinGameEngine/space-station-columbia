extends Node3D
class_name NpcCharacter

## A generated person in the world: skeleton + skinned body mesh + materials, built from their
## traits (NpcTraits) by NpcBody / NpcColor.  Nothing here is stored per person: rebuild from the
## same traits and the same person comes out.
##
##   var v := NpcTraits.shared().person(world_seed, "B14823:2")
##   var npc := NpcCharacter.create(v)
##   add_child(npc)

const SHADER := preload("res://remake/characters/npc_toon.gdshader")

var traits: Dictionary
var params: Dictionary
var built: Dictionary
var skeleton: Skeleton3D
var body_mesh: MeshInstance3D


static func create(v: Dictionary, id := "") -> NpcCharacter:
	var n := NpcCharacter.new()
	n.name = "Npc_" + id.replace(":", "_") if id != "" else "Npc"
	n.traits = v
	n._build()
	return n


func _build() -> void:
	params = NpcBody.from_traits(traits)
	built = NpcBody.build(params)
	var J: Dictionary = built.joints
	skeleton = Skeleton3D.new()
	skeleton.name = "Skeleton"
	add_child(skeleton)
	var skin := Skin.new()
	for i in NpcBody.BONES.size():
		var bn: String = NpcBody.BONES[i]
		skeleton.add_bone(bn)
		var par: String = NpcBody.PARENT[bn]
		var local: Vector3 = J[bn] - (J[par] if par != "" else Vector3.ZERO)
		if par != "":
			skeleton.set_bone_parent(i, NpcBody.BONES.find(par))
		skeleton.set_bone_rest(i, Transform3D(Basis(), local))
		skin.add_bind(i, Transform3D(Basis(), -(J[bn] as Vector3)))
	skeleton.reset_bone_poses()
	body_mesh = MeshInstance3D.new()
	body_mesh.name = "Body"
	body_mesh.mesh = _skin_mesh()
	body_mesh.skin = skin
	skeleton.add_child(body_mesh)
	body_mesh.skeleton = NodePath("..")


func _skin_mesh() -> ArrayMesh:
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()
	var uv2s := PackedVector2Array()
	var bones := PackedInt32Array()
	var weights := PackedFloat32Array()
	var idx := PackedInt32Array()
	for part: NpcBody.Part in built.parts:
		var base := verts.size()
		verts.append_array(part.verts)
		normals.append_array(part.normals)
		uvs.append_array(part.uvs)
		uv2s.append_array(part.uv2s)
		bones.append_array(part.bones)
		weights.append_array(part.weights)
		var pi := part.indices
		for t in range(0, pi.size(), 3):                 # built counter-clockwise; Godot's front faces are clockwise
			idx.append_array([base + pi[t], base + pi[t + 2], base + pi[t + 1]])
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = normals
	arr[Mesh.ARRAY_TEX_UV] = uvs
	arr[Mesh.ARRAY_TEX_UV2] = uv2s
	arr[Mesh.ARRAY_BONES] = bones
	arr[Mesh.ARRAY_WEIGHTS] = weights
	arr[Mesh.ARRAY_INDEX] = idx
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	m.surface_set_material(0, _skin_material())
	return m


func _skin_material() -> ShaderMaterial:
	var mat := ShaderMaterial.new()
	mat.shader = SHADER
	var lit := NpcColor.skin(traits.get("skin", [0.3, 0.5]))
	_set_paint(mat, lit, true)
	var hair := NpcColor.hair(traits.get("hair_colour", [0.2, 0.5]), float(traits.get("hair_grey", 0.0)))
	mat.set_shader_parameter("eye_color", NpcColor.eyes(traits.get("eye_colour", [0.2, 0.2])))
	mat.set_shader_parameter("brow_color", hair.darkened(0.25))
	mat.set_shader_parameter("line_color", NpcColor.from_lab(NpcColor.to_lab(lit) * Vector3(0.28, 1.2, 1.0)))
	mat.set_shader_parameter("mouth_color", NpcColor.shade(lit, true).darkened(0.35))
	var f: Array = params.face
	mat.set_shader_parameter("eye_size", f[5])
	mat.set_shader_parameter("eye_spacing", f[6])
	mat.set_shader_parameter("mouth_width", f[7])
	var brow: String = traits.get("brow", "straight")
	mat.set_shader_parameter("brow_thick", {"thin": 0.1, "sparse": 0.2, "straight": 0.45, "arched": 0.4, "heavy": 0.8, "bushy": 1.0}.get(brow, 0.5))
	mat.set_shader_parameter("brow_arch", {"arched": 0.9, "straight": 0.1, "thin": 0.5}.get(brow, 0.35))
	var marks: Array = traits.get("face_marks", [])
	mat.set_shader_parameter("freckles", 1.0 if "freckles" in marks else 0.0)
	mat.set_shader_parameter("glasses", 1.0 if "glasses" in marks else 0.0)
	var age := float(traits.get("age", 30))
	mat.set_shader_parameter("age_lines", clampf((age - 45.0) / 30.0, 0.0, 1.0))
	mat.set_shader_parameter("blush", clampf(0.8 - age / 70.0, 0.1, 0.8))
	return mat


static func _set_paint(mat: ShaderMaterial, lit: Color, is_skin: bool) -> void:
	var sh := NpcColor.shade(lit, is_skin)
	var ll := lit.srgb_to_linear()
	var sl := sh.srgb_to_linear()
	mat.set_shader_parameter("lit_color", lit)
	mat.set_shader_parameter("shade_mul", Vector3(sl.r / maxf(ll.r, 1e-3), sl.g / maxf(ll.g, 1e-3), sl.b / maxf(ll.b, 1e-3)))
