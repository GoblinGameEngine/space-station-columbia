extends Node3D
class_name NpcTraffic

## The station's road vehicles (remake/characters/npc_fleet.json, baked by tools/places/make_vehicles.py):
## people's own cars and the places' work vehicles, parked where they are and driven where they go.
##
## Where a vehicle is follows from the clock alone (like TransitSystem), so it is the same whenever the
## player comes by:
##   a household car  is parked by its driver's home until their first car trip of the day (NpcLife);
##                    on a trip it is on the road, the driver at the wheel, for as long as the drive
##                    really takes at CAR_SPEED; then it is parked by wherever they went until they
##                    drive on (and home again at the end of the day);
##   a work vehicle   is parked at its place; the ones with rounds (mail, deliveries, police, refuse,
##                    taxis...) drive a loop through their town's places in their hours, stopping a
##                    while at each.
## Parked: on the door's side of the nearest road -- in the parking lane at the kerb of a main road,
## else just off the road beyond the pavement -- facing the way traffic goes on that side, clear of
## buildings and of other parked vehicles (and the player's pods and vans). Driving: LANE right of
## the centre line, clear of the parking lanes. Driving: the right-hand lane (CAR_EDGE).
## Only vehicles within RANGE of the player are built (GLB, collider, and a driver when moving).

const FLEET := "res://remake/characters/npc_fleet.json"
const RANGE := 160.0
const SLICE := 50                    # vehicles placed per frame (the far ones are a distance check)
const CAR_SPEED := 11.0              # m/s on town streets (40 km/h)
const LANE := 1.8                    # the driving lane: this far right of the centre line
const PARK_LANE := 10.0              # roads this wide have a parking lane at each kerb
const VERGE := 3.0                   # parked: the car's centre this far beyond the road's edge (past the pavement)
const WALK_S := 40.0                 # real seconds from the door to the car before driving off
const DWELL_S := 45.0                # real seconds at each stop on a round
const SEAT_H := 0.36
const ROADS := ["street", "main", "county", "hwy", "gravel", "alley"]
const MODEL := {"city_car": "pod", "minivan": "van"}

var player: Node3D
var world_seed := 1
var vehicles: Array = []             # fleet entries (+ runtime: where, slot)
var live := {}                       # id -> {node, wheels, driver, pending}
var _i := 0
var _life: NpcLife
var _clock: Node
var _scenes := {}
var _spot_cache := {}
var _route_cache := {}
var _here := Vector2.ZERO
var _types := {}                     # vehicle type -> npc_vehicles.json entry (size_m, phys)
var _built_this_frame := 0
var _spots_this_frame := 0
var _taken: Array = []               # parking places handed out
var _sites := {}                     # 40 m cell -> buildings (placement.json), for parking clear of them


func _ready() -> void:
	name = "NpcTraffic"
	_clock = get_tree().current_scene.get_node_or_null("DaySkySystem")
	if not FileAccess.file_exists(FLEET) or not FileAccess.file_exists(NpcLife.PATH):
		return
	_life = NpcLife.shared()
	TrafficSigns.load_all()
	world_seed = _life.seed
	var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(FLEET))
	vehicles = d.vehicles
	_types = (JSON.parse_string(FileAccess.get_file_as_string("res://remake/characters/npc_vehicles.json")) as Dictionary).vehicles
	if FileAccess.file_exists("res://remake/groundcars.json"):              # the player's pods and vans: their places are taken
		for g in (JSON.parse_string(FileAccess.get_file_as_string("res://remake/groundcars.json")) as Dictionary).groundcars:
			_taken.append(Vector2(float(g.s), float(g.x)))
	var per_door := {}
	for v in vehicles:
		var k := "%.1f,%.1f" % [float(v.door[0]), float(v.door[1])]
		v.slot = int(per_door.get(k, 0))
		per_door[k] = v.slot + 1
		v.where = {}
	print("NpcTraffic: %d vehicles (%d with rounds)" % [vehicles.size(), vehicles.filter(func(x): return not (x.rounds as Array).is_empty()).size()])


# -- the clock --------------------------------------------------------------------------------------

func _game_h_per_s() -> float:
	return 24.0 / DaySkySystem.DAY_LENGTH_SECONDS


