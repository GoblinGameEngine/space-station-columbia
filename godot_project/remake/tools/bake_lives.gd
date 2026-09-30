extends SceneTree

## Bakes where everyone's life happens: every resident of the station (the households of every home
## and every flat over a shop), the few traits a day's plan needs, their workplace (by occupation,
## distance and how many posts the place has left -- so the shops are staffed, not one of them
## crowded), their school, and the one place of each kind they go to regularly (the nearest-ish
## grocery, barber, bar, church; a gravity choice: closer is likelier, a car widens the reach).
##   ../godot/godot4 --headless --path . --script res://remake/tools/bake_lives.gd [-- seed]
## Writes res://remake/characters/npc_lives.json; NpcLife reads it. RERUN after the traits,
## households, placement or places change (and after tools/places/bake_places.py).

const OUT := "res://remake/characters/npc_lives.json"
const NEED := ["age", "sex", "occupation", "wage", "car_access", "commute_mode", "mobility_aid", "worship", "addictions", "finances", "personality"]
const NO_WORK := ["retired", "preschool", "student", "homemaker", "unemployed", "university_student"]
const REACH_WALK := 400.0        # m: the gravity choice's distance scale without a car
const REACH_CAR := 1000.0        # with one
const SAME_TOWN := 2.5           # and the town's own shops are liked better
const WORK_WALK := 2500.0
const WORK_CAR := 9000.0


