extends Node3D
class_name NpcCharacter

## A generated person in the world: skeleton + skinned body, hair and clothes, built from their
## traits (NpcTraits) by NpcBody / NpcHair / NpcGarments / NpcColor.  Nothing is stored per person:
## rebuild from the same (seed, id) and the same person comes out.
##
##   var v := NpcTraits.shared().person(world_seed, "B14823:2")
##   var npc := NpcCharacter.create(v, "B14823:2", world_seed)
##   add_child(npc)
##   npc.dress("casual")          # change clothes at any time: only the garment meshes are rebuilt

const SHADER := preload("res://remake/characters/npc_toon.gdshader")
const PATTERN_ID := {"solid": 0, "stripes": 1, "pinstripe": 2, "check": 3, "tartan": 4, "dots": 5, "floral": 6,
	"knit": 7, "denim": 8, "pleats": 9, "weave": 10, "herring": 11}
const TUCKED := ["shirt", "shirt_short", "tunic_uniform", "blouse", "chef_jacket"]

var traits: Dictionary
var pid := ""
var world_seed := 0
var params: Dictionary
var built: Dictionary
var outfit: Array = []
var occasion := "work"
var skeleton: Skeleton3D
var body_mesh: MeshInstance3D
var clothes_mesh: MeshInstance3D
var _skin: Skin


static func create(v: Dictionary, id := "", seed := 0, p_occasion := "work") -> NpcCharacter:
	var n := NpcCharacter.new()
	n.name = "Npc_" + id.replace(":", "_") if id != "" else "Npc"
	n.traits = v
	n.pid = id
	n.world_seed = seed
	n.occasion = p_occasion
	n._build()
	return n


func _build() -> void:
	params = NpcBody.from_traits(traits)
	built = NpcBody.build(params)
	var J: Dictionary = built.joints
	skeleton = Skeleton3D.new()
	skeleton.name = "Skeleton"
	add_child(skeleton)
	_skin = Skin.new()
	for i in NpcBody.BONES.size():
		var bn: String = NpcBody.BONES[i]
		skeleton.add_bone(bn)
		var par: String = NpcBody.PARENT[bn]
		var local: Vector3 = J[bn] - (J[par] if par != "" else Vector3.ZERO)
		if par != "":
			skeleton.set_bone_parent(i, NpcBody.BONES.find(par))
		skeleton.set_bone_rest(i, Transform3D(Basis(), local))
		_skin.add_bind(i, Transform3D(Basis(), -(J[bn] as Vector3)))
	skeleton.reset_bone_poses()
	body_mesh = _instance("Body")
	clothes_mesh = _instance("Clothes")
	var m := ArrayMesh.new()
	_add_surface(m, built.parts, _skin_material())
	body_mesh.mesh = m
	dress(occasion)


func _instance(n: String) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.name = n
	mi.skin = _skin
	skeleton.add_child(mi)
	mi.skeleton = NodePath("..")
	return mi


func dress(p_occasion: String) -> void:
	## (Re)build clothes and hair for an occasion ("work", "casual" ...).  Cheap: the body mesh and
	## skeleton stay; only garment surfaces are made.
	occasion = p_occasion
	outfit = NpcGarments.outfit(traits, world_seed, pid, occasion)
	var m := ArrayMesh.new()
	var tucked := outfit.any(func(g): return g.slot == "top" and g.garment in TUCKED)
	var has_hat := outfit.any(func(g): return g.slot == "head")
	for g in outfit:
		var def: Dictionary = g.def.duplicate(true)
		var extra := 0.0
		match str(g.slot):
			"top":
				extra = 0.0 if tucked else 0.009
				if tucked and def.has("torso"):
					def.torso = [maxf(float(def.torso[0]), 2.7), def.torso[1]]
			"bottom":
				extra = 0.009 if tucked else 0.0
			"dress":
				extra = 0.004
			"over":
				extra = 0.01 + 0.005 * float(def.get("layer", 1))
		var parts := NpcGarments.build(def, built, extra)
		if parts.is_empty():
			continue
		_add_surface(m, parts, _fabric_material(g))
	var style := str(traits.get("hair_style", "crop"))
	var hair := NpcHair.build(_under_hat(style) if has_hat else style, built, NpcRng.for_trait(world_seed, pid, "hair"), has_hat)
	if not hair.is_empty():
		_add_surface(m, hair, _hair_material())
	clothes_mesh.mesh = m


static func _under_hat(style: String) -> String:
	## Under a hat only what shows below the brim matters: long styles keep their length, short
	## ones become a close crop so no volume pokes through the crown.
	return style if style in ["shoulder", "long_loose", "braids", "curly_long", "bald", "balding"] else "crop"


func _add_surface(m: ArrayMesh, parts: Array, mat: Material) -> void:
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()
	var uv2s := PackedVector2Array()
	var bones := PackedInt32Array()
	var weights := PackedFloat32Array()
	var idx := PackedInt32Array()
	for part: NpcBody.Part in parts:
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
	if verts.is_empty():
		return
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = normals
	arr[Mesh.ARRAY_TEX_UV] = uvs
	arr[Mesh.ARRAY_TEX_UV2] = uv2s
	arr[Mesh.ARRAY_BONES] = bones
	arr[Mesh.ARRAY_WEIGHTS] = weights
	arr[Mesh.ARRAY_INDEX] = idx
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	m.surface_set_material(m.get_surface_count() - 1, mat)


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


func _fabric_material(g: Dictionary) -> ShaderMaterial:
	var mat := ShaderMaterial.new()
	mat.shader = SHADER
	_set_paint(mat, g.colour, false)
	mat.set_shader_parameter("pattern", PATTERN_ID.get(g.pattern, 0))
	mat.set_shader_parameter("col2", g.colours[0])
	mat.set_shader_parameter("col3", g.colours[1])
	mat.set_shader_parameter("pat_scale", g.scale)
	return mat


func _hair_material() -> ShaderMaterial:
	var mat := ShaderMaterial.new()
	mat.shader = SHADER
	_set_paint(mat, NpcColor.hair(traits.get("hair_colour", [0.2, 0.5]), float(traits.get("hair_grey", 0.0))), false)
	return mat


static func _set_paint(mat: ShaderMaterial, lit: Color, is_skin: bool) -> void:
	var sh := NpcColor.shade(lit, is_skin)
	var ll := lit.srgb_to_linear()
	var sl := sh.srgb_to_linear()
	mat.set_shader_parameter("lit_color", lit)
	mat.set_shader_parameter("shade_mul", Vector3(sl.r / maxf(ll.r, 1e-3), sl.g / maxf(ll.g, 1e-3), sl.b / maxf(ll.b, 1e-3)))