func _now() -> Array:
	## [day, hour, real seconds since day 0]
	if _clock == null:
		return [0, 12.0, Time.get_ticks_msec() / 1000.0]
	var day := int(_clock.get("day"))
	var h := float(_clock.time_of_day) * 24.0
	return [day, h, (day + float(_clock.time_of_day)) * DaySkySystem.DAY_LENGTH_SECONDS]


# -- where a vehicle is -----------------------------------------------------------------------------

func _locate(v: Dictionary, now: Array) -> Dictionary:
	## {pos (s, x), yaw, driving, speed} or {} (nowhere near the player, or not out).
	if str(v.kind) == "home":
		return _locate_home(v, now)
	var hours: Array = v.hours
	if not (v.rounds as Array).is_empty() and hours.size() == 2:
		var h: float = now[1]
		if h >= float(hours[0]) and h < float(hours[1]):
			var r := _round(v, now)
			if not r.is_empty():
				return r
	return _parked(Vector2(float(v.door[0]), float(v.door[1])), v)


func _locate_home(v: Dictionary, now: Array) -> Dictionary:
	var pid: String = v.driver
	var P := _life.person(pid)
	var home := Vector2(float(v.door[0]), float(v.door[1]))
	if P.is_empty():
		return _parked(home, v)
	var day: int = now[0]
	var h: float = now[1]
	var last := {}
	for seg in _life.timeline(pid, day):
		if seg.kind == "trip" and seg.get("mode", "") == "car" and float(seg.t0) <= h:
			last = seg
	if last.is_empty():
		return _parked(home, v)
	var gh := _game_h_per_s()
	var a := _life.door(P, str(last.from))
	var b := _life.door(P, str(last.to))
	var dest := b if str(last.to) != "" else home
	var trip := "%s|%d|%.4f" % [pid, day, float(last.t0)]
	if (v.get("done", {}) as Dictionary).has(trip):
		return _parked(dest, v)                                    # driven already (in the traffic, slower than the timetable)
	var start := float(last.t0) + WALK_S * gh
	if h < start:
		return _parked(a if str(last.from) != "" else home, v)
	# on the road for as long as the drive takes (the straight line first: is it near at all?)
	var straight := NpcPlaces.dist(a, b)
	var rough_end := start + straight * 1.6 / CAR_SPEED * gh
	if h < rough_end:
		if _near_line(a, b):
			var r := _route(_life.place_of(P, str(last.from)), _life.place_of(P, str(last.to)))
			var L := NpcPlaces.route_length(r)
			var t := (h - start) / gh * CAR_SPEED
			if t < L:
				var w := _on_route(r, t, CAR_SPEED)
				w.trip = trip
				w.dest = dest
				w.length = L
				return w
		elif h < start + straight / CAR_SPEED * gh:
			return {}                                              # driving, far away
	return _parked(dest, v)


func _round(v: Dictionary, now: Array) -> Dictionary:
	## A work vehicle's loop through its town's places: like a tram line, on the clock.
	var at := Vector2(float(v.door[0]), float(v.door[1]))
	if NpcPlaces.dist(at, _here) > 1600.0:
		return {"away": true}
	var key := "round:" + str(v.id)
	if not _route_cache.has(key):
		var stops: Array = [v.at] + (v.rounds as Array) + [v.at]
		var pts := PackedVector2Array()
		var marks: Array = []                                      # distance along at each stop
		for i in stops.size() - 1:
			var ba := str(NpcPlaces.unit(str(stops[i])).get("building", ""))
			var bb := str(NpcPlaces.unit(str(stops[i + 1])).get("building", ""))
			if ba == "" or bb == "" or ba == bb:
				continue
			var came := pts[pts.size() - 2] if pts.size() >= 2 else Vector2.INF
			var r := NpcPlaces.route(ba, bb, Vector2.INF, Vector2.INF, 0.0, ROADS, [], came, LANE)
			if r.size() < 3:
				continue
			marks.append(NpcPlaces.route_length(pts))
			for k in range(1, r.size() - 1):
				if pts.size() == 0 or NpcPlaces.dist(pts[pts.size() - 1], r[k]) > 0.3:
					pts.append(r[k])
		_route_cache[key] = [pts, marks]
	var rc: Array = _route_cache[key]
	var pts2: PackedVector2Array = rc[0]
	var marks2: Array = rc[1]
	if pts2.size() < 2:
		return {}
	var L := NpcPlaces.route_length(pts2)
	var period := L / CAR_SPEED + marks2.size() * DWELL_S
	var t: float = fposmod(float(now[2]) + float(hash(v.id) % 1000), period)
	var d := 0.0
	for i in marks2.size():
		var m0: float = marks2[i]
		var m1: float = marks2[i + 1] if i + 1 < marks2.size() else L
		if t < DWELL_S:
			return _round_at(pts2, m0, L, marks2)
		t -= DWELL_S
		var run := (m1 - m0) / CAR_SPEED
		if t < run:
			return _round_at(pts2, m0 + t * CAR_SPEED, L, marks2)
		t -= run
	return _round_at(pts2, L, L, marks2)


