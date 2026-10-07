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
const RANGE := 130.0                  # (cars are simulated and shown within this; 160 m held ~175 at a rush hour in Calder)
const SLICE := 50                    # vehicles placed per frame (the far ones are a distance check)
const FAR_RECHECK_MS := 3000         # a vehicle found far away isn't looked at again for this long (3 s at
                                     # town speed is ~40 m: inside the RANGE + 100 m margin it was judged by)
var _ms := 0
const CAR_SPEED := 11.0              # m/s on town streets (40 km/h)
const LANE := 1.8                    # the driving lane: this far right of the centre line
const PARK_LANE := 10.0              # roads this wide have a parking lane at each kerb
const VERGE := 3.0                   # parked: the car's centre this far beyond the road's edge (past the pavement)
const WALK_S := 40.0                 # real seconds from the door to the car before driving off
const DWELL_S := 45.0                # real seconds at each stop on a round
const SEAT_H := 0.36
const ROADS := ["street", "main", "county", "hwy", "gravel", "alley"]
const MODEL := {}                     # (hand-built models by type: none now -- every type on the roads is a modular
                                     #  body, FleetBodies; the pod and the minibus joined them 2026-10-04)

var player: Node3D
var world_seed := 1
var vehicles: Array = []             # fleet entries (+ runtime: where, slot)
var live := {}                       # id -> {node, wheels, driver, pending}
var _i := 0
var _life: NpcLife
var _clock: Node
var _scenes := {}
## Parked cars beyond PARKED_FULL_M of the camera are drawn as one merged mesh per vehicle type (build_merged: 2
## surfaces instead of ~40 pieces): Calder's streets park ~80 cars round the player (2026-10-06).
const PARKED_FULL_M := 12.0         # (a full model is ~65 parts: the 20 km ring's Calder drew ~1,600 traffic draws a frame)
const MOVING_FULL_M := 25.0
const FAR_TRIS := 3000               # triangles in a car's far (merged) mesh
const FAR_STEP_M := 25.0
const DRIVER_M := 50.0
const ROUTES_IN_FLIGHT := 4         # routes being planned on worker threads at once
var _route_pending := {}           # driven every frame inside this, every 2nd to 100 m, every 3rd beyond
var _frame := 0
var _merged := {}                    # model key -> ArrayMesh
var _daylight := 1.0                 # read once a frame (DaySkySystem), not from the RenderingServer: that call waits
var _cam_pos := Vector3.INF          # the camera this frame
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
	vehicles = (d.vehicles as Array).filter(func(x): return MODEL.has(str(x.type)) or FleetBodies.has(str(x.type)))
	var used := {}
	for x in vehicles:
		used[str(x.type)] = true
	FleetBodies.warm_all(used.keys())                     # (only the types on the roads)
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
	Prof.begin("traffic.timeline")
	var tl := _life.timeline(pid, day)
	Prof.end("traffic.timeline")
	for seg in tl:
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
			var rk := _life.place_of(P, str(last.from)) + ">" + _life.place_of(P, str(last.to))
			if not _route_cache.has(rk):
				# planned on a worker thread (a long route was 20-70 ms on the main thread); till it's back the
				# car counts as away, and is looked at again soon
				_route_async(_life.place_of(P, str(last.from)), _life.place_of(P, str(last.to)))
				if live.has(v.id):
					return _parked(a if str(last.from) != "" else home, v)     # (in sight: it waits where it is)
				return {"away": true, "soon": true}
			Prof.begin("traffic.route")
			var r := _route(_life.place_of(P, str(last.from)), _life.place_of(P, str(last.to)))
			var cum: PackedFloat32Array = _cum_of(rk, r)
			Prof.end("traffic.route")
			var L := cum[cum.size() - 1] if cum.size() > 0 else 0.0
			var t := (h - start) / gh * CAR_SPEED
			if t < L:
				var w := _on_route(r, t, CAR_SPEED, cum)
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
	var cum2: PackedFloat32Array = _cum_of(key, pts2)
	var L := cum2[cum2.size() - 1]
	var period := L / CAR_SPEED + marks2.size() * DWELL_S
	var t: float = fposmod(float(now[2]) + float(hash(v.id) % 1000), period)
	var d := 0.0
	for i in marks2.size():
		var m0: float = marks2[i]
		var m1: float = marks2[i + 1] if i + 1 < marks2.size() else L
		if t < DWELL_S:
			return _round_at(pts2, m0, L, marks2, cum2)
		t -= DWELL_S
		var run := (m1 - m0) / CAR_SPEED
		if t < run:
			return _round_at(pts2, m0 + t * CAR_SPEED, L, marks2, cum2)
		t -= run
	return _round_at(pts2, L, L, marks2, cum2)