func _initialize() -> void:
	var a := OS.get_cmdline_user_args()
	var seed := int(a[0]) if a.size() > 0 else 1
	var t0 := Time.get_ticks_msec()
	var db := NpcTraits.shared()
	NpcPlaces.load_all()
	var st: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://remake/placement.json"))
	var homes: Array = []
	for b in st.structures:
		if NpcHouseholds.is_home(b):
			homes.append(b)
	homes.append_array(NpcPlaces.flats(st.structures))
	var types := NpcPlaces.types()
	# purposes: purpose -> [type, who, per_week]
	var purposes := {}
	for tid in types:
		if types[tid].station:
			continue
		for v in types[tid].visits:
			if not NpcPlaces.of_type(tid).is_empty():
				purposes[v.purpose] = [tid, str(v.who), float(v.per_week)]
	var who_expr := {}
	for p in purposes:
		var src: String = purposes[p][1]
		if src == "congregant":
			src = "worship == 'weekly' or worship == 'monthly'"
		var e := Expression.new()
		if e.parse(src, PackedStringArray(["age", "sex", "occupation", "car_access", "worship"])) != OK:
			push_error("who: %s" % src)
		who_expr[p] = e
	# 1. everyone
	var people := {}
	var order := []
	for b in homes:
		var hh := NpcHouseholds.of_building(seed, b)
		var door := NpcHouseholds.door(b)
		NpcPlaces.register_door(b.id, door)
		for m in hh.members:
			var v := db.some(seed, m.pid, NEED, hh.population, m.pinned)
			var p: Dictionary = v.personality
			people[m.pid] = {"home": b.id, "door": [snappedf(door.x, 0.01), snappedf(door.y, 0.01)], "settlement": b.get("settlement") if b.get("settlement") != null else "",
				"hh": int(m.household), "role": m.role, "pop": hh.population, "age": int(v.age), "sex": v.sex, "occupation": v.occupation,
				"car": v.car_access, "commute": v.commute_mode, "mobility": v.mobility_aid, "worship": v.worship, "addictions": v.addictions,
				"finances": v.finances, "E": snappedf(float(p.extraversion), 0.01), "C": snappedf(float(p.conscientiousness), 0.01),
				"home_kind": b.kind, "given": m.pinned.get("given_name", ""), "surname": m.pinned.get("surname", ""),
				"lineage": m.pinned.get("lineage", ""), "name_heritage": m.pinned.get("name_heritage", "")}
			order.append(m.pid)
	var t1 := Time.get_ticks_msec()
	# 2. work: in a hashed order, each takes a post by occupation, distance and posts left
	order.sort_custom(func(x, y): return NpcRng.fnv1a64("%d|%s|order" % [seed, x]) < NpcRng.fnv1a64("%d|%s|order" % [seed, y]))
	var filled := {}
	var by_occ := {}
	for uid in NpcPlaces.units():
		var u: Dictionary = NpcPlaces.unit(uid)
		for o in u.jobs:
			if not by_occ.has(o):
				by_occ[o] = []
			by_occ[o].append(uid)
	# every workplace first gets someone to open it: the nearest free worker of one of its trades
	# (a farm is its family's; a church without its own pastor shares one)
	var free_by_occ := {}
	for pid in order:
		var o: String = people[pid].occupation
		if not (o in NO_WORK):
			if not free_by_occ.has(o):
				free_by_occ[o] = []
			free_by_occ[o].append(pid)
	var uids: Array = NpcPlaces.units().keys()
	uids.sort_custom(func(x, y): return NpcRng.fnv1a64("%d|%s|open" % [seed, x]) < NpcRng.fnv1a64("%d|%s|open" % [seed, y]))
	for uid in uids:
		var u: Dictionary = NpcPlaces.unit(uid)
		if u.type == "farm" or u.type == "church" or (u.jobs as Dictionary).is_empty():
			continue
		var at := Vector2(float(u.door[0]), float(u.door[1]))
		var best := ""
		var bd := INF
		for o in u.jobs:
			for pid in free_by_occ.get(o, []):
				if people[pid].has("work"):
					continue
				var d := NpcPlaces.dist(at, Vector2(float(people[pid].door[0]), float(people[pid].door[1])))
				if d < bd and d < (WORK_CAR if people[pid].car != "none" else WORK_WALK):
					bd = d
					best = pid
		if best != "":
			var o2: String = people[best].occupation
			people[best].work = uid
			filled[uid + "|" + o2] = int(filled.get(uid + "|" + o2, 0)) + 1
			filled[uid] = int(filled.get(uid, 0)) + 1
	var unplaced := 0
	for pid in order:
		var P: Dictionary = people[pid]
		var occ: String = P.occupation
		if occ in NO_WORK or P.has("work"):
			continue
		var home := Vector2(float(P.door[0]), float(P.door[1]))
		# farm and fish-house families work their own place
		if (occ == "farmer" or occ == "farmhand") and P.home_kind == "farm" or occ == "fisher" and P.home_kind == "fishhouse":
			var own := "%s/0" % str(P.home).replace("-house", "-barn")
			if not NpcPlaces.unit(own).is_empty():
				P.work = own
				filled[own] = int(filled.get(own, 0)) + 1
				continue
		var reach := WORK_CAR if P.car != "none" else WORK_WALK
		var ws := []
		var tot := 0.0
		for uid in by_occ.get(occ, []):
			var u: Dictionary = NpcPlaces.unit(uid)
			var posts := float(u.jobs[occ])
			var left := maxf(0.03, 1.0 - float(filled.get(uid + "|" + occ, 0)) / posts)
			var d := NpcPlaces.dist(home, Vector2(float(u.door[0]), float(u.door[1])))
			var w := posts * left * left * exp(-d / reach)
			ws.append([uid, w])
			tot += w
		if tot <= 0.0:
			unplaced += 1
			continue
		var r := NpcRng.for_trait(seed, pid, "work").rand() * tot
		for x in ws:
			r -= float(x[1])
			if r <= 0.0:
				P.work = x[0]
				break
		if not P.has("work"):
			P.work = ws[ws.size() - 1][0]
		filled[P.work + "|" + occ] = int(filled.get(P.work + "|" + occ, 0)) + 1
		filled[P.work] = int(filled.get(P.work, 0)) + 1
	# 3. school, and each purpose's regular place
	for pid in order:
		var P: Dictionary = people[pid]
		var home := Vector2(float(P.door[0]), float(P.door[1]))
		var reach := REACH_CAR if P.car != "none" else REACH_WALK
		var occ: String = P.occupation
		if occ == "student":
			P.school = _gravity(seed, pid, "school", NpcPlaces.of_type("school"), home, 2500.0)
		elif occ == "university_student":
			var c := NpcPlaces.of_type("college")
			P.school = _gravity(seed, pid, "school", c if not c.is_empty() else NpcPlaces.of_type("school"), home, 20000.0)
		elif occ == "preschool" and NpcRng.for_trait(seed, pid, "childcare").rand() < 0.6:
			P.school = _gravity(seed, pid, "school", NpcPlaces.of_type("childcare"), home, 3000.0)
		var reg := {}
		for purpose in purposes:
			var e: Expression = who_expr[purpose]
			var ok: Variant = e.execute([P.age, P.sex, P.occupation, P.car, P.worship])
			if not ok:
				continue
			var tid: String = purposes[purpose][0]
			var uid := _gravity(seed, pid, "reg:" + purpose, NpcPlaces.of_type(tid), home, reach, P.settlement)
			if uid != "":
				reg[purpose] = uid
		P.reg = reg
		P.erase("home_kind")
	# report
	var staffed := {}
	for pid in people:
		if people[pid].has("work"):
			staffed[people[pid].work] = true
	var workplaces := 0
	for uid in NpcPlaces.units():
		var u: Dictionary = NpcPlaces.unit(uid)
		if not (u.jobs as Dictionary).is_empty():
			workplaces += 1
	var workers := 0
	for pid in people:
		if not (people[pid].occupation in NO_WORK):
			workers += 1
	var f := FileAccess.open(OUT, FileAccess.WRITE)
	f.store_string(JSON.stringify({"_about": "Everyone's home, workplace, school and regular places (tools: remake/tools/bake_lives.gd). NpcLife reads it.",
		"seed": seed, "people": people}))
	f.close()
	print("people %d (traits %.1f s); workers %d, unplaced %d; workplaces %d, staffed %d (%.0f%%); total %.1f s" % [
		people.size(), (t1 - t0) / 1000.0, workers, unplaced, workplaces, staffed.size(), 100.0 * staffed.size() / maxf(1, workplaces), (Time.get_ticks_msec() - t0) / 1000.0])
	quit()


func _gravity(seed: int, pid: String, key: String, uids: Array, home: Vector2, reach: float, town := "") -> String:
	## Closer is likelier (Huff): weight exp(-d / reach) times a personal liking.
	if uids.is_empty():
		return ""
	var rng := NpcRng.for_trait(seed, pid, key)
	var ws := []
	var tot := 0.0
	for uid in uids:
		var u: Dictionary = NpcPlaces.unit(uid)
		var d := NpcPlaces.dist(home, Vector2(float(u.door[0]), float(u.door[1])))
		var w := exp(-d / reach) * (0.5 + NpcRng.for_trait(seed, pid, key + "|" + uid).rand()) * (SAME_TOWN if town != "" and u.settlement == town else 1.0)
		ws.append(w)
		tot += w
	if tot <= 0.0:
		return uids[0]
	var r := rng.rand() * tot
	for i in uids.size():
		r -= float(ws[i])
		if r <= 0.0:
			return uids[i]
	return uids[uids.size() - 1]