func _round_at(pts: PackedVector2Array, t: float, L: float, marks: Array) -> Dictionary:
	var w := _on_route(pts, t, CAR_SPEED)
	w.loop = L
	w.marks = marks
	return w


func _near_line(a: Vector2, b: Vector2) -> bool:
	var ab := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)
	var ap := Vector2(StationGeo.wrap_ds(_here.x - a.x), _here.y - a.y)
	var t := clampf(ap.dot(ab) / maxf(ab.length_squared(), 1e-6), 0.0, 1.0)
	return (ap - ab * t).length() < RANGE + 0.35 * ab.length() + 60.0


func _route(from_b: String, to_b: String) -> PackedVector2Array:
	var key := from_b + ">" + to_b
	if not _route_cache.has(key):
		if _route_cache.size() > 400:
			_route_cache.clear()
		var r := NpcPlaces.route(from_b, to_b, Vector2.INF, Vector2.INF, 0.0, ROADS, [], Vector2.INF, LANE)
		_route_cache[key] = r.slice(1, r.size() - 1) if r.size() > 3 else r
	return _route_cache[key]


func _on_route(r: PackedVector2Array, t: float, speed: float) -> Dictionary:
	var p := _pos_along(r, t)
	var q := _pos_along(r, t + 2.0)
	var o := _pos_along(r, t - 2.0)
	var dir := Vector2(StationGeo.wrap_ds(q.x - o.x), q.y - o.y)
	if dir.length() < 0.01:
		dir = Vector2(1, 0)
	return {"pos": p, "yaw": atan2(-dir.y, dir.x), "driving": speed > 0.0, "speed": speed, "moving": true, "route": r, "t": t}


static func _pos_along(r: PackedVector2Array, t: float) -> Vector2:
	if r.size() == 0:
		return Vector2.ZERO
	t = maxf(t, 0.0)
	for i in r.size() - 1:
		var seg := NpcPlaces.dist(r[i], r[i + 1])
		if t <= seg:
			var f := t / maxf(seg, 1e-6)
			return Vector2(fposmod(r[i].x + StationGeo.wrap_ds(r[i + 1].x - r[i].x) * f, StationGeo.CIRC), r[i].y + (r[i + 1].y - r[i].y) * f)
		t -= seg
	return r[r.size() - 1]


func _parked(door: Vector2, v: Dictionary) -> Dictionary:
	## Off the road by this door: beyond the pavement on the door's side of the nearest road
	## (VERGE), parallel to it and facing with the traffic on that side, clear of buildings and of
	## the other parked vehicles -- the nearest free place along the road.
	if NpcPlaces.dist(door, _here) > RANGE + 100.0:
		return {"away": true}                                      # (its place is never this far from its door)
	var key := "%.1f,%.1f#%d" % [door.x, door.y, int(v.slot)]
	if not _spot_cache.has(key):
		if _spots_this_frame >= 2:
			return {}                                              # (found in a frame or two)
		_spots_this_frame += 1
		_spot_cache[key] = _find_spot(door)
	var sp: Dictionary = _spot_cache[key]
	if sp.is_empty():
		return {}
	var p: Vector2 = sp.p
	if NpcPlaces.dist(p, _here) > RANGE + 40.0:
		return {"away": true}
	var dir: Vector2 = sp.dir
	return {"pos": p, "yaw": atan2(-dir.y, dir.x), "driving": false, "speed": 0.0}


