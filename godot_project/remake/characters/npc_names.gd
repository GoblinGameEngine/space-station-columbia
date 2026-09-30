extends RefCounted
class_name NpcNames

## Names from the game bible (research/bible/02_names.md; godot_project/remake/bible/names.json).
## A household's surname is drawn from the 2752 surname frequencies, weighted by its town's
## heritage leanings and the great families' strongholds there (lineages.json, settlements.json).
## A person's given name comes from the pools mixed for their birth cohort (born = 2752 - age),
## with their family's heritage pool raised. Everything is a pure function of (seed, ids).
##
##   NpcNames.surname(seed, "HF-012#0", "Harrow Falls")  -> {surname, heritage, lineage}
##   NpcNames.given(seed, pid, "F", 34, "hispanic")      -> "Ximena"

const NAMES := "res://remake/bible/names.json"
const LINEAGES := "res://remake/bible/lineages.json"
const SETTLEMENTS := "res://remake/bible/settlements.json"
const PRESENT_AD := 2752
const TOP_SURNAMES := 4000                         # the long tail beyond this is rare enough to skip
# heritage labels (surnames) -> given-name heritage pool
const HERITAGE_POOL := {"hispanic": "heritage_hispanic", "francophone": "heritage_francophone", "black": "heritage_black",
	"black_anglo": "heritage_black_anglo", "arab": "heritage_arab", "south_asian": "heritage_south_asian", "east_asian": "heritage_east_asian",
	"se_asian": "heritage_se_asian", "african": "heritage_african", "indigenous": "heritage_indigenous"}

static var _d: Dictionary
static var _lineage_of: Dictionary                 # surname (lower) -> lineage record
static var _town: Dictionary                       # test-town name -> bible settlement
static var _cum_surname: Dictionary                # town -> [PackedFloat64Array cumulative, Array rows]
static var _cum_pool: Dictionary                   # "pool|sex" -> [PackedFloat64Array, PackedStringArray]
static var _mutex := Mutex.new()


static func data() -> Dictionary:
	_mutex.lock()
	if _d.is_empty():
		_d = JSON.parse_string(FileAccess.get_file_as_string(NAMES))
		for l in (JSON.parse_string(FileAccess.get_file_as_string(LINEAGES)) as Dictionary).lineages:
			_lineage_of[str(l.get("key", str(l.surname).to_lower()))] = l
			_lineage_of[str(l.surname).to_lower()] = l
		for s in (JSON.parse_string(FileAccess.get_file_as_string(SETTLEMENTS)) as Dictionary).settlements:
			if s.test_town != null:
				_town[str(s.test_town)] = s
	_mutex.unlock()
	return _d


static func settlement(test_town: Variant) -> Dictionary:
	data()
	return _town.get(str(test_town), {})


static func lineage(surname_: String) -> Dictionary:
	data()
	var parts := surname_.split("-")
	return _lineage_of.get(parts[0].to_lower(), {}) if parts.size() > 0 else {}


static func _pick_cum(cum: PackedFloat64Array, r: float) -> int:
	var x := r * cum[cum.size() - 1]
	var lo := 0
	var hi := cum.size() - 1
	while lo < hi:
		var mid := (lo + hi) >> 1
		if cum[mid] < x:
			lo = mid + 1
		else:
			hi = mid
	return lo


static func _surname_table(town: String) -> Array:
	_mutex.lock()
	if not _cum_surname.has(town):
		var d := _d
		var st: Dictionary = _town.get(town, {})
		var lean: Dictionary = st.get("heritage_lean", {})
		var sid: String = st.get("id", "")
		var cum := PackedFloat64Array()
		var rows := []
		var acc := 0.0
		var n := 0
		for r in d.surnames:
			if n >= TOP_SURNAMES:
				break
			n += 1
			var w := float(r[1]) * float(lean.get(r[2], 1.0))
			var l: Dictionary = _lineage_of.get(str(r[0]).to_lower(), {})
			if not l.is_empty() and sid != "":
				w *= 1.0 + 3.0 * float((l.strongholds as Dictionary).get(sid, 0.0))
			acc += w
			cum.append(acc)
			rows.append(r)
		_cum_surname[town] = [cum, rows]
	var t: Array = _cum_surname[town]
	_mutex.unlock()
	return t


