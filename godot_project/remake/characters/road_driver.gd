extends RefCounted
class_name RoadDriver

## Someone driving a road vehicle (a car, van, truck, or a tram's operator) along a path, by Ohio's
## rules of the road as they apply to what this driver can SEE (research/traffic/01): the signs facing
## them, the stop bars and signals ahead, the junctions, the centre-line markings beside them, the
## rail crossings, and the other road users around. Nothing is baked per road: a speed sign sets the
## limit, a stop sign makes them stop at its bar, a dashed centre line lets them overtake.
##
## Whether they keep each rule is theirs (the generator's drive_* traits, research/traffic/02-03):
## how far over the limit, whether the stop is a full one, how close they follow, whether they pass
## on the right, run a fresh red, cross a double yellow to overtake, or stop for someone about to
## cross. Professionals (tram operators) keep every rule. Nobody drives into anybody.
##
## Motion: the Intelligent Driver Model (Treiber et al. 2000) toward the desired speed, against the
## nearest constraint ahead (a leader, a stop line, a red signal, a person, a train).
##   var d := RoadDriver.new(); d.setup(path_fn, length_m, traits, seed)
##   each frame: d.step(dt, agents, peds, clock_s)   then d.t (distance along), d.v, d.lat (m right)
## agents: [{id, p (s, x), dir (s, x) unit, v, len, kind ("car", "tram", "train", "player")}]

const URBAN := 40.0 / 3.6            # Ohio's prima-facie 25 mph in a municipal corporation (posted as 40 km/h)
const RURAL := 90.0 / 3.6            # 55 mph outside one
const ALLEY := 24.0 / 3.6            # 15 mph in alleys
const LOOK_MIN := 25.0
const B_COMF := 2.2                  # m/s^2, a comfortable stop
const S0 := 2.0                      # m, the gap kept standing behind a stopped vehicle
const ROLL := 2.2                    # m/s, a rolling stop

static var tally := {}


class Path:
	## A polyline in (s, x) with its distances, for quick lookups along it.
	var pts: PackedVector2Array
	var cum := PackedFloat64Array()
	var length := 0.0

	func _init(p: PackedVector2Array) -> void:
		pts = p
		cum.resize(p.size())
		var acc := 0.0
		for i in p.size():
			if i > 0:
				acc += NpcPlaces.dist(p[i - 1], p[i])
			cum[i] = acc
		length = acc

	func at(d: float) -> Vector2:
		if pts.size() == 0:
			return Vector2.ZERO
		d = clampf(d, 0.0, length)
		var i := maxi(0, cum.bsearch(d) - 1)
		if i >= pts.size() - 1:
			return pts[pts.size() - 1]
		var f := (d - cum[i]) / maxf(cum[i + 1] - cum[i], 1e-6)
		var a := pts[i]
		var b := pts[i + 1]
		return Vector2(fposmod(a.x + StationGeo.wrap_ds(b.x - a.x) * f, StationGeo.CIRC), a.y + (b.y - a.y) * f)               # violation -> count (everyone, since load)

var path: Callable                   # distance -> (s, x)
var path_len := INF                  # INF: a loop
var t := 0.0
var v := 0.0
var lat := 0.0
var length := 4.8
var limit := URBAN
var professional := false
var v_cap := INF                     # an outside limit on speed (a tram keeping to its timetable)
var stop_at_end := false             # a trip that ends parked (its route runs into the space): to a stop at its end
var id: Variant = null

var speeding := 0.0
var full_stop := 0.3
var headway := 1.5
var pass_right := 0.1
var red_light := 0.03
var yield_peds := 0.5
var cross_solid := 0.02
var sensation := 0.45

var violations := {}
var dbg := {}                        # what this driver last saw and wanted (for tools)
var _rng := RandomNumberGenerator.new()
var _decided := {}                   # an encounter -> its decision (once per encounter)
var _passed := {}                    # sign ids gone by
var _stopped_s := 0.0                # seconds stood still at a stop line
var _still_s := 0.0                  # seconds stood still, for any reason (the standoff rule below)
const STANDOFF_S := 4.0
var last_obstacles: Array = []
var _last_acc := 0.0
var _last_hard := false


