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
const SLICE_BUDGET_USEC := 2500
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
	# (a type's body plan is warmed when its first car becomes a candidate near the player: _refresh_candidates --
	# every type's at load was ~130 MB)
	_types = (JSON.parse_string(FileAccess.get_file_as_string("res://remake/characters/npc_vehicles.json")) as Dictionary).vehicles
	if FileAccess.file_exists("res://remake/groundcars.json"):              # the player's pods and vans: their places are taken
		for g in (JSON.parse_string(FileAccess.get_file_as_string("res://remake/groundcars.json")) as Dictionary).groundcars:
			_taken.append(Vector2(float(g.s), float(g.x)))
	_load_fleet()
	TrafficReports.load_saved()
	print("NpcTraffic: %d vehicles (%d with rounds)" % [_f_id.size(), _f_rounds.size()])


# -- the clock --------------------------------------------------------------------------------------

# -- the fleet, packed ------------------------------------------------------------------------------------------
# 135,000 vehicles at 1:1 (2026-10-08): kept as columns on a FLEET_CELL grid; a vehicle becomes a Dictionary in
# `vehicles` only while it's a candidate -- parked within NEAR_PARKED of the player, a work vehicle with rounds within
# ROUNDS_R, or a car of a settlement whose people are loaded within LOADED_R.  (A car from farther off passing near the
# player isn't seen: the fake that keeps the footprint small.)
const FLEET_CELL := 500.0
const NEAR_PARKED := 300.0
const ROUNDS_R := 2000.0
const LOADED_R := 1500.0                 # (3 km held ~18,000 cars in a city: their drivers' days recomputed past the caches)
const FLEET_BIN := "res://remake/characters/npc_fleet.bin"   # (the packed fleet: bake_fleet(); the JSON was ~400 MB parsed)
var _f_id := PackedStringArray()
var _f_str := PackedStringArray()        # the types, kinds and places, interned
var _f_type := PackedInt32Array()
var _f_kind := PackedInt32Array()
var _f_at := PackedInt32Array()
var _f_driver := PackedStringArray()
var _f_door := PackedFloat64Array()
var _f_slot := PackedInt32Array()
var _f_rounds := {}                      # fleet index -> [rounds, hours] (the few with rounds)
var _f_grid := {}                        # cell -> PackedInt32Array of fleet indices
var _cand := {}                          # fleet index -> its Dictionary (the candidates)
var _cand_t := 0.0
var _warmed := {}                        # vehicle types whose body plans are being / have been prepared


static func _fleet_stamp() -> String:
	return BakedMeshes.fingerprint([FLEET], 1)


static func bake_fleet() -> int:
	## (remake/tools/bake_world.gd pads) npc_fleet.json packed to npc_fleet.bin
	var d := _pack_fleet()
	d["_stamp"] = _fleet_stamp()
	var f := FileAccess.open(FLEET_BIN, FileAccess.WRITE)
	f.store_var(d)
	f.close()
	return (d.id as PackedStringArray).size()


func _load_fleet() -> void:
	var d := {}
	if FileAccess.file_exists(FLEET_BIN):
		var f := FileAccess.open(FLEET_BIN, FileAccess.READ)
		var v = f.get_var()
		f.close()
		if typeof(v) == TYPE_DICTIONARY and str(v.get("_stamp", "")) == _fleet_stamp():
			d = v
	if d.is_empty():
		d = _pack_fleet()
	_f_id = d.id
	_f_str = d.str
	_f_type = d.type
	_f_kind = d.kind
	_f_at = d.at
	_f_driver = d.driver
	_f_door = d.door
	_f_slot = d.slot
	_f_rounds = d.rounds
	for i in _f_id.size():
		var c := Vector2i(floori(fposmod(_f_door[i * 2], StationGeo.CIRC) / FLEET_CELL), floori(_f_door[i * 2 + 1] / FLEET_CELL))
		var a: PackedInt32Array = _f_grid.get(c, PackedInt32Array())
		a.append(i)
		_f_grid[c] = a


static func _pack_fleet() -> Dictionary:
	## the fleet's vehicles with a model, as columns
	var all_v := ((JSON.parse_string(FileAccess.get_file_as_string(FLEET)) as Dictionary).vehicles as Array).filter(
		func(x): return MODEL.has(str(x.type)) or FleetBodies.has(str(x.type)))
	var ids := PackedStringArray()
	var strs := PackedStringArray()
	var types := PackedInt32Array()
	var kinds := PackedInt32Array()
	var ats := PackedInt32Array()
	var drivers := PackedStringArray()
	var doors := PackedFloat64Array()
	var slots := PackedInt32Array()
	var rounds := {}
	var sidx := {}
	var per_door := {}
	for i in all_v.size():
		var v: Dictionary = all_v[i]
		var k := "%.1f,%.1f" % [float(v.door[0]), float(v.door[1])]
		var slot := int(per_door.get(k, 0))
		per_door[k] = slot + 1
		ids.append(str(v.id))
		for q in [[str(v.type), types], [str(v.kind), kinds], [str(v.at), ats]]:
			if not sidx.has(q[0]):
				sidx[q[0]] = strs.size()
				strs.append(q[0])
		types.append(sidx[str(v.type)])
		kinds.append(sidx[str(v.kind)])
		ats.append(sidx[str(v.at)])
		drivers.append(str(v.driver))
		doors.append(float(v.door[0]))
		doors.append(float(v.door[1]))
		slots.append(slot)
		if not (v.rounds as Array).is_empty() or not (v.hours as Array).is_empty():
			rounds[i] = [v.rounds, v.hours]
	return {"id": ids, "str": strs, "type": types, "kind": kinds, "at": ats, "driver": drivers, "door": doors, "slot": slots,
		"rounds": rounds}


