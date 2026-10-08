extends RefCounted
class_name Placement

## Every placed structure (remake/placement.json, remake/tools/placement.py), one packed copy for everyone.
##
## placement.json is ~18 MB, ~200 MB parsed, and the station, the people, the traffic, the occupancy, the transit, the
## menu and the terrain each parsed their own (the 1:1 station's 63,000 structures, 2026-10-08).  Here the structures
## are columns (placement.bin, baked by bake_world.gd pads; the JSON packed on first use without it): an entry is a
## Dictionary like the JSON's only when entry(i) is asked for.
##
##   Placement.count()            Placement.index(id) -> i or -1        Placement.entry(i) -> {id, kind, settlement, ...}
##   Placement.id(i) s(i) x(i) yaw(i) kind(i) settlement(i) model(i)    Placement.entries() -> every entry (transient!)

const SRC := "res://remake/placement.json"
const BIN := "res://remake/placement.bin"

static var _d: Dictionary = {}
static var _ix: Dictionary = {}              # id -> index
static var _mx := Mutex.new()


static func _stamp() -> String:
	return BakedMeshes.fingerprint([SRC], 1)


static func load_all() -> void:
	_mx.lock()
	if _d.is_empty():
		if FileAccess.file_exists(BIN):
			var f := FileAccess.open(BIN, FileAccess.READ)
			var d = f.get_var()
			f.close()
			if typeof(d) == TYPE_DICTIONARY and str(d.get("_stamp", "")) == _stamp():
				_d = d
		if _d.is_empty() and FileAccess.file_exists(SRC):
			_d = _compact((JSON.parse_string(FileAccess.get_file_as_string(SRC)) as Dictionary).structures)
		var ids: PackedStringArray = _d.get("id", PackedStringArray())
		for i in ids.size():
			_ix[ids[i]] = i
	_mx.unlock()


static func bake_bin() -> int:
	var d := _compact((JSON.parse_string(FileAccess.get_file_as_string(SRC)) as Dictionary).structures)
	d["_stamp"] = _stamp()
	var f := FileAccess.open(BIN, FileAccess.WRITE)
	f.store_var(d)
	f.close()
	return (d.id as PackedStringArray).size()


static func _compact(pl: Array) -> Dictionary:
	var strs := PackedStringArray([""])
	var sidx := {"": 0}
	var intern := func(v) -> int:
		var k := "" if v == null else str(v)
		if not sidx.has(k):
			sidx[k] = strs.size()
			strs.append(k)
		return sidx[k]
	var c := {"id": PackedStringArray(), "kind": PackedInt32Array(), "set": PackedInt32Array(), "model": PackedInt32Array(),
		"s": PackedFloat64Array(), "x": PackedFloat64Array(), "yaw": PackedFloat32Array(), "mn": PackedFloat32Array(),
		"mx": PackedFloat32Array(), "fmn": PackedFloat32Array(), "fmx": PackedFloat32Array(), "hh": PackedInt32Array(),
		"deck": PackedFloat32Array(), "ow": PackedByteArray(), "has_set": PackedByteArray()}
	for e in pl:
		c.id.append(str(e.id))
		c.kind.append(intern.call(e.kind))
		c.set.append(intern.call(e.get("settlement")))
		c.has_set.append(0 if e.get("settlement") == null else 1)
		c.model.append(intern.call(e.get("model", e.id)))
		c.s.append(float(e.s))
		c.x.append(float(e.x))
		c.yaw.append(float(e.yaw))
		for k in 3:
			c.mn.append(float(e.min[k]))
			c.mx.append(float(e.max[k]))
		for k in 2:
			c.fmn.append(float(e.fmin[k]))
			c.fmx.append(float(e.fmax[k]))
		c.hh.append(int(e.households) if e.has("households") else -1)
		var dk: Array = e.get("deck", [NAN, NAN])
		c.deck.append(float(dk[0]))
		c.deck.append(float(dk[1]))
		c.ow.append(1 if e.get("over_water", false) else 0)
	c["str"] = strs
	return c


static func count() -> int:
	load_all()
	return (_d.get("id", PackedStringArray()) as PackedStringArray).size()


static func index(id: String) -> int:
	load_all()
	return _ix.get(id, -1)


static func id(i: int) -> String:
	return _d.id[i]


static func s(i: int) -> float:
	return _d.s[i]


static func x(i: int) -> float:
	return _d.x[i]


static func yaw(i: int) -> float:
	return _d.yaw[i]


static func kind(i: int) -> String:
	return _d.str[_d.kind[i]]


static func settlement(i: int) -> String:
	## "" for none (farms, crossings: the JSON's null)
	return _d.str[_d.set[i]]


static func model(i: int) -> String:
	return _d.str[_d.model[i]]


static var _ecache := {}                     # index -> entry (two generations of ECACHE_MAX)
static var _ecache_old := {}
const ECACHE_MAX := 4096


static func entry(i: int) -> Dictionary:
	## the structure as placement.json has it (kept a while: the scans round the player ask for the same ones)
	var got = _ecache.get(i)
	if got != null:
		return got
	got = _ecache_old.get(i)
	if got == null:
		got = _make_entry(i)
	_mx.lock()
	if _ecache.size() >= ECACHE_MAX:
		_ecache_old = _ecache
		_ecache = {}
	_ecache[i] = got
	_mx.unlock()
	return got


static func _make_entry(i: int) -> Dictionary:
	load_all()
	var e := {"id": _d.id[i], "kind": kind(i), "settlement": settlement(i) if _d.has_set[i] == 1 else null,
		"glb": "res://remake/buildings/%s.glb" % model(i), "model": model(i), "s": _d.s[i], "x": _d.x[i], "yaw": _d.yaw[i],
		"min": [_d.mn[i * 3], _d.mn[i * 3 + 1], _d.mn[i * 3 + 2]], "max": [_d.mx[i * 3], _d.mx[i * 3 + 1], _d.mx[i * 3 + 2]],
		"fmin": [_d.fmn[i * 2], _d.fmn[i * 2 + 1]], "fmax": [_d.fmx[i * 2], _d.fmx[i * 2 + 1]]}
	if _d.hh[i] >= 0:
		e["households"] = _d.hh[i]
	if not is_nan(_d.deck[i * 2]):
		e["deck"] = [_d.deck[i * 2], _d.deck[i * 2 + 1]]
	if _d.ow[i] == 1:
		e["over_water"] = true
	return e


static func fmin(i: int) -> Vector2:
	return Vector2(_d.fmn[i * 2], _d.fmn[i * 2 + 1])


static func fmax(i: int) -> Vector2:
	return Vector2(_d.fmx[i * 2], _d.fmx[i * 2 + 1])


static func entry_of(id: String) -> Dictionary:
	var i := index(id)
	return {} if i < 0 else entry(i)


static func entries() -> Array:
	## every entry as a Dictionary (transient: for a pass over them, not to keep)
	load_all()
	var out := []
	for i in count():
		out.append(_make_entry(i))                   # (not through the cache: a pass over all of them)
	return out