func _find_spot(door: Vector2) -> Dictionary:
	var a := NpcPlaces._attach_on(door, ROADS)
	if a.is_empty():
		return {}
	var e: Array = NpcPlaces._paths.edges[int(a[0])]
	var ri := int(e[2])
	var u := float(a[1])
	var c := NpcPlaces._at(ri, u)
	var c2 := NpcPlaces._at(ri, u + 0.05)
	var c1 := NpcPlaces._at(ri, maxf(u - 0.05, 0.0))
	var t := Vector2(StationGeo.wrap_ds(c2.x - c1.x), c2.y - c1.y).normalized()
	if t.length() < 0.5:
		t = Vector2(1, 0)
	var right := Vector2(-t.y, t.x)                            # (s, x): facing +s, +x is to the right
	var side := signf(Vector2(StationGeo.wrap_ds(door.x - c.x), door.y - c.y).dot(right))
	side = side if side != 0.0 else 1.0
	var w := float(NpcPlaces._road(ri).w)
	var face := t if side > 0.0 else -t
	var off := w * 0.5 - 1.15 if w >= PARK_LANE else w * 0.5 + VERGE    # the parking lane, or off the road past the pavement
	for k in 17:                                               # 0, +6.5, -6.5, +13 ... along the road
		var along := ceilf(k / 2.0) * 6.5 * (1.0 if k % 2 == 1 else -1.0)
		var p := c + right * side * off + t * along
		p = Vector2(fposmod(p.x, StationGeo.CIRC), p.y)
		if _blocked(p, face):
			continue
		_taken.append(p)
		return {"p": p, "dir": face}
	return {}


func _blocked(p: Vector2, face: Vector2) -> bool:
	for q in _taken:
		if NpcPlaces.dist(q, p) < 5.6:
			return true
	# the car's corners and middle, against the buildings' footprints
	var side := Vector2(-face.y, face.x)
	for o in [Vector2.ZERO, face * 2.4, -face * 2.4, side * 1.0, -side * 1.0]:
		if _in_building(p + o, 0.6):
			return true
	return false


func _in_building(q: Vector2, margin: float) -> bool:
	if _sites.is_empty():
		var st: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://remake/placement.json"))
		for b in st.structures:
			var cell := Vector2i(floori(float(b.s) / 40.0), floori(float(b.x) / 40.0))
			if not _sites.has(cell):
				_sites[cell] = []
			(_sites[cell] as Array).append(b)
	var cs := Vector2i(floori(q.x / 40.0), floori(q.y / 40.0))
	for dx in [-1, 0, 1]:
		for dy in [-1, 0, 1]:
			for b in _sites.get(Vector2i(posmod(cs.x + dx, ceili(StationGeo.CIRC / 40.0)), cs.y + dy), []):
				# the footprint in the building's frame: local -Z is (cos yaw, -sin yaw), +X (sin yaw, cos yaw)
				var rel := Vector2(StationGeo.wrap_ds(q.x - float(b.s)), q.y - float(b.x))
				var yaw := float(b.yaw)
				var lx := rel.dot(Vector2(sin(yaw), cos(yaw)))
				var lz := rel.dot(Vector2(-cos(yaw), sin(yaw)))
				var fmn: Array = b.get("fmin", [-5, -5])
				var fmx: Array = b.get("fmax", [5, 5])
				if lx > float(fmn[0]) - margin and lx < float(fmx[0]) + margin and lz > float(fmn[1]) - margin and lz < float(fmx[1]) + margin:
					return true
	return false


# -- the frame --------------------------------------------------------------------------------------