func _fleet_dict(i: int) -> Dictionary:
	var rh: Array = _f_rounds.get(i, [[], []])
	return {"id": _f_id[i], "type": _f_str[_f_type[i]], "kind": _f_str[_f_kind[i]], "at": _f_str[_f_at[i]], "door": [_f_door[i * 2], _f_door[i * 2 + 1]],
		"driver": _f_driver[i], "rounds": rh[0], "hours": rh[1], "slot": _f_slot[i], "where": {}}


func _refresh_candidates() -> void:
	var want := {}
	var r := int(ceil(maxf(ROUNDS_R, LOADED_R) / FLEET_CELL))
	var ncol := ceili(StationGeo.CIRC / FLEET_CELL)
	var ci := floori(fposmod(_here.x, StationGeo.CIRC) / FLEET_CELL)
	var cj := floori(_here.y / FLEET_CELL)
	for di in range(-r, r + 1):
		for dj in range(-r, r + 1):
			for i in _f_grid.get(Vector2i(posmod(ci + di, ncol), cj + dj), PackedInt32Array()):
				if _gone.has(_f_id[i]):
					continue
				var d := NpcPlaces.dist(Vector2(_f_door[i * 2], _f_door[i * 2 + 1]), _here)
				if d <= NEAR_PARKED or (_f_rounds.has(i) and d <= ROUNDS_R) \
						or (d <= LOADED_R and _f_driver[i] != "" and _life.is_loaded(_f_driver[i])):
					want[i] = true
	for i in _cand.keys():
		if not want.has(i) and not live.has(_cand[i].id):
			_cand.erase(i)
	for i in want:
		if not _cand.has(i):
			_cand[i] = _fleet_dict(i)
			var t := _f_str[_f_type[i]]
			if not _warmed.has(t):
				_warmed[t] = true
				FleetBodies.warm_all([t])
	vehicles = _cand.values()
	_i = _i % maxi(1, vehicles.size())


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
	var home := Vector2(float(v.door[0]), float(v.door[1]))
	# a driver living farther off than any trip reaches can't be near: not looked up (looking every one up loaded each
	# settlement's people in turn, 10-50 MB each, round the 1:1 station -- NpcLife keeps MAX_SHARDS of them)
	if NpcPlaces.dist(home, _here) > TRIP_REACH:
		return {}
	if not _life.is_loaded(pid):
		return _parked(home, v)              # (a town whose people aren't in: its cars stay home rather than load them all)
	var P := _life.person(pid)
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
	if r.size() < 2:
		_no_route(key)
	if not is_inside_tree():
		return
	if _route_cache.size() > 20000:
		_route_cache.clear()
	_route_cache[key] = r.slice(1, r.size() - 1) if r.size() > 3 else r


func _no_route(key: String) -> void:
	var ab := key.split(">")
	var bi := Placement.index(ab[0])
	if bi >= 0:
		TrafficReports.file("no_route", Vector2(Placement.s(bi), Placement.x(bi)), "no road route from %s to %s" % [ab[0], ab[1] if ab.size() > 1 else "?"])


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