func _round_at(pts: PackedVector2Array, t: float, L: float, marks: Array, cum := PackedFloat32Array()) -> Dictionary:
	var w := _on_route(pts, t, CAR_SPEED, cum)
	w.loop = L
	w.marks = marks
	return w


func _near_line(a: Vector2, b: Vector2) -> bool:
	var ab := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)
	var ap := Vector2(StationGeo.wrap_ds(_here.x - a.x), _here.y - a.y)
	var t := clampf(ap.dot(ab) / maxf(ab.length_squared(), 1e-6), 0.0, 1.0)
	return (ap - ab * t).length() < RANGE + 0.35 * ab.length() + 60.0


func _route_async(from_b: String, to_b: String) -> void:
	var key := from_b + ">" + to_b
	if _route_pending.has(key) or _route_pending.size() >= ROUTES_IN_FLIGHT:
		return
	_route_pending[key] = true
	WorkerThreadPool.add_task(func():
		var r := NpcPlaces.route(from_b, to_b, Vector2.INF, Vector2.INF, 0.0, ROADS, [], Vector2.INF, LANE)
		_route_ready.call_deferred(key, r))


func _route_ready(key: String, r: PackedVector2Array) -> void:
	_route_pending.erase(key)
	if not is_inside_tree():
		return
	if _route_cache.size() > 20000:
		_route_cache.clear()
	_route_cache[key] = r.slice(1, r.size() - 1) if r.size() > 3 else r


func _route(from_b: String, to_b: String) -> PackedVector2Array:
	var key := from_b + ">" + to_b
	if not _route_cache.has(key):
		if _route_cache.size() > 20000:
			_route_cache.clear()
		var r := NpcPlaces.route(from_b, to_b, Vector2.INF, Vector2.INF, 0.0, ROADS, [], Vector2.INF, LANE)
		_route_cache[key] = r.slice(1, r.size() - 1) if r.size() > 3 else r
	return _route_cache[key]


var _cums := {}                      # route key -> its running length at each point


func _cum_of(key: String, r: PackedVector2Array) -> PackedFloat32Array:
	var c = _cums.get(key)
	if c != null and (c as PackedFloat32Array).size() == r.size():
		return c
	if _cums.size() > 20000:
		_cums.clear()
	var out := PackedFloat32Array()
	out.resize(r.size())
	var acc := 0.0
	for i in r.size():
		if i > 0:
			acc += NpcPlaces.dist(r[i - 1], r[i])
		out[i] = acc
	_cums[key] = out
	return out


func _on_route(r: PackedVector2Array, t: float, speed: float, cum := PackedFloat32Array()) -> Dictionary:
	var p := _pos_along(r, t, cum)
	var q := _pos_along(r, t + 2.0, cum)
	var o := _pos_along(r, t - 2.0, cum)
	var dir := Vector2(StationGeo.wrap_ds(q.x - o.x), q.y - o.y)
	if dir.length() < 0.01:
		dir = Vector2(1, 0)
	return {"pos": p, "yaw": atan2(-dir.y, dir.x), "driving": speed > 0.0, "speed": speed, "moving": true, "route": r, "t": t}


