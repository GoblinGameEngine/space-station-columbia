extends Node3D
class_name StopCrowds

## The people at the tram stops near the player (the user, 2026-10-01: "I do not want passengers simply
## disappearing when they exit the tram"):
##   - waiting at a stop: as many as the stop's demand (TransitDemand) calls for, standing on the
##     kerbside behind its sign; more walk in from the doors round about as the hour fills it;
##   - a tram that stops takes them aboard (take(): they walk to its doors themselves);
##   - those who get off (walk_away()) go on along the pavement to a building near the stop and in.
## Only stops within NEAR of the player have anyone at them (no one sees the rest); the people go
## when the player is far.

const NEAR := 160.0
const FAR := 220.0                     # walkers and crowds past this from the player are let go
const WAIT_MAX := 7                    # the most waiting at a stop
const WALK := 1.35                     # m/s
const MAX_WALKERS := 30                # people walking to or from the stops at once, at most
const SPOT_SPAN := 18.0                # m of kerb behind the stop's mark people wait along

var transit: Node                      # TransitSystem
var player: Node3D
var _stops := {}                       # key -> {line, stop, p (s, x), dir, wait: [person], spots: n}
var _walkers: Array = []               # {npc, an, pts (s, x), i, done: Callable/null, to: "door"/"stop", key}
var _pending: Array = []               # people being made (worker threads)
var _t := 0.0
var _rng := RandomNumberGenerator.new()
var _serial := 0


func _ready() -> void:
	name = "StopCrowds"
	_rng.randomize()


func _exit_tree() -> void:
	for job in _pending:
		WorkerThreadPool.wait_for_task_completion(job.task)
	_pending.clear()


func _process(delta: float) -> void:
	Prof.begin("transit.crowds")
	_collect()
	_walk(delta)
	_t -= delta
	if _t <= 0.0 and player != null and not StationGeo.loading:
		_t = 1.0
		_tend()
	Prof.end("transit.crowds")


# -- the stops near the player ------------------------------------------------------------------------

func _tend() -> void:
	var here := Vector2(StationGeo.s_of(player.global_position), player.global_position.x)
	var hour: float = transit.hour()
	var day: int = transit.day()
	var near := {}
	for l in TransitNet.lines():
		if str(l.kind) != "tram":
			continue
		for i in (l.stops as Array).size():
			var sp: Dictionary = l.stops[i]
			var p := TransitNet.point_at(l, float(sp.d))
			if NpcPlaces.dist(p, here) > NEAR:
				continue
			var key := "%s#%d" % [l.id, i]
			near[key] = true
			if not _stops.has(key):
				_stops[key] = {"line": l, "stop": i, "p": p, "wait": [], "coming": 0, "seen": false}
			var st: Dictionary = _stops[key]
			var want := int(round(TransitDemand.load_at(p, hour, day) * WAIT_MAX))
			var have: int = (st.wait as Array).size() + int(st.coming) + _walkers.filter(func(w): return w.key == key).size()
			if have < want and _walkers.size() < MAX_WALKERS:
				# a stop just come into range already has its people; later ones walk in from a door
				var walk_in: bool = st.seen
				for k in mini(want - have, 2 if walk_in else WAIT_MAX):
					_make(key, walk_in)
			st.seen = true
	for key in _stops.keys():
		if near.has(key):
			continue
		var st: Dictionary = _stops[key]
		if NpcPlaces.dist(st.p, here) > FAR:
			for w in st.wait:
				if is_instance_valid(w.npc):
					(w.npc as Node).queue_free()
			_stops.erase(key)
	for w in _walkers.duplicate():
		var npc := w.npc as Node3D
		if not is_instance_valid(npc) or player.global_position.distance_to(npc.global_position) > FAR:
			if is_instance_valid(npc):
				npc.queue_free()
			_walkers.erase(w)


func _spot(st: Dictionary, k: int) -> Array:
	## [ (s, x), yaw ]: a waiting place on the kerbside behind the stop's mark, facing the street.
	var l: Dictionary = st.line
	var d := float(l.stops[st.stop].d) - 4.0 - fmod(k * 7.3 + 3.1, SPOT_SPAN)
	var a := TransitNet.point_at(l, d - 1.0)
	var b := TransitNet.point_at(l, d + 1.0)
	var t := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y).normalized()
	var right := Vector2(-t.y, t.x)
	var kerb := TransitNet.stop_pull(l, int(st.stop)) + TransitNet.PULL_HALF_W + TransitNet.PULL_GAP
	var p := TransitNet.point_at(l, d) + right * (kerb + 1.2 + fmod(k * 0.53, 1.1))
	var face := -right
	return [Vector2(fposmod(p.x, StationGeo.CIRC), p.y), atan2(-face.y, face.x)]


func _make(key: String, walk_in: bool) -> void:
	var st: Dictionary = _stops[key]
	st.coming = int(st.coming) + 1
	_serial += 1
	var pid := "S%s_%d_%d" % [key.replace("#", ""), _serial, _rng.randi() % 100000]
	var seed: int = transit.world_seed
	var v := NpcTraits.shared().person(seed, pid, ["L0", "L1"], "", {"age": 14 + _rng.randi() % 66})
	var job := {"pid": pid, "key": key, "walk_in": walk_in, "data": {}}
	job.task = WorkerThreadPool.add_task(func(): job.data = NpcCharacter.prepare(v, pid, seed, "work"), false, "stop person")
	_pending.append(job)