func _find_spot(door: Vector2, want_face := Vector2.ZERO) -> Dictionary:
	## want_face: the way the car arriving will be pointing -- the space is taken on the side of the street that faces
	## it (its right-hand kerb), so it drives straight in.
	var a := NpcPlaces._attach_on(door, ROADS)
	if a.is_empty():
		return {}
	var e: Array = NpcPlaces._edge(int(a[0]))
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
	if want_face != Vector2.ZERO:
		side = 1.0 if want_face.dot(t) >= 0.0 else -1.0       # (face = t on the +side, -t on the other)
	var ix_door := 1 if side > 0.0 else 0
	if want_face == Vector2.ZERO and int(park[ix_door]) == 0 and int(park[1 - ix_door]) == 1:
		side = -side                                           # across the street, where parking is allowed
		ix_door = 1 - ix_door
	var face := t if side > 0.0 else -t
	var kerb := kerb_r if side > 0.0 else kerb_l
	if int(park[ix_door]) == 1 and kerb - 2.1 < LANE + 1.15:
		park = [0, 0]                                          # (a lane too narrow to park in clear of the traffic: off the street)
	var off := kerb - 1.15 if int(park[ix_door]) == 1 \
		else kerb + float(rd.get("lawn", 0.0)) + float(rd.get("walk", 0.0)) + (VERGE if float(rd.get("walk", 0.0)) > 0.0 else VERGE)
	var sides := [side] if want_face != Vector2.ZERO else [side, -side]   # (the door's side first, then across the street)
	for k in 25 * sides.size():                                # 0, +6.5, -6.5, +13 ... along the road, out to 78 m
		var sd: float = sides[k / 25]
		if k % 25 == 0 and k > 0:
			var ixo := 1 if sd > 0.0 else 0                    # (the other side: its own lane or verge)
			face = t if sd > 0.0 else -t
			kerb = kerb_r if sd > 0.0 else kerb_l
			off = kerb - 1.15 if int(park[ixo]) == 1 and kerb - 2.1 >= LANE + 1.15 \
				else kerb + float(rd.get("lawn", 0.0)) + float(rd.get("walk", 0.0)) + VERGE
		var kk := k % 25
		var along := ceilf(kk / 2.0) * 6.5 * (1.0 if kk % 2 == 1 else -1.0)
		var p := c + right * sd * off + t * along
		p = Vector2(fposmod(p.x, StationGeo.CIRC), p.y)
		if _blocked(p, face):
			continue
		if not TrafficSigns.junctions_near(p, JUNCTION_CLEAR).is_empty():
			continue                                           # (none within 20 ft of a crosswalk at a junction: 4511.68)
		if int(park[ix_door]) == 1 and TramStopZones.inside(p, 2.5):
			continue                                           # a tram stop's kerb: no parking (R7-107)
		_taken.append(p)
		return {"p": p, "dir": face}
	TrafficReports.file("no_parking", door, "nowhere legal to park within 78 m of this door, either side of %s" % str(rd.get("name", "its road")))
	return {}


const JUNCTION_CLEAR := 13.0         # m from a junction's middle: its cross street's half width, the crosswalk, 20 ft


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
		Placement.load_all()
		for i in Placement.count():
			var cell := Vector2i(floori(Placement.s(i) / 40.0), floori(Placement.x(i) / 40.0))
			if not _sites.has(cell):
				_sites[cell] = PackedInt32Array()
			var a: PackedInt32Array = _sites[cell]
			a.append(i)
			_sites[cell] = a
	var cs := Vector2i(floori(q.x / 40.0), floori(q.y / 40.0))
	for dx in [-1, 0, 1]:
		for dy in [-1, 0, 1]:
			for bi in _sites.get(Vector2i(posmod(cs.x + dx, ceili(StationGeo.CIRC / 40.0)), cs.y + dy), PackedInt32Array()):
				# the footprint in the building's frame: local -Z is (cos yaw, -sin yaw), +X (sin yaw, cos yaw)
				var rel := Vector2(StationGeo.wrap_ds(q.x - Placement.s(bi)), q.y - Placement.x(bi))
				var yaw := Placement.yaw(bi)
				var lx := rel.dot(Vector2(sin(yaw), cos(yaw)))
				var lz := rel.dot(Vector2(-cos(yaw), sin(yaw)))
				var fmn := Placement.fmin(bi)
				var fmx := Placement.fmax(bi)
				if lx > float(fmn[0]) - margin and lx < float(fmx[0]) + margin and lz > float(fmn[1]) - margin and lz < float(fmx[1]) + margin:
					return true
	return false


# -- the frame --------------------------------------------------------------------------------------

const TRIP_REACH := 9500.0           # m: the farthest a car trip takes anyone from home (bake_lives WORK_CAR 9 km)


func _process(delta: float) -> void:
	Prof.begin("traffic")
	_tick_traffic(delta)
	Prof.end("traffic")
	TrafficReports.tick()


func _exit_tree() -> void:
	TrafficReports.save()


func _tick_traffic(delta: float) -> void:
	if player == null or _f_id.is_empty() or StationGeo.loading:
		return                                                     # nothing drives till the world is in
	var t_us := Time.get_ticks_usec()
	_ms = Time.get_ticks_msec()
	_here = Vector2(StationGeo.s_of(player.global_position), player.global_position.x)
	_cand_t -= delta
	if _cand_t <= 0.0 or vehicles.is_empty():
		_cand_t = 2.0
		_refresh_candidates()
	if vehicles.is_empty():
		return
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
		if k > 0 and Time.get_ticks_usec() - t_us > SLICE_BUDGET_USEC:
			break                                                  # (every candidate is a real look now: a time budget, not a count)
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
		var f := _flat((e.node as Node3D).global_transform)
		if e.sim == null:
			# parked (or a wreck): only in a driver's way if it stands in their lane -- RoadDriver's leader looks within
			# 1.9 m of its line (a car at the kerb is ~2.5 m off it), and goes round one on the left when it's clear
			agents.append({"id": id, "p": f[0], "dir": f[1], "v": 0.0, "len": float(e.len), "kind": "parked"})
			continue
		agents.append({"id": id, "p": f[0], "dir": f[1], "v": (e.sim as RoadDriver).v, "len": float(e.len), "kind": "car"})
	var st := get_tree().current_scene
	# the player's fleet parked about the streets (pods, vans, bicycles: VehicleStreamer) -- obstacles like any parked car
	if _streamers.is_empty() or _ms > _streamers_ms:
		_streamers_ms = _ms + 10000
		_streamers = st.find_children("*", "VehicleStreamer", true, false)
	for vs in _streamers:
		if not is_instance_valid(vs):
			continue
		for n in (vs as VehicleStreamer)._nodes.values():
			if is_instance_valid(n) and n is RemakeAirVehicle and (n as Node3D).global_position.distance_squared_to(player.global_position) < 40000.0:
				var fv := _flat((n as Node3D).global_transform)
				agents.append({"id": "pv:" + str((n as Node).name), "p": fv[0], "dir": fv[1], "v": (n as RigidBody3D).linear_velocity.length(),
					"len": 4.5 if not n is RemakeBicycle else 1.8, "kind": "parked"})
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
		var plen := 1.0
		if player is CharacterBody3D:
			pv = (player as CharacterBody3D).velocity.length()
		var pveh = player.get("_vehicle")
		if pveh is RigidBody3D:                                    # (driving: the vehicle is what the others see)
			f = _flat((pveh as Node3D).global_transform)
			pv = (pveh as RigidBody3D).linear_velocity.length()
			plen = 4.6
		agents.append({"id": "player", "p": f[0], "dir": f[1], "v": pv, "len": plen, "kind": "player"})
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


