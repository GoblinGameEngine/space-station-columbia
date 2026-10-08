extends RefCounted
class_name NpcOccupancy

## Who belongs in every building and every room, generated on the fly (the user, 2026-10-07: "every single building
## needs a purpose, every house needs residents, every shop needs workers and every store needs shoppers ... each and
## every room ... generate it on the fly while in-game"; the contract with the story engine: research/lives/07_occupancy.md).
##
## The data: res://remake/rooms/<Settlement>.json (tools/rooms/make_rooms.py) -- every building's rooms, doors, units and
## rostered posts.  Everything here is a pure function of (world seed, settlement): solve() makes a settlement's people
## (the households of its dwelling units, each resident's bed), fills its posts from them (its labour market: one
## settlement is one market, so the answer never depends on what else is loaded) and leaves a few posts vacant at a seeded
## rate set by the town's economy.  Nothing is stored; the story's changes (hired, fired, moved, died) are a journal on top
## (deck-ea's) that overrides only the person it names -- a firing leaves the post open, never re-solves the market.
##
##   NpcOccupancy.solve(seed, town)               -> {people, posts, vacant, homes}  (cached; slow the first time: call it
##                                                   off the main thread for a big town)
##   NpcOccupancy.on_duty(seed, uid_or_room, day, hour) -> [{post, pid, role, room}]   (uid "C-015/B0", room "C-077#R1F0_0")
##   NpcOccupancy.roster(seed, uid)               -> every post of a business unit, filled or vacant
##   NpcOccupancy.rooms_of(seed, pid)             -> {home, bed, work, post, school}
##   NpcOccupancy.residents(seed, building[, unit])-> [pid]
##   NpcOccupancy.who(seed, place, day, hour)     -> [{pid, why}]  (place "C-077" | "C-077/B0" | "C-077#R1F0_0")
##   NpcOccupancy.where(seed, pid, day, hour)     -> {building, room, unit, doing}

const ROOMS := "res://remake/rooms/"
const NEED := ["age", "sex", "occupation", "wage", "car_access", "commute_mode", "mobility_aid", "worship", "addictions", "finances", "personality"]
const NO_WORK := ["retired", "preschool", "student", "homemaker", "unemployed", "university_student"]
const FLEX := ["unemployed", "homemaker"]            # adults who take a post nobody of its trade is free for
const SAMPLE := 16                                   # candidates a post looks at (nearest of a hashed sample)
const VACANCY := {"stable_town": 0.02, "county_seat": 0.02, "college_town": 0.025, "exurban": 0.015, "lake_resort": 0.03,
	"rust_belt": 0.06, "_default": 0.03}               # (posts standing empty, by the town's economy: npc_settlements.json)
const VACANT_WHY := ["unfilled", "chute_shortage", "just_quit", "budget_cut", "on_leave"]
const DAYS := ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

static var _manifest := {}                           # town -> {buildings}
static var _manifest_lru: Array = []
static var _placement := {}                          # building id -> placement structure
static var _town_of := {}                            # building id -> town
static var _solved := {}                             # "seed|town" -> result
static var _mutex := Mutex.new()


static func _load_placement() -> void:
	Placement.load_all()                                 # (the one packed copy: Placement)


static func manifest(town: String) -> Dictionary:
	_mutex.lock()
	if not _manifest.has(town):
		var p := ROOMS + town + ".json"
		_manifest[town] = (JSON.parse_string(FileAccess.get_file_as_string(p)) as Dictionary).get("buildings", {}) if FileAccess.file_exists(p) else {}
		# (a city's manifest is ~56 MB of JSON, ~600 MB parsed: the least recently used go past max_solved)
		_manifest_lru.erase(town)
		_manifest_lru.append(town)
		while _manifest_lru.size() > max_solved:
			_manifest.erase(_manifest_lru.pop_front())
	else:
		_manifest_lru.erase(town)
		_manifest_lru.append(town)
	var m: Dictionary = _manifest[town]
	_mutex.unlock()
	return m


static func town_of(building: String) -> String:
	var i := Placement.index(building)
	if i < 0:
		return "_country"
	var t := Placement.settlement(i)
	return t if t != "" else "_country"


static func building(bid: String) -> Dictionary:
	return manifest(town_of(bid)).get(bid, {})


static func has_manifest(town: String) -> bool:
	return not manifest(town).is_empty()


static func world(b: Dictionary, lx: float, lz: float, out_m := 0.0) -> Vector2:
	## a point of a building's glb frame (x right, z back) on the map (s, x); out_m pushes it away from the centre
	var c := cos(float(b.yaw))
	var sn := sin(float(b.yaw))
	var p := Vector2(float(b.s) + lx * sn - lz * c, float(b.x) + lx * c + lz * sn)
	if out_m > 0.0:
		var d := p - Vector2(float(b.s), float(b.x))
		p += d.normalized() * out_m
	return p