static func _pos_along(r: PackedVector2Array, t: float, cum := PackedFloat32Array()) -> Vector2:
	if r.size() == 0:
		return Vector2.ZERO
	t = maxf(t, 0.0)
	if cum.size() == r.size() and r.size() > 1:
		# (with the running lengths: straight to the segment)
		var i := clampi(cum.bsearch(t) - 1, 0, r.size() - 2)
		var seg := cum[i + 1] - cum[i]
		var f := clampf((t - cum[i]) / maxf(seg, 1e-6), 0.0, 1.0)
		return Vector2(fposmod(r[i].x + StationGeo.wrap_ds(r[i + 1].x - r[i].x) * f, StationGeo.CIRC), r[i].y + (r[i + 1].y - r[i].y) * f)
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
	# (per vehicle: keyed by the door and slot, a car parked at someone else's door -- at work, on a visit -- was
	#  given that household's own car's spot, the two drawn in one another; WorldQuery check found it)
	var key := "%.1f,%.1f#%s" % [door.x, door.y, str(v.id)]
	if not _spot_cache.has(key):
		if _spots_this_frame >= 2:
			return {"later": true}                                 # (found in a frame or two)
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
	# where the law lets it park (tools/street_rules.py, the city's ordinance): the door side's parking
	# lane; else the far side's; else off the street -- past the tree lawn and sidewalk, as on a drive
	var rd := NpcPlaces._road(ri)
	var w := float(rd.w)
	var park: Array = rd.get("park", [1 if w >= PARK_LANE else 0, 1 if w >= PARK_LANE else 0])
	var kerb_r := float(rd.get("hr", w * 0.5))
	var kerb_l := float(rd.get("hl", w * 0.5))
	var ix_door := 1 if side > 0.0 else 0
	if int(park[ix_door]) == 0 and int(park[1 - ix_door]) == 1:
		side = -side                                           # across the street, where parking is allowed
		ix_door = 1 - ix_door
	var face := t if side > 0.0 else -t
	var kerb := kerb_r if side > 0.0 else kerb_l
	var off := kerb - 1.15 if int(park[ix_door]) == 1 \
		else kerb + float(rd.get("lawn", 0.0)) + float(rd.get("walk", 0.0)) + (VERGE if float(rd.get("walk", 0.0)) > 0.0 else VERGE)
	for k in 17:                                               # 0, +6.5, -6.5, +13 ... along the road
		var along := ceilf(k / 2.0) * 6.5 * (1.0 if k % 2 == 1 else -1.0)
		var p := c + right * side * off + t * along
		p = Vector2(fposmod(p.x, StationGeo.CIRC), p.y)
		if _blocked(p, face):
			continue
		if int(park[ix_door]) == 1 and TramStopZones.inside(p, 2.5):
			continue                                           # a tram stop's kerb: no parking (R7-107)
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
	Prof.begin("traffic")
	_tick_traffic(delta)
	Prof.end("traffic")


func _tick_traffic(delta: float) -> void:
	if player == null or vehicles.is_empty() or StationGeo.loading:
		return                                                     # nothing drives till the world is in
	var t_us := Time.get_ticks_usec()
	_ms = Time.get_ticks_msec()
	_here = Vector2(StationGeo.s_of(player.global_position), player.global_position.x)
	var now := _now()
	var ts0 := Time.get_ticks_usec()
	_spots_this_frame = 0
	Prof.begin("traffic.sense")
	_sense_world()
	Prof.end("traffic.sense")
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
		if int(v.get("far_until", 0)) > _ms:
			continue                                               # far off a moment ago: can't be near yet
		var tl := Time.get_ticks_usec()
		Prof.begin("traffic.locate")
		v.where = _locate(v, now)
		Prof.end("traffic.locate")
		var tm := Time.get_ticks_usec()
		_show(v)
		var wh: Dictionary = v.where
		if (wh.is_empty() or wh.get("away", false)) and not live.has(v.id):
			v.far_until = _ms + (300 if wh.get("soon", false) else FAR_RECHECK_MS)    # (soon: its route is being planned)
		t_loc += tm - tl
		t_show += Time.get_ticks_usec() - tm
	var t_slice := Time.get_ticks_usec() - t_us
	_built_this_frame = 0
	var cam := get_viewport().get_camera_3d()
	_cam_pos = cam.global_position if cam else Vector3.INF
	_frame += 1
	var sky := get_tree().current_scene.get_node_or_null("DaySkySystem")
	if sky and sky.has_method("daylight"):
		_daylight = sky.daylight()
	var t_d := 0
	var t_v := 0
	for id in live.keys():
		var e: Dictionary = live[id]
		var t1 := Time.get_ticks_usec()
		if e.sim != null:
			# a driver decides (RoadDriver.step: lights, junctions, the car ahead) every frame only within
			# FAR_STEP_M of the camera; farther, 20 times a second (traffic simulators run drivers at ~10 Hz) and
			# in a queue 10 times -- in between the car coasts on at its speed, so it still moves smoothly (Calder's
			# rush hour: 30 decisions a frame at ~240 us each, 2026-10-06)
			var dc := (e.node as Node3D).global_position.distance_to(_cam_pos) if _cam_pos != Vector3.INF else 0.0
			var every := 1 if dc <= FAR_STEP_M else 3
			if (e.sim as RoadDriver).v < 0.1 and (e.sim as RoadDriver)._still_s > 1.0:
				every = 6
			Prof.begin("traffic.drive")
			_drive(e, delta, now, every == 1 or (_frame + int(e.get("parity", 0))) % every == 0)
			Prof.end("traffic.drive")
		var t2 := Time.get_ticks_usec()
		if live.has(id):
			Prof.begin("traffic.visual")
			# (past 40 m the on-screen check, the model swap and the driver are looked at every 3rd frame)
			var ev: Dictionary = live[id]
			var far := _cam_pos != Vector3.INF and (ev.node as Node3D).global_position.distance_squared_to(_cam_pos) > 1600.0
			ev.vis_dt = float(ev.get("vis_dt", 0.0)) + delta
			if not far or (_frame + int(ev.get("parity", hash(id)))) % 3 == 0 or ev.model == null:
				_visual(ev, float(ev.vis_dt), cam)
				_driver_lod(ev)
				ev.vis_dt = 0.0
			Prof.end("traffic.visual")
			Prof.begin("traffic.animate")
			_animate(live[id], delta)
			Prof.end("traffic.animate")
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
	# the agents by 100 m cell (trains in every cell: a crossing looks 400 m out), so each driver is handed only
	# those round it (every driver scanning every agent was O(n^2): ~1 ms a frame at a rush hour's 90 cars)
	_agrid.clear()
	_near_cache.clear()
	_trains.clear()
	for a in agents:
		if str(a.kind) == "train":
			_trains.append(a)
			continue
		var c := _acell(a.p)
		if not _agrid.has(c):
			_agrid[c] = []
		(_agrid[c] as Array).append(a)


