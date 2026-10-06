extends RefCounted
class_name NpcLife

## People's days (research/lives/): everyone has a home, most a workplace or a school, and a
## regular place of each kind (their grocery, their barber, their bar, their church) -- baked by
## remake/tools/bake_lives.gd. A day's plan is a pure function of (person, day): work by the
## occupation's hours and the workplace's days, school, worship, and errands and leisure drawn from
## each place type's visit rates (npc_places.json), shifted by personality and addictions. Between
## stays they travel -- walking, cycling, driving, the bus or transit -- by distance, car access and
## their usual commute.
##
##   var life := NpcLife.shared()
##   life.timeline(pid, day)       -> [{t0, t1, kind: "home"|"at"|"trip"|"out", uid, what, from, to, mode}]
##   life.state(pid, day, hour)    -> the segment now (hours past 24 run into the next day)
##   life.card(pid, day, hour)     -> the [LIFE] lines of the dialogue prompt

const PATH := "res://remake/characters/npc_lives.json"
const HOURS := {                                   # occupation hours column -> (start, end)
	"day": Vector2(9.0, 17.0), "early": Vector2(6.0, 14.0), "evening": Vector2(16.0, 24.0),
	"school": Vector2(8.0, 15.5)}
const SHIFTS := [Vector2(6.0, 14.0), Vector2(14.0, 22.0), Vector2(22.0, 30.0)]
const SPEED := {"walk": 1.3, "bike": 4.2, "car": 10.0, "transit": 5.0, "bus": 6.0}      # m/s door to door
const OVERHEAD := {"walk": 0.0, "bike": 2.0, "car": 4.0, "transit": 8.0, "bus": 5.0}    # min: parking, waiting
const DETOUR := 1.3                                # street distance over straight-line
const NOT_ERRANDS := ["school", "classes", "childcare", "worship", "visit_elder"]
const LATE := ["drinks", "film", "games", "dinner_out", "meeting"]

static var _shared: NpcLife
var seed := 1
var people: Dictionary
var _cache := {}                                  # "pid|day" -> timeline
var by_home := {}                                 # building/flat id -> [pid]
var by_unit := {}                                 # uid -> [pid] (works there, studies there or goes regularly)
var _occ_hours: Dictionary


static func shared() -> NpcLife:
	if _shared == null:
		_shared = NpcLife.new()
		_shared._load()
	return _shared


func _load() -> void:
	var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(PATH))
	seed = int(d.seed)
	people = d.people
	NpcPlaces.load_all()
	for pid in people:
		var P: Dictionary = people[pid]
		_add(by_home, P.home, pid)
		if P.has("work"):
			_add(by_unit, P.work, pid)
		if P.has("school"):
			_add(by_unit, P.school, pid)
		for p in P.reg:
			_add(by_unit, P.reg[p], pid)
		NpcPlaces.register_door(P.home, Vector2(float(P.door[0]), float(P.door[1])))
	var occ: Dictionary = NpcTraits.shared().tables.occupations
	var col := (occ._cols as Array).find("hours")
	for o in occ:
		if o != "_cols":
			_occ_hours[o] = occ[o][col]


static func _add(d: Dictionary, k: String, pid: String) -> void:
	if not d.has(k):
		d[k] = []
	if not (d[k] as Array).has(pid):
		d[k].append(pid)


func person(pid: String) -> Dictionary:
	return people.get(pid, {})


func _r(pid: String, key: String) -> NpcRng:
	return NpcRng.for_trait(seed, pid, key)


# -- travel ----------------------------------------------------------------------------------------------

func place_of(P: Dictionary, uid: String) -> String:
	## The building (or flat) a stay happens in: "" is home.
	return P.home if uid == "" else str(NpcPlaces.unit(uid).get("building", P.home))


func door(P: Dictionary, uid: String) -> Vector2:
	if uid == "":
		return Vector2(float(P.door[0]), float(P.door[1]))
	var u := NpcPlaces.unit(uid)
	return Vector2(float(u.door[0]), float(u.door[1]))


func mode(pid: String, P: Dictionary, metres: float, purpose: String, day: int) -> String:
	var commute: String = P.commute
	var car: String = P.car
	if metres < 450.0:
		return "walk"
	if purpose == "work" or purpose == "school" or purpose == "classes" or purpose == "childcare":
		match commute:
			"drive", "carpool", "driven":
				return "car"
			"school_bus":
				return "bus"
			"transit":
				return "transit"
			"bike":
				return "bike" if metres < 9000.0 else "transit"
			"walk":
				return "walk" if metres < 2500.0 else "transit"
	# a bicycle for the short trips: about a third of people keep one (research/lives/06), and in
	# these small towns they use it, car or no car
	var age := int(P.age)
	if age >= 10 and age <= 75 and P.mobility == "none" and _r(pid, "owns_bike").rand() < 0.35 and metres < 4000.0:
		if _r(pid, "bike:%d:%d" % [day, int(metres)]).rand() < (0.6 if car == "none" else 0.2):
			return "bike"
	if car == "own_car" or (car == "shared_car" and _r(pid, "car:%d" % day).rand() < 0.6):
		return "car" if metres > 900.0 or int(P.age) >= 70 else "walk"
	if int(P.age) < 12:
		return "car" if metres > 1200.0 else "walk"               # with a parent
	if commute == "bike" and metres < 7000.0:
		return "bike"
	return "walk" if metres < 1600.0 else "transit"