static func unit_door(bid: String, uid: String) -> Vector2:
	## where a unit's people come and go: its delivery door, on the map; the building's front otherwise
	_load_placement()
	var b: Dictionary = Placement.entry_of(bid)
	var m := building(bid)
	var u: Dictionary = m.get("units", {}).get(uid, {})
	var dn = (u.get("delivery", {}) as Dictionary).get("door")
	if dn != null:
		for d in m.doors:
			if d.node == dn:
				return world(b, float(d.at[0]), float(d.at[1]), 1.2 if d.ext else 0.0)
	return NpcHouseholds.door(b)


# -- solving a settlement --------------------------------------------------------------------------------------------

const CACHE := "res://remake/rooms/solved/"          # (bake_lives writes the settlements it solved, a file each, and
                                                     # _seed.json; a cache, never the authority)
static var max_solved := 2                             # settlements' solutions held at once (a city's is ~100 MB in memory)
static var _cache_seed := -1
static var _solved_lru: Array = []
static var ignore_cache := false                     # (bake_lives: always solve afresh)


static func _load_cache(town: String) -> Variant:
	## the baked solution of a settlement for the world seed, or null
	if ignore_cache:
		return null
	if _cache_seed == -1:
		_cache_seed = -2
		if FileAccess.file_exists(CACHE + "_seed.json"):
			_cache_seed = int((JSON.parse_string(FileAccess.get_file_as_string(CACHE + "_seed.json")) as Dictionary).seed)
	var p := CACHE + town.replace(" ", "_") + ".json"
	if not FileAccess.file_exists(p):
		return null
	return JSON.parse_string(FileAccess.get_file_as_string(p))


static func save_cache(seed: int, towns: Array) -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(CACHE))
	for town in towns:
		var S: Dictionary = solve(seed, town).duplicate()
		S.erase("_posts_at")                             # (the indexes are rebuilt on load)
		S.erase("_homes_of")
		var f := FileAccess.open(CACHE + town.replace(" ", "_") + ".json", FileAccess.WRITE)
		f.store_string(JSON.stringify(S))
		f.close()
	var fs := FileAccess.open(CACHE + "_seed.json", FileAccess.WRITE)
	fs.store_string(JSON.stringify({"_about": "NpcOccupancy.solve() for the world seed, cached by bake_lives.gd (recomputed on the fly for any other seed)",
		"seed": seed, "towns": towns}))
	fs.close()
	var old := "res://remake/rooms/_solved.json"                  # (the single file it was)
	if FileAccess.file_exists(old):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(old))


static func _remember(key: String, r: Dictionary) -> void:
	## (called locked) keep a solution, letting the least recently used go past max_solved
	_solved[key] = r
	_solved_lru.erase(key)
	_solved_lru.append(key)
	while _solved_lru.size() > max_solved:
		_solved.erase(_solved_lru.pop_front())


static func solve(seed: int, town: String) -> Dictionary:
	var key := "%d|%s" % [seed, town]
	_mutex.lock()
	var have: Variant = _solved.get(key)
	if have != null:
		_solved_lru.erase(key)
		_solved_lru.append(key)
	_mutex.unlock()
	if have != null:
		return have
	var r: Dictionary
	var cached: Variant = _load_cache(town)
	if cached != null and seed == _cache_seed and typeof(cached) == TYPE_DICTIONARY:
		r = cached
	else:
		r = _solve(seed, town)
	_index(r)
	_mutex.lock()
	_remember(key, r)
	_mutex.unlock()
	return r


static func _index(r: Dictionary) -> void:
	## lookups by place (a 1:1 city has ~20,000 posts and ~18,000 homes: on_duty / residents scanned them all per query)
	var by_place := {}
	for post in r.posts:
		var p: Dictionary = r.posts[post]
		for k in [p.uid, p.room]:
			if not by_place.has(k):
				by_place[k] = []
			by_place[k].append(post)
	var homes_of := {}
	for hk in r.homes:
		var bid: String = hk.get_slice("/", 0)
		if not homes_of.has(bid):
			homes_of[bid] = []
		homes_of[bid].append(hk)
	r["_posts_at"] = by_place
	r["_homes_of"] = homes_of


static func _indexed(S: Dictionary) -> Dictionary:
	if not S.has("_posts_at"):
		_mutex.lock()
		if not S.has("_posts_at"):
			_index(S)                                    # (a solve from the cache file)
		_mutex.unlock()
	return S