func _process(delta: float) -> void:
	if player == null or vehicles.is_empty() or StationGeo.loading:
		return                                                     # nothing drives till the world is in
	var t_us := Time.get_ticks_usec()
	_here = Vector2(StationGeo.s_of(player.global_position), player.global_position.x)
	var now := _now()
	var ts0 := Time.get_ticks_usec()
	_spots_this_frame = 0
	_sense_world()
	var t_sense := Time.get_ticks_usec() - ts0
	var t_loc := 0
	var t_show := 0
	# a slice of the fleet each frame: where each is, and whether it's near
	for k in mini(SLICE, vehicles.size()):
		var v: Dictionary = vehicles[_i]
		_i = (_i + 1) % vehicles.size()
		if live.has(v.id) and live[v.id].sim != null:
			continue                                               # being driven: RoadDriver places it
		if live.has(v.id) and live[v.id].get("crashed", false):
			var wn := live[v.id].node as Node3D                    # a wreck: the physics has it till it's left behind
			if NpcPlaces.dist(Vector2(StationGeo.s_of(wn.global_position), wn.global_position.x), _here) > RANGE + 20.0:
				wn.queue_free()
				live.erase(v.id)
			continue
		var tl := Time.get_ticks_usec()
		v.where = _locate(v, now)
		var tm := Time.get_ticks_usec()
		_show(v)
		t_loc += tm - tl
		t_show += Time.get_ticks_usec() - tm
	var t_slice := Time.get_ticks_usec() - t_us
	_built_this_frame = 0
	var cam := get_viewport().get_camera_3d()
	var t_d := 0
	var t_v := 0
	for id in live.keys():
		var e: Dictionary = live[id]
		var t1 := Time.get_ticks_usec()
		if e.sim != null:
			_drive(e, delta, now)
		var t2 := Time.get_ticks_usec()
		if live.has(id):
			_visual(live[id], delta, cam)
			_animate(live[id], delta)
		t_d += t2 - t1
		t_v += Time.get_ticks_usec() - t2
	prof = {"sense_ms": t_sense / 1000.0, "locate_ms": t_loc / 1000.0, "show_ms": t_show / 1000.0, "slice_ms": t_slice / 1000.0, "drive_ms": t_d / 1000.0, "visual_ms": t_v / 1000.0}
	_collect()
	frame_ms = lerpf(frame_ms, (Time.get_ticks_usec() - t_us) / 1000.0, 0.1)


# -- the road users a driver sees ------------------------------------------------------------------

var frame_ms := 0.0
var prof := {}                  # how long this takes a frame (smoothed)
var agents: Array = []               # [{id, p, dir, v, len, kind}] -- moving vehicles, trams, trains, the player
var peds: Array = []                 # [{id, p}] -- people out of doors near the player


static func _flat(xf: Transform3D) -> Array:
	## A world transform as (s, x) position and heading.
	var o := xf.origin
	var s := StationGeo.s_of(o)
	var f := -xf.basis.z
	var dir := Vector2(f.dot(StationGeo.forward(s)), f.x)
	return [Vector2(s, o.x), dir.normalized() if dir.length() > 0.01 else Vector2(1, 0)]


func _sense_world() -> void:
	agents.clear()
	peds.clear()
	for id in live:
		var e: Dictionary = live[id]
		if e.sim == null:
			continue                                               # parked: off the carriageway
		var f := _flat((e.node as Node3D).global_transform)
		agents.append({"id": id, "p": f[0], "dir": f[1], "v": (e.sim as RoadDriver).v, "len": float(e.len), "kind": "car"})
	var st := get_tree().current_scene
	var tr = st.get("transit")
	if tr != null:
		for key in tr.live:
			var tv = tr.live[key]
			var kind := "tram" if str(tv.line.kind) == "tram" else "train"
			var sp: float = tv.drv.v if tv.get("drv") != null else 9.0
			for k in (tv.parts as Array).size():
				var pt: Array = tv.parts[k]
				var f := _flat((pt[0] as Node3D).global_transform)
				var mid := (float(pt[1]) + float(pt[2])) * 0.5
				agents.append({"id": "%s#%d" % [key, k], "p": (f[0] as Vector2) + (f[1] as Vector2) * mid, "dir": f[1], "v": sp,
					"len": absf(float(pt[1]) - float(pt[2])) + 0.5, "kind": kind})
	if player != null:
		var f := _flat(player.global_transform)
		var pv := 0.0
		if player is CharacterBody3D:
			pv = (player as CharacterBody3D).velocity.length()
		agents.append({"id": "player", "p": f[0], "dir": f[1], "v": pv, "len": 1.0, "kind": "player"})
	var pop = st.get("npcs")
	if pop != null:
		for pid in pop.live:
			var n = pop.live[pid].get("npc")
			if n is Node3D:
				var o := (n as Node3D).global_position
				peds.append({"id": pid, "p": Vector2(StationGeo.s_of(o), o.x)})


# -- driving ----------------------------------------------------------------------------------------