const ACELL := 100.0
var _agrid := {}
var _near_cache := {}
var _trains: Array = []


func _acell(p: Vector2) -> Vector2i:
	return Vector2i(floori(fposmod(p.x, StationGeo.CIRC) / ACELL), floori(p.y / ACELL))


func _agents_near(p: Vector2) -> Array:
	var c := _acell(p)
	if _near_cache.has(c):
		return _near_cache[c]
	var out: Array = _trains.duplicate()
	var ncol := ceili(StationGeo.CIRC / ACELL)
	for di in [-1, 0, 1]:
		for dj in [-1, 0, 1]:
			out.append_array(_agrid.get(Vector2i(posmod(c.x + di, ncol), c.y + dj), []))
	_near_cache[c] = out
	return out


# -- driving ----------------------------------------------------------------------------------------

func _spot_taken(p: Vector2, me: String) -> bool:
	for id in live:
		var o: Dictionary = live[id]
		if id == me or o.sim == null:
			continue
		var s: RoadDriver = o.sim
		if NpcPlaces.dist(s.pos_at(s.t), p) < 7.0:
			return true
	return false


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
	e.parity = hash(str(v.id)) % 6                                 # (the far cars' steps spread over the frames)


static func _next_mark(t: float, L: float, marks: Array) -> float:
	var lap := floorf(t / L) * L
	for m in marks:
		if lap + float(m) > t + 0.5:
			return lap + float(m)
	return lap + L + (float(marks[0]) if not marks.is_empty() else 0.0)


func _drive(e: Dictionary, dt: float, now: Array, think := true) -> void:
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
	if think:
		Prof.begin("drive.step")
		s.step(dt, _agents_near(s.pos_at(s.t)), peds, now[2])
		Prof.end("drive.step")
	else:
		s.coast(dt)
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
	Prof.begin("drive.ground")
	(e.node as Node3D).global_transform = _on_ground(e.node, str(v.type), q, atan2(-d.y, d.x))
	Prof.end("drive.ground")
	e.speed = s.v
	(e.node as NpcCarBody).v_now = -(e.node as Node3D).global_transform.basis.z * s.v


var _wheelbox := {}                   # type -> Vector2(half the wheelbase, half the track)


