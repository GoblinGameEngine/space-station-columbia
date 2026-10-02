extends Node3D
class_name NpcPopulation

## The people of the station, near the player (procedural_npcs.md 2): nobody is stored.  Around the
## player, the homes' households (NpcHouseholds, a pure function of the building, and the flats over
## shops) give who lives here, and the places' staff and regulars (NpcLife) who works and shops
## here.  Where each of them is now is their day's plan (NpcLife.state, a pure function of person,
## day and hour): leaving home for work, walking the streets to the grocery, arriving by car at the
## kerb, out for a stroll, lingering at the bandstand.  Those people are generated (traits on the
## main thread, bodies and clothes on the worker pool) and play that part of their day.  Leave and
## come back and the same people are there, doing what their day says.  Using one of them (the
## interact key) is "contact": their persona (L2) is made then, not before.  Without a lives bake
## (remake/tools/bake_lives.gd) residents just step out for random walks.
##
##   var pop := NpcPopulation.new(); pop.player = player; add_child(pop)
##   DevBridge: root.get_node("RemakeStation/NpcPopulation").stats()

const SPAWN_R := 70.0
const DESPAWN_R := 100.0
const MAX_LIVE := 24
const MAX_BUILDS := 3            # geometry jobs in flight on the worker pool
const CELL := 40.0               # the building index's cell (m)
const TICK := 0.5

@export var world_seed := 1
var player: Node3D
var live := {}                   # pid -> {npc, anim, zone, plan, i, wait, s, x, speed, pop, member}
var _pending := {}               # pid -> {task, data: {}}
var _gone_in := {}               # pid -> the half-hour slot they went back indoors in (not out again till the next)
const PERSONAL := 0.75           # m, centre to centre: people keep at least this far apart (couples leave side by side)
var _index := {}                 # Vector2i(cell s, cell x) -> [building]
var _unit_index := {}            # Vector2i(cell s, cell x) -> [place unit id]
var _by_id := {}                 # building id -> structure
var _buildings: Array = []
var _here := Vector2.ZERO        # the player (s, x), for _trip_pos
var _next := {}                  # pid -> day * 24 + hour before which there's nothing of theirs to see
var _life: NpcLife               # everyone's days (null without a lives bake: the old random walks)
const OUTDOORS := ["park_pavilion", "food_stand", "amusement"]      # places whose visitors stay in view
const BIKE_SPEED := 4.2          # m/s, a town cyclist
var _house_cache := {}           # building id -> NpcHouseholds.of_building (tiny; rebuilt freely)
var _tick := 0.0
var _clock: Node
var built_count := 0
var out_boost := 0.0             # (tests: added to everyone's chance of being out)
var drawing_rate := 1            # 1 smooth; 2 twos; 3 threes (Ghibli walks are mostly on threes --
                                 # research/animation/principles.md 4); set_drawing_rate() to try
var assemble_ms_max := 0.0
var assemble_ms: Array = []


func _ready() -> void:
	name = "NpcPopulation"
	# warm the static caches the worker threads read (JSON, trig tables, weight lists)
	NpcTraits.shared()
	NpcGarments.data()
	NpcHouseholds.data()
	for n in [9, 10, NpcBody.RING, NpcBody.RING + 4, NpcBody.HEAD_AROUND, 40]:
		NpcBody._table(n)
	var st: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://remake/placement.json"))
	var homes: Array = []
	for b in st.structures:
		_by_id[b.id] = b
		if NpcHouseholds.is_home(b):
			homes.append(b)
	if FileAccess.file_exists(NpcLife.PATH):
		_life = NpcLife.shared()
		homes.append_array(NpcPlaces.flats(st.structures))
		for uid in NpcPlaces.units():
			var u: Dictionary = NpcPlaces.unit(uid)
			var k := _cell(float(u.door[0]), float(u.door[1]))
			if not _unit_index.has(k):
				_unit_index[k] = []
			_unit_index[k].append(uid)
	for b in homes:
		_buildings.append(b)
		var k := _cell(float(b.s), float(b.x))
		if not _index.has(k):
			_index[k] = []
		_index[k].append(b)
	_clock = get_tree().current_scene.get_node_or_null("DaySkySystem")
	# one hidden person during loading: the character shader's pipelines compile now, not as the
	# first resident steps out (that first assembly cost ~25 ms; the rest ~1 ms)
	var warm := NpcCharacter.create(NpcTraits.shared().person(world_seed, "warmup:0", ["L0", "L1"]), "warmup:0", world_seed)
	add_child(warm)
	warm.position = Vector3(0, -500, 0)
	get_tree().create_timer(1.0).timeout.connect(warm.queue_free)