func travel_h(m: String, metres: float) -> float:
	return (metres * DETOUR / float(SPEED[m]) / 60.0 + float(OVERHEAD[m])) / 60.0


# -- the day's plan --------------------------------------------------------------------------------------

func stays(pid: String, day: int) -> Array:
	## Where they'll be, away from home, on day `day` (0 = a Monday): [{t0, t1, uid, what}] in
	## hours of that day (a night shift runs past 24), sorted, not overlapping.
	var P := person(pid)
	if P.is_empty():
		return []
	var wd := posmod(day, 7)
	var week := floori(day / 7.0)
	var out: Array = []
	var occ: String = P.occupation
	var jit := _r(pid, "habit")                                      # the same every day: their habits
	var habit := (jit.rand() - 0.5) * (1.4 - float(P.C))            # conscientious people keep closer to the clock
	var today := _r(pid, "day:%d" % day)
	# work
	if P.has("work"):
		var t := NpcPlaces.kind_of(P.work)
		var hrs: String = _occ_hours.get(occ, "day")
		var span: Vector2 = HOURS.get(hrs, HOURS.day)
		if hrs == "shift":
			span = SHIFTS[posmod(week + int(jit.rand() * 3.0), 3)]
		if occ == "bartender":
			span = Vector2(17.0, 25.0)
		# within the place's own hours: no night shift at a school
		var open_ := NpcPlaces.hours_of(t) if not t.is_empty() else Vector2(0.0, 24.0)
		if open_.y - open_.x < 23.9 and (span.x < open_.x - 1.0 or span.y > open_.y + 1.0):
			var st_ := clampf(span.x, open_.x - 0.5, maxf(open_.x - 0.5, open_.y - 8.0))
			span = Vector2(st_, minf(st_ + 8.0, open_.y + 0.5))
		var works := true
		var days: String = t.get("hours", {}).get("days", "mon-fri")
		if days == "mon-fri":
			works = wd < 5
		else:
			var off := int(_r(pid, "offday").rand() * 7.0)          # two days off in a row, their own
			works = wd != off and wd != posmod(off + 1, 7)
			if days == "mon-sat" and wd == 6:
				works = false
		if P.commute == "remote" and today.rand() < 0.65:
			works = false                                         # a day working from home
		if t.get("category", "") == "farm":
			works = wd != 6 or today.rand() < 0.6                 # a farm's work doesn't keep Sundays
		if works:
			var s := span.x + habit * 0.5 + (today.rand() - 0.5) * 0.25
			out.append({"t0": s, "t1": s + (span.y - span.x) + (today.rand() - 0.5) * 0.4, "uid": P.work, "what": "work"})
	# school
	if P.has("school") and wd < 5:
		match occ:
			"student":
				out.append({"t0": 8.0, "t1": 15.25, "uid": P.school, "what": "school"})
			"preschool":
				out.append({"t0": 8.0 + habit * 0.5, "t1": 16.5 + habit * 0.5, "uid": P.school, "what": "childcare"})
			"university_student":
				var s2 := 9.0 + floorf(today.rand() * 3.0)
				out.append({"t0": s2, "t1": s2 + 3.0 + floorf(today.rand() * 4.0), "uid": P.school, "what": "classes"})
	# worship
	var reg: Dictionary = P.reg
	if reg.has("worship") and wd == 6:
		if P.worship == "weekly" or (P.worship == "monthly" and posmod(week + int(jit.rand() * 4.0), 4) == 0):
			out.append({"t0": 10.0, "t1": 11.25, "uid": reg.worship, "what": "worship"})
	# errands and leisure
	var types := NpcPlaces.types()
	var free := _free(out)
	var adds: Array = P.addictions
	var purposes: Array = reg.keys()
	purposes.sort()
	for purpose in purposes:
		if purpose in NOT_ERRANDS:
			continue
		var uid: String = reg[purpose]
		var t: Dictionary = NpcPlaces.kind_of(uid)
		var v: Dictionary = {}
		for vv in t.visits:
			if vv.purpose == purpose:
				v = vv
		if v.is_empty():
			continue
		var p := float(v.per_week) / 7.0
		for a in t.addictions:
			if a in adds:
				p *= 3.0
		if t.third_place:
			p *= 0.4 + 1.2 * float(P.E)
		if wd >= 5 and t.category in ["retail", "leisure", "food", "drink"]:
			p *= 1.4
		if int(P.age) < 13 and not (purpose in ["snack", "outing", "ride", "games", "film"]):
			p *= 0.15                                             # errands are the grown-ups'
		if today.rand() >= p:
			continue
		var hrs := NpcPlaces.hours_of(t)
		var dwell := float(v.dwell_min) / 60.0 * (0.7 + today.rand() * 0.6)
		var lo := maxf(hrs.x, 7.0 if not (purpose in LATE) else 17.0)
		var hi := minf(hrs.y, 21.5 if not (purpose in LATE) else 24.5) - dwell
		if hi <= lo or not NpcPlaces.open_on(t, day):
			continue
		for attempt in 5:
			var s := lo + today.rand() * (hi - lo)
			if _fits(free, s - 0.5, s + dwell + 0.5):
				out.append({"t0": s, "t1": s + dwell, "uid": uid, "what": purpose})
				free = _free(out)
				break
	# out of doors near home: a stroll, children at play
	var p_out := 0.3 + 0.2 * float(P.E) + (0.2 if occ == "retired" else 0.0) + (0.25 if int(P.age) < 13 else 0.0)
	if today.rand() < p_out and int(P.age) >= 4:
		var s3 := 8.0 + today.rand() * 12.0 if int(P.age) >= 13 else 15.5 + today.rand() * 3.0
		var len3 := 0.3 + today.rand() * 0.7
		if _fits(free, s3 - 0.2, s3 + len3 + 0.2):
			out.append({"t0": s3, "t1": s3 + len3, "uid": "", "what": "stroll"})
	out.sort_custom(func(a, b): return float(a.t0) < float(b.t0))
	return out