func _wheel_box(vtype: String) -> Vector2:
	if not _wheelbox.has(vtype):
		var wb := Vector2(1.25, 0.75)
		if vtype == "minivan":
			wb = Vector2(1.67, 0.84)
		var info := FleetBodies.of(vtype)
		if not info.is_empty() and str(info.get("board", "none")) != "none":
			var b := RemakeModularCar._board(str(info.board))
			if not b.is_empty():
				wb = Vector2(float(b.wheelbase_m) / 2.0, float(b.track_m) / 2.0)
		_wheelbox[vtype] = wb
	return _wheelbox[vtype]


func _on_ground(node: Node3D, vtype: String, p: Vector2, yaw: float) -> Transform3D:
	## Stood on the road's real surface. The height at each wheel's contact is a ray down onto the colliders (the road's
	## own mesh, a kerb, a bridge's deck); the body is pitched and rolled to that plane and lifted by any twist, so every
	## wheel is on the surface and none in it. (Standing it level at the terrain's height under its middle put its wheels
	## into the road wherever the road sat above the terrain, sloped, or was cambered.)
	# far from the camera (40 m+), the road-height ray and the four wheel rays are redone only every 2 m of travel;
	# in between, the last pitch, roll, lift and road height carry on (Calder's busy streets: the rays were 11 ms a
	# frame, 2026-10-06)
	var bas := StationGeo.basis(p.x, yaw)
	var g: Array = node.get_meta("ground", [])
	if _cam_pos != Vector3.INF and g.size() == 5 and ((g[0] as Vector2).distance_to(p) < 0.5
			or (g[0] as Vector2).distance_to(p) < 2.0 and StationGeo.point(p.x, p.y, 0.0).distance_to(_cam_pos) > 40.0):
		var o2 := StationGeo.point(p.x, p.y, float(g[4]))         # (under 2 m on: the road's height changes < 0.1 m)
		var b2 := bas.rotated(bas.x.normalized(), float(g[1]))
		b2 = b2.rotated(b2.z.normalized(), float(g[2]))
		return Transform3D(b2.orthonormalized(), o2 + bas.y * float(g[3]))
	Prof.begin("ground.road_h")
	var h := _road_h(p, node)
	Prof.end("ground.road_h")
	var origin := StationGeo.point(p.x, p.y, h)
	var box := _wheel_box(vtype)
	var up := bas.y
	var space := node.get_world_3d().direct_space_state
	var ex: Array[RID] = []
	if node is CollisionObject3D:
		ex.append((node as CollisionObject3D).get_rid())
	var hs: Array[float] = []
	for c: Vector2 in [Vector2(-box.y, -box.x), Vector2(box.y, -box.x), Vector2(-box.y, box.x), Vector2(box.y, box.x)]:   # FL FR BL BR
		var at: Vector3 = origin + bas.x * c.x + bas.z * c.y
		var hit := _surface_hit(space, at + up * 1.2, at - up * 1.5, ex)
		var hp: Vector3 = hit.position if not hit.is_empty() else origin
		hs.append((hp - origin).dot(up))
	var f := (hs[0] + hs[1]) * 0.5
	var bk := (hs[2] + hs[3]) * 0.5
	var l := (hs[0] + hs[2]) * 0.5
	var r := (hs[1] + hs[3]) * 0.5
	var mean := (hs[0] + hs[1] + hs[2] + hs[3]) * 0.25
	var plane: Array[float] = [mean + (f - bk) * 0.5 + (l - r) * 0.5, mean + (f - bk) * 0.5 - (l - r) * 0.5,
		mean - (f - bk) * 0.5 + (l - r) * 0.5, mean - (f - bk) * 0.5 - (l - r) * 0.5]
	var twist := 0.0
	for i in 4:
		twist = maxf(twist, hs[i] - float(plane[i]))
	var pitch := atan2(f - bk, 2.0 * box.x)                # (nose up when the front is higher)
	var roll := atan2(r - l, 2.0 * box.y)                  # (right side up when the right is higher)
	node.set_meta("ground", [p, pitch, roll, mean + twist, h])
	bas = bas.rotated(bas.x.normalized(), pitch)
	bas = bas.rotated(bas.z.normalized(), roll)
	return Transform3D(bas.orthonormalized(), origin + up * (mean + twist))