func coast(dt: float) -> void:
	## Between decisions (a far car decides 20 times a second, NpcTraffic): on along the road with the last
	## acceleration it chose, and on toward its lane.
	if dt <= 0.0:
		return
	v = maxf(0.0, v + _last_acc * dt)
	if _last_hard:
		v = minf(v, 0.3)
	t += v * dt
	if path_len < INF:
		t = minf(t, path_len)
	lat = move_toward(lat, _lat_target, 1.3 * dt)
	_still_s = _still_s + dt if v < 0.1 else 0.0
var _cleared := {}                   # stop/yield controls dealt with
var _held := 0.0
var _passing := ""
var _pass_id: Variant = null
var _lat_target := 0.0
var _warn_until := -1.0
var _limit_set := false
var _sense_t := 0.0
var _stop_abs: Array = []            # [distance along the path of the line, sign]
var _curves: Array = []              # [distance along, curvature]
var _sig := {}
var _juncs: Array = []
var _xing := {}


func setup(p_path: Callable, p_len: float, traits: Dictionary, seed: int, p_professional := false) -> void:
	path = p_path
	length = p_len
	professional = p_professional
	_rng.seed = seed
	if not professional:
		speeding = float(traits.get("drive_speeding", 0.0))
		full_stop = float(traits.get("drive_full_stop", 0.3))
		headway = float(traits.get("drive_headway", 1.5))
		pass_right = float(traits.get("drive_pass_right", 0.1))
		red_light = float(traits.get("drive_red_light", 0.03))
		yield_peds = float(traits.get("drive_yield_peds", 0.5))
		cross_solid = float(traits.get("drive_cross_solid", 0.02))
		sensation = float(traits.get("sensation_seeking", 0.45))
	else:
		headway = 1.8


func pos_at(d: float) -> Vector2:
	return path.call(clampf(d, 0.0, path_len) if path_len < INF else d)


func dir_at(d: float) -> Vector2:
	var a := pos_at(d - 1.5)
	var b := pos_at(d + 1.5)
	var u := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)
	return u.normalized() if u.length() > 0.01 else Vector2(1, 0)


static func _rel(a: Vector2, b: Vector2) -> Vector2:
	return Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)


func _violate(kind: String) -> void:
	violations[kind] = int(violations.get(kind, 0)) + 1
	tally[kind] = int(tally.get(kind, 0)) + 1


func _decide(key: String, p: float) -> bool:
	if not _decided.has(key):
		_decided[key] = _rng.randf() < p
	return _decided[key]


# -- one frame --------------------------------------------------------------------------------------

