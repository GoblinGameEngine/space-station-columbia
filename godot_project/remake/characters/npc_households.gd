extends RefCounted
class_name NpcHouseholds

## Who lives in a building: household-first synthesis (scale_survey.md 2.4 -- Beckman et al.
## 1996, SPEW).  A building's households, and each household's members with their ages, sexes and
## relations, are a pure function of (world seed, building id): nothing is stored, and the same
## house holds the same family every time.  Members are people ids "<building>:<n>" whose traits
## NpcTraits derives with the household's facts pinned (age, sex), in the town's population.
##
##   var h := NpcHouseholds.of_building(seed, building)     # building: a placement.json structure
##   for m in h.members: NpcTraits.shared().person(seed, m.pid, [], h.population, m.pinned)

const PATH := "res://remake/characters/npc_settlements.json"
static var _data: Dictionary


static func data() -> Dictionary:
	if _data.is_empty():
		_data = JSON.parse_string(FileAccess.get_file_as_string(PATH))
	return _data


static func population_of(settlement: Variant) -> String:
	var d := data()
	return str(d.settlements.get(str(settlement) if settlement != null else "_none", d.settlements._none))


static func is_residential(kind: String) -> bool:
	return data().buildings.has(kind)


static func of_building(world_seed: int, b: Dictionary) -> Dictionary:
	## -> {population, households: [{type, members: [{pid, role, pinned}]}], members: [...all]}
	var d := data()
	var pop := population_of(b.get("settlement"))
	var out := {"population": pop, "households": [], "members": []}
	var kind: String = b.kind
	if not d.buildings.has(kind):
		return out
	var bdef: Dictionary = d.buildings[kind]
	var mix: Dictionary = (d.mix.get(pop, d.mix.stable_town) as Dictionary).duplicate()
	for k in bdef.mix:
		mix[k] = float(mix.get(k, 0.0)) * float(bdef.mix[k])
	var n := 0
	for hh in int(bdef.households):
		var rng := NpcRng.for_trait(world_seed, "%s#%d" % [b.id, hh], "household")
		var htype: String = rng.pick(mix)
		var spec: Array = d.household_types[htype].members
		var h := {"type": htype, "members": []}
		var head_age := 0
		var head_sex := ""
		for m in spec:
			var chance := float(m[3]) if m.size() > 3 else 1.0
			if rng.rand() >= chance:
				continue
			var role: String = m[0]
			var age: int
			if typeof(m[1]) == TYPE_STRING and m[1] == "couple":
				age = clampi(head_age + int(round(rng.normal(0.0, 3.5))), 18, 99)
			else:
				age = int(m[1][0]) + int(rng.rand() * (int(m[1][1]) - int(m[1][0]) + 1))
			if role == "child" and head_age > 0:
				age = mini(age, maxi(0, head_age - 18))          # children younger than their parents by 18+
			var sex: String = m[2]
			if sex == "any":
				sex = "female" if rng.rand() < 0.5 else "male"
			if role == "partner" and rng.rand() < 0.93 and head_sex != "":
				sex = "male" if head_sex == "female" else "female"
			if role == "head":
				head_age = age
				head_sex = sex
			var pinned := {"age": age, "sex": sex}
			var mem := {"pid": "%s:%d" % [b.id, n], "role": role, "household": hh, "pinned": pinned}
			n += 1
			h.members.append(mem)
			out.members.append(mem)
		out.households.append(h)
	return out


static func door(b: Dictionary) -> Vector2:
	## The front door on the map, (s, x): the middle of the footprint's front edge (local -z; see
	## StationGeo.basis).
	var yaw: float = b.yaw
	var fz: float = b.fmin[1]
	var fx: float = (float(b.fmin[0]) + float(b.fmax[0])) * 0.5
	var front := Vector2(cos(yaw), -sin(yaw))                     # (s, x) per metre of local -z
	var right := Vector2(sin(yaw), cos(yaw))                      # (s, x) per metre of local +x
	return Vector2(float(b.s), float(b.x)) + front * (-fz + 1.2) + right * fx