static func _cell(s: float, x: float) -> Vector2i:
	return Vector2i(floori(fposmod(s, StationGeo.CIRC) / CELL), floori(x / CELL))


func hour() -> float:
	return (float(_clock.time_of_day) if _clock else 0.4) * 24.0


func today() -> int:
	return int(_clock.get("day")) if _clock and _clock.get("day") != null else 0


func _process(delta: float) -> void:
	Prof.begin("population")
	_tick_population(delta)
	Prof.end("population")


func _tick_population(delta: float) -> void:
	if player == null:
		return
	_collect()
	for pid in live:
		var rg = live[pid].get("rag")
		if rg != null and (rg as NpcRagdoll).down:
			continue                                               # on the ground: the physics has them
		_move(live[pid], delta)
	_personal_space(delta)
	_tick -= delta
	if _tick > 0.0:
		return
	_tick = TICK
	_refresh()


# -- who is out -------------------------------------------------------------------------------------

func out_now(pid: String, v0: Dictionary) -> bool:
	## A pure function of the person and the half-hour: whether they're out of doors now.
	var h := hour()
	var slot := floori(h * 2.0)
	var age := float(v0.get("age", 30))
	var p := 0.0
	if h < 6.0 or h >= 22.0:
		p = 0.02
	elif h < 9.0:
		p = 0.14
	elif h < 17.0:
		p = 0.22 if not (age >= 6.0 and age < 18.0) else 0.06          # children are at school
	elif h < 21.0:
		p = 0.3
	else:
		p = 0.1
	if age >= 65.0 and h >= 8.0 and h < 12.0:
		p += 0.12                                                       # elders' morning errands
	p += out_boost
	return NpcRng.for_trait(world_seed, pid, "out:%d" % slot).rand() < p


func _refresh() -> void:
	var pp := player.global_position
	var ps := StationGeo.s_of(pp)
	var px := pp.x
	# despawn the far
	for pid in live.keys():
		var e: Dictionary = live[pid]
		if _dist(ps, px, e.s, e.x) > DESPAWN_R:
			_despawn(pid)
	# who should be here: residents of buildings in range who are out now, nearest first
	var want := []
	var c := _cell(ps, px)
	var r := ceili(SPAWN_R / CELL)
	for i in range(-r, r + 1):
		for j in range(-r, r + 1):
			for b in _index.get(Vector2i(posmod(c.x + i, ceili(StationGeo.CIRC / CELL)), c.y + j), []):
				var d := _dist(ps, px, float(b.s), float(b.x))
				if d > SPAWN_R:
					continue
				var hh: Dictionary = _house_cache.get(b.id, {})
				if hh.is_empty():
					hh = NpcHouseholds.of_building(world_seed, b)
					_house_cache[b.id] = hh
				for m in hh.members:
					if _life and _life.people.has(m.pid):
						_consider(want, m.pid, ps, px)
					elif out_now(m.pid, m.pinned) and str(_gone_in.get(m.pid, "")) != str(floori(hour() * 2.0)):
						want.append([d, m, b, hh.population, {}])
			if _life:                                          # the places: who works or shops here
				for uid in _unit_index.get(Vector2i(posmod(c.x + i, ceili(StationGeo.CIRC / CELL)), c.y + j), []):
					for pid in _life.by_unit.get(uid, []):
						_consider(want, pid, ps, px)
	var seen := {}
	var uniq := []
	for w in want:
		if not seen.has(w[1].pid):
			seen[w[1].pid] = true
			uniq.append(w)
	want = uniq
	want.sort_custom(func(a, b): return a[0] < b[0])
	var n := 0
	for w in want:
		if n >= MAX_LIVE:
			break
		n += 1
		var pid: String = w[1].pid
		if live.has(pid) or _pending.has(pid):
			continue
		if _pending.size() >= MAX_BUILDS:
			continue
		_spawn(w[1], w[2], w[3], w[4])
	# home: through the door and indoors (the plan's last step is inside the house) -- gone until
	# the next half-hour
	for pid in live.keys():
		if live[pid].i >= (live[pid].plan as Array).size() and not _pending.has(pid):
			_gone_in[pid] = str(live[pid].get("sig", floori(hour() * 2.0)))
			_despawn(pid)
	# those no longer wanted (gone home) leave when out of the player's sight
	var keep := {}
	for w in want.slice(0, MAX_LIVE):
		keep[w[1].pid] = true
	for pid in live.keys():
		if not keep.has(pid) and live[pid].i >= (live[pid].plan as Array).size():
			_despawn(pid)


# -- their days (NpcLife) ------------------------------------------------------------------------------