func _surface_hit(space: PhysicsDirectSpaceState3D, from: Vector3, to: Vector3, ex: Array[RID]) -> Dictionary:
	## A ray down onto the surface a wheel stands on, through any vehicle in the way -- the traffic's own (this one's
	## body among them: tilted, its sill under a ray lifted that side again, and again, until it stood on edge), a
	## summoned one, a loose panel.
	var skip: Array[RID] = ex.duplicate()
	for i in 6:
		var q := PhysicsRayQueryParameters3D.create(from, to, 1)
		q.exclude = skip
		var hit: Dictionary = space.intersect_ray(q)
		if hit.is_empty():
			return hit
		var c := hit.collider as CollisionObject3D
		if c == null or not (is_ancestor_of(c) or c is RigidBody3D or (c.collision_layer & (RemakeGroundVehicle.HULL_LAYER | (1 << 10))) != 0 \
				or c.is_in_group("delivered_wagon") or c.get_parent() is RigidBody3D):
			return hit
		skip.append(hit.rid)
	return {}


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
	# a car setting off onto the road (its trip's timetable puts it there) waits till its spot is clear of the
	# cars already being driven: dropped on top of one, both stopped for good and the queue locked (Calder)
	if bool(w.get("moving", false)) and (e.is_empty() or e.sim == null) and w.has("route") and _spot_taken(w.pos, str(v.id)):
		return
	if e.is_empty():
		e = _build(v)
		if e.is_empty():
			return
		live[v.id] = e
	var node := e.node as Node3D
	var p: Vector2 = w.pos
	node.global_transform = _on_ground(node, str(v.type), p, float(w.yaw))
	e.speed = float(w.get("speed", 0.0))
	e.moving = bool(w.get("moving", false))
	if bool(w.get("moving", false)) and e.sim == null and w.has("route"):
		_make_sim(v, e, w)
	# a driver at the wheel only where one can be seen: a skinned, animated person in each of a rush hour's ~60
	# moving cars was ~200 animators and their draws (Calder, 2026-10-06)
	var wants_driver := bool(w.get("moving", false)) and (_cam_pos == Vector3.INF
		or node.global_position.distance_to(_cam_pos) < DRIVER_M)
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
	if FleetBodies.has(str(v.type)) and not MODEL.has(str(v.type)):
		return FleetBodies.board_path(str(FleetBodies.of(str(v.type)).board))      # (the board; the body goes on it)
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
		var dcam := p.distance_to(cam.global_position) if cam else 0.0
		# far and parked, or far, moving and in daylight (at night a moving car keeps its full model: its lamps
		# light the road), draws as the merged mesh
		var was := bool(e.get("lite", false))
		var hy := 6.0 if was else 0.0                                   # (hysteresis: no flipping at the line)
		var lite := dcam >= PARKED_FULL_M - hy and (not bool(e.moving) and e.sim == null
			or dcam >= MOVING_FULL_M - hy and _daylight > 0.5)
		var mk: String = e.get("mkey", "")
		if mk == "":
			mk = _merge_key(e.v)
			e.mkey = mk
		if e.model != null and bool(e.get("lite", false)) != lite:
			if not lite or _merged.has(mk):                # (swap: full model near or moving, merged far and parked)
				if e.driver != null:
					(e.driver as Node).queue_free()
					e.driver = null
				(e.model as Node).queue_free()
				e.model = null
				e.wheels = []
				e.seat = null
		if e.model == null and lite and _merged.has(mk):
			var mi := MeshInstance3D.new()
			mi.mesh = _merged[mk]
			mi.visibility_range_end = RANGE + 30.0
			node.add_child(mi)
			e.model = mi
			e.lite = true
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
				var vt := str(e.v.type)
				if FleetBodies.has(vt) and not MODEL.has(vt):           # a modular body on its board
					FleetBodies.strip_board(m)
					var vb := VehicleBody.make(VehicleBody.prepare(str(FleetBodies.of(vt).blueprint)))
					m.add_child(vb)
				var wheels: Array = []
				for n in m.find_children("wheel_*", "Node3D", true, false):
					wheels.append([n, (n as Node3D).transform.basis])
				e.wheels = wheels
				var seat := m.find_child("seat_driver", true, false) as Node3D
				if seat == null:
					seat = m.find_child("seat_pilot", true, false) as Node3D
				e.seat = seat
				for g in m.find_children("*", "GeometryInstance3D", true, false):
					var gi := g as GeometryInstance3D
					gi.visibility_range_end = RANGE + 30.0
					# the cabin and the small fittings (gauges, needles, seats, linings) only close up, and casting no
					# shadow: 20 full cars' interiors were ~1,300 draws a frame, twice over with the sun's shadows
					var ab := gi.get_aabb()
					var nm := String(gi.name).to_lower() + String(gi.get_parent().name).to_lower()
					if ab.get_longest_axis_size() < 0.6 or "_in" in nm or "lining" in nm or "seat" in nm or "gauge" in nm \
							or "needle" in nm or "dash" in nm or "steer" in nm:
						gi.visibility_range_end = 30.0
						gi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
				e.lite = false
				if not _merged.has(mk) and not _merge_pending.has(mk):
					_merge_async(mk, m)
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


