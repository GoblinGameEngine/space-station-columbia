extends SceneTree

## Bakes where everyone's life happens: every resident of the station (the households of every home
## and every flat over a shop), the few traits a day's plan needs, their workplace (by occupation,
## distance and how many posts the place has left -- so the shops are staffed, not one of them
## crowded), their school, and the one place of each kind they go to regularly (the nearest-ish
## grocery, barber, bar, church; a gravity choice: closer is likelier, a car widens the reach).
##   ../godot/godot4 --headless --path . --script res://remake/tools/bake_lives.gd [-- seed]
## Writes res://remake/characters/lives/<Settlement>.json and lives/_index.json; NpcLife reads them. RERUN after the traits,
## households, placement or places change (and after tools/places/bake_places.py).

const OUT := "res://remake/characters/npc_lives.json"   # (the old single file: removed when the shards are written)
const OUT_DIR := "res://remake/characters/lives/"
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
	NpcOccupancy.ignore_cache = true
	NpcOccupancy.max_solved = 1000                       # (all of them: save_cache writes each)
	var db := NpcTraits.shared()
	NpcPlaces.load_all()
	var st: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://remake/placement.json"))
	# settlements with room manifests (tools/rooms/make_rooms.py) are NpcOccupancy's: their people, beds and posts come from
	# it -- the same answer the game computes on the fly -- and this bake only caches them (2026-10-07)
	var solved_towns := {}
	var solved_units := {}
	for b in st.structures:
		var town := str(b.settlement) if b.get("settlement") != null else "_country"
		if not solved_towns.has(town):
			solved_towns[town] = NpcOccupancy.has_manifest(town)
	var homes: Array = []
	for b in st.structures:
		var town := str(b.settlement) if b.get("settlement") != null else "_country"
		if solved_towns[town]:
			continue
		if NpcHouseholds.is_home(b):
			homes.append(b)
	for fl in NpcPlaces.flats(st.structures):
		if not solved_towns.get(str(fl.get("settlement", "_country")), false):
			homes.append(fl)
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
	for town in solved_towns:
		if not solved_towns[town]:
			continue
		var S := NpcOccupancy.solve(seed, town)
		for pid in S.people:
			var P: Dictionary = S.people[pid].duplicate(true)
			P["home_kind"] = "manifest"
			people[pid] = P
			order.append(pid)
			NpcPlaces.register_door(P.home, Vector2(float(P.door[0]), float(P.door[1])))
		for post in S.posts:
			solved_units[S.posts[post].uid] = true
		print("%s: %d people, %d posts (%d vacant) -- NpcOccupancy" % [town, S.people.size(), S.posts.size(), S.vacant.size()])
	var t1 := Time.get_ticks_msec()
	# 2. work: in a hashed order, each takes a post by occupation, distance and posts left
	order.sort_custom(func(x, y): return NpcRng.fnv1a64("%d|%s|order" % [seed, x]) < NpcRng.fnv1a64("%d|%s|order" % [seed, y]))
	var filled := {}
	var by_occ := {}
	for uid in NpcPlaces.units():
		var u: Dictionary = NpcPlaces.unit(uid)
		if solved_units.has(uid):
			continue                                      # (its posts are NpcOccupancy's, filled already)
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
		if u.type == "farm" or u.type == "church" or (u.jobs as Dictionary).is_empty() or solved_units.has(uid):
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
		if occ in NO_WORK or P.has("work") or P.get("home_kind", "") == "manifest":
			continue                                      # (a solved settlement's jobless stay jobless: one town, one market)
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
	var solved := []
	for town in solved_towns:
		if solved_towns[town]:
			solved.append(town)
	NpcOccupancy.save_cache(seed, solved)
	# one file per settlement (the 1:1 station's 218,000 people were 242 MB in one: NpcLife loads a town's when it's needed),
	# and the index: the seed, the settlements, the homes with a bicycle by the door (remake_station places them at start)
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	var shards := {}
	var by_home := {}
	for pid in people:
		var P: Dictionary = people[pid]
		var sh := NpcLife.shard_name(str(P.get("settlement", "")) if P.get("settlement") != null else "")
		if sh == NpcLife.shard_name(""):
			sh = NpcLife.shard_name(NpcOccupancy.town_of(str(P.home)))
		if not shards.has(sh):
			shards[sh] = {}
		shards[sh][pid] = P
		if not by_home.has(P.home):
			by_home[P.home] = []
		by_home[P.home].append(pid)
	var bikes := []
	for home in by_home:
		var owner := false
		for pid in by_home[home]:
			if int(people[pid].age) >= 10 and int(people[pid].age) <= 75 and NpcRng.for_trait(seed, pid, "owns_bike").rand() < 0.35:
				owner = true
				break
		if owner and NpcRng.for_trait(seed, str(home), "bike_parked").rand() <= 0.66:
			bikes.append(home)
	var counts := {}
	for sh in shards:
		var f := FileAccess.open(OUT_DIR + sh + ".json", FileAccess.WRITE)
		f.store_string(JSON.stringify({"seed": seed, "people": shards[sh]}))
		f.close()
		counts[sh] = shards[sh].size()
	var fi := FileAccess.open(NpcLife.PATH, FileAccess.WRITE)
	fi.store_string(JSON.stringify({"_about": "Everyone's home, workplace, school and regular places, a file per settlement (tools: remake/tools/bake_lives.gd). NpcLife reads them.",
		"seed": seed, "shards": counts, "bikes": bikes}))
	fi.close()
	if FileAccess.file_exists(OUT):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(OUT))      # (the old single file)
	print("people %d (traits %.1f s); workers %d, unplaced %d; workplaces %d, staffed %d (%.0f%%); total %.1f s" % [
		people.size(), (t1 - t0) / 1000.0, workers, unplaced, workplaces, staffed.size(), 100.0 * staffed.size() / maxf(1, workplaces), (Time.get_ticks_msec() - t0) / 1000.0])
	quit()