func _sig(seg: Dictionary) -> String:
	return "%d|%s|%.3f" % [int(seg.get("day", today())), str(seg.kind), float(seg.t0)]


func _consider(want: Array, pid: String, ps: float, px: float) -> void:
	## If this part of their day happens near the player, they're wanted: [distance, member,
	## building, population, segment].  Time runs 30x faster than walking does (an hour is two
	## minutes), so a trip on foot is on the street for as long as it takes to walk in real time,
	## from its start by the clock -- the schedule says when they set off, their legs how long it takes.
	var day := today()
	var h := hour()
	if float(_next.get(pid, -1.0)) > day * 24.0 + h:
		return                                                          # indoors till later
	var P := _life.person(pid)
	var here := Vector2(ps, px)
	_here = here
	var b: Dictionary = _home_struct(P)
	var m := {"pid": pid, "pinned": {"age": int(P.age), "sex": P.sex, "given_name": P.get("given", ""), "surname": P.get("surname", ""),
		"lineage": P.get("lineage", ""), "name_heritage": P.get("name_heritage", "")}}
	var s := _life.state(pid, day, h)
	_next[pid] = _next_event(pid, day, h)
	if s.kind == "out" and str(_gone_in.get(pid, "")) != _sig(s):
		var d := NpcPlaces.dist(here, _life.door(P, ""))
		if d < SPAWN_R:
			want.append([d, m, b, P.pop, s])
		return
	if s.kind == "at" and str(NpcPlaces.unit(s.uid).get("type", "")) in OUTDOORS and str(_gone_in.get(pid, "")) != _sig(s):
		var d2 := NpcPlaces.dist(here, _life.door(P, s.uid))
		if d2 < SPAWN_R:
			want.append([d2, m, b, P.pop, s])
		return
	for dd in [day, day - 1]:
		var hh := h + (24.0 if dd == day - 1 else 0.0)
		for seg in _life.timeline(pid, dd):
			if seg.kind != "trip" or float(seg.t0) > hh or float(seg.t0) < hh - 4.0:
				continue
			var sg: Dictionary = seg.duplicate()
			sg.day = dd
			if str(_gone_in.get(pid, "")) == _sig(sg):
				continue
			var p := _trip_pos(P, sg, hh)
			if p == Vector2.INF:
				continue
			var d3 := NpcPlaces.dist(here, p)
			if d3 < SPAWN_R:
				want.append([d3, m, b, P.pop, sg])
				return


func _next_event(pid: String, day: int, h: float) -> float:
	## When (day * 24 + hour) they might next be seen: now if something is under way (a walk takes
	## real time, so it's looked at again every refresh or so), else the start of the next trip or
	## stroll.
	for dd in [day - 1, day]:
		var hh := h + (24.0 if dd == day - 1 else 0.0)
		for seg in _life.timeline(pid, dd):
			if seg.kind == "home" or float(seg.t0) > hh:
				continue
			var outdoors: bool = seg.kind == "out" or seg.kind == "at" and str(NpcPlaces.unit(seg.uid).get("type", "")) in OUTDOORS
			if seg.kind == "trip" and hh - float(seg.t0) < 4.0 or outdoors and hh < float(seg.t1):
				return day * 24.0 + h + 0.03
	for dd in [day, day + 1]:
		for seg in _life.timeline(pid, dd):
			var t0 := float(seg.t0) + (24.0 if dd == day + 1 else 0.0)
			if (seg.kind == "trip" or seg.kind == "out" or seg.kind == "at") and t0 > h:
				return day * 24.0 + t0
	return day * 24.0 + 48.0


func _home_struct(P: Dictionary) -> Dictionary:
	var id: String = P.home
	if _by_id.has(id):
		return _by_id[id]
	var b: Dictionary = (_by_id.get(id.split("/")[0], {}) as Dictionary).duplicate()
	b.id = id
	b.kind = "flat"
	return b


