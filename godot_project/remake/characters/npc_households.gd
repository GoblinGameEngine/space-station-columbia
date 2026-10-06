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


static func is_home(b: Dictionary) -> bool:
	## A building people live in: a residential kind, but of a farm only its house (the barn, silo
	## and shed are where the work is).
	var id := str(b.id)
	return is_residential(str(b.kind)) and not (b.kind == "farm" and id.begins_with("FARM-") and not id.ends_with("-house"))


static func of_building(world_seed: int, b: Dictionary) -> Dictionary:
	## -> {population, households: [{type, members: [{pid, role, pinned}]}], members: [...all]}
	var d := data()
	var pop := population_of(b.get("settlement"))
	var out := {"population": pop, "households": [], "members": []}
	var kind: String = b.kind
	if not is_home(b):
		return out
	var bdef: Dictionary = d.buildings[kind]
	var mix: Dictionary = (d.mix.get(pop, d.mix.stable_town) as Dictionary).duplicate()
	for k in bdef.mix:
		mix[k] = float(mix.get(k, 0.0)) * float(bdef.mix[k])
	var n := 0
	for hh in int(b.get("households", bdef.households)):     # (a building may carry its own count: apartments, rows, doubles)
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
		_name_household(world_seed, "%s#%d" % [b.id, hh], b.get("settlement"), h)
		out.households.append(h)
	return out


static func _name_household(world_seed: int, key: String, town: Variant, h: Dictionary) -> void:
	## Surnames and given names from the game bible (NpcNames), pinned on each member. Charter art. 9:
	## a child takes either parent's surname (about 65% the head's, 30% the partner's, 5% both
	## joined); partners keep their own surname a little under half the time; housemates are
	## unrelated; an elder in a three-generation home is the head's or the partner's parent.
	var head := NpcNames.surname(world_seed, key, town)
	var partner := head
	var rng := NpcRng.for_trait(world_seed, key, "surname_rule")
	var mates := 0
	for m in h.members:
		var sn := head
		match str(m.role):
			"partner":
				if rng.rand() < 0.45:
					partner = NpcNames.surname(world_seed, key + "#partner", town)
				sn = partner
			"child":
				var r := rng.rand()
				if r < 0.65 or partner.surname == head.surname:
					sn = head
				elif r < 0.95:
					sn = partner
				else:
					sn = {"surname": "%s-%s" % [head.surname, partner.surname], "heritage": head.heritage, "lineage": head.lineage}
			"elder":
				sn = head if rng.rand() < 0.5 else partner
			"mate":
				mates += 1
				sn = NpcNames.surname(world_seed, "%s#mate%d" % [key, mates], town)
		var pinned: Dictionary = m.pinned
		pinned["surname"] = sn.surname
		pinned["lineage"] = sn.lineage
		pinned["name_heritage"] = sn.heritage
		pinned["given_name"] = NpcNames.given(world_seed, m.pid, str(pinned.sex), int(pinned.age), str(sn.heritage))


static func door(b: Dictionary) -> Vector2:
	## The front door on the map, (s, x): the middle of the footprint's front edge (local -z; see
	## StationGeo.basis).
	var yaw: float = b.yaw
	var fz: float = b.fmin[1]
	var fx: float = (float(b.fmin[0]) + float(b.fmax[0])) * 0.5
	var front := Vector2(cos(yaw), -sin(yaw))                     # (s, x) per metre of local -z
	var right := Vector2(sin(yaw), cos(yaw))                      # (s, x) per metre of local +x
	return Vector2(float(b.s), float(b.x)) + front * (-fz + 1.2) + right * fx