func _make_sim(v: Dictionary, e: Dictionary, w: Dictionary) -> void:
	var r: PackedVector2Array = w.route
	var person: Dictionary = e.get("person", {})
	if person.is_empty():
		person = _person(v)
		e.person = person
	var s := RoadDriver.new()
	s.id = v.id
	if w.has("loop"):
		var L: float = w.loop
		var rp := RoadDriver.Path.new(r)
		s.setup(func(dd): return rp.at(fposmod(dd, L)), float(e.len), person, hash(str(v.id)))
		e.loop = L
		e.marks = w.marks
		e.next_mark = _next_mark(float(w.t), L, w.marks)
	else:
		var rp2 := RoadDriver.Path.new(r)
		s.setup(func(dd): return rp2.at(dd), float(e.len), person, hash(str(v.id)))
		s.path_len = float(w.get("length", NpcPlaces.route_length(r)))
		e.trip = w.get("trip", "")
		e.dest = w.get("dest", Vector2.ZERO)
		e.loop = 0.0
	s.t = float(w.t)
	s.v = CAR_SPEED * 0.8 if float(w.t) > 1.0 else 0.0
	e.sim = s
	e.hold = 0.0


static func _next_mark(t: float, L: float, marks: Array) -> float:
	var lap := floorf(t / L) * L
	for m in marks:
		if lap + float(m) > t + 0.5:
			return lap + float(m)
	return lap + L + (float(marks[0]) if not marks.is_empty() else 0.0)


func _drive(e: Dictionary, dt: float, now: Array) -> void:
	var s: RoadDriver = e.sim
	var v: Dictionary = e.v
	# a round's stop at each place, for a while (the timetable's dwell)
	if float(e.loop) > 0.0:
		var hours: Array = v.hours
		var h: float = now[1]
		if hours.size() == 2 and (h < float(hours[0]) or h >= float(hours[1])):
			_end_drive(e)
			return
		if float(e.hold) > 0.0:
			e.hold = float(e.hold) - dt
			s.v_cap = 0.0 if absf(s.lat) > 2.2 else 2.0               # in to the kerb, then stand
			s.pull_over(float(e.hold) > 0.0)
		elif s.t >= float(e.next_mark) - 0.5:
			e.hold = DWELL_S
			e.next_mark = _next_mark(s.t + 1.0, float(e.loop), e.marks)
		else:
			s.v_cap = INF if absf(s.lat) < 0.3 else 3.0              # back out into the lane first
			s.pull_over(false)
	s.step(dt, agents, peds, now[2])
	if float(e.loop) <= 0.0 and s.t >= s.path_len - 0.5:
		var done: Dictionary = v.get("done", {})
		done[e.trip] = true
		v.done = done
		_end_drive(e)
		return
	var p := s.pos_at(s.t)
	var d := s.dir_at(s.t)
	var q := p + Vector2(-d.y, d.x) * s.lat
	if NpcPlaces.dist(q, _here) > RANGE + 30.0:
		(e.node as Node).queue_free()
		live.erase(v.id)
		return
	(e.node as Node3D).global_transform = Transform3D(StationGeo.basis(q.x, atan2(-d.y, d.x)), StationGeo.point(q.x, q.y, _road_h(q, e.node)))
	e.speed = s.v
	(e.node as NpcCarBody).v_now = -(e.node as Node3D).global_transform.basis.z * s.v


func _road_h(p: Vector2, node: Node3D) -> float:
	var ex: Array[RID] = []
	if node is CollisionObject3D:
		ex.append((node as CollisionObject3D).get_rid())
	return RoadSurface.stand_h(node.get_world_3d().direct_space_state, p, StationGeo.h_of(node.global_position), ex)


func _end_drive(e: Dictionary) -> void:
	e.sim = null
	e.moving = false
	e.speed = 0.0
	if e.driver != null:
		(e.driver as Node).queue_free()
		e.driver = null
	var v: Dictionary = e.v
	v.where = _locate(v, _now())
	_show(v)


func _person(v: Dictionary) -> Dictionary:
	## The driver as the generator makes them, to the layer their driving traits live on (L2).
	var pid := str(v.driver)
	var pinned := {}
	var pop := ""
	if pid != "":
		var P := _life.person(pid)
		pinned = {"age": int(P.age), "sex": P.sex, "given_name": P.get("given", ""), "surname": P.get("surname", ""),
			"lineage": P.get("lineage", ""), "name_heritage": P.get("name_heritage", "")}
		pop = str(P.get("pop", ""))
	else:
		pid = "driver:" + str(v.id)
		pinned = {"age": 25 + int(abs(hash(pid)) % 35)}
	var person := NpcTraits.shared().person(world_seed, pid, ["L0", "L1", "L2"], pop, pinned)
	person["_pid"] = pid
	return person