func _trip_pos(P: Dictionary, s: Dictionary, hh: float) -> Vector2:
	## Where on the trip they are at hour `hh` (of the trip's day), if on foot within sight of it
	## (and sets s.frac): walkers (and, for now, cyclists) along their route at walking pace;
	## drivers and riders only for the door-to-kerb walk at either end.
	var game_h_per_s := 24.0 / DaySkySystem.DAY_LENGTH_SECONDS
	if s.mode == "walk" or s.mode == "bike":
		var bike: bool = s.mode == "bike"
		# (a cheap look first: could the way between the two doors come near the player at all?)
		var a := _life.door(P, s.from)
		var b := _life.door(P, s.to)
		var ab := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)
		var ap := Vector2(StationGeo.wrap_ds(_here.x - a.x), _here.y - a.y)
		var t := clampf(ap.dot(ab) / maxf(ab.length_squared(), 1e-6), 0.0, 1.0)
		if (ap - ab * t).length() > SPAWN_R + 0.35 * ab.length():
			return Vector2.INF
		var r := NpcPlaces.route(_life.place_of(P, s.from), _life.place_of(P, s.to), Vector2.INF, Vector2.INF, NpcPlaces.BIKE_EDGE if bike else NpcPlaces.PAVEMENT)
		var L := NpcPlaces.route_length(r)
		var dur := L / (BIKE_SPEED if bike else 1.3) * game_h_per_s
		if hh - float(s.t0) >= dur:
			return Vector2.INF
		s.frac = (hh - float(s.t0)) / maxf(dur, 1e-6)
		return _pos_along(r, float(s.frac) * L)
	var walk := 40.0 * game_h_per_s                                  # ~40 s between door and kerb
	if hh - float(s.t0) < walk:
		s.frac = 0.0
		return _life.door(P, s.from)
	if hh >= float(s.t1) and hh - float(s.t1) < walk:
		s.frac = 1.0
		return _life.door(P, s.to)
	return Vector2.INF


static func _pos_along(r: PackedVector2Array, at: float) -> Vector2:
	var left := at
	for i in r.size() - 1:
		var l := NpcPlaces.dist(r[i], r[i + 1])
		if left <= l:
			var t := left / maxf(l, 1e-6)
			return Vector2(fposmod(r[i].x + StationGeo.wrap_ds(r[i + 1].x - r[i].x) * t, StationGeo.CIRC), r[i].y + (r[i + 1].y - r[i].y) * t)
		left -= l
	return r[r.size() - 1]


func _inside(building: String, door: Vector2) -> Vector2:
	## Two steps through the door (a flat's is its shop's street door).
	var b: Dictionary = _by_id.get(building.split("/")[0], {})
	if b.is_empty():
		return door
	var yaw: float = b.yaw
	return door - Vector2(cos(yaw), -sin(yaw)) * 2.2


func _day_plan(pid: String, s: Dictionary) -> Array:
	## The waypoints for this part of their day (pauses as negative seconds, as in _plan).
	var P := _life.person(pid)
	var rng := NpcRng.for_trait(world_seed, pid, "plan:" + _sig(s))
	if s.kind == "at":                                                     # lingering out of doors
		var d := _life.door(P, s.uid)
		var secs := (float(s.t1) - hour()) / 24.0 * DaySkySystem.DAY_LENGTH_SECONDS
		var plan: Array = []
		while secs > 0.0 and plan.size() < 16:
			plan.append(d + Vector2(rng.rand() * 8.0 - 4.0, rng.rand() * 8.0 - 4.0))
			var w := 15.0 + rng.rand() * 45.0
			plan.append(-w)
			secs -= w + 5.0
		return plan
	var to_b := _life.place_of(P, s.to)
	var d0 := _life.door(P, s.from)
	var d1 := _life.door(P, s.to)
	if s.mode == "bike":
		# the road from kerb to kerb, at cycling pace; they wheel the bike in at the far end
		var rb := NpcPlaces.route(_life.place_of(P, s.from), to_b, Vector2.INF, Vector2.INF, NpcPlaces.BIKE_EDGE)
		var atb := float(s.frac) * NpcPlaces.route_length(rb)
		var planb: Array = [_pos_along(rb, atb)]
		var runb := 0.0
		for i in range(1, rb.size() - 2):
			runb += NpcPlaces.dist(rb[i - 1], rb[i])
			if runb > atb:
				planb.append(rb[i])
		if rb.size() >= 2:
			planb.append(rb[rb.size() - 2])
		return planb
	if s.mode == "walk":
		var r := NpcPlaces.route(_life.place_of(P, s.from), to_b)
		var at := float(s.frac) * NpcPlaces.route_length(r)
		var plan2: Array = [_pos_along(r, at)]
		var run := 0.0
		for i in r.size() - 1:
			run += NpcPlaces.dist(r[i], r[i + 1])
			if run > at:
				plan2.append(r[i + 1])
		plan2.append(_inside(to_b, d1))
		return plan2
	# by car, tram or bus: the walk between the door and the kerb
	if float(s.frac) < 0.5:
		var k0: Dictionary = _near_road(d0)
		return [d0, k0.side if not k0.is_empty() else d0, -(2.0 + rng.rand() * 4.0)]        # and away
	var k1: Dictionary = _near_road(d1)
	return [k1.side if not k1.is_empty() else d1, -(1.0 + rng.rand() * 2.0), d1, _inside(to_b, d1)]