func step(dt: float, all_agents: Array, all_peds: Array, clock_s: float) -> void:
	if dt <= 0.0:
		return
	var p := pos_at(t)
	# every check below looks within 90 m (trains: 400 m): sift the lists once, not in each of the six loops (a busy
	# town's ~40 drivers each scanning ~80 agents six times a step was 5 ms a frame -- Calder, 2026-10-06)
	var agents: Array = []
	var near_all: Array = []                                   # (and the parked: only ever a leader, standing in the lane)
	for a in all_agents:
		var ap: Vector2 = a.p
		var dsq := (ap - p).length_squared()
		var wrapped := absf(ap.x - p.x) > 9000.0
		if a.kind == "parked":
			if dsq < 8100.0 or wrapped:
				near_all.append(a)
		elif a.kind == "train" or dsq < 12100.0 or wrapped:
			agents.append(a)
			near_all.append(a)
	var peds: Array = []
	for q in all_peds:
		if ((q.p as Vector2) - p).length_squared() < 1600.0 or absf((q.p as Vector2).x - p.x) > 9000.0:
			peds.append(q)
	var d := dir_at(t)
	var right := Vector2(-d.y, d.x)
	if not _limit_set:
		_limit_set = true
		limit = URBAN if not TrafficSigns.junctions_near(p, 150.0).is_empty() else RURAL
	var look := clampf(LOOK_MIN + v * 4.5, LOOK_MIN, 110.0)
	var obstacles: Array = []                                  # [gap m, speed of the obstacle m/s]
	var vdes := limit * (1.0 + speeding)

	# -- what's ahead on the road: re-read four times a second, carried forward as they drive ------
	_sense_t -= dt
	if _sense_t <= 0.0:
		_sense_t = 0.25
		Prof.begin("step.perceive")
		_perceive(p, look)
		Prof.end("step.perceive")
	var stop_ctl: Array = []                                   # [dist to line, sign]
	for c in _stop_abs:
		stop_ctl.append([float(c[0]) - t, c[1]])
	if t < _warn_until:
		vdes = minf(vdes, limit * 0.8)
	# the road's own bends, seen ahead: no faster than the corner allows (a_lat), braking in time
	var a_lat := (1.4 if professional else 2.0 + 1.6 * sensation)
	for c in _curves:
		var dd := float(c[0]) - t
		if dd > -3.0:
			vdes = minf(vdes, sqrt(a_lat / float(c[1]) + 2.0 * B_COMF * maxf(0.0, dd - 3.0)))
	vdes = minf(vdes, v_cap)

	Prof.begin("step.junctions")
	# -- stop and yield signs: stop at the bar, then wait for a clear junction (4511.43) ------------
	stop_ctl.sort_custom(func(x, y): return x[0] < y[0])
	if not stop_ctl.is_empty():
		var ctl: Array = stop_ctl[0]
		var gap: float = ctl[0]
		var s: Dictionary = ctl[1]
		var key := "stop:%d" % int(s.id)
		if not _cleared.has(key) and gap > -2.0:
			var j := pos_at(t + gap + 8.0)                         # the junction just past the line
			var busy := _anyone_near(j, 35.0, agents, peds)
			var conflict := _conflict(j, d, agents, 4.0)
			if str(s.t) == "yield":
				vdes = minf(vdes, maxf(4.0, sqrt(16.0 + 2.0 * B_COMF * maxf(0.0, gap))))
				if conflict:
					obstacles.append([gap + S0 - 0.3, 0.0, "stop"])
				elif gap < 1.0:
					_cleared[key] = true
			else:
				var full := professional or _decide(key, clampf(full_stop + (0.26 if busy else 0.0), 0.0, 1.0))
				if full or conflict:
					obstacles.append([gap + S0 - 0.3, 0.0, "stop2"])                # (the obstacle S0 past the line: they stop at it)
					if gap < 1.5 and v < 0.15:
						_stopped_s += dt
						if _stopped_s > 1.0 and not conflict and _my_turn(j, agents, clock_s):
							_cleared[key] = true
							_stopped_s = 0.0
				else:
					vdes = minf(vdes, sqrt(ROLL * ROLL + 2.0 * B_COMF * maxf(0.0, gap)))
					if gap < 0.8:
						_cleared[key] = true
						_violate("rolling_stop")

	# -- signals (4511.13) ----------------------------------------------------------------------------
	var g := _sig
	if not g.is_empty():
		var rel := _rel(p, g.p)
		var along := rel.dot(d)
		if along > 0.0:
			var gap := along - 10.0                                # the stop line, back from the junction centre
			var st := TrafficSigns.signal_state(g, d, clock_s)
			var key := "sig:%s:%d" % [str(g.p), int(clock_s / 26.0)]
			if st == "amber" and gap > v * v / (2.0 * 3.0):          # can stop: should
				if not _decide(key, 0.0 if professional else red_light):
					obstacles.append([gap + S0 - 0.3, 0.0, "amber"])
			elif st == "red" and gap > 0.0:
				if professional or not _decide(key + "r", red_light * 0.4) or gap > 25.0:
					obstacles.append([gap + S0 - 0.3, 0.0, "red"])
				elif gap < 2.0:
					_violate("red_light")

	# -- junctions without control: yield to the right (4511.41); left turns yield (4511.42) --------
	for jp in _juncs:
		var rel := _rel(p, jp)
		var along := rel.dot(d)
		if along < 3.0 or along > look or absf(rel.dot(right)) > 8.0:
			continue
		if not stop_ctl.is_empty() and absf(float(stop_ctl[0][0]) + 8.0 - along) < 10.0:
			continue                                               # a stop/yield sign governs this one
		var eta := along / maxf(v, 1.0)
		var turn := dir_at(t + along - 6.0).angle_to(dir_at(t + along + 6.0))
		for a in agents:
			if _me(a):
				continue
			var ra := _rel(a.p, jp)
			var ad: float = ra.length()
			if ad > 60.0 or (a.dir as Vector2).dot(ra) <= 0.0:
				continue                                           # not heading for this junction
			var their_eta := ad / maxf(float(a.v), 0.5)
			var from_right := _rel(jp, a.p).dot(right) > 3.0 and absf((a.dir as Vector2).dot(d)) < 0.6
			var oncoming := (a.dir as Vector2).dot(d) < -0.7
			if from_right and absf(their_eta - eta) < 3.0 and their_eta < 6.0:
				obstacles.append([along - 7.0, 0.0, "yield_right"])
			elif turn < -0.6 and oncoming and their_eta < 5.0:    # turning left across them
				obstacles.append([along - 4.0, 0.0, "yield_left"])
		break

	# -- rail crossings (4511.62) ---------------------------------------------------------------------
	var x := _xing
	if not x.is_empty():
		var along := _rel(p, x.p).dot(d)
		if along > 0.0:
			for a in agents:
				if str(a.kind) == "train" and NpcPlaces.dist(a.p, x.p) < 400.0:
					obstacles.append([along - 8.0, 0.0, "train"])
					break

	# -- people on or by the road ahead (4511.46) ----------------------------------------------------
	for q in peds:
		var rel := _rel(p, q.p)
		var along := rel.dot(d)
		var side := rel.dot(right) - lat
		if along < 0.0 or along > 18.0:
			continue
		if absf(side) < 1.6:
			obstacles.append([along - length * 0.5 - 1.5, 0.0, "ped"])    # in the path: everyone stops
		elif absf(side) < 4.5 and along < 14.0:
			if professional or _decide("ped:%s" % str(q.id), yield_peds):
				obstacles.append([along - length * 0.5 - 2.5, 0.0, "ped_yield"])
			elif along < 6.0 and absf(side) < 3.0:
				_note_once("ped:%s" % str(q.id), "failed_to_yield_pedestrian")

	Prof.end("step.junctions")
	Prof.begin("step.ahead")
	# -- the vehicle ahead, and passing it --------------------------------------------------------------
	var leader := {}
	var lgap := INF
	for a in near_all:
		if _me(a) or (_passing != "" and a.id == _pass_id):
			continue
		var rel := _rel(p, a.p)
		var along := rel.dot(d)
		var side := rel.dot(right) - lat
		if along <= 0.0 or along > 90.0 or absf(side) > 1.9:
			continue
		var gap := along - (length + float(a.len)) * 0.5
		# a standoff: two cars each with the other in its way (on top of each other, or nose to nose across a
		# junction), both stood still -- the one with the lower id goes, as drivers wave each other on. Without it a
		# rush hour's queues locked solid and grew to ~200 cars (Calder's Main St, 2026-10-06)
		if float(a.v) < 0.1 and not parked_kind(a) and str(id) < str(a.id) and (gap < 0.0 or (_still_s > STANDOFF_S and gap < 6.0)):
			continue
		var same := (a.dir as Vector2).dot(d) > 0.3
		if gap < lgap:
			lgap = gap
			leader = a
		obstacles.append([gap, float(a.v) if same else 0.0, "leader"])
	_overtaking(dt, leader, lgap, vdes, p, d, near_all)
	lat = move_toward(lat, _lat_target, 1.3 * dt)

	# -- the end of the trip: in to the kerb over the last stretch, and stopped at the end -----------------------
	if path_len < INF and stop_at_end:
		obstacles.append([path_len - t + S0 - 0.3, 0.0, "end"])
	Prof.end("step.ahead")
	Prof.begin("step.idm")
	last_obstacles = obstacles                                     # (for debugging a stuck driver)
	# -- IDM ------------------------------------------------------------------------------------------
	var amax := (1.0 if professional else 1.3 + 1.0 * sensation)
	var free := 1.0 - pow(v / maxf(vdes, 0.1), 4.0)
	var inter := 0.0
	var hard := false
	for o in obstacles:
		var gap := maxf(float(o[0]), 0.05)
		var vo: float = o[1]
		var s_star := S0 + v * headway + v * (v - vo) / (2.0 * sqrt(amax * B_COMF))
		inter = maxf(inter, pow(maxf(s_star, 0.0) / gap, 2.0))
		if gap < 0.4 and vo < 0.1:
			hard = true
	var near_gap := INF
	for o in obstacles:
		near_gap = minf(near_gap, float(o[0]))
	dbg = {"limit_kmh": roundi(limit * 3.6), "vdes": snappedf(vdes, 0.1), "v": snappedf(v, 0.1), "gap": snappedf(near_gap, 0.1),
		"stops": stop_ctl.size(), "passing": _passing}
	var acc := clampf(amax * (free - inter), -8.0, amax)
	_last_acc = acc
	_last_hard = hard
	v = maxf(0.0, v + acc * dt)
	if hard:
		v = minf(v, 0.3)
	t += v * dt
	if path_len < INF:
		t = minf(t, path_len)
	# speeding: 8 km/h (5 mph) or more over the limit for a few seconds counts, once per limit zone
	if not professional and v > limit + 8.0 / 3.6:
		_over_s += dt
		if _over_s > 3.0:
			_note_once("spd:%d:%d" % [int(limit * 3.6), int(t / 300.0)], "speeding")
	else:
		_over_s = 0.0
	_still_s = _still_s + dt if v < 0.1 else 0.0
	Prof.end("step.idm")