static func _solve(seed: int, town: String) -> Dictionary:
	_load_placement()
	var man := manifest(town)
	var db := NpcTraits.shared()
	var people := {}
	var homes := {}                                  # "<building>/<unit>" -> [pid]
	var order := []
	var bids: Array = man.keys()
	bids.sort()
	# 1. the households of every dwelling unit, their beds
	for bid in bids:
		var m: Dictionary = man[bid]
		var b: Dictionary = Placement.entry_of(bid)
		if b.is_empty():
			continue
		var dunits := []
		for uid in m.units:
			if m.units[uid].type == "dwelling":
				dunits.append(uid)
		if dunits.is_empty():
			continue
		dunits.sort()
		var total := 0
		for uid in dunits:
			total += int(m.units[uid].get("households", 1))
		var b2 := b.duplicate()
		b2["households"] = total
		if not NpcHouseholds.is_home(b2):
			b2["kind"] = "flat"                          # (homes in a building that isn't one: the flats over the shops)
		var hh := NpcHouseholds.of_building(seed, b2)
		var hi := 0
		for uid in dunits:
			var u: Dictionary = m.units[uid]
			var door := unit_door(bid, uid)
			var beds := _bedrooms(m, u)
			for k in int(u.get("households", 1)):
				if hi >= hh.households.size():
					break
				var h: Dictionary = hh.households[hi]
				hi += 1
				var assign := _beds_for(h.members, beds)
				for mm in h.members:
					var v := db.some(seed, mm.pid, NEED, hh.population, mm.pinned)
					var pp: Dictionary = v.personality
					var P := {"home": bid, "unit": uid, "bed": "%s#%s" % [bid, assign.get(mm.pid, "")], "door": [snappedf(door.x, 0.01), snappedf(door.y, 0.01)],
						"settlement": town, "hh": int(mm.household), "role": mm.role, "pop": hh.population, "age": int(v.age), "sex": v.sex,
						"occupation": v.occupation, "car": v.car_access, "commute": v.commute_mode, "mobility": v.mobility_aid, "worship": v.worship,
						"addictions": v.addictions, "finances": v.finances, "E": snappedf(float(pp.extraversion), 0.01), "C": snappedf(float(pp.conscientiousness), 0.01),
						"given": mm.pinned.get("given_name", ""), "surname": mm.pinned.get("surname", ""), "lineage": mm.pinned.get("lineage", ""),
						"name_heritage": mm.pinned.get("name_heritage", ""), "reg": {}}
					people[mm.pid] = P
					order.append(mm.pid)
					var hk := "%s/%s" % [bid, uid]
					if not homes.has(hk):
						homes[hk] = []
					homes[hk].append(mm.pid)
	# 2. the posts, each filled from the settlement's own people (one settlement, one labour market)
	var posts := {}                                  # post id -> {pid, role, room, shift, days, off, uid}
	var vacant := {}
	var plist := []
	for bid in bids:
		var m: Dictionary = man[bid]
		for uid in m.units:
			var u: Dictionary = m.units[uid]
			if u.type != "business":
				continue
			for p in u.get("posts", []):
				var q: Dictionary = (p as Dictionary).duplicate()
				q["uid"] = "%s/%s" % [bid, uid]
				q["building"] = bid
				q["door"] = unit_door(bid, uid)
				plist.append(q)
	plist.sort_custom(func(a, b): return NpcRng.fnv1a64("%d|%s|post" % [seed, a.post]) < NpcRng.fnv1a64("%d|%s|post" % [seed, b.post]))
	var rate: float = VACANCY.get(str(NpcHouseholds.data().settlements.get(town, "_default")), VACANCY._default)
	var by_occ := {}
	var flex := []
	order.sort_custom(func(a, b): return NpcRng.fnv1a64("%d|%s|order" % [seed, a]) < NpcRng.fnv1a64("%d|%s|order" % [seed, b]))
	for pid in order:
		var P: Dictionary = people[pid]
		var o: String = P.occupation
		if o in FLEX and P.age >= 18 and P.age <= 66:
			flex.append(pid)
		elif not (o in NO_WORK):
			if not by_occ.has(o):
				by_occ[o] = []
			by_occ[o].append(pid)
	var roles_present := {}
	for q in plist:
		roles_present[q.role] = true
	# workers whose trade has no post in town are flexible too (they take what there is)
	for o in by_occ.keys():
		if not roles_present.has(o):
			flex.append_array(by_occ[o])
			by_occ.erase(o)
	var taken := {}
	for q in plist:
		var vr := NpcRng.for_trait(seed, q.post, "vacancy")
		if vr.rand() < rate and not q.get("relief", false):
			vacant[q.post] = VACANT_WHY[int(vr.rand() * VACANT_WHY.size()) % VACANT_WHY.size()]
			posts[q.post] = _post_rec(q, "")
			continue
		var at: Vector2 = q.door
		var pid := _nearest(people, by_occ.get(q.role, []), taken, at, seed, q.post)
		if pid == "":
			pid = _nearest(people, flex, taken, at, seed, q.post)
			if pid != "":
				people[pid]["occupation_was"] = people[pid].occupation
				people[pid]["occupation"] = q.role       # (they took the job there was)
		if pid == "":
			vacant[q.post] = "no_one_in_town"
			posts[q.post] = _post_rec(q, "")
			continue
		taken[pid] = true
		var P: Dictionary = people[pid]
		P["work"] = q.uid
		P["post"] = q.post
		P["post_room"] = "%s#%s" % [q.building, q.room]
		P["shift"] = q.shift
		P["days"] = q.days
		if q.has("off"):
			P["off"] = q.off
		posts[q.post] = _post_rec(q, pid)
	for pid in order:
		var P: Dictionary = people[pid]
		if not P.has("work") and not (P.occupation in NO_WORK):
			P["jobless"] = true                          # (a trade with no post left in town: looking for work)
	return {"people": people, "posts": posts, "vacant": vacant, "homes": homes}