func _dist(s0: float, x0: float, s1: float, x1: float) -> float:
	return Vector2(StationGeo.wrap_ds(s1 - s0), x1 - x0).length()


# -- making people ------------------------------------------------------------------------------------

func _spawn(m: Dictionary, b: Dictionary, pop: String, seg := {}) -> void:
	var v := NpcTraits.shared().person(world_seed, m.pid, ["L0", "L1"], pop, m.pinned)
	var job := {"v": v, "pid": m.pid, "b": b, "m": m, "pop": pop, "data": {}, "seg": seg}
	job.task = WorkerThreadPool.add_task(func(): job.data = NpcCharacter.prepare(v, m.pid, world_seed, "work"), false, "npc " + m.pid)
	_pending[m.pid] = job


func _collect() -> void:
	## Finished geometry jobs become people in the world (one per frame: the node and mesh upload
	## is the only main-thread cost).
	for pid in _pending.keys():
		var job: Dictionary = _pending[pid]
		if not WorkerThreadPool.is_task_completed(job.task):
			continue
		WorkerThreadPool.wait_for_task_completion(job.task)
		_pending.erase(pid)
		if job.data.is_empty():
			continue
		var t0 := Time.get_ticks_usec()
		var npc := NpcCharacter.from_prepared(job.data)
		add_child(npc)
		var ms := (Time.get_ticks_usec() - t0) / 1000.0
		assemble_ms_max = maxf(assemble_ms_max, ms)
		assemble_ms.append(snappedf(ms, 0.1))
		built_count += 1
		var anim := NpcAnimator.attach(npc)
		anim.drawing_rate = drawing_rate
		var seg: Dictionary = job.seg
		var plan := _plan(job.b, pid) if seg.is_empty() or seg.kind == "out" else _day_plan(pid, seg)
		if plan.is_empty():
			npc.queue_free()
			return
		var start := plan[0] as Vector2
		var e := {"npc": npc, "anim": anim, "plan": plan, "i": 1, "wait": 0.0, "s": start.x, "x": start.y,
			"speed": _walk_speed(job.v), "pop": job.pop, "member": job.m, "b": job.b, "persona": {}}
		e.sig = _sig(seg) if not seg.is_empty() else str(floori(hour() * 2.0))
		e.seg = seg
		if not seg.is_empty() and seg.get("kind", "") == "trip" and seg.get("mode", "") == "bike" and int(job.v.get("age", 30)) >= 10:
			var bike := NpcBike.make()
			add_child(bike)
			e.bike = bike
			e.speed = BIKE_SPEED * (0.85 + 0.3 * NpcRng.for_trait(world_seed, pid, "bike_pace").rand())
			e.yaw_prev = 0.0
		live[pid] = e
		# knockable: a vehicle through them and they go down as a ragdoll, then get up and go on
		var rag := NpcRagdoll.attach(npc, float(job.v.get("weight", 70.0)))
		e.rag = rag
		rag.got_up.connect(func(at: Vector3):
			if live.has(pid):
				var ee: Dictionary = live[pid]
				ee.s = fposmod(StationGeo.s_of(at), StationGeo.CIRC)
				ee.x = at.x
				if ee.has("bike"):
					(ee.bike as Node).queue_free()             # the bike stays where it fell: they walk on
					ee.erase("bike")
					ee.speed = _walk_speed(job.v)
				_place(ee))
		e.zone = RemakeInteractZone.make(npc, "Talk", Transform3D(Basis(), Vector3(0, float(npc.params.height) * 0.55, 0)),
			Vector3(0.7, float(npc.params.height), 0.7), func(_by): return _contact(pid), func(): return "Talk")
		_place(e)
		return


func _despawn(pid: String) -> void:
	var e: Dictionary = live[pid]
	(e.npc as Node).queue_free()
	if e.has("bike"):
		(e.bike as Node).queue_free()
	live.erase(pid)


func _walk_speed(v: Dictionary) -> float:
	var age := float(v.get("age", 30))
	var g: Array = v.get("gait", [1.0, 1.0, 1.0, 1.0])
	var base := 1.25 if age < 60 else lerpf(1.1, 0.7, clampf((age - 60.0) / 30.0, 0.0, 1.0))
	if str(v.get("mobility_aid", "none")) != "none":
		base *= 0.6
	return base * float(g[0]) * float(g[1]) * (0.8 if age < 8 else 1.0) * float(NpcStyle.params(v).speed)


# -- where they go ------------------------------------------------------------------------------------