func bend_speed(from_t: float, ahead: float, a_lat := 3.0, b := 5.0) -> float:
	## The fastest it can be going now and still take every bend in the next `ahead` m of its route (lateral a_lat,
	## braking at b): a car on its wheels checks this itself (NpcCarBody), so a timetable that handed it over at speed
	## just before a corner can't send it through the corner.
	var vmin := INF
	var dd := 0.0
	var top := path_len - from_t if path_len < INF else INF
	while dd <= minf(ahead, top):
		var kap := absf(dir_at(from_t + dd - 2.0).angle_to(dir_at(from_t + dd + 2.0))) / 4.0
		if kap > 0.004:
			vmin = minf(vmin, sqrt(a_lat / kap + 2.0 * b * maxf(0.0, dd - 1.0)))
		dd += 2.0
	return vmin


func pull_over(on: bool) -> void:
	## Stopping on a round (a delivery, the mail): over to the kerb, out of the lane.
	if _passing == "":
		_lat_target = 2.4 if on else 0.0


func _perceive(p: Vector2, look: float) -> void:
	## Read the road ahead: signs facing this driver (and passing them: speed limits, town limits,
	## warnings), the stop/yield lines, the bends, the signal, the junctions and crossings.
	var seen := {}
	var stop_ctl: Array = []
	var k := -1
	while k * 8.0 <= look:
		var sd := t + k * 8.0
		if path_len < INF and (sd < 0.0 or sd > path_len):
			k += 1
			continue
		var sp := pos_at(sd)
		var sdir := dir_at(sd)
		var sright := Vector2(-sdir.y, sdir.x)
		for s in TrafficSigns.signs_near(sp, 9.0):
			if seen.has(s.id):
				continue
			var rel := _rel(sp, s.p)
			var along := sd - t + rel.dot(sdir)
			var side := rel.dot(sright)
			var facing := (s.face as Vector2).dot(sdir)
			seen[s.id] = true
			if facing < -0.6 and side > -1.0:
				_on_sign(s, along, stop_ctl)
				_check_sign(s, side)
			elif facing > 0.6 and side < 1.0 and str(s.t) == "town" and along <= 0.0 and not _passed.has(s.id):
				_passed[s.id] = true                               # the back of a town sign: leaving town
				limit = RURAL
		k += 1
	_stop_abs.clear()
	for c in stop_ctl:
		_stop_abs.append([t + float(c[0]), c[1]])
	# (every 3 m over a 4 m window from just ahead: driven on its wheels, a car has to be slow enough at a town corner's
	# 5-7 m arc -- sampled every 6 m from 5 m on, the corner just ahead was missed and the car ran wide)
	_curves.clear()
	var dd := 1.0
	while dd < minf(look, 80.0):
		var h0 := dir_at(t + dd - 2.0)
		var h1 := dir_at(t + dd + 2.0)
		var kap := absf(h0.angle_to(h1)) / 4.0
		if kap > 0.004:
			_curves.append([t + dd, kap])
		dd += 3.0
	_sig = TrafficSigns.signal_near(pos_at(t + minf(look, 40.0)), 30.0)
	_juncs = TrafficSigns.junctions_near(pos_at(t + minf(look, 45.0) * 0.5), minf(look, 45.0) * 0.5 + 8.0)
	_xing = TrafficSigns.crossing_near(pos_at(t + minf(look, 40.0)), 30.0)