static func surname(world_seed: int, household_key: String, town: Variant) -> Dictionary:
	## A household's surname: {surname, heritage, lineage (id or "")}.
	data()
	var t := _surname_table(str(town) if town != null else "")
	var rng := NpcRng.for_trait(world_seed, household_key, "surname")
	var r: Array = t[1][_pick_cum(t[0], rng.rand())]
	var l := lineage(str(r[0]))
	return {"surname": str(r[0]), "heritage": str(r[2]), "lineage": str(l.get("id", ""))}


static func _pool(pool: String, sex: String) -> Array:
	var key := pool + "|" + sex
	_mutex.lock()
	if not _cum_pool.has(key):
		var src: Array = []
		if pool.begins_with("vogue:"):
			src = (_d.vogue.get(pool.substr(6), {}) as Dictionary).get(sex, [])
		else:
			src = (_d.given_pools.get(pool, {}) as Dictionary).get(sex, [])
		var cum := PackedFloat64Array()
		var names := PackedStringArray()
		var acc := 0.0
		for e in src:
			acc += maxf(0.001, float(e[1]))
			cum.append(acc)
			names.append(str(e[0]))
		_cum_pool[key] = [cum, names]
	var t: Array = _cum_pool[key]
	_mutex.unlock()
	return t


static func given(world_seed: int, pid: String, sex: String, age: int, heritage := "") -> String:
	var d := data()
	var s := "F" if sex == "female" or sex == "F" else "M"
	var born := PRESENT_AD - age
	var coh: Dictionary = d.cohorts[0]
	for c in d.cohorts:
		if born >= int(c.from) and born <= int(c.to):
			coh = c
	if born > int(d.cohorts[d.cohorts.size() - 1].to):
		coh = d.cohorts[d.cohorts.size() - 1]
	var mix: Dictionary = (coh.mix as Dictionary).duplicate()
	var rng := NpcRng.for_trait(world_seed, pid, "given_name")
	# the family's heritage pool, if it has one; otherwise its share goes to the Earth pools
	var hp: String = HERITAGE_POOL.get(heritage, "")
	if mix.has("heritage"):
		var hw := float(mix.heritage)
		mix.erase("heritage")
		if hp != "":
			mix[hp] = hw
		else:
			mix["earth_old"] = float(mix.get("earth_old", 0.0)) + hw * 0.4
			mix["earth_new"] = float(mix.get("earth_new", 0.0)) + hw * 0.6
	if mix.has("vogue"):
		var vw := float(mix.vogue)
		mix.erase("vogue")
		var decade := str(int(floor(born / 10.0)) * 10)
		if d.vogue.has(decade):
			mix["vogue:" + decade] = vw
	# choose the pool, then the name
	var tot := 0.0
	for k in mix:
		tot += float(mix[k])
	var x := rng.rand() * tot
	var pool := ""
	for k in mix:
		x -= float(mix[k])
		pool = k
		if x <= 0.0:
			break
	var t := _pool(pool, s)
	if (t[1] as PackedStringArray).is_empty():
		t = _pool("earth_new", s)
	return (t[1] as PackedStringArray)[_pick_cum(t[0], rng.rand())]


static func nickname(world_seed: int, pid: String, given_: String) -> String:
	var d := data()
	var nn: Array = d.nicknames.get(given_, [])
	if nn.is_empty():
		return ""
	var rng := NpcRng.for_trait(world_seed, pid, "nickname")
	if rng.rand() < 0.45:
		return ""
	return str(nn[int(rng.rand() * nn.size()) % nn.size()])