func _plan(b: Dictionary, pid: String) -> Array:
	## Waypoints (s, x) with pauses: out of the door, to the street, along it and back, home.
	## Pauses are negative numbers in the list (seconds) -- ma, the long stops.
	var rng := NpcRng.for_trait(world_seed, pid, "walk:%d" % floori(hour() * 2.0))
	var door0 := NpcHouseholds.door(b)
	# each member of a household has their own spot at the door and the kerb, so a couple goes out
	# side by side rather than as one body (a fixed per-person offset, the same every walk)
	var me := NpcRng.for_trait(world_seed, pid, "spot")
	var yaw: float = b.yaw
	var front := Vector2(cos(yaw), -sin(yaw))
	var right := Vector2(sin(yaw), cos(yaw))
	var door := door0 + right * (me.rand() - 0.5) * 1.4 + front * me.rand() * 0.5
	var inside := door0 - front * 2.2                                   # through the door, into the house
	var plan: Array = [door]
	var road := _near_road(door)
	if road.is_empty():
		plan.append(-(3.0 + rng.rand() * 10.0))
		plan.append(door + Vector2(rng.rand() * 6.0 - 3.0, rng.rand() * 6.0 - 3.0))
		plan.append(-(5.0 + rng.rand() * 20.0))
		plan.append(door)
		plan.append(inside)
		return plan
	var side: Vector2 = road.side + (road.dir as Vector2) * (me.rand() - 0.5) * 2.0
	var dirn: Vector2 = road.dir * (1.0 if rng.rand() < 0.5 else -1.0)
	var walk := 12.0 + rng.rand() * 40.0
	plan.append(side)
	if rng.rand() < 0.5:
		plan.append(-(2.0 + rng.rand() * 8.0))                             # a look up and down the street
	plan.append(side + dirn * walk * 0.5)
	if rng.rand() < 0.6:
		plan.append(-(4.0 + rng.rand() * 25.0))                            # stopping to chat, to look
	plan.append(side + dirn * walk)
	plan.append(-(3.0 + rng.rand() * 15.0))
	plan.append(side)
	plan.append(door)
	plan.append(inside)
	# spawned part-way through (they didn't all just step out as the player arrived): start at a
	# waypoint a few steps along
	var skip := int(rng.rand() * 4.0)
	while skip > 0 and typeof(plan[skip]) != TYPE_VECTOR2:
		skip -= 1
	return plan.slice(skip)


func _near_road(p: Vector2) -> Dictionary:
	## The nearest road to a point (s, x): the kerb-side point on the point's side and the road's
	## direction there.  {} if none within 45 m.
	MapTerrain.elevation(p.x, p.y)
	var best := 45.0
	var out := {}
	var c := Vector2i(floori(fposmod(p.x, StationGeo.CIRC) / MapTerrain.CELL), floori(p.y / MapTerrain.CELL))
	for i in range(-1, 2):
		for j in range(-1, 2):
			for it in MapTerrain._grid.get(c + Vector2i(i, j), []):
				if it[0] != "road":
					continue
				var rd: Dictionary = MapTerrain._d.roads[it[1]]
				if rd.cls == "rail" or rd.cls == "hwy":
					continue
				var q: Array = rd.pts[it[2]]
				var r: Array = rd.pts[it[2] + 1]
				var a := Vector2(float(q[0]), float(q[1]))
				var bb := a + Vector2(StationGeo.wrap_ds(float(r[0]) - float(q[0])), float(r[1]) - float(q[1]))
				var pl := Vector2(a.x + StationGeo.wrap_ds(p.x - a.x), p.y)
				var ab := bb - a
				var t := clampf((pl - a).dot(ab) / maxf(ab.length_squared(), 1e-6), 0.0, 1.0)
				var foot := a + ab * t
				var d := (pl - foot).length()
				if d < best:
					best = d
					var n := (pl - foot).normalized() if d > 0.01 else Vector2(-ab.y, ab.x).normalized()
					out = {"side": foot + n * (float(rd.w) * 0.5 + 1.2), "dir": ab.normalized()}
	return out