var _merge_pending := {}


func _merge_async(mk: String, m: Node3D) -> void:
	## A car type's far mesh: its surfaces gathered here (the scene tree is the main thread's), merged and given
	## automatic detail levels (meshoptimizer) on a worker thread -- the merge was a 100 ms hitch the first time
	## each type was seen, the LODs ~60 ms (the user, 2026-10-06: "we skipped LOD models for the new vehicles").
	## Till it's back, that type's cars keep their full models.
	_merge_pending[mk] = true
	var parts := gather_model(m)
	WorkerThreadPool.add_task(func():
		var merged := build_merged(parts)
		var im := ImporterMesh.new()
		for si in merged.get_surface_count():
			im.add_surface(Mesh.PRIMITIVE_TRIANGLES, merged.surface_get_arrays(si), [], {}, merged.surface_get_material(si))
		im.generate_lods(25.0, 60.0, [])
		# the far mesh itself is a simplified level (~FAR_TRIS a car): the renderer's own LOD choice kept the 18-24 k
		# triangle original at 40-130 m -- ~60 such cars were 1.2 M triangles in Calder on the 20 km ring
		var total := 0
		for si in im.get_surface_count():
			total += (im.get_surface_arrays(si)[Mesh.ARRAY_INDEX] as PackedInt32Array).size()
		var keep := float(FAR_TRIS * 3) / maxf(1.0, float(total))
		var far := ArrayMesh.new()
		for si in im.get_surface_count():
			var arr := im.get_surface_arrays(si)
			var base := (arr[Mesh.ARRAY_INDEX] as PackedInt32Array).size()
			var best: PackedInt32Array = arr[Mesh.ARRAY_INDEX]
			var below := PackedInt32Array()
			for li in im.get_surface_lod_count(si):
				var ix := im.get_surface_lod_indices(si, li)
				if ix.size() >= base * keep:
					if ix.size() < best.size():
						best = ix
				elif ix.size() > below.size():
					below = ix
			if best.size() == base and below.size() > 0:
				best = below                         # (every level is under the target: the nearest one)
			arr[Mesh.ARRAY_INDEX] = best
			far.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
			far.surface_set_material(si, im.get_surface_material(si))
		_merge_done.call_deferred(mk, far))


func _merge_done(mk: String, mesh: ArrayMesh) -> void:
	_merge_pending.erase(mk)
	if is_inside_tree():
		_merged[mk] = mesh


func _merge_key(v: Dictionary) -> String:
	return _model_path(v) + "|" + str(v.type)


static var _far_opaque: StandardMaterial3D
static var _far_glass: StandardMaterial3D


static func _mat_colour(mat: Material) -> Color:
	if mat is ShaderMaterial:
		var t = (mat as ShaderMaterial).get_shader_parameter("tint")
		return t if t is Color else Color(0.6, 0.6, 0.6)
	if mat is BaseMaterial3D:
		return (mat as BaseMaterial3D).albedo_color
	return Color(0.5, 0.5, 0.5)


static func _is_glass(mat: Material) -> bool:
	if mat == null:
		return false
	if "glass" in mat.resource_name.to_lower():
		return true
	return mat is BaseMaterial3D and ((mat as BaseMaterial3D).transparency != BaseMaterial3D.TRANSPARENCY_DISABLED
		or (mat as BaseMaterial3D).albedo_color.a < 0.99)