func _make_sim(v: Dictionary, e: Dictionary, w: Dictionary, was_parked := false) -> void:
	var r: PackedVector2Array = w.route
	var fresh := false
	var arrive := {}
	if not w.has("loop"):
		# a trip, driven: out of the space it's parked in (just setting off), and into a free space at the far end facing
		# the way it arrives -- from one place to another, never popping onto or off the road (the user, 2026-10-09)
		if was_parked:                                     # (stood at the kerb when its trip began: off from there)
			var r2 := _depart_leg(e.node as Node3D, r)
			fresh = r2 != r
			r = r2
			trips["departed"] = int(trips.get("departed", 0)) + (1 if fresh else 0)
			trips["set_off_on_road"] = int(trips.get("set_off_on_road", 0)) + (0 if fresh else 1)
		var dest: Vector2 = w.get("dest", Vector2.INF)
		if dest != Vector2.INF and r.size() >= 2:
			var n := r.size()
			var de := Vector2(StationGeo.wrap_ds(r[n - 1].x - r[n - 2].x), r[n - 1].y - r[n - 2].y).normalized()
			var key := "%.1f,%.1f#%s" % [dest.x, dest.y, str(v.id)]
			var old_sp: Dictionary = _spot_cache.get(key, {})
			if not old_sp.is_empty():
				_taken.erase(old_sp.p)
			var sp := _find_spot(dest, de)
			if not sp.is_empty():
				var r3 := _arrive_leg(r, sp)
				if r3 != r:
					r = r3
					_spot_cache[key] = sp
					arrive = sp
		trips["into_a_space" if not arrive.is_empty() else "no_space_leg"] = int(trips.get("into_a_space" if not arrive.is_empty() else "no_space_leg", 0)) + 1
	r = drivable(r, false, str(v.id))
	var person: Dictionary = e.get("person", {})
	if person.is_empty():
		person = _person(v)
		e.person = person
	var s := RoadDriver.new()
	s.id = v.id
	# (the rounded route is a little shorter than the timetable's: its distances are scaled to it)
	var k := 1.0
	if w.has("loop"):
		var rp := RoadDriver.Path.new(r)
		var L: float = rp.length
		k = L / maxf(float(w.loop), 1.0)
		s.setup(func(dd): return rp.at(fposmod(dd, L)), float(e.len), person, hash(str(v.id)))
		e.loop = L
		e.marks = (w.marks as Array).map(func(m): return float(m) * k)
		e.next_mark = _next_mark(float(w.t) * k, L, e.marks)
	else:
		var rp2 := RoadDriver.Path.new(r)
		s.setup(func(dd): return rp2.at(dd), float(e.len), person, hash(str(v.id)))
		s.path_len = rp2.length
		k = rp2.length / maxf(float(w.get("length", rp2.length)), 1.0)
		s.stop_at_end = not arrive.is_empty()
		e.trip = w.get("trip", "")
		e.dest = w.get("dest", Vector2.ZERO)
		e.loop = 0.0
	s.t = 0.0 if fresh else float(w.t) * k
	if not fresh:                                       # (where it really stands, on the cleaned route)
		var bp := (e.node as Node3D).global_position
		s.t = _project(s, Vector2(StationGeo.s_of(bp), bp.x))
	s.v = CAR_SPEED * 0.8 if float(w.t) > 1.0 else 0.0
	e.sim = s
	(e.node as NpcCarBody).sim = s
	e.hold = 0.0
	e.parity = hash(str(v.id)) % 6                                 # (the far cars' steps spread over the frames)


