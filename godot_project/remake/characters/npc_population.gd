extends Node3D
class_name NpcPopulation

## The people of the station, near the player (procedural_npcs.md 2): nobody is stored.  Around the
## player, the residential buildings' households (NpcHouseholds, a pure function of the building)
## give who lives here; who of them is out of doors is a pure function of the person and the
## half-hour; those people are generated (traits on the main thread, bodies and clothes on the
## worker pool), walk from their door to the street and along it, pause, look about, and go home.
## Leave and come back and the same people are there, doing the same kind of thing.  Using one of
## them (the interact key) is "contact": their persona (L2) is made then, not before.
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
var _index := {}                 # Vector2i(cell s, cell x) -> [building]
var _buildings: Array = []
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
	for b in st.structures:
		if NpcHouseholds.is_residential(str(b.kind)):
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


func _process(delta: float) -> void:
	if player == null:
		return
	_collect()
	for pid in live:
		_move(live[pid], delta)
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
					if out_now(m.pid, m.pinned):
						want.append([d, m, b, hh.population])
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
		_spawn(w[1], w[2], w[3])
	# those no longer wanted (gone home) leave when out of the player's sight
	var keep := {}
	for w in want.slice(0, MAX_LIVE):
		keep[w[1].pid] = true
	for pid in live.keys():
		if not keep.has(pid) and live[pid].i >= (live[pid].plan as Array).size():
			_despawn(pid)


func _dist(s0: float, x0: float, s1: float, x1: float) -> float:
	return Vector2(StationGeo.wrap_ds(s1 - s0), x1 - x0).length()


# -- making people ------------------------------------------------------------------------------------

func _spawn(m: Dictionary, b: Dictionary, pop: String) -> void:
	var v := NpcTraits.shared().person(world_seed, m.pid, ["L0", "L1"], pop, m.pinned)
	var job := {"v": v, "pid": m.pid, "b": b, "m": m, "pop": pop, "data": {}}
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
		var plan := _plan(job.b, pid)
		var start := plan[0] as Vector2
		var e := {"npc": npc, "anim": anim, "plan": plan, "i": 1, "wait": 0.0, "s": start.x, "x": start.y,
			"speed": _walk_speed(job.v), "pop": job.pop, "member": job.m, "b": job.b, "persona": {}}
		live[pid] = e
		e.zone = RemakeInteractZone.make(npc, "Talk", Transform3D(Basis(), Vector3(0, float(npc.params.height) * 0.55, 0)),
			Vector3(0.7, float(npc.params.height), 0.7), func(_by): return _contact(pid), func(): return "Talk")
		_place(e)
		return


func _despawn(pid: String) -> void:
	var e: Dictionary = live[pid]
	(e.npc as Node).queue_free()
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
	var door := NpcHouseholds.door(b)
	var plan: Array = [door]
	var road := _near_road(door)
	if road.is_empty():
		plan.append(-(3.0 + rng.rand() * 10.0))
		plan.append(door + Vector2(rng.rand() * 6.0 - 3.0, rng.rand() * 6.0 - 3.0))
		plan.append(-(5.0 + rng.rand() * 20.0))
		plan.append(door)
		return plan
	var side: Vector2 = road.side
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
	_place(e)


func _turn_body(e: Dictionary, delta: float) -> void:
	## The body turns to its heading over ~half a second (the head has already gone ahead).
	var target := float(e.get("yaw", 0.0))
	e.yaw_body = lerp_angle(float(e.get("yaw_body", target)), target, 1.0 - exp(-6.0 * delta))


func _place(e: Dictionary) -> void:
	var s: float = e.s
	var x: float = e.x
	var npc: Node3D = e.npc
	npc.global_transform = Transform3D(StationGeo.basis(s, float(e.get("yaw_body", e.get("yaw", 0.0)))), StationGeo.point(s, x, MapTerrain.elevation(s, x)))


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
		(e.anim as NpcAnimator).talk(4.5)
	var v: Dictionary = e.persona
	var who := describe(v)
	var b: Dictionary = e.b
	var tree := {
		"start": {"speaker": who.capitalize(), "text": _greeting(v), "choices": [
			{"text": "What do you do?", "next": "work"},
			{"text": "Do you live around here?", "next": "home"},
			{"text": "[Leave]", "next": ""}]},
		"work": {"speaker": who.capitalize(), "text": _work_line(v), "choices": [{"text": "[Leave]", "next": ""}]},
		"home": {"speaker": who.capitalize(), "text": "Just there -- the %s by the road%s." % [str(b.kind), (" in " + str(b.settlement)) if b.settlement != null else ""], "choices": [{"text": "[Leave]", "next": ""}]},
	}
	var dlg := get_node_or_null("/root/DialogBox")
	if dlg:
		dlg.start(e.npc, tree)
	return ""


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


static func _work_line(v: Dictionary) -> String:
	var occ := str(v.get("occupation", ""))
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