static func _post_rec(q: Dictionary, pid: String) -> Dictionary:
	var r := {"pid": pid, "role": q.role, "room": "%s#%s" % [q.building, q.room], "uid": q.uid, "shift": q.shift, "days": q.days}
	if q.has("off"):
		r["off"] = q.off
	return r


static func _nearest(people: Dictionary, pool: Array, taken: Dictionary, at: Vector2, seed: int, key: String) -> String:
	## the nearest free one of a hashed sample of the pool (a post looks at SAMPLE candidates, not the whole town)
	if pool.is_empty():
		return ""
	var best := ""
	var bd := INF
	var n := pool.size()
	var start := int(NpcRng.fnv1a64("%d|%s|start" % [seed, key]) % n)
	var seen := 0
	var i := 0
	while i < n and seen < SAMPLE:
		var pid: String = pool[(start + i * 7919) % n] if n % 7919 != 0 else pool[(start + i) % n]
		i += 1
		if taken.has(pid):
			continue
		seen += 1
		var d := NpcPlaces.dist(at, Vector2(float(people[pid].door[0]), float(people[pid].door[1])))
		if d < bd:
			bd = d
			best = pid
	if best == "":
		for pid in pool:                                 # (the sample was all taken: the first free one)
			if not taken.has(pid):
				return pid
	return best


static func _bedrooms(m: Dictionary, u: Dictionary) -> Array:
	var out := []
	for rn in u.rooms:
		if m.rooms[rn].use == "bedroom" or m.rooms[rn].use == "guest_room":
			out.append([rn, float(m.rooms[rn].area)])
	out.sort_custom(func(a, b): return a[1] > b[1])
	if out.is_empty():
		for rn in u.rooms:
			if m.rooms[rn].use == "living":
				out.append([rn, float(m.rooms[rn].area)])
	return out


static func _beds_for(members: Array, beds: Array) -> Dictionary:
	## who sleeps where: the couple in the biggest bedroom, then the eldest first one each, small children of a sex
	## sharing when rooms run out, and the rest sharing the least crowded room
	var out := {}
	if beds.is_empty():
		return out
	var load := {}
	var next := 0
	var couple := []
	var rest := []
	for mm in members:
		if mm.role == "head" or mm.role == "partner":
			couple.append(mm)
		else:
			rest.append(mm)
	for mm in couple:
		out[mm.pid] = beds[0][0]
	if not couple.is_empty():
		load[beds[0][0]] = couple.size()
		next = 1
	rest.sort_custom(func(a, b): return int(a.pinned.age) > int(b.pinned.age))
	for mm in rest:
		if next < beds.size():
			out[mm.pid] = beds[next][0]
			load[beds[next][0]] = 1
			next += 1
		else:
			var best = beds[0][0]
			var bl := 1 << 30
			for bd in beds.slice(1 if not couple.is_empty() and beds.size() > 1 else 0):
				if int(load.get(bd[0], 0)) < bl:
					bl = int(load.get(bd[0], 0))
					best = bd[0]
			out[mm.pid] = best
			load[best] = int(load.get(best, 0)) + 1
	return out


# -- questions -------------------------------------------------------------------------------------------------------