func _free(stays_: Array) -> Array:
	var busy := []
	for s in stays_:
		busy.append(Vector2(float(s.t0), float(s.t1)))
	return busy


func _fits(busy: Array, a: float, b: float) -> bool:
	for r in busy:
		if a < (r as Vector2).y and b > (r as Vector2).x:
			return false
	return true


func timeline(pid: String, day: int) -> Array:
	## The day as segments from 0 to 24 (and past, for a night shift): home, trips, stays, strolls.
	var key := "%s|%d" % [pid, day]
	if _cache.has(key):
		return _cache[key]
	if _cache.size() > 30000:                                   # (above the station's population: a cache that clears thrashes -- Calder, 2026-10-06)
		_cache.clear()
	var P := person(pid)
	var segs: Array = []
	var here := ""                                               # "" = home
	var came := ""                                               # how they got here (a car or bike comes along)
	var t := 0.0
	var ss := stays(pid, day)
	for i in ss.size():
		var s: Dictionary = ss[i]
		if s.what == "stroll":
			if here != "":
				continue
			segs.append({"t0": t, "t1": float(s.t0), "kind": "home", "uid": "", "what": "home"})
			segs.append({"t0": float(s.t0), "t1": float(s.t1), "kind": "out", "uid": "", "what": "stroll"})
			t = float(s.t1)
			continue
		var d := NpcPlaces.dist(door(P, here), door(P, s.uid))
		var m := _onward(came, mode(pid, P, d, s.what, day))
		var tr := travel_h(m, d)
		# a long gap: home in between
		if here != "":
			var dh := NpcPlaces.dist(door(P, here), door(P, ""))
			var mh := _onward(came, mode(pid, P, dh, "home", day))
			var dn := NpcPlaces.dist(door(P, ""), door(P, s.uid))
			var mn := mode(pid, P, dn, s.what, day)
			if float(s.t0) - t > travel_h(mh, dh) + travel_h(mn, dn) + 0.75:
				segs.append({"t0": t, "t1": t + travel_h(mh, dh), "kind": "trip", "uid": "", "from": here, "to": "", "mode": mh, "what": "home"})
				t += travel_h(mh, dh)
				here = ""
				d = dn
				m = mn
				tr = travel_h(m, d)
		var leave := maxf(t, float(s.t0) - tr)
		if here == "" and leave > t:
			segs.append({"t0": t, "t1": leave, "kind": "home", "uid": "", "what": "home"})
		if here != s.uid:
			segs.append({"t0": leave, "t1": leave + tr, "kind": "trip", "uid": s.uid, "from": here, "to": s.uid, "mode": m, "what": s.what})
		var arrive := leave + (tr if here != s.uid else 0.0)
		if here != s.uid:
			came = m
		segs.append({"t0": arrive, "t1": maxf(arrive, float(s.t1)), "kind": "at", "uid": s.uid, "what": s.what})
		t = maxf(arrive, float(s.t1))
		here = s.uid
	if here != "":
		var d2 := NpcPlaces.dist(door(P, here), door(P, ""))
		var m2 := _onward(came, mode(pid, P, d2, "home", day))
		segs.append({"t0": t, "t1": t + travel_h(m2, d2), "kind": "trip", "uid": "", "from": here, "to": "", "mode": m2, "what": "home"})
		t += travel_h(m2, d2)
	segs.append({"t0": t, "t1": maxf(t, 24.0), "kind": "home", "uid": "", "what": "home"})
	_cache[key] = segs
	return segs