func _collect() -> void:
	for job in _pending.duplicate():
		if not WorkerThreadPool.is_task_completed(job.task):
			continue
		WorkerThreadPool.wait_for_task_completion(job.task)
		_pending.erase(job)
		var st: Dictionary = _stops.get(job.key, {})
		if not st.is_empty():
			st.coming = maxi(0, int(st.coming) - 1)
		if job.data.is_empty() or st.is_empty():
			continue
		var npc := NpcCharacter.from_prepared(job.data)
		var an := NpcAnimator.attach(npc)
		an.ambient = true
		add_child(npc)
		var k: int = (st.wait as Array).size() + _walkers.filter(func(w): return w.key == job.key).size()
		var spot := _spot(st, k)
		var person := {"npc": npc, "an": an}
		if job.walk_in:
			var from := _door_near(spot[0], 50.0, 140.0, true)
			var pts := _path(from, spot[0]) if from != Vector2.INF else PackedVector2Array([spot[0]])
			_place(npc, pts[0], 0.0)
			_walkers.append({"npc": npc, "an": an, "pts": pts, "i": 1, "to": "stop", "key": job.key, "yaw": spot[1]})
		else:
			_place(npc, spot[0], spot[1])
			an.speed = 0.0
			(st.wait as Array).append(person)
		return                                                   # one a frame


# -- boarding and alighting -------------------------------------------------------------------------

func take(line_id: String, stop: int, n: int) -> Array:
	## Up to n of the people waiting at this stop, for a tram there: [{npc, an}], theirs to move now.
	var st: Dictionary = _stops.get("%s#%d" % [line_id, stop], {})
	if st.is_empty():
		return []
	var out: Array = []
	var wait: Array = st.wait
	while out.size() < n and not wait.is_empty():
		var person: Dictionary = wait.pop_front()
		if is_instance_valid(person.npc):
			out.append(person)
	return out


func tracked(line_id: String, stop: int) -> bool:
	## Is the player near enough to this stop that its people are real?
	return _stops.has("%s#%d" % [line_id, stop])


func walk_away(npc: Node3D, an: NpcAnimator) -> void:
	## Someone off a tram: on along the pavement to a building near the stop, and in.
	var xf := npc.global_transform
	npc.get_parent().remove_child(npc)
	add_child(npc)
	npc.global_transform = xf
	an.ride = {}
	an.ambient = true
	var here := Vector2(StationGeo.s_of(xf.origin), xf.origin.x)
	var to := _door_near(here, 25.0, 160.0, false)
	if to == Vector2.INF:
		npc.queue_free()
		return
	var pts := _path(here, to)
	_walkers.append({"npc": npc, "an": an, "pts": pts, "i": 0, "to": "door", "key": "", "yaw": 0.0})


func _door_near(p: Vector2, r0: float, r1: float, unseen: bool) -> Vector2:
	## A building door between r0 and r1 from p (if unseen: one the camera isn't looking at, so nobody
	## steps out of thin air).
	var cam := get_viewport().get_camera_3d()
	var picks: Array = []
	for b in NpcPlaces._doors:
		var dp: Vector2 = NpcPlaces._doors[b]
		var d := NpcPlaces.dist(dp, p)
		if d < r0 or d > r1:
			continue
		if unseen and cam and cam.is_position_in_frustum(StationGeo.point(dp.x, dp.y, MapTerrain.elevation(dp.x, dp.y) + 1.0)) \
				and cam.global_position.distance_to(StationGeo.point(dp.x, dp.y, 0.0)) < 120.0:
			continue
		picks.append(dp)
	if picks.is_empty():
		return Vector2.INF
	return picks[_rng.randi() % picks.size()]


func _path(a: Vector2, b: Vector2) -> PackedVector2Array:
	## Along the pavements (NpcPlaces.route), else straight.
	var classes := ["street", "main", "county", "hwy", "gravel", "alley"]
	var r := NpcPlaces.route("", "", a, b, NpcPlaces.PAVEMENT, classes)
	if r.size() < 2:
		r = PackedVector2Array([a, b])
	return r


func _place(npc: Node3D, p: Vector2, yaw: float) -> void:
	var s := fposmod(p.x, StationGeo.CIRC)
	npc.global_transform = Transform3D(StationGeo.basis(s, yaw), StationGeo.point(s, p.y, MapTerrain.elevation(s, p.y)))


func _walk(delta: float) -> void:
	for w in _walkers.duplicate():
		var npc := w.npc as Node3D
		if not is_instance_valid(npc):
			_walkers.erase(w)
			continue
		var pts: PackedVector2Array = w.pts
		var at := Vector2(StationGeo.s_of(npc.global_position), npc.global_position.x)
		if int(w.i) >= pts.size():
			_arrived(w)
			continue
		var tgt: Vector2 = pts[w.i]
		var dv := Vector2(StationGeo.wrap_ds(tgt.x - at.x), tgt.y - at.y)
		var step := WALK * delta
		var nxt := at
		if dv.length() <= step:
			nxt = tgt
			w.i = int(w.i) + 1
		else:
			nxt = at + dv.normalized() * step
		var yaw := atan2(-dv.y, dv.x) if dv.length() > 0.05 else 0.0
		_place(npc, nxt, yaw)
		(w.an as NpcAnimator).speed = WALK


func _arrived(w: Dictionary) -> void:
	_walkers.erase(w)
	var npc := w.npc as Node3D
	if w.to == "door":
		npc.queue_free()                                          # in at the door
		return
	var st: Dictionary = _stops.get(w.key, {})
	if st.is_empty():
		npc.queue_free()
		return
	(w.an as NpcAnimator).speed = 0.0
	var at := Vector2(StationGeo.s_of(npc.global_position), npc.global_position.x)
	_place(npc, at, float(w.yaw))
	(st.wait as Array).append({"npc": npc, "an": w.an})
