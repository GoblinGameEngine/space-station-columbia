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
		var f := pack.slice(off, off + n * 24).to_float32_array()
		var pos := PackedVector3Array()
		var nor := PackedVector3Array()
		pos.resize(n)
		nor.resize(n)
		for i in n:
			pos[i] = Vector3(f[i * 3], f[i * 3 + 1], f[i * 3 + 2])
			nor[i] = Vector3(f[n * 3 + i * 3], f[n * 3 + i * 3 + 1], f[n * 3 + i * 3 + 2])
		out[m] = [pos, nor]
	_mx.lock()
	_geo[cid] = out
	_mx.unlock()
	return out


static func material(style: String, name: String) -> StandardMaterial3D:
	## A style's material for the game (shared: callers duplicate what they change per vehicle, e.g. lamps).
	var key := style + "/" + name
	_mx.lock()
	var got = _palettes.get("_made_" + key)
	_mx.unlock()
	if got != null:
		return got
	var spec: Dictionary = palette(style).get(name, {})
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
	_mx.lock()
	_palettes["_made_" + key] = m
	_mx.unlock()
	return m