func _move(e: Dictionary, delta: float) -> void:
	var plan: Array = e.plan
	var anim: NpcAnimator = e.anim
	if e.wait > 0.0:
		e.wait -= delta
		anim.speed = 0.0
		if e.wait < 0.4 and not e.get("antic", false):          # the plan knows a start is coming
			anim.anticipate()
			e.antic = true
		_turn_body(e, delta)
		return
	e.antic = false
	if e.i >= plan.size():
		anim.speed = 0.0
		return
	var tgt: Variant = plan[e.i]
	if typeof(tgt) == TYPE_FLOAT:
		e.wait = -float(tgt)
		e.i += 1
		return
	var to := Vector2((tgt as Vector2).x, (tgt as Vector2).y)
	var ds := StationGeo.wrap_ds(to.x - e.s)
	var dx: float = to.y - e.x
	var d := sqrt(ds * ds + dx * dx)
	var step: float = e.speed * delta
	if d <= step:
		e.s = fposmod(to.x, StationGeo.CIRC)
		e.x = to.y
		e.i += 1
	else:
		e.s = fposmod(e.s + ds / d * step, StationGeo.CIRC)
		e.x += dx / d * step
		e.yaw = atan2(-dx, ds)
	anim.speed = e.speed if d > step else 0.0
	# the head leads into the next turn: near a waypoint, look toward where the path goes next
	anim.lead_turn = 0.0
	if d < 1.5 and e.i + 1 < plan.size():
		var nxt: Variant = plan[e.i + 1]
		if typeof(nxt) == TYPE_VECTOR2:
			var ns := StationGeo.wrap_ds((nxt as Vector2).x - to.x)
			var nx := (nxt as Vector2).y - to.y
			if absf(ns) + absf(nx) > 0.1:
				anim.lead_turn = clampf(angle_difference(float(e.get("yaw_body", 0.0)), atan2(-nx, ns)), -1.0, 1.0) * (1.0 - d / 1.5)
	_turn_body(e, delta)
	if e.has("bike"):
		_ride(e, delta, d > step)
		return
	_place(e)


func _ride(e: Dictionary, delta: float, moving: bool) -> void:
	## A cyclist: the bike steers, leans and turns its cranks by the motion; the rider sits on it.
	var bike: NpcBike = e.bike
	var anim: NpcAnimator = e.anim
	var yb := float(e.get("yaw_body", 0.0))
	var rate := angle_difference(float(e.get("yaw_prev", yb)), yb) / maxf(delta, 1e-3)
	e.yaw_prev = yb
	anim.speed = 0.0
	anim.lead_turn = 0.0
	bike.update(delta, e.speed if moving else 0.0, rate)
	_place(e)
	anim.ride = bike.rider_pose()


func _personal_space(delta: float) -> void:
	## No two people in one place: anyone closer than PERSONAL to another steps aside (half each), so
	## crossings, waits at the kerb and chance meetings keep a natural gap.
	var keys := live.keys()
	for i in keys.size():
		var a: Dictionary = live[keys[i]]
		if a.has("bike") or (a.get("rag") != null and (a.rag as NpcRagdoll).down):
			continue
		for j in range(i + 1, keys.size()):
			var b: Dictionary = live[keys[j]]
			if b.has("bike") or (b.get("rag") != null and (b.rag as NpcRagdoll).down):
				continue
			var d := Vector2(StationGeo.wrap_ds(float(b.s) - float(a.s)), float(b.x) - float(a.x))
			var l := d.length()
			if l >= PERSONAL:
				continue
			var n := d / l if l > 0.001 else Vector2(0.0, 1.0 if keys[i] < keys[j] else -1.0)
			var push := minf(PERSONAL - l, 1.5 * delta) * 0.5                 # a step aside, not a jump
			a.s = fposmod(float(a.s) - n.x * push, StationGeo.CIRC)
			a.x = float(a.x) - n.y * push
			b.s = fposmod(float(b.s) + n.x * push, StationGeo.CIRC)
			b.x = float(b.x) + n.y * push
			_place(a)
			_place(b)


func _turn_body(e: Dictionary, delta: float) -> void:
	## The body turns to its heading over ~half a second (the head has already gone ahead).
	var target := float(e.get("yaw", 0.0))
	e.yaw_body = lerp_angle(float(e.get("yaw_body", target)), target, 1.0 - exp(-6.0 * delta))


func _place(e: Dictionary) -> void:
	var s: float = e.s
	var x: float = e.x
	var npc: Node3D = e.npc
	var xf := Transform3D(StationGeo.basis(s, float(e.get("yaw_body", e.get("yaw", 0.0)))), StationGeo.point(s, x, MapTerrain.elevation(s, x)))
	if e.has("bike"):
		var bike: NpcBike = e.bike
		bike.global_transform = xf
		npc.global_transform = bike.rider_frame()
		return
	npc.global_transform = xf


# -- contact --------------------------------------------------------------------------------------------