func _depart_leg(node: Node3D, r: PackedVector2Array) -> PackedVector2Array:
	## The route from where the car stands (parked at a kerb, by its trip's start): ahead and out into the lane if it
	## points the route's way, else round in a U-turn first. Unchanged if it isn't by the route's start.
	var f := _flat(node.global_transform)
	var p0: Vector2 = f[0]
	var face: Vector2 = f[1]
	if r.size() < 2 or NpcPlaces.dist(p0, r[0]) > 60.0:
		return r
	var d0 := Vector2(StationGeo.wrap_ds(r[1].x - r[0].x), r[1].y - r[0].y).normalized()
	var out := PackedVector2Array([p0])
	var go := face
	if face.dot(d0) < 0.0:
		# a U-turn to the left, from a little ahead (in (s, x) +x is right of +s: a left turn is clockwise)
		const R := 3.6
		var left := Vector2(face.y, -face.x)
		var a := p0 + face * 2.5
		var c := a + left * R
		var a0 := (a - c).angle()
		for m in range(0, 9):
			out.append(c + Vector2.from_angle(a0 - PI * m / 8.0) * R)
		go = -face
	else:
		out.append(p0 + face * 5.0)
	# on into the route, from its first point well ahead of where the turn left the car
	var tip := out[out.size() - 1]
	for i in r.size():
		var q := r[i]
		var dq := Vector2(StationGeo.wrap_ds(q.x - tip.x), q.y - tip.y)
		if dq.dot(go) > 8.0:
			for k in range(i, r.size()):
				out.append(r[k])
			return out
		if NpcPlaces.dist(q, r[0]) > 80.0:
			break
	return r


func _arrive_leg(r: PackedVector2Array, sp: Dictionary) -> PackedVector2Array:
	## The route cut a little before the free space and run into it (it faces the way the car arrives). Unchanged if the
	## space isn't by the route's end.
	var p: Vector2 = sp.p
	var face: Vector2 = sp.dir
	var n := r.size()
	if n < 2 or NpcPlaces.dist(r[n - 1], p) > 70.0:
		return r
	var acc := 0.0
	for i in range(n - 1, -1, -1):
		if i < n - 1:
			acc += NpcPlaces.dist(r[i], r[i + 1])
		if acc > 120.0:
			break
		var dq := Vector2(StationGeo.wrap_ds(r[i].x - p.x), r[i].y - p.y)
		if absf(dq.cross(face)) > 7.0:
			continue                                     # (not on the space's street: never across a block)
		if dq.dot(face) < -14.0:
			var out := r.slice(0, i + 1)
			out.append(p - face * 6.0)
			out.append(p)
			return out
	return r


static func drivable(r: PackedVector2Array, loop := false, report := "") -> PackedVector2Array:
	## A route a car can steer along: the lane offset's loops cut out (offsetting a turn leaves a little swallowtail on
	## its inside, and a spike back on itself), and every corner rounded into an arc (radius up to CORNER_R). On rails
	## the spikes were never seen; on wheels a car can't go back on itself, and a van turning a corner climbed the car
	## parked on it (2026-10-09). (s, x) unwrapped from the first point, wrapped again at the end.
	if r.size() < 3:
		return r
	var u := PackedVector2Array()
	u.append(r[0])
	var prev := r[0]
	var unw := r[0]
	for i in range(1, r.size()):
		unw = Vector2(unw.x + StationGeo.wrap_ds(r[i].x - prev.x), r[i].y)
		prev = r[i]
		# (points closer than MERGE_M to the last kept one go -- a junction's bunch of 1 m legs left no room to round
		# its turn: TrafficReports turn_too_tight, 2026-10-09 -- the last point is always kept)
		if unw.distance_to(u[u.size() - 1]) > MERGE_M or i == r.size() - 1:
			if i == r.size() - 1 and u.size() > 1 and unw.distance_to(u[u.size() - 1]) < 0.25:
				continue
			u.append(unw)
	# loops: a segment crossing one a few on -- what lies between is cut, the crossing kept
	var i := 0
	while i < u.size() - 3:
		var cut := false
		for j in range(i + 2, mini(i + 9, u.size() - 1)):
			var x = Geometry2D.segment_intersects_segment(u[i], u[i + 1], u[j], u[j + 1])
			var loop_len := 0.0
			if x != null:
				for q in range(i + 1, j):
					loop_len += u[q].distance_to(u[q + 1])
			if x != null and loop_len < 15.0:               # (a lane offset's little loop; never a real block the route rounds)
				var keep := u.slice(0, i + 1)
				keep.append(x)
				keep.append_array(u.slice(j + 1))
				u = keep
				cut = true
				break
		if not cut:
			i += 1
	# spikes: a point the route turns back through (more than ~115 degrees) -- an offset's artefact, dropped; or a real
	# reversal (a round going back the way it came: both legs 6 m and more, nearly opposite), made a U-turn to the left
	# (radius UTURN_R, wide of the lane it returns in: a car can't turn on the spot -- TrafficReports off_route, 2026-10-09)
	var changed := true
	var guard := 0
	while changed and u.size() > 2 and guard < 200:
		changed = false
		guard += 1
		for k in range(1, u.size() - 1):
			var la2 := u[k].distance_to(u[k - 1])
			var lb2 := u[k + 1].distance_to(u[k])
			var a := (u[k] - u[k - 1]) / maxf(la2, 1e-6)
			var b := (u[k + 1] - u[k]) / maxf(lb2, 1e-6)
			if a.dot(b) < -0.42:
				if a.dot(b) < -0.85 and la2 >= 6.0 and lb2 >= 6.0:
					var left := Vector2(a.y, -a.x)
					var start := u[k] - a * 2.0
					var c := start + left * UTURN_R
					var a0 := (start - c).angle()
					var arc := PackedVector2Array()
					for m in range(0, 9):
						arc.append(c + Vector2.from_angle(a0 - PI * m / 8.0) * UTURN_R)
					var keep := u.slice(0, k)
					keep.append_array(arc)
					keep.append_array(u.slice(k + 1))
					u = keep
				else:
					u.remove_at(k)
				changed = true
				break
	# corners: an arc tangent to both legs
	var out := PackedVector2Array()
	out.append(u[0])
	for k in range(1, u.size() - 1):
		var a := u[k] - u[k - 1]
		var b := u[k + 1] - u[k]
		var la := a.length()
		var lb := b.length()
		var th := absf(a.angle_to(b))
		if th < 0.12 or la < 0.3 or lb < 0.3:
			out.append(u[k])
			continue
		var tan_d := minf(CORNER_R * tan(th * 0.5), 0.45 * minf(la, lb))
		var rad := tan_d / tan(th * 0.5)
		# a right turn (in (s, x) +x is right of +s: a right turn is anticlockwise, a.cross(b) > 0) has the kerb's corner
		# inside it: the arc may cut no more than CUT_IN inside the lane's corner -- the rest of the way it swings wide.
		# (Rounded on the corner itself it ran over the kerb, through the corner's sign posts: TrafficReports sign_in_lane
		# and sign_hit at Ocean Rd, 38th and 39th Sts, 2026-10-09)
		var vk := u[k]
		if a.cross(b) > 0.0:
			var dev := rad * (1.0 / cos(th * 0.5) - 1.0)
			if dev > CUT_IN:
				var inward := (-a / la + b / lb).normalized()
				vk -= inward * (dev - CUT_IN)
		if rad < TrafficReports.MIN_R and th > 0.6 and report != "":
			TrafficReports.file("turn_too_tight", Vector2(fposmod(u[k].x, StationGeo.CIRC), u[k].y),
				"a %d-degree turn with room for a %.1f m radius (legs %.1f and %.1f m)" % [roundi(rad_to_deg(th)), rad, la, lb], report)
		var p0 := vk - a / la * tan_d
		var p1 := vk + b / lb * tan_d
		var n := clampi(ceili(th * rad / 1.2), 2, 12)
		# the arc's centre: off p0 square to the incoming leg, toward the turn
		var left := Vector2(-a.y, a.x) / la * signf(a.cross(b))
		var c := p0 + left * rad
		var a0 := (p0 - c).angle()
		var sweep := (p1 - c).angle() - a0
		sweep = wrapf(sweep, -PI, PI)
		for m in n + 1:
			out.append(c + Vector2.from_angle(a0 + sweep * m / n) * rad)
	out.append(u[u.size() - 1])
	for k in out.size():
		out[k] = Vector2(fposmod(out[k].x, StationGeo.CIRC), out[k].y)
	return out


