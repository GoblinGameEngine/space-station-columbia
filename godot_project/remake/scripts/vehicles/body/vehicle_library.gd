extends RefCounted
class_name VehicleLibrary

## The vehicle component libraries (research/vehicles/MODULAR_VEHICLES.md): each class standard's
## components, from every maker's style, read from remake/vehicles/components/<standard>/<style>.catalog.json
## and .pack (written by remake/blender/kit/components.py). Thread-safe reads (the assembler binds bodies on
## worker threads at load).

const ROOT := "res://remake/vehicles/components/"

static var _mx := Mutex.new()
static var _catalogs := {}            # standard -> {component id -> entry (with "pack" path)}
static var _palettes := {}            # "standard/style" -> {material name -> spec} (a maker's tram and car differ)
static var _packs := {}               # pack path -> PackedByteArray
static var _geo := {}                 # component id -> {material: [PackedVector3Array positions, normals]}
static var _standards := {}


static func standard(std_id: String) -> Dictionary:
	_mx.lock()
	if not _standards.has(std_id):
		var d = JSON.parse_string(FileAccess.get_file_as_string("res://remake/vehicles/standards/%s.json" % std_id))
		_standards[std_id] = d if d is Dictionary else {}
	var out: Dictionary = _standards[std_id]
	_mx.unlock()
	return out


static func catalog(std_id: String) -> Dictionary:
	## Every component built to this standard, whoever made it.
	_mx.lock()
	if not _catalogs.has(std_id):
		var all := {}
		var dir := DirAccess.open(ROOT + std_id)
		if dir:
			for f in dir.get_files():
				if not f.ends_with(".catalog.json"):
					continue
				var c = JSON.parse_string(FileAccess.get_file_as_string(ROOT + std_id + "/" + f))
				if not c is Dictionary:
					continue
				_palettes[std_id + "/" + str(c.style)] = c.palette
				for id in c.components:
					var e: Dictionary = c.components[id]
					e["pack"] = c.pack
					all[id] = e
		_catalogs[std_id] = all
	var out: Dictionary = _catalogs[std_id]
	_mx.unlock()
	return out


static func palette(style: String) -> Dictionary:
	## style: "standard/style", e.g. "SW180/carrow"
	_mx.lock()
	var out: Dictionary = _palettes.get(style, {})
	_mx.unlock()
	return out


static var _stamp := {}                # standard -> the newest modified time of its catalogs and packs when loaded


static func refresh(std_id: String) -> void:
	## A rebuilt library (its catalogs or packs newer than what was loaded) is read again -- else a body built after a
	## rebuild asks for components (new shapes, new ids) the cached catalog has never heard of, and draws no panels.
	var newest := 0
	var dir := DirAccess.open(ROOT + std_id)
	if dir == null:
		return
	for f in dir.get_files():
		if f.ends_with(".catalog.json") or f.ends_with(".pack"):
			newest = maxi(newest, FileAccess.get_modified_time(ROOT + std_id + "/" + f))
	_mx.lock()
	var was: int = _stamp.get(std_id, -1)
	if was != -1 and newest != was:
		_catalogs.erase(std_id)
		_standards.erase(std_id)
		for k in _packs.keys():
			if str(k).begins_with(ROOT + std_id + "/"):
				_packs.erase(k)
		for k in _geo.keys():
			if str(k).begins_with(std_id + "."):
				_geo.erase(k)
	_stamp[std_id] = newest
	_mx.unlock()


static func compatible(std_id: String, interface: String) -> Array:
	## The components that fit this interface (any style): what can be swapped in.
	var out: Array = []
	for id in catalog(std_id):
		if str(catalog(std_id)[id].interface) == interface:
			out.append(id)
	return out