static func _covers(p: Dictionary, day: int, hour: float) -> bool:
	## a post is on at (day, hour): its shift that day, or the night shift that started the day before (a night shift
	## belongs to the day it starts)
	for back: int in [0, 1]:
		var d: int = day - back
		var h: float = hour + 24.0 * back
		if h < float(p.shift[0]) or h >= float(p.shift[1]):
			continue
		var wd: String = DAYS[posmod(d, 7)]
		var days: String = p.get("days", "mon-fri")
		if days == "mon-fri" and posmod(d, 7) >= 5:
			continue
		if days == "mon-sat" and posmod(d, 7) == 6:
			continue
		if p.has("off") and wd in p.off:
			continue
		return true
	return false


static func on_duty(seed: int, place: String, day: int, hour: float) -> Array:
	## place: a business unit "C-015/B0" or a room "C-077#R1F0_0" (the posts whose room it is)
	var bid := place.get_slice("/", 0).get_slice("#", 0)
	var S := _indexed(solve(seed, town_of(bid)))
	var out := []
	var seen := {}
	for post in S._posts_at.get(place, []):
		if seen.has(post):
			continue
		seen[post] = true
		var p: Dictionary = S.posts[post]
		if _covers(p, day, hour):
			out.append({"post": post, "pid": p.pid, "role": p.role, "room": p.room, "vacant": S.vacant.get(post, "")})
	return out


static func roster(seed: int, uid: String) -> Array:
	var S := _indexed(solve(seed, town_of(uid.get_slice("/", 0))))
	var out := []
	for post in S._posts_at.get(uid, []):
		var p: Dictionary = S.posts[post]
		if p.uid == uid:
			out.append({"post": post, "pid": p.pid, "role": p.role, "room": p.room, "shift": p.shift, "days": p.days,
				"off": p.get("off", []), "vacant": S.vacant.get(post, "")})
	return out


static func person(seed: int, pid: String) -> Dictionary:
	var bid := pid.get_slice(":", 0)
	return solve(seed, town_of(bid)).people.get(pid, {})


static func residents(seed: int, bid: String, uid := "") -> Array:
	var S := _indexed(solve(seed, town_of(bid)))
	var out := []
	for hk in S._homes_of.get(bid, []):
		if uid == "" or hk.get_slice("/", 1) == uid:
			out.append_array(S.homes[hk])
	return out


static func rooms_of(seed: int, pid: String) -> Dictionary:
	var P := person(seed, pid)
	if P.is_empty():
		return {}
	return {"home": "%s/%s" % [P.home, P.unit], "bed": P.bed, "work": P.get("work", ""), "post": P.get("post", ""),
		"post_room": P.get("post_room", ""), "school": P.get("school", "")}


static func who(seed: int, place: String, day: int, hour: float) -> Array:
	## who is in a place now: residents at home (NpcLife's day), the staff on duty there
	var bid := place.get_slice("/", 0).get_slice("#", 0)
	var out := []
	var life := NpcLife.shared()
	var room := place.get_slice("#", 1) if place.contains("#") else ""
	for pid in residents(seed, bid, place.get_slice("/", 1) if place.contains("/") else ""):
		var st := life.state(pid, day, hour)
		if st.get("kind", "home") == "home":
			var P := person(seed, pid)
			if room == "" or P.bed == place:
				out.append({"pid": pid, "why": "home"})
	for p in on_duty(seed, place, day, hour):
		if p.pid != "":
			out.append({"pid": p.pid, "why": "on duty: " + str(p.role)})
	if not place.contains("#") and not place.contains("/"):
		var m := building(bid)
		for uid in m.get("units", {}):
			if m.units[uid].type == "business":
				for p in on_duty(seed, "%s/%s" % [bid, uid], day, hour):
					if p.pid != "":
						out.append({"pid": p.pid, "why": "on duty: " + str(p.role)})
	return out


static func where(seed: int, pid: String, day: int, hour: float) -> Dictionary:
	var P := person(seed, pid)
	if P.is_empty():
		return {}
	var st := NpcLife.shared().state(pid, day, hour)
	match str(st.get("kind", "home")):
		"home":
			return {"building": P.home, "unit": P.unit, "room": P.bed, "doing": "home"}
		"at":
			var uid := str(st.get("uid", ""))
			if uid == P.get("work", "") and P.has("post_room"):
				return {"building": uid.get_slice("/", 0), "unit": uid, "room": P.post_room, "doing": str(st.get("what", "work"))}
			return {"building": uid.get_slice("/", 0), "unit": uid, "room": "", "doing": str(st.get("what", ""))}
	return {"building": "", "unit": "", "room": "", "doing": str(st.get("kind", ""))}