const CORNER_R := 7.0                 # m: the most a corner is rounded by (a town street's turn)
const MERGE_M := 5.0                   # m: route points closer than this merge (legs long enough for a ~3 m turn)
const UTURN_R := 2.9                  # m: a reversal's U-turn
const CUT_IN := 0.6                   # m: the most a right turn's arc cuts inside its lane's corner


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
	# near the player it drives on its wheels (NpcCarBody: the physics), farther off it is placed along the route
	var body := e.node as NpcCarBody
	var bp := body.global_position
	var near_d := NpcPlaces.dist(Vector2(StationGeo.s_of(bp), bp.x), _here)
	if not body.driving and near_d < PHYS_R and not body.crashed:
		body.start_driving(s.v)
	elif body.driving and near_d > PHYS_R + 20.0:
		body.stop_driving()
	if body.driving:
		if think:
			# where the physics has it: along its route, and how fast (a crawl in a queue is standing still: else it
			# never counts as stopped -- the standoff rule and the slow decisions of a stood queue wait on that)
			s.t = _project(s, Vector2(StationGeo.s_of(bp), bp.x))
			s.v = maxf(0.0, body.speed) if body.speed > 0.15 else 0.0
			Prof.begin("drive.step")
			s.step(dt, _agents_near(s.pos_at(s.t)), peds, now[2])
			Prof.end("drive.step")
			body.want_acc = s._last_acc
			body.hard_stop = s._last_hard
			# the last word: anything right in front of its nose, the way it's really pointing -- brakes on, whatever the
			# rules said (they judge along the route; a body turning across it at a junction, or one stood half in the lane,
			# was hit on wheels where on rails it was driven through)
			Prof.begin("drive.ahead")
			var blk := _blocked_ahead(e, body)
			Prof.end("drive.ahead")
			if blk != "":
				if int(e.get("blocked_ms", 0)) == 0:
					e.blocked_ms = _ms
				# two stood nose to nose (a junction's standoff): after a few seconds the lower id goes first, slowly
				if (_ms - int(e.blocked_ms)) > STANDOFF_S * 1000.0 and str(v.id) < blk:
					body.want_acc = minf(body.want_acc, 0.6 if body.speed < 1.5 else -1.0)
				else:
					body.want_acc = -8.0
					body.hard_stop = body.speed < 0.5
			else:
				e.blocked_ms = 0
			if body.want_acc > 0.3 and not body.hard_stop:
				body.wake()
			_watch(e, s, body, Vector2(StationGeo.s_of(bp), bp.x), blk)
	elif think:
		Prof.begin("drive.step")
		s.step(dt, _agents_near(s.pos_at(s.t)), peds, now[2])
		Prof.end("drive.step")
	else:
		s.coast(dt)
	# (stood 5 s within 12 m of the end -- someone else in its space, the household's other car: it parks there)
	var near_end := float(e.loop) <= 0.0 and body.driving and s.path_len - s.t < 12.0 and body.speed < 0.2 \
		and int(e.get("still_ms", 0)) > 0 and _ms - int(e.still_ms) > 5000
	if float(e.loop) <= 0.0 and (s.t >= s.path_len - (2.0 if body.driving else 0.5) or near_end):
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
	if body.driving:
		e.speed = body.speed
		return
	Prof.begin("drive.ground")
	(e.node as Node3D).global_transform = _on_ground(e.node, str(v.type), q, atan2(-d.y, d.x))
	Prof.end("drive.ground")
	e.speed = s.v
	body.v_now = -(e.node as Node3D).global_transform.basis.z * s.v