static func geometry(std_id: String, cid: String) -> Dictionary:
	## {material: [positions, normals]} of a component, in its slot's frame.
	_mx.lock()
	var got = _geo.get(cid)
	_mx.unlock()
	if got != null:
		return got
	var e: Dictionary = catalog(std_id).get(cid, {})
	if e.is_empty():
		return {}
	_mx.lock()
	if not _packs.has(e.pack):
		_packs[e.pack] = FileAccess.get_file_as_bytes(str(e.pack))
	var pack: PackedByteArray = _packs[e.pack]
	_mx.unlock()
	var out := {}
	for m in e.mats:
		var off := int(e.mats[m][0])
		var n := int(e.mats[m][1])
		var has_wear := bool(e.get("wear", false))         # (packs since 2026-10-05: each vertex's edge wear after the normals)
		var f := pack.slice(off, off + n * (28 if has_wear else 24)).to_float32_array()
		var pos := PackedVector3Array()
		var nor := PackedVector3Array()
		var wr := PackedFloat32Array()
		pos.resize(n)
		nor.resize(n)
		for i in n:
			pos[i] = Vector3(f[i * 3], f[i * 3 + 1], f[i * 3 + 2])
			nor[i] = Vector3(f[n * 3 + i * 3], f[n * 3 + i * 3 + 1], f[n * 3 + i * 3 + 2])
		if has_wear:
			wr = f.slice(n * 6, n * 7)
		out[m] = [pos, nor, wr]
	_mx.lock()
	_geo[cid] = out
	_mx.unlock()
	return out


# the generic surfaces (tools/assets/surfaces.py; research/vehicles/TEXTURES.md): which one each palette material wears, and
# its tile (m): grey tileable maps, tinted by the material's colour, projected in the vehicle's own frame (object-space
# triplanar: no UVs, and the texture rides with the vehicle)
const SURFACE := {"paint": ["paint", 0.6], "paint2": ["paint", 0.6], "livery1": ["paint", 0.6], "livery2": ["paint", 0.6],
	"black": ["plastic", 0.25], "dash": ["plastic", 0.25], "tub": ["plastic", 0.3], "chrome": ["brushed", 0.4],
	"frame_tube": ["brushed", 0.5], "rubber": ["rubber", 0.25], "seat": ["fabric", 0.15], "headliner": ["fabric", 0.2],
	"carpet": ["carpet", 0.3], "lining": ["vinyl", 0.3], "wood": ["wood", 0.8], "canvas1": ["canvas", 2.0], "canvas2": ["canvas", 2.0]}
const SURFACE_DIR := "res://remake/vehicles/surfaces/"
static var _surf_tex := {}


static func _surface(m: StandardMaterial3D, name: String) -> void:
	if not SURFACE.has(name):
		return
	var sname := str(SURFACE[name][0])
	if not _surf_tex.has(sname):
		var maps := {}
		for k in ["albedo", "normal", "rough"]:
			var path := SURFACE_DIR + "%s_%s.png" % [sname, k]
			maps[k] = load(path) if ResourceLoader.exists(path) else null
		_surf_tex[sname] = maps
	var t: Dictionary = _surf_tex[sname]
	if t.albedo == null:
		return
	m.albedo_texture = t.albedo
	# (no normal maps: the toon outline finds edges in the normals, and a surface's fine bumps came out as black speckle
	#  over every panel -- the albedo and roughness carry the surface; the normal maps stay in the set for later)
	if t.rough:
		m.roughness_texture = t.rough
		m.roughness_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_RED
	m.uv1_triplanar = true
	m.uv1_world_triplanar = false
	m.uv1_triplanar_sharpness = 4.0
	m.uv1_scale = Vector3.ONE / float(SURFACE[name][1])
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC


const SURFACE_SHADER := "res://remake/shaders/vehicle_surface.gdshader"
const PAINTED := ["paint", "paint2", "livery1", "livery2", "frame_tube"]   # (these wear to primer and metal; the rest scuff)
const INDOOR := ["seat", "headliner", "carpet", "lining", "dash"]          # (no road dirt in the cabin)
static var _shader: Shader