func _check_sign(s: Dictionary, side: float) -> void:
	## Anything wrong with a sign this driver faces, reported once (TrafficReports): a stop or yield with no junction
	## to stop for, a sign standing in the lane being driven.
	if _reported.has(s.id):
		return
	_reported[s.id] = true
	var ty := str(s.t)
	if (ty == "stop" or ty == "yield") and TrafficSigns.junctions_near(s.p, 30.0).is_empty():
		TrafficReports.file("sign_no_junction", s.p, "a %s sign facing traffic, no junction within 30 m" % ty, str(id))
	if absf(side - lat) < 1.3:
		TrafficReports.file("sign_in_lane", s.p, "a %s sign standing in the driving lane (%.1f m off the lane's line)" % [ty, side - lat], str(id))


var _reported := {}


func _on_sign(s: Dictionary, along: float, stop_ctl: Array) -> void:
	var ty := str(s.t)
	if along <= 0.5 and not _passed.has(s.id):
		_passed[s.id] = true
		if ty.begins_with("speed_"):
			limit = float(ty.substr(6)) / 3.6
		elif ty == "town":
			limit = URBAN
		elif ty in ["stop_ahead", "curve_l", "curve_r", "junction", "rr_ahead"]:
			_warn_until = t + 120.0
	if (ty == "stop" or ty == "yield") and along > -3.0:
		# the line: a stop bar across this lane near the sign, else the sign itself
		var line := along
		var sp: Vector2 = s.p
		for b in TrafficSigns.bars_near(sp, 14.0):
			var rel := _rel(pos_at(t), b.c)
			var a2 := rel.dot(dir_at(t))
			var side := rel.dot(Vector2(-dir_at(t).y, dir_at(t).x)) - lat
			if absf(side) < 3.5 and a2 > -2.0 and absf((b.across as Vector2).dot(dir_at(t))) < 0.5:
				line = a2 - length * 0.5
				break
		stop_ctl.append([line if line != along else along - length * 0.5, s])