func _show(v: Dictionary) -> void:
	var w: Dictionary = v.where
	var near := w.has("pos") and NpcPlaces.dist(w.pos, _here) < RANGE
	var e: Dictionary = live.get(v.id, {})
	if not near:
		if not e.is_empty() and (not w.has("pos") or NpcPlaces.dist(w.pos, _here) > RANGE + 20.0):
			(e.node as Node).queue_free()
			live.erase(v.id)
		return
	if e.is_empty():
		e = _build(v)
		if e.is_empty():
			return
		live[v.id] = e
	var node := e.node as Node3D
	var p: Vector2 = w.pos
	node.global_transform = Transform3D(StationGeo.basis(p.x, float(w.yaw)), StationGeo.point(p.x, p.y, _road_h(p, node)))
	e.speed = float(w.get("speed", 0.0))
	e.moving = bool(w.get("moving", false))
	if bool(w.get("moving", false)) and e.sim == null and w.has("route"):
		_make_sim(v, e, w)
	var wants_driver := bool(w.get("moving", false))
	if wants_driver and e.driver == null and e.pending.is_empty():
		_hire(v, e)
	elif not wants_driver and e.driver != null:
		(e.driver as Node).queue_free()
		e.driver = null


func _build(v: Dictionary) -> Dictionary:
	## Its body only: a box of its type's size and mass (it collides and is placed whether or not
	## it's seen). The model comes when it's on screen (_visual).
	var spec: Dictionary = _types.get(str(v.type), {})
	var size: Array = spec.get("size_m", [4.8, 1.9, 1.5])
	var phys: Dictionary = spec.get("phys", {})
	var body := NpcCarBody.new()
	body.name = str(v.id)
	body.traffic = self
	body.entry_id = str(v.id)
	body.mass = float(phys.get("mass_kg", 1500.0))
	body.center_of_mass_mode = RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
	body.center_of_mass = Vector3(0, float(size[2]) * 0.35, 0)     # low: batteries in the floor
	body.collision_layer = 1 | RemakeGroundVehicle.HULL_LAYER
	body.collision_mask = 1 | RemakeGroundVehicle.HULL_LAYER
	var cs := CollisionShape3D.new()
	var sh := BoxShape3D.new()
	sh.size = Vector3(float(size[1]), float(size[2]) * 0.85, float(size[0])) * 0.96
	cs.shape = sh
	cs.position = Vector3(0, float(size[2]) * 0.85 * 0.5 + float(size[2]) * 0.1, 0)
	body.add_child(cs)
	add_child(body)
	return {"node": body, "v": v, "wheels": [], "seat": null, "driver": null, "pending": {}, "speed": 0.0, "moving": false, "spin": 0.0,
		"sim": null, "len": float(size[0]), "loop": 0.0, "hold": 0.0, "model": null, "unseen": 0.0, "radius": float(size[0]) * 0.6}


func _model_path(v: Dictionary) -> String:
	return "res://remake/vehicles/%s.glb" % str(MODEL.get(str(v.type), str(v.type)))