static func material(style: String, name: String) -> Material:
	## A style's material for the game (shared: callers duplicate what they change per vehicle, e.g. lamps). A surfaced
	## one is the vehicle surface shader (tint, the generic surface, dirt and wear); glass, lamps, screens: standard.
	var key := style + "/" + name
	_mx.lock()
	var got = _palettes.get("_made_" + key)
	_mx.unlock()
	if got != null:
		return got
	var spec: Dictionary = palette(style).get(name, {})
	if SURFACE.has(name) and spec.get("emit") == null and float(spec.get("alpha", 1.0)) >= 1.0 and ResourceLoader.exists(SURFACE_SHADER):
		var sm := _surface_material(name, spec)
		if sm:
			_mx.lock()
			_palettes["_made_" + key] = sm
			_mx.unlock()
			return sm
	return _standard(key, name, spec)


static func _surface_material(name: String, spec: Dictionary) -> ShaderMaterial:
	var sname := str(SURFACE[name][0])
	if not _surf_tex.has(sname):
		var maps := {}
		for k in ["albedo", "normal", "rough"]:
			var path := SURFACE_DIR + "%s_%s.png" % [sname, k]
			maps[k] = load(path) if ResourceLoader.exists(path) else null
		_surf_tex[sname] = maps
	if not _surf_tex.has("_grime"):
		_surf_tex["_grime"] = load(SURFACE_DIR + "grime_mask.png") if ResourceLoader.exists(SURFACE_DIR + "grime_mask.png") else null
	var t: Dictionary = _surf_tex[sname]
	if t.albedo == null:
		return null
	if _shader == null:
		_shader = load(SURFACE_SHADER)
	var m := ShaderMaterial.new()
	m.resource_name = name
	m.shader = _shader
	if name == "frame_tube":
		m.set_shader_parameter("tint", Color(0.28, 0.3, 0.32))
		m.set_shader_parameter("roughness", 0.45)
		m.set_shader_parameter("metallic", 0.7)
	else:
		var a: Array = spec.get("albedo", [0.8, 0.8, 0.8])
		m.set_shader_parameter("tint", Color(a[0], a[1], a[2]))
		m.set_shader_parameter("roughness", float(spec.get("rough", 0.5)))
		m.set_shader_parameter("metallic", float(spec.get("metal", 0.0)))
	m.set_shader_parameter("surface_albedo", t.albedo)
	m.set_shader_parameter("surface_rough", t.rough)
	m.set_shader_parameter("grime_mask", _surf_tex["_grime"])
	m.set_shader_parameter("tile", float(SURFACE[name][1]))
	m.set_shader_parameter("painted", name in PAINTED)
	m.set_shader_parameter("dirt_height", 0.0 if name in INDOOR else 0.9)
	return m


static func _standard(key: String, name: String, spec: Dictionary) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.resource_name = name
	m.cull_mode = BaseMaterial3D.CULL_DISABLED          # (panels are seen from both sides: inside and out)
	if name == "frame_tube":
		m.albedo_color = Color(0.28, 0.3, 0.32)
		m.metallic = 0.7
		m.roughness = 0.45
	elif not spec.is_empty():
		var a: Array = spec.albedo
		m.albedo_color = Color(a[0], a[1], a[2], float(spec.get("alpha", 1.0)))
		m.roughness = float(spec.rough)
		m.metallic = float(spec.metal)
		if spec.get("emit") != null:
			var e: Array = spec.emit
			m.emission_enabled = true
			m.emission = Color(e[0], e[1], e[2])
			m.emission_energy_multiplier = float(spec.emit_strength)
		if float(spec.get("alpha", 1.0)) < 1.0:
			m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			m.cull_mode = BaseMaterial3D.CULL_DISABLED
			m.metallic_specular = 0.9
	if not name.begins_with("lamp_") and name != "lcd" and float(spec.get("alpha", 1.0)) >= 1.0:
		_surface(m, name)
	_mx.lock()
	_palettes["_made_" + key] = m
	_mx.unlock()
	return m