func _anyone_near(j: Vector2, r: float, agents: Array, peds: Array) -> bool:
	for a in agents:
		if not _me(a) and NpcPlaces.dist(a.p, j) < r:
			return true
	for q in peds:
		if NpcPlaces.dist(q.p, j) < 15.0:
			return true
	return false


func _conflict(j: Vector2, d: Vector2, agents: Array, eta_s: float) -> bool:
	## Anyone in the junction, or coming at it on another road so close as to be an immediate hazard.
	for a in agents:
		if _me(a):
			continue
		var ra := _rel(a.p, j)
		var dist: float = ra.length()
		if dist < 9.0 and float(a.v) > 0.3:
			return true
		if (a.dir as Vector2).dot(d) > 0.8:
			continue                                               # behind or ahead of us on our own road
		if (a.dir as Vector2).dot(ra) > 0.0 and dist / maxf(float(a.v), 0.5) < eta_s and dist < 45.0:
			return true
	return false


static var _arrivals := {}           # junction -> {driver id: arrival clock}

func _my_turn(j: Vector2, agents: Array, clock_s: float) -> bool:
	## All-way stops: whoever stopped first goes first.
	var key := "%d,%d" % [int(j.x), int(j.y)]
	if not _arrivals.has(key):
		_arrivals[key] = {}
	var arr: Dictionary = _arrivals[key]
	if not arr.has(id):
		arr[id] = clock_s
	for other in arr.keys():
		if clock_s - float(arr[other]) > 20.0:
			arr.erase(other)
	var mine: float = arr.get(id, clock_s)
	for other in arr:
		if other != id and float(arr[other]) < mine - 0.2:
			return false
	arr.erase(id)
	return true