const STANDOFF_S := 3.0
const STUCK_S := 60.0


func _watch(e: Dictionary, s: RoadDriver, body: NpcCarBody, at: Vector2, blk: String) -> void:
	## What a driver reports about the road as they go (TrafficReports): a road they couldn't keep to, and being stuck.
	var p := s.pos_at(s.t)
	var d := s.dir_at(s.t)
	var side := Vector2(StationGeo.wrap_ds(at.x - p.x), at.y - p.y).dot(Vector2(-d.y, d.x)) - s.lat
	if absf(side) > 3.0 and body.speed > 1.0:
		if int(e.get("off_ms", 0)) == 0:
			e.off_ms = _ms
		elif _ms - int(e.off_ms) > 2000 and not e.get("off_told", false):
			e.off_told = true
			TrafficReports.file("off_route", p, "couldn't keep to its route: %.1f m off it at %.0f km/h, heading %d degrees off" % [
				side, body.speed * 3.6, roundi(rad_to_deg(absf(Vector2(-body.global_transform.basis.z.dot(StationGeo.forward(at.x)),
				-body.global_transform.basis.z.x).angle_to(d))))], str(e.v.id))
	else:
		e.off_ms = 0
	if body.speed < 0.2 and float(e.get("hold", 0.0)) <= 0.0:
		if int(e.get("still_ms", 0)) == 0:
			e.still_ms = _ms
		elif _ms - int(e.still_ms) > STUCK_S * 1000.0 and not e.get("stuck_told", false):
			e.stuck_told = true
			var why: Array = []
			for o in s.last_obstacles:
				if not why.has(str(o[2])):
					why.append(str(o[2]))
			TrafficReports.file("stuck", at, "stood %d s wanting to go; held by %s%s" % [int(STUCK_S), ", ".join(why) if not why.is_empty() else "nothing it could see",
				(" (in front of its nose: %s)" % blk) if blk != "" else ""], str(e.v.id))
	else:
		e.still_ms = 0
		e.stuck_told = false

func _blocked_ahead(e: Dictionary, body: NpcCarBody) -> String:
	## The id of whatever stands right ahead of this car's nose (within its stopping distance, across its width), or "".
	var f := _flat(body.global_transform)
	var me: Vector2 = f[0]
	var hd: Vector2 = f[1]
	var rt := Vector2(-hd.y, hd.x)
	var v := maxf(body.speed, 0.0)
	var reach := float(e.len) * 0.5 + 1.0 + v * 0.4 + v * v / 12.0
	var my_id := str(e.v.id)
	for a in _agents_near(me):
		if str(a.id) == my_id:
			continue
		var rel := Vector2(StationGeo.wrap_ds((a.p as Vector2).x - me.x), (a.p as Vector2).y - me.y)
		var along := rel.dot(hd)
		if along <= 0.0:
			continue
		# its extent toward us: half its length along its own heading, half a car's width across it
		var ad: Vector2 = a.dir
		var c := absf(ad.dot(hd))
		var ext := float(a.len) * 0.5 * c + 1.0 * (1.0 - c)
		if along - ext > reach:
			continue
		var side_ext := float(a.len) * 0.5 * (1.0 - c) + 1.0 * c
		if absf(rel.dot(rt)) < 1.0 + side_ext + 0.15:
			return str(a.id)
	return ""


static var PHYS_R := 90.0             # m from the player: driven cars within this drive on their wheels (NpcCarBody; the
                                     # user, 2026-10-09: "NPC cars need to be driving with physics not moving arbitrarily").
                                     # Past it (to RANGE) they follow the same drivable route at their drivers' speeds: 50 on
                                     # wheels at a rush hour was 12 fps, and from 90 m the two can't be told apart


