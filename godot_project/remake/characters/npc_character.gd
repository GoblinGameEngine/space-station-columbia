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
	## Build and assemble in one go (tools; the main thread).
	return from_prepared(prepare(v, id, seed, p_occasion))


static func prepare(v: Dictionary, id := "", seed := 0, p_occasion := "work") -> Dictionary:
	## Everything but nodes and materials: body, outfit, garment and hair geometry as mesh arrays.
	## Thread-safe -- NpcPopulation runs this on the worker pool (traits must be computed first, on
	## the main thread: Expression isn't thread-safe).
	var params := NpcBody.from_traits(v)
	var built := NpcBody.build(params)
	var d := {"traits": v, "pid": id, "seed": seed, "occasion": p_occasion, "params": params, "built": built,
		"body": _arrays(built.parts)}
	d.merge(_clothes(v, id, seed, p_occasion, built), true)
	return d


static func from_prepared(d: Dictionary) -> NpcCharacter:
	var n := NpcCharacter.new()
	n.name = "Npc_" + str(d.pid).replace(":", "_") if d.pid != "" else "Npc"
	n.traits = d.traits
	n.pid = d.pid
	n.world_seed = d.seed
	n.occasion = d.occasion
	n.params = d.params
	n.built = d.built
	n._assemble(d)
	return n


func _assemble(d: Dictionary) -> void:
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
	_add_arrays(m, d.body, _skin_material())
	body_mesh.mesh = m
	_apply_clothes(d)


func _instance(n: String) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.name = n
	mi.skin = _skin
	skeleton.add_child(mi)
	mi.skeleton = NodePath("..")
	return mi


func dress(p_occasion: String) -> void:
	## Change clothes for an occasion ("work", "casual" ...) at any time: only garment and hair
	## surfaces are rebuilt; the body and skeleton stay.
	occasion = p_occasion
	_apply_clothes(_clothes(traits, pid, world_seed, occasion, built))


func _apply_clothes(d: Dictionary) -> void:
	outfit = d.outfit
	var m := ArrayMesh.new()
	for s in d.surfaces:
		_add_arrays(m, s.arrays, _fabric_material(s.g) if s.kind == "fabric" else _hair_material())
	clothes_mesh.mesh = m


static func _clothes(v: Dictionary, id: String, seed: int, p_occasion: String, built: Dictionary) -> Dictionary:
	## The outfit for an occasion and its geometry (thread-safe): {outfit, surfaces: [{kind, g, arrays}]}.
	var outfit := NpcGarments.outfit(v, seed, id, p_occasion)
	var surfaces := []
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
		if not parts.is_empty():
			surfaces.append({"kind": "fabric", "g": g, "arrays": _arrays(parts)})
	var style := str(v.get("hair_style", "crop"))
	var hair := NpcHair.build(_under_hat(style) if has_hat else style, built, NpcRng.for_trait(seed, id, "hair"), has_hat)
	if not hair.is_empty():
		surfaces.append({"kind": "hair", "g": {}, "arrays": _arrays(hair)})
	return {"outfit": outfit, "surfaces": surfaces}


static func _under_hat(style: String) -> String:
	## Under a hat only what shows below the brim matters: long styles keep their length, short
	## ones become a close crop so no volume pokes through the crown.
	return style if style in ["shoulder", "long_loose", "braids", "curly_long", "bald", "balding"] else "crop"


static func _arrays(parts: Array) -> Array:
	## Parts -> one surface's mesh arrays (or [] if empty).
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
		return []
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = normals
	arr[Mesh.ARRAY_TEX_UV] = uvs
	arr[Mesh.ARRAY_TEX_UV2] = uv2s
	arr[Mesh.ARRAY_BONES] = bones
	arr[Mesh.ARRAY_WEIGHTS] = weights
	arr[Mesh.ARRAY_INDEX] = idx
	return arr


static func _add_arrays(m: ArrayMesh, arr: Array, mat: Material) -> void:
	if arr.is_empty():
		return
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