func _overtaking(dt: float, leader: Dictionary, lgap: float, vdes: float, p: Vector2, d: Vector2, agents: Array) -> void:
	if _passing != "":
		var done := true
		for a in agents:
			if a.id == _pass_id:
				done = _rel(p, a.p).dot(d) < -(length + float(a.len)) * 0.5 - 4.0
		if done:
			_passing = ""
			_pass_id = null
			_lat_target = 0.0
		return
	if leader.is_empty() or lgap > 18.0 or professional:
		_held = 0.0
		return
	_held += dt
	var lv := float(leader.v)
	var lid := str(leader.id)
	# passing on the right: a stopped vehicle (4511.28: only round a left-turner, on pavement wide
	# enough for two lines, never off the roadway -- our streets have one lane each way)
	if lv < 0.5 and not parked_kind(leader) and _held > 3.0 and _decide("pr:" + lid, pass_right):
		_passing = "right"
		_pass_id = leader.id
		_lat_target = 2.6
		_violate("passed_on_right")
		return
	# overtaking on the left: a slow vehicle, or one parked out in the lane (4511.29-.31), nothing coming, no junction near
	var parked := str(leader.get("kind", "")) == "parked"
	if (parked or lv > 0.5 and lv < 0.6 * vdes) and _held > (2.0 if parked else 4.0):
		for a in agents:
			var rel := _rel(p, a.p)
			if not parked_kind(a) and (a.dir as Vector2).dot(d) < -0.5 and rel.dot(d) > 0.0 and rel.dot(d) < 220.0:
				return                                             # oncoming: not now
		if not TrafficSigns.junctions_near(pos_at(t + 30.0), 30.0).is_empty():
			return
		var line := TrafficSigns.centre_line(p)
		var slow_exception := lv < 0.5 * limit or parked          # 4511.31(B); an obstruction (4511.31(A)(3))
		if line == "solid" and not slow_exception:
			if not _decide("xs:" + lid, cross_solid):
				return
			_violate("crossed_double_yellow")
		_passing = "left"
		_pass_id = leader.id
		_lat_target = -3.5


var _noted := {}
var _over_s := 0.0


static func parked_kind(a: Dictionary) -> bool:
	return str(a.get("kind", "")) == "parked"


func _me(a: Dictionary) -> bool:
	## This driver's own vehicle (a tram's bodies are "<its id>#<n>").
	return a.id == id or str(a.id).begins_with(str(id) + "#")

func _note_once(key: String, kind: String) -> void:
	if not _noted.has(key):
		_noted[key] = true
		_violate(kind)