static func _project(s: RoadDriver, at: Vector2) -> float:
	## How far along its route the point nearest `at` is, from where the driver last was (a few Newton steps).
	var t := s.t
	for k in 3:
		var a := s.pos_at(t)
		var d := s.dir_at(t)
		var step := clampf(Vector2(StationGeo.wrap_ds(at.x - a.x), at.y - a.y).dot(d), -12.0, 12.0)
		t += step
		if absf(step) < 0.02:
			break
	if s.path_len < INF:
		t = clampf(t, 0.0, s.path_len)
	return maxf(t, s.t - 1.0)                   # (never back: a car nosing past its line doesn't re-live the stop)


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
	var body := e.node as NpcCarBody
	if body.driving and not body.crashed and Vector2(e.get("dest", Vector2.ZERO)) != Vector2.ZERO:
		# parked where it really stopped, as it stands (else it snapped to its space's exact middle)
		var f := _flat(body.global_transform)
		var dest: Vector2 = e.dest
		var key := "%.1f,%.1f#%s" % [dest.x, dest.y, str(e.v.id)]
		var old_sp: Dictionary = _spot_cache.get(key, {})
		if not old_sp.is_empty():
			_taken.erase(old_sp.p)
		_taken.append(f[0])
		_spot_cache[key] = {"p": f[0], "dir": f[1]}
		trips["parked_on_arrival"] = int(trips.get("parked_on_arrival", 0)) + 1
	(e.node as NpcCarBody).stop_driving()
	(e.node as NpcCarBody).sim = null
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
	var was_parked := e.sim == null and not bool(e.get("moving", false)) and e.has("placed")
	if bool(w.get("moving", false)) and e.sim == null and w.has("route"):
		e.moving = true
		e.speed = float(w.get("speed", 0.0))
		if not was_parked:
			node.global_transform = _on_ground(node, str(v.type), w.pos, float(w.yaw))
		_make_sim(v, e, w, was_parked)                         # (parked: it sets off from where it stands)
		return
	var p: Vector2 = w.pos
	node.global_transform = _on_ground(node, str(v.type), p, float(w.yaw))
	e.placed = true
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
	body.phys = phys
	var wb := _wheel_box(str(v.type))
	body.half_wb = wb.x
	body.half_tr = wb.y
	body.wheel_r = float(phys.get("wheel_r", 0.34))
	body.center_of_mass_mode = RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
	body.center_of_mass = Vector3(0, minf(float(size[2]) * 0.3, 0.55), 0)     # low: batteries in the floor
	body.collision_layer = 1 | RemakeGroundVehicle.HULL_LAYER
	body.collision_mask = 1 | RemakeGroundVehicle.HULL_LAYER | RemakeGroundVehicle.PED_LAYER
	var cs := CollisionShape3D.new()
	var sh := BoxShape3D.new()
	var h := float(size[2]) * 0.95 - NpcCarBody.CLEAR               # (from CLEAR up: driven, kerbs pass under it)
	sh.size = Vector3(float(size[1]) * 0.96, h, float(size[0]) * 0.96)
	cs.shape = sh
	cs.position = Vector3(0, NpcCarBody.CLEAR + h * 0.5, 0)
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


var trips := {}                      # how trips began and ended near the player, since load (tools)
var _streamers: Array = []
var _streamers_ms := 0
var _gone := {}                      # vehicle id -> true: taken by the player, or dismissed -- never shown again


func take_over(id: String, by: StationPlayer) -> String:
	## A parked car, got into: its traffic box goes, and the full drivable body of its type (RemakeModularCar, as Edit >
	## Summon makes) stands where it was, the player at the wheel. From then on it's the player's (group taken_vehicle):
	## the traffic forgets it.
	var e: Dictionary = live.get(id, {})
	if e.is_empty() or e.sim != null:
		return ""
	var vt := str(e.v.type)
	var info := FleetBodies.of(vt)
	if info.is_empty() or bool(info.get("prop", false)) or bool(info.get("air", false)) or bool(info.get("boat", false)):
		return ""
	var node := e.node as Node3D
	var xf := node.global_transform
	var car: RemakeAirVehicle = RemakeBicycle.new() if vt == "bicycle" else RemakeModularCar.new(vt)
	car.name = "Taken_" + id.replace("/", "_")
	car.add_to_group("taken_vehicle")
	get_tree().current_scene.add_child(car)
	car.global_transform = Transform3D(xf.basis, xf.origin + xf.basis.y * 0.05)
	forget(id)
	car.take_seat(by)
	return "car"


func forget(id: String) -> void:
	## Off the roads for good (taken, or dismissed from the PDA): its box freed, never placed again.
	_gone[id] = true
	var e: Dictionary = live.get(id, {})
	if not e.is_empty():
		(e.node as Node).queue_free()
		live.erase(id)
	for i in _cand.keys():
		if str(_cand[i].id) == id:
			_cand.erase(i)
	vehicles = _cand.values()
	_i = _i % maxi(1, vehicles.size())


func on_crash(id: String) -> void:
	## Hit: no longer driven -- the physics has it now (a wreck, with its driver sat in it).
	var e: Dictionary = live.get(id, {})
	if e.is_empty():
		return
	e.sim = null
	(e.node as NpcCarBody).sim = null
	(e.node as NpcCarBody).crashed = true
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