static func _onward(came: String, wanted: String) -> String:
	## Whoever drove or cycled somewhere leaves the same way.
	return came if came == "car" or came == "bike" else wanted


func state(pid: String, day: int, hour: float) -> Dictionary:
	## The segment this person is in at `hour` of `day`, with `frac` along it. Yesterday's night
	## shift or late drink runs into the small hours.
	for dd in [day - 1, day]:
		var h := hour + (24.0 if dd == day - 1 else 0.0)
		var tl := timeline(pid, dd)
		for s in tl:
			if h >= float(s.t0) and h < float(s.t1):
				if dd == day - 1 and s.kind == "home" and s == tl[tl.size() - 1]:
					continue                                           # yesterday's evening at home: today's plan decides
				var out: Dictionary = s.duplicate()
				out.frac = (h - float(s.t0)) / maxf(float(s.t1) - float(s.t0), 1e-6)
				return out
	return {"t0": 0.0, "t1": 24.0, "kind": "home", "uid": "", "what": "home", "frac": 0.0}


# -- words for the dialogue prompt ------------------------------------------------------------------------

func place_words(uid: String) -> String:
	if uid == "":
		return "home"
	var u := NpcPlaces.unit(uid)
	var t := NpcPlaces.kind_of(uid)
	var s := str(u.get("settlement", ""))
	return "the %s%s" % [str(t.get("name", "place")).to_lower(), (" in " + s) if s != "" else ""]


func card(pid: String, day: int, hour: float) -> String:
	## [LIFE]: home, work, how they get about, money, habits, and today -- the concrete daily life
	## the dialogue model can draw on (only this person's own life; they know their own days).
	var P := person(pid)
	if P.is_empty():
		return ""
	var lines := []
	var home := "a flat over a shop" if str(P.home).contains("/") else "a house"
	lines.append("[LIFE]  lives in %s%s" % [home, (" in " + str(P.settlement)) if str(P.settlement) != "" else ""])
	if P.has("work"):
		var hrs: String = _occ_hours.get(P.occupation, "day")
		lines.append("        works as a %s at %s (%s hours)" % [str(P.occupation).replace("_", " "), place_words(P.work), hrs])
	elif P.has("school"):
		lines.append("        goes to %s" % place_words(P.school))
	var getting := {"drive": "drives", "carpool": "shares a ride", "transit": "takes the tram", "walk": "walks", "bike": "cycles",
		"remote": "works from home mostly", "school_bus": "takes the school bus", "driven": "is driven", "none": "gets about on foot or by car"}
	lines.append("        %s; %s" % [getting.get(P.commute, "gets about"), {"own_car": "has a car", "shared_car": "shares the household car", "none": "has no car"}.get(P.car, "")])
	lines.append("        money: %s" % str(P.finances).replace("_", " "))
	var regs := []
	for p in ["groceries", "coffee", "drinks", "haircut", "hair", "worship", "meal"]:
		if (P.reg as Dictionary).has(p):
			regs.append("%s at %s" % [p, place_words(P.reg[p])])
	if not regs.is_empty():
		lines.append("        regular places: " + ", ".join(regs))
	if not (P.addictions as Array).is_empty():
		lines.append("        private struggles (never named unless trust is high): " + ", ".join(P.addictions).replace("_", " "))
	var today := []
	for s in stays(pid, day):
		today.append("%s %s" % [_clock(float(s.t0)), "a walk nearby" if s.what == "stroll" else "%s at %s" % [str(s.what).replace("_", " "), place_words(s.uid)]])
	if not today.is_empty():
		lines.append("        today: " + "; ".join(today))
	var now := state(pid, day, hour)
	lines.append("        right now: %s" % _now_words(now))
	return "\n".join(lines)


func _now_words(s: Dictionary) -> String:
	match str(s.kind):
		"trip":
			return "on the way %s (%s)" % ["home" if s.to == "" else "to " + place_words(s.to), s.mode]
		"at":
			return "%s at %s" % [str(s.what).replace("_", " "), place_words(s.uid)]
		"out":
			return "out for a walk near home"
	return "at home"


static func _clock(h: float) -> String:
	var m := int(round(h * 60.0))
	return "%02d:%02d" % [posmod(m / 60, 24), m % 60]