func _visual(e: Dictionary, delta: float, cam: Camera3D) -> void:
	## The model only while it can be seen (on screen, or close by): asked for on a loader thread,
	## put in when it's ready, taken away after a few seconds out of sight.
	var node := e.node as Node3D
	var p := node.global_position
	var seen := p.distance_to(cam.global_position) < 25.0 if cam else true
	if cam and not seen:
		var r: float = e.radius
		var b := node.global_transform.basis
		for q in [p, p + b.z * r, p - b.z * r, p + b.y * 2.0]:
			if cam.is_position_in_frustum(q):
				seen = true
				break
	if seen:
		e.unseen = 0.0
		if e.model == null:
			var path := _model_path(e.v)
			if not _scenes.has(path):
				if not ResourceLoader.exists(path):
					_scenes[path] = null
				elif ResourceLoader.load_threaded_get_status(path) == ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
					ResourceLoader.load_threaded_request(path)
				elif ResourceLoader.load_threaded_get_status(path) == ResourceLoader.THREAD_LOAD_LOADED:
					_scenes[path] = ResourceLoader.load_threaded_get(path)
			var sc = _scenes.get(path)
			if sc is PackedScene and _built_this_frame < 2:
				_built_this_frame += 1
				var m := (sc as PackedScene).instantiate() as Node3D
				node.add_child(m)
				e.model = m
				var wheels: Array = []
				for n in m.find_children("wheel_*", "Node3D", true, false):
					wheels.append([n, (n as Node3D).transform.basis])
				e.wheels = wheels
				var seat := m.find_child("seat_driver", true, false) as Node3D
				if seat == null:
					seat = m.find_child("seat_pilot", true, false) as Node3D
				e.seat = seat
				for g in m.find_children("*", "GeometryInstance3D", true, false):
					(g as GeometryInstance3D).visibility_range_end = RANGE + 30.0
	elif e.model != null:
		e.unseen = float(e.unseen) + delta
		if float(e.unseen) > 3.0 and p.distance_to(cam.global_position) > 30.0:
			if e.driver != null:
				(e.driver as Node).queue_free()
				e.driver = null
			(e.model as Node).queue_free()
			e.model = null
			e.wheels = []
			e.seat = null


func on_crash(id: String) -> void:
	## Hit: no longer driven -- the physics has it now (a wreck, with its driver sat in it).
	var e: Dictionary = live.get(id, {})
	if e.is_empty():
		return
	e.sim = null
	e.moving = false
	e.crashed = true
	e.speed = 0.0
	RoadDriver.tally["crashes"] = int(RoadDriver.tally.get("crashes", 0)) + 1


func _animate(e: Dictionary, delta: float) -> void:
	var sp: float = e.speed
	if sp <= 0.0:
		return
	e.spin = fmod(float(e.spin) - sp / 0.34 * delta, TAU)
	for w in e.wheels:
		(w[0] as Node3D).transform.basis = (w[1] as Basis) * Basis(Vector3.RIGHT, e.spin)


# -- drivers ----------------------------------------------------------------------------------------

func _hire(v: Dictionary, e: Dictionary) -> void:
	## The driver: the car's owner as the population draws them, or for a work vehicle someone made
	## up for it (the same person every time).
	if e.seat == null:
		return
	var pid := str(v.driver)
	var pinned := {"age": 35}
	var pop := ""
	if pid != "":
		var P := _life.person(pid)
		pinned = {"age": int(P.age), "sex": P.sex, "given_name": P.get("given", ""), "surname": P.get("surname", ""),
			"lineage": P.get("lineage", ""), "name_heritage": P.get("name_heritage", "")}
		pop = str(P.get("pop", ""))
	else:
		pid = "driver:" + str(v.id)
		pinned = {"age": 25 + int(abs(hash(pid)) % 35)}
	var person: Dictionary = e.get("person", {})
	if person.is_empty():
		person = NpcTraits.shared().person(world_seed, pid, ["L0", "L1"], pop, pinned)
	pid = str(person.get("_pid", pid))
	var job := {"pid": pid, "data": {}}
	job.task = WorkerThreadPool.add_task(func(): job.data = NpcCharacter.prepare(person, pid, world_seed, "work"), false, "driver " + pid)
	e.pending = job


func _collect() -> void:
	for id in live:
		var e: Dictionary = live[id]
		var job: Dictionary = e.pending
		if job.is_empty() or not WorkerThreadPool.is_task_completed(job.task):
			continue
		WorkerThreadPool.wait_for_task_completion(job.task)
		e.pending = {}
		if job.data.is_empty() or not bool(e.moving) or e.seat == null:
			continue
		var npc := NpcCharacter.from_prepared(job.data)
		var seat := e.seat as Node3D
		seat.get_parent().add_child(npc)
		npc.transform = seat.transform * Transform3D(Basis(), Vector3(0, -SEAT_H, 0))
		var an := NpcAnimator.attach(npc)
		an.ambient = false
		an.ride = NpcRide.seated(npc, SEAT_H)
		e.driver = npc
		return                                                     # one a frame


func stats() -> Dictionary:
	var moving := 0
	var drivers := 0
	for id in live:
		if bool(live[id].moving):
			moving += 1
		if live[id].driver != null:
			drivers += 1
	return {"live": live.size(), "moving": moving, "drivers": drivers, "violations": RoadDriver.tally.duplicate()}