func _contact(pid: String) -> String:
	## The player starts a conversation: now, and only now, is this person's persona made (L2).
	var e: Dictionary = live.get(pid, {})
	if e.is_empty():
		return ""
	if (e.persona as Dictionary).is_empty():
		e.persona = NpcTraits.shared().person(world_seed, pid, ["L0", "L1", "L2"], e.pop, e.member.pinned)
	e.wait = maxf(e.wait, 20.0)                                         # they stop to talk
	(e.anim as NpcAnimator).speed = 0.0
	if player:                                                           # and turn to you
		var pp := player.global_position
		var ds := StationGeo.wrap_ds(StationGeo.s_of(pp) - float(e.s))
		var dx := pp.x - float(e.x)
		e.yaw = atan2(-dx, ds)                                  # (the body turns to it over ~0.5 s)
		(e.anim as NpcAnimator).greet(e.persona)
		(e.anim as NpcAnimator).talk(4.5)
	var v: Dictionary = e.persona
	var who := full_name(v) if full_name(v) != "" else describe(v).capitalize()
	var b: Dictionary = e.b
	var tree := {
		"start": {"speaker": who, "text": _greeting(v), "choices": [
			{"text": "What do you do?", "next": "work"},
			{"text": "Do you live around here?", "next": "home"},
			{"text": "Where are you off to?", "next": "going"},
			{"text": "[Leave]", "next": ""}]},
		"work": {"speaker": who, "text": _work_line(v, _life, pid), "choices": [{"text": "[Leave]", "next": ""}]},
		"going": {"speaker": who, "text": _going_line(pid, e.get("seg", {})), "choices": [{"text": "[Leave]", "next": ""}]},
		"home": {"speaker": who, "text": "Just there -- the %s by the road%s." % [str(b.kind), (" in " + str(b.settlement)) if b.settlement != null else ""], "choices": [{"text": "[Leave]", "next": ""}]},
	}
	var dlg := get_node_or_null("/root/DialogBox")
	if dlg:
		dlg.start(e.npc, tree)
	return ""


static func full_name(v: Dictionary) -> String:
	var g := str(v.get("given_name", ""))
	var s := str(v.get("surname", ""))
	return ("%s %s" % [g, s]).strip_edges()


static func describe(v: Dictionary) -> String:
	var age := int(v.get("age", 30))
	var occ := str(v.get("occupation", "")).replace("_", " ")
	var who := "child" if age < 13 else ("young " + ("woman" if v.sex == "female" else "man")) if age < 30 else ("old " + ("woman" if v.sex == "female" else "man")) if age >= 70 else ("woman" if v.sex == "female" else "man")
	return "%s, %d, %s" % [who, age, occ]


static func _greeting(v: Dictionary) -> String:
	var p: Dictionary = v.get("personality", {})
	var warm := float(p.get("warmth", 0.5))
	var extra := float(p.get("extraversion", 0.5))
	if warm > 0.65 and extra > 0.55:
		return "Oh, hello! Lovely day for it, isn't it?"
	if warm > 0.6:
		return "Hello there."
	if extra < 0.35:
		return "...Yes?"
	if warm < 0.35:
		return "Can I help you with something?"
	return "Afternoon."


func _going_line(pid: String, seg: Dictionary) -> String:
	if _life == null or seg.is_empty():
		return "Nowhere in particular. Just out for some air."
	match str(seg.kind):
		"trip":
			if seg.to == "":
				return "Home, at last."
			return "Off to %s -- %s." % [_life.place_words(seg.to), str(seg.what).replace("_", " ")]
		"at":
			return "Just enjoying %s." % _life.place_words(seg.uid)
	return "Nowhere in particular. Just out for a walk."


static func _work_line(v: Dictionary, life: NpcLife = null, pid := "") -> String:
	var occ := str(v.get("occupation", ""))
	if life and life.person(pid).has("work") and not (occ in ["retired", "student", "university_student", "preschool", "unemployed", "homemaker"]):
		return "I'm a %s, at %s." % [occ.replace("_", " "), life.place_words(life.person(pid).work)]
	match occ:
		"retired":
			return "Oh, I'm retired now. Keeps me busier than work ever did."
		"student", "university_student":
			return "Still at school. Don't remind me."
		"preschool":
			return "*stares at you and hides behind a leg*"
		"unemployed":
			return "Between things at the moment."
		"homemaker":
			return "I keep the house. Somebody has to."
	return "I'm a %s. Have been for a while now." % occ.replace("_", " ")


func set_drawing_rate(n: int) -> void:
	## Hold each pose for n frames of 24 (1, 2 or 3), for everyone out now and everyone after.
	drawing_rate = clampi(n, 1, 3)
	for pid in live:
		(live[pid].anim as NpcAnimator).drawing_rate = drawing_rate


func stats() -> Dictionary:
	return {"live": live.size(), "pending": _pending.size(), "built": built_count, "buildings": _buildings.size(),
		"hour": snappedf(hour(), 0.1), "assemble_ms": assemble_ms.slice(-12)}