const GRID := 1000.0             # m: the cells places are filed in for _gravity
const FAR := 6.0                 # reaches past which a place's weight (exp(-6) = 0.25 %) isn't worth weighing
var _grids := {}                 # a uids array's key (size, first, last) -> {cell: [uid]}
var _near_cache := {}            # (places, home cell, radius) -> the nearest places
const HOME_CELL := 200.0         # m: homes this close share their candidate places
const NEAREST := 16              # places weighed per choice (the nearest: the farther ones' weight is next to nothing)


func _near(uids: Array, home: Vector2, reach: float) -> Array:
	## the places within FAR reaches of home, from a grid of them (242,000 people weighing every place of a kind on the
	## ring was ~10^9 tests, 2026-10-08); all of them when that radius is most of the ring or none fall inside it
	var R := reach * FAR
	if R > 12000.0 or uids.size() < 40:
		return uids
	var gk := "%d|%s|%s" % [uids.size(), uids[0], uids[uids.size() - 1]]
	if not _grids.has(gk):
		var g := {}
		for uid in uids:
			var u: Dictionary = NpcPlaces.unit(uid)
			var c := Vector2i(int(floor(fposmod(float(u.door[0]), StationGeo.CIRC) / GRID)), int(floor(float(u.door[1]) / GRID)))
			if not g.has(c):
				g[c] = []
			g[c].append(uid)
		_grids[gk] = g
	# the NEAREST places within R of the home's HOME_CELL cell, once per cell (everyone living there shares the list;
	# weighing the hundred-odd shops of a city with a generator each, for 3.6 M choices, didn't finish in an hour)
	var hk := "%s|%d|%d|%d" % [gk, int(floor(fposmod(home.x, StationGeo.CIRC) / HOME_CELL)), int(floor(home.y / HOME_CELL)), int(R)]
	if _near_cache.has(hk):
		return _near_cache[hk]
	var g: Dictionary = _grids[gk]
	var n := int(ceil(R / GRID))
	var ncol := int(ceil(StationGeo.CIRC / GRID))
	var ci := int(floor(fposmod(home.x, StationGeo.CIRC) / GRID))
	var cj := int(floor(home.y / GRID))
	var cand := []
	for i in range(-n, n + 1):
		for j in range(-n, n + 1):
			for uid in g.get(Vector2i(posmod(ci + i, ncol), cj + j), []):
				var u: Dictionary = NpcPlaces.unit(uid)
				cand.append([NpcPlaces.dist(home, Vector2(float(u.door[0]), float(u.door[1]))), uid])
	var out := []
	if cand.is_empty():
		out = uids
	else:
		cand.sort_custom(func(p_, q_): return p_[0] < q_[0])
		for k in mini(NEAREST, cand.size()):
			out.append(cand[k][1])
	_near_cache[hk] = out
	return out


func _gravity(seed: int, pid: String, key: String, uids: Array, home: Vector2, reach: float, town := "") -> String:
	## Closer is likelier (Huff): weight exp(-d / reach) times a personal liking.
	if uids.is_empty():
		return ""
	uids = _near(uids, home, reach)
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