static func _far_materials() -> void:
	if _far_opaque != null:
		return
	_far_opaque = StandardMaterial3D.new()
	_far_opaque.resource_name = "car_far"
	_far_opaque.vertex_color_use_as_albedo = true
	_far_opaque.roughness = 0.55
	_far_opaque.cull_mode = BaseMaterial3D.CULL_DISABLED
	_far_glass = StandardMaterial3D.new()
	_far_glass.resource_name = "car_far_glass"
	_far_glass.albedo_color = Color(0.12, 0.16, 0.2, 0.55)
	_far_glass.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_far_glass.roughness = 0.1
	_far_glass.metallic = 0.3
	_far_glass.cull_mode = BaseMaterial3D.CULL_DISABLED


static func gather_model(m: Node3D) -> Array:
	## [[arrays, transform, colour, glass?]] of a model's outside surfaces, in the model's frame (the interior
	## layer and hidden parts left out). Main thread: it reads the scene tree.
	_far_materials()
	var out: Array = []
	for g in m.find_children("*", "MeshInstance3D", true, false):
		var mi := g as MeshInstance3D
		if mi.mesh == null or (mi.layers & VehicleBody.INTERIOR_LAYER) != 0:
			continue
		var hidden := false
		var xf := Transform3D()
		var n: Node = mi
		while n != null and n != m:
			if n is Node3D:
				if not (n as Node3D).visible:
					hidden = true
					break
				xf = (n as Node3D).transform * xf
			n = n.get_parent()
		if hidden:
			continue
		for si in mi.mesh.get_surface_count():
			if mi.mesh.surface_get_primitive_type(si) != Mesh.PRIMITIVE_TRIANGLES:
				continue
			var mat := mi.get_active_material(si)
			var glass := _is_glass(mat)
			out.append([mi.mesh.surface_get_arrays(si), xf, _mat_colour(mat) if not glass else Color(1, 1, 1), glass])
	return out


static func build_merged(parts: Array) -> ArrayMesh:
	## One mesh in two surfaces -- everything opaque, coloured per vertex with its material's colour, and the glass
	## -- for far cars: 2 draws instead of ~40 pieces. Safe on a worker thread.
	var P2 := [[PackedVector3Array(), PackedVector3Array(), PackedColorArray(), PackedInt32Array()],
		[PackedVector3Array(), PackedVector3Array(), PackedColorArray(), PackedInt32Array()]]
	for part in parts:
		var arr: Array = part[0]
		var xf: Transform3D = part[1]
		var c: Color = part[2]
		var nb := xf.basis.inverse().transposed()
		var vs: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
		var ns = arr[Mesh.ARRAY_NORMAL]
		var ix = arr[Mesh.ARRAY_INDEX]
		var P: Array = P2[1 if part[3] else 0]
		var base := (P[0] as PackedVector3Array).size()
		for i in vs.size():
			P[0].append(xf * vs[i])
			P[1].append((nb * ns[i]).normalized() if ns is PackedVector3Array and i < ns.size() else Vector3.UP)
			P[2].append(c)
		if ix is PackedInt32Array and ix.size() > 0:
			for i in ix.size():
				P[3].append(base + ix[i])
		else:
			for i in vs.size():
				P[3].append(base + i)
	var out := ArrayMesh.new()
	for k in 2:
		var P: Array = P2[k]
		if (P[0] as PackedVector3Array).is_empty():
			continue
		var a := []
		a.resize(Mesh.ARRAY_MAX)
		a[Mesh.ARRAY_VERTEX] = P[0]
		a[Mesh.ARRAY_NORMAL] = P[1]
		a[Mesh.ARRAY_COLOR] = P[2]
		a[Mesh.ARRAY_INDEX] = P[3]
		out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, a)
		out.surface_set_material(out.get_surface_count() - 1, _far_opaque if k == 0 else _far_glass)
	return out


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

func _driver_lod(e: Dictionary) -> void:
	## A driven car's driver comes when it's within DRIVER_M of the camera, and goes again past it (+10 m).
	if e.sim == null or _cam_pos == Vector3.INF:
		return
	var d := (e.node as Node3D).global_position.distance_to(_cam_pos)
	if d < DRIVER_M and e.driver == null and (e.pending as Dictionary).is_empty():
		_hire(e.v, e)
	elif d > DRIVER_M + 10.0 and e.driver != null:
		(e.driver as Node).queue_free()
		e.driver = null


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
