extends Node
class_name RoadSurvey

## The road survey (the user, 2026-10-09): "send npcs in cars to drive all of the major roads and bridges at once. Have
## them report any misalignments and anomalies. Have one NPC drive each major road and all bridges in one direction
## while another NPC drives the other way. Have one NPC every six kilometers on the major roads, and one npc in each
## direction start .5km from the start of each bridge ... write an evaluation algorithm for the NPCs to run when they
## encounter an anomaly, so that you are not wasting tokens figuring out problems that can be automated."
##
## Every other road user is stood down (the traffic, the people, the trams, the parked fleet). Surveyors are laid out:
##   the major roads (hwy, county, main), each chained end to end by its name: one every SPACING m, each way, each
##     driving its SPACING m stretch -- so every metre of every major road is driven both ways at once;
##   every bridge, great (GreatBridges) and small (the crossings): one each way, from BRIDGE_LEAD m before its deck to
##     BRIDGE_LEAD m past it;
##   with --survey-all, every other road as well (one each way per road chain).
## They drive their lane (the right-hand one, as traffic does) a STEP at a time, all of them, round-robin within a frame
## budget, measuring the surface they're on -- the ground the road is drawn on (MapTerrain.elevation), a great bridge's
## deck (GreatBridges.deck_h), a crossing's deck -- with the game's own data, so far from the player as near.
##
## What a surveyor checks at each metre (the anomaly kinds):
##   step            a rise or drop of more than STEP_MAX within a metre (a kerb under a wheel)
##   grade           steeper than the class allows over 8 m (ROAD_GRADE); past GRADE_BLOCK no passenger car climbs it
##   crest           a crest a long car (WHEELBASE) grounds on: the road between its axles stands CLEARANCE above them
##   sag             a dip its bumpers scrape: the road under the car's middle SCRAPE below its axles
##   camber          the lane tilted across by more than CROSS_MAX
##   bend            a bend tighter than a car's turning circle (TURN_R) away from a junction
##   narrow          a road too narrow for a car (once per road)
##   flooded         the lane under water
##   obstructed      a building standing on the lane
##   sign_in_road    a sign inside the carriageway
##   sign_hidden     a sign standing right behind another, facing the same way
##   sign_no_junction a stop or yield sign with no junction within 30 m
##   bridge_offset   a road meeting a bridge's deck off its line by more than BRIDGE_OFF
##   dangling_end    a road ending close to another road without joining it
## and on finding one it runs the evaluation (_evaluate): what's round it -- a bridge's end, a levelled pad, a junction,
## the natural slope, water -- decides the cause, the fix and the severity, recorded with the anomaly. Results go to
## user://road_survey.json (the TrafficReports format and more: cause, fix, severity, value); tools/road_survey.py
## summarises them. Start: `godot4 --path . -- --roadsurvey [--survey-all] [--quit-after-survey]`, or add a RoadSurvey
## from DevBridge.

const PATH := "user://road_survey.json"
const MAJOR := ["hwy", "county", "main"]
const DRIVEN := ["hwy", "county", "main", "street", "gravel", "alley"]
const SPACING := 6000.0
const BRIDGE_LEAD := 500.0
const STEP := 1.0
const LANE := 1.8
const BUDGET_USEC := 45000          # (a survey run is nobody's game: most of each frame is the surveyors')
const STEP_MAX := 0.12
const ROAD_GRADE := {"hwy": 0.05, "county": 0.07, "main": 0.07, "street": 0.08, "gravel": 0.10, "alley": 0.08}
const GRADE_BLOCK := 0.20
const WHEELBASE := 3.6              # m: a long passenger car (a limousine, a hearse)
const CLEARANCE := 0.13             # m under its middle
const SCRAPE := 0.22
const CROSS_MAX := 0.08
const TURN_R := 6.0
const BRIDGE_OFF := 0.6

var survey_all := false
var surveyors: Array = []           # {id, kind, line (PackedVector2Array), cum, u, end, cls, name, road, hist, ...}
var anomalies := {}
var _chains: Array = []             # [{cls, name, roads: [ri], pts (PackedVector2Array), w, hw}]
var _road_chain := {}               # road index -> [chain, its start along the chain]
var _sites := {}                    # 40 m cell -> placements (for buildings on the lane)
var _signs_seen := {}
var _i := 0
var _done := 0
var _t0 := 0
var _samples := 0
var _visual: Array = []             # [RemakeModularCar, surveyor] near the player
var finished := false


func _ready() -> void:
	name = "RoadSurvey"
	_t0 = Time.get_ticks_msec()
	survey_all = survey_all or OS.get_cmdline_user_args().has("--survey-all")
	_stand_down()
	MapTerrain.elevation(0.0, 0.0)
	TrafficSigns.load_all()
	_build_chains()
	_lay_out()
	print("RoadSurvey: %d surveyors on %d road chains (%s)" % [surveyors.size(), _chains.size(), "every road" if survey_all else "major roads and bridges"])


# ------------------------------------------------------------------ setting up
func _stand_down() -> void:
	## Every other road user off: the traffic, the people, the trams, the parked fleet (they cost the survey's time).
	var sc := get_tree().current_scene
	var tr := sc.find_child("NpcTraffic", true, false)
	if tr:
		tr.set_process(false)
		for id in tr.live.keys():
			(tr.live[id].node as Node).queue_free()
		tr.live.clear()
	for key in ["npcs", "transit"]:
		var n = sc.get(key)
		if n is Node:
			(n as Node).process_mode = Node.PROCESS_MODE_DISABLED
			if n is Node3D:
				(n as Node3D).visible = false
	for vs in sc.find_children("*", "VehicleStreamer", true, false):
		(vs as Node).process_mode = Node.PROCESS_MODE_DISABLED
		(vs as Node3D).visible = false


func _build_chains() -> void:
	## Each road's pieces end to end, by name and class: a surveyor follows its road through the joins.
	var roads: Array = MapTerrain._d.roads
	var ends := {}                    # cell -> [[ri, at_start]]
	for ri in roads.size():
		var rd: Dictionary = roads[ri]
		if not DRIVEN.has(str(rd.cls)):
			continue
		var pts: PackedVector2Array = rd.pts
		for e in [[0, true], [pts.size() - 1, false]]:
			var p: Vector2 = pts[e[0]]
			var key := Vector2i(floori(fposmod(p.x, StationGeo.CIRC) / 4.0), floori(p.y / 4.0))
			if not ends.has(key):
				ends[key] = []
			(ends[key] as Array).append([ri, e[1]])
	var used := {}
	for ri in roads.size():
		var rd: Dictionary = roads[ri]
		if used.has(ri) or not DRIVEN.has(str(rd.cls)):
			continue
		var seq: Array = [[ri, true]]           # [road, forwards]
		used[ri] = true
		# grow both ways through the ends that meet one of the same name and class
		for dir in [1, -1]:
			while true:
				var last: Array = seq[seq.size() - 1] if dir == 1 else seq[0]
				var lr: Dictionary = roads[last[0]]
				var lp: PackedVector2Array = lr.pts
				var tip: Vector2 = (lp[lp.size() - 1] if last[1] else lp[0]) if dir == 1 else (lp[0] if last[1] else lp[lp.size() - 1])
				var nxt := []
				var c := Vector2i(floori(fposmod(tip.x, StationGeo.CIRC) / 4.0), floori(tip.y / 4.0))
				for di in [-1, 0, 1]:
					for dj in [-1, 0, 1]:
						for e in ends.get(Vector2i(c.x + di, c.y + dj), []):
							var rj: int = e[0]
							if used.has(rj) or str(roads[rj].cls) != str(rd.cls) or str(roads[rj].get("name", "")) != str(rd.get("name", "")):
								continue
							var rjp: PackedVector2Array = roads[rj].pts
							var q: Vector2 = rjp[0] if e[1] else rjp[rjp.size() - 1]
							if Vector2(StationGeo.wrap_ds(q.x - tip.x), q.y - tip.y).length() < 2.0:
								nxt = [rj, e[1] if dir == 1 else not e[1]]
				if nxt.is_empty() or str(rd.get("name", "")) == "":
					break
				used[nxt[0]] = true
				if dir == 1:
					seq.append(nxt)
				else:
					seq.push_front(nxt)
		var pts := PackedVector2Array()
		var at := []
		var unw := Vector2.INF
		for e in seq:
			var rp: PackedVector2Array = roads[e[0]].pts
			var idx := range(rp.size()) if e[1] else range(rp.size() - 1, -1, -1)
			at.append([e[0], pts.size()])
			for k in idx:
				var q: Vector2 = rp[k]
				q = q if unw == Vector2.INF else Vector2(unw.x + StationGeo.wrap_ds(q.x - unw.x), q.y)
				if unw == Vector2.INF or q.distance_to(unw) > 0.05:
					pts.append(q)
					unw = q
		var ch := {"idx": _chains.size(), "cls": str(rd.cls), "name": str(rd.get("name", "")), "roads": seq, "at": at, "pts": pts}
		for e in seq:
			_road_chain[e[0]] = ch
		_chains.append(ch)


func _lane(pts: PackedVector2Array, ch: Dictionary) -> PackedVector2Array:
	## The right-hand lane's line along pts (each piece's own width: on a one-lane road, its middle).
	var out := PackedVector2Array()
	var roads: Array = MapTerrain._d.roads
	var rd: Dictionary = roads[ch.roads[0][0]]
	var off := lane_off(rd)
	for k in pts.size():
		var a := pts[maxi(k - 1, 0)]
		var b := pts[mini(k + 1, pts.size() - 1)]
		var d := (b - a).normalized()
		out.append(pts[k] + Vector2(-d.y, d.x) * off)
	return out


static func lane_off(rd: Dictionary) -> float:
	return minf(LANE, maxf(0.0, float(rd.get("hr", float(rd.w) * 0.5)) - 1.05))


static func _cum(pts: PackedVector2Array) -> PackedFloat64Array:
	var c := PackedFloat64Array()
	c.resize(pts.size())
	var acc := 0.0
	for k in pts.size():
		if k > 0:
			acc += pts[k].distance_to(pts[k - 1])
		c[k] = acc
	return c


func _lay_out() -> void:
	for ch in _chains:
		if not survey_all and not MAJOR.has(ch.cls):
			continue
		var L: float = _cum(ch.pts)[ch.pts.size() - 1]
		var n := maxi(1, ceili(L / SPACING)) if MAJOR.has(ch.cls) else 1
		for dirn in ["fwd", "back"]:
			var pts: PackedVector2Array = ch.pts if dirn == "fwd" else _reversed(ch.pts)
			var line := _lane(pts, ch)
			for k in n:
				var u0 := k * SPACING if MAJOR.has(ch.cls) else 0.0
				_add("road", "%s %s #%d %s" % [ch.cls, ch.name if ch.name != "" else "(unnamed)", k + 1, dirn], line, u0, minf(u0 + SPACING, L) if MAJOR.has(ch.cls) else L, ch)
	# the bridges: great, then the crossings
	for sp in GreatBridges.decks:
		var line0: PackedVector2Array = sp.line
		_bridge_surveyors(str(sp.get("name", sp.id)), line0[0], line0[line0.size() - 1])
	for bd in MapTerrain._bridges:
		if float(bd[9]) <= 0.0:
			continue
		# the crossing's frame in (s, x): lx = rel . (sin, cos), lz = rel . (-cos, sin) (MapTerrain.on_small_bridge); its
		# deck's middle at the footprint's middle, its road along local z
		var xh := Vector2(float(bd[3]), float(bd[2]))
		var along := Vector2(-float(bd[2]), float(bd[3]))
		var c := Vector2(float(bd[0]), float(bd[1])) + xh * (float(bd[4]) + float(bd[6])) * 0.5 + along * (float(bd[5]) + float(bd[7])) * 0.5
		var half := float(bd[9]) * 0.5
		_bridge_surveyors("crossing at %.0f, %.0f" % [c.x, c.y], c - along * half, c + along * half)


func _bridge_surveyors(label: String, a: Vector2, b: Vector2) -> void:
	## One each way along the road that carries the bridge, from BRIDGE_LEAD m before its end to BRIDGE_LEAD past.
	var mid := Vector2(a.x + StationGeo.wrap_ds(b.x - a.x) * 0.5, (a.y + b.y) * 0.5)
	var at := NpcPlaces._attach_on(Vector2(fposmod(mid.x, StationGeo.CIRC), mid.y), DRIVEN)
	if at.is_empty():
		return
	var ri := int(NpcPlaces._edge(int(at[0]))[2])
	var ch: Dictionary = _road_chain.get(ri, {})
	if ch.is_empty():
		return
	var pts: PackedVector2Array = ch.pts
	var cum := _cum(pts)
	var um := _project(pts, cum, mid)
	var half := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y).length() * 0.5
	var L := cum[cum.size() - 1]
	var u0 := maxf(0.0, um - half - BRIDGE_LEAD)
	var u1 := minf(L, um + half + BRIDGE_LEAD)
	_add("bridge", "%s fwd" % label, _lane(pts, ch), u0, u1, ch, {"bridge": label, "a": a, "b": b})
	var rp := _reversed(pts)
	_add("bridge", "%s back" % label, _lane(rp, ch), L - u1, L - u0, ch, {"bridge": label, "a": a, "b": b})


func _add(kind: String, id: String, line: PackedVector2Array, u0: float, u1: float, ch: Dictionary, extra := {}) -> void:
	var s := {"id": id, "kind": kind, "line": line, "cum": _cum(line), "u": u0, "end": u1, "cls": ch.cls, "name": ch.name,
		"chain": ch, "hist": [], "prev_dir": Vector2.ZERO, "start": u0, "lane": lane_off(MapTerrain._d.roads[ch.roads[0][0]])}
	s.merge(extra)
	surveyors.append(s)


static func _reversed(p: PackedVector2Array) -> PackedVector2Array:
	var r := PackedVector2Array()
	for k in range(p.size() - 1, -1, -1):
		r.append(p[k])
	return r


static func _project(pts: PackedVector2Array, cum: PackedFloat64Array, q: Vector2) -> float:
	var best := INF
	var bu := 0.0
	for k in pts.size() - 1:
		var a := pts[k]
		var d := pts[k + 1] - a
		var rel := Vector2(StationGeo.wrap_ds(q.x - a.x), q.y - a.y)
		var t := clampf(rel.dot(d) / maxf(d.length_squared(), 1e-9), 0.0, 1.0)
		var dd := (rel - d * t).length()
		if dd < best:
			best = dd
			bu = cum[k] + t * d.length()
	return bu


static func _at(line: PackedVector2Array, cum: PackedFloat64Array, u: float) -> Array:
	## [(s, x) wrapped, unit direction] at u along line
	var i := clampi(cum.bsearch(u) - 1, 0, line.size() - 2)
	var seg := cum[i + 1] - cum[i]
	var f := clampf((u - cum[i]) / maxf(seg, 1e-6), 0.0, 1.0)
	var p := line[i].lerp(line[i + 1], f)
	return [Vector2(fposmod(p.x, StationGeo.CIRC), p.y), (line[i + 1] - line[i]).normalized()]


# ------------------------------------------------------------------ driving
func _process(_delta: float) -> void:
	if finished:
		return
	var t0 := Time.get_ticks_usec()
	var live := 0
	while Time.get_ticks_usec() - t0 < BUDGET_USEC:
		var any := false
		for k in surveyors.size():
			_i = (_i + 1) % surveyors.size()
			var sv: Dictionary = surveyors[_i]
			if float(sv.u) > float(sv.end):
				continue
			any = true
			_drive(sv)
			if float(sv.u) > float(sv.end):
				_arrive(sv)
				_done += 1
			if Time.get_ticks_usec() - t0 >= BUDGET_USEC:
				break
		if not any:
			_finish()
			return
	live = surveyors.size() - _done
	_show_near()
	if Engine.get_process_frames() % 300 == 0:
		print("RoadSurvey: %d of %d surveyors still driving, %d m surveyed, %d anomalies" % [live, surveyors.size(), _samples, anomalies.size()])


func _drive(sv: Dictionary) -> void:
	var u: float = sv.u
	var r := _at(sv.line, sv.cum, u)
	var p: Vector2 = r[0]
	var d: Vector2 = r[1]
	var hist: Array = sv.hist
	var surf := _surface(p, hist.back() if not hist.is_empty() else [], d)
	var h: float = surf[0]
	hist.append([u, p, h, d, surf[1]])
	if hist.size() > 10:
		hist.pop_front()
	_samples += 1
	if u == float(sv.start) and float(sv.start) < 0.5:
		_check_end(sv, p, d, true)
	_check(sv, hist, p, d, h, surf[1])
	sv.u = u + STEP


func _arrive(sv: Dictionary) -> void:
	var r := _at(sv.line, sv.cum, float(sv.end))
	var cum: PackedFloat64Array = sv.cum
	if float(sv.end) >= cum[cum.size() - 1] - 0.5:
		_check_end(sv, r[0], r[1], false)


func _surface(p: Vector2, prev: Array = [], d := Vector2.ZERO) -> Array:
	## [the height of what's driven on at p, "ground" | "deck" | "crossing"]. A deck across the road's way (not along it),
	## far above or below the last sample where the ground stays level with it, is one the road passes under, not one it
	## climbs onto (rounds 1-2: the streets under the Miami Gateway Bridge's approach "falling" 14 m off it). (By the
	## heights alone, round 3 had College Rd's own lane, a moment off its approach, "under" the bridge all the way over.)
	var g := MapTerrain.elevation(p.x, p.y)
	var gd := GreatBridges.deck_h(p.x, p.y)
	var on := "deck"
	if gd == -INF:
		gd = _crossing_deck(p)
		on = "crossing"
		if is_nan(gd):
			return [g, "ground"]
	if not prev.is_empty() and d != Vector2.ZERO and absf(gd - float(prev[2])) > 2.0 and absf(g - float(prev[2])) < 2.0:
		var along := _deck_dir(p)
		if along != Vector2.ZERO and absf(along.dot(d)) < 0.7:
			return [g, "ground"]
	return [gd, on]


static func _deck_dir(p: Vector2) -> Vector2:
	## The way the deck at p runs (unit), or ZERO
	for sp in GreatBridges.decks:
		var line: PackedVector2Array = sp.line
		var hw: float = float(sp.hw) + 0.3
		for k in line.size() - 1:
			var a := line[k]
			var dd := Vector2(StationGeo.wrap_ds(line[k + 1].x - a.x), line[k + 1].y - a.y)
			var L2 := dd.length_squared()
			if L2 < 1e-9:
				continue
			var v := Vector2(StationGeo.wrap_ds(p.x - a.x), p.y - a.y)
			var t := v.dot(dd) / L2
			if t >= 0.0 and t <= 1.0 and (v - dd * t).length() <= hw:
				return dd.normalized()
	var s := fposmod(p.x, StationGeo.CIRC)
	for it in MapTerrain._items(Vector2i(floori(s / MapTerrain.CELL), floori(p.y / MapTerrain.CELL))):
		if it[0] != "bridge":
			continue
		var bd: Array = MapTerrain._bridges[it[1]]
		if float(bd[9]) > 0.0:
			return Vector2(-float(bd[2]), float(bd[3]))          # (lz's way: the crossing's length)
	return Vector2.ZERO


static func _crossing_deck(p: Vector2) -> float:
	var s := fposmod(p.x, StationGeo.CIRC)
	for it in MapTerrain._items(Vector2i(floori(s / MapTerrain.CELL), floori(p.y / MapTerrain.CELL))):
		if it[0] != "bridge":
			continue
		var bd: Array = MapTerrain._bridges[it[1]]
		if float(bd[9]) <= 0.0:
			continue
		var ds := StationGeo.wrap_ds(s - float(bd[0]))
		var dx: float = p.y - float(bd[1])
		var lx: float = dx * float(bd[2]) + ds * float(bd[3])
		var lz: float = dx * float(bd[3]) - ds * float(bd[2])
		if absf(lz - (float(bd[5]) + float(bd[7])) * 0.5) <= float(bd[9]) * 0.5 and absf(lx - (float(bd[4]) + float(bd[6])) * 0.5) <= float(bd[10]) * 0.5:
			return float(bd[8])
	return NAN


# ------------------------------------------------------------------ the checks
func _check(sv: Dictionary, hist: Array, p: Vector2, d: Vector2, h: float, on: String) -> void:
	var n := hist.size()
	var cls: String = sv.cls
	if n >= 2:
		var hp: float = hist[n - 2][2]
		if absf(h - hp) > STEP_MAX:
			_found(sv, "step", p, absf(h - hp), "a %.2f m %s within a metre (%s to %s)" % [absf(h - hp), "rise" if h > hp else "drop", hist[n - 2][4], on])
		# a bridge's deck met off its line
		if on != hist[n - 2][4] and (on == "deck" or on == "crossing" or hist[n - 2][4] != "ground"):
			_check_bridge_line(sv, p, d)
	if n >= 9:
		var h8: float = hist[n - 9][2]
		var g := absf(h - h8) / 8.0
		var lim: float = ROAD_GRADE.get(cls, 0.08)
		if g > GRADE_BLOCK:
			_found(sv, "grade", p, g, "%.0f %% over 8 m: no passenger car climbs that (limit %.0f %%)" % [g * 100.0, GRADE_BLOCK * 100.0], "blocker")
		elif g > lim * 1.6:
			_found(sv, "grade", p, g, "%.0f %% over 8 m (a %s's standard is %.0f %%)" % [g * 100.0, cls, lim * 100.0], "minor")
	if n >= 5:
		# a car WHEELBASE long, its axles at u and u - 3.6, its middle at u - 1.8 (samples 1 m apart: 4 back ~ 3.6)
		var hb: float = hist[n - 5][2]
		var hm: float = hist[n - 3][2]
		var bulge := hm - (h + hb) * 0.5
		if bulge > CLEARANCE:
			_found(sv, "crest", p, bulge, "a crest %.2f m above a long car's axles (it grounds at %.2f)" % [bulge, CLEARANCE], "blocker" if bulge > 0.25 else "major")
		elif -bulge > SCRAPE:
			_found(sv, "sag", p, -bulge, "a dip %.2f m under a long car's middle (bumpers scrape past %.2f)" % [-bulge, SCRAPE])
		# the bend, over the last 4 m
		var d4: Vector2 = hist[n - 5][3]
		var kap := absf(d4.angle_to(d)) / 4.0
		if kap > 1.0 / TURN_R and TrafficSigns.junctions_near(p, 20.0).is_empty():
			_found(sv, "bend", p, 1.0 / kap, "a %.1f m radius bend: tighter than a car turns (%.0f m)" % [1.0 / kap, TURN_R])
	if on == "ground" and _samples % 4 == 0:              # (the tilt across, the water, a building: every 4 m)
		var right := Vector2(-d.y, d.x)
		var hl := MapTerrain.elevation(p.x - right.x, p.y - right.y)
		var hr := MapTerrain.elevation(p.x + right.x, p.y + right.y)
		var cross := absf(hl - hr) / 2.0
		if cross > CROSS_MAX:
			_found(sv, "camber", p, cross, "the lane tilted %.0f %% across" % (cross * 100.0))
		var wa := MapTerrain.water_at(p.x, p.y)
		if wa.x > h + 0.05:
			_found(sv, "flooded", p, wa.x - h, "the lane %.2f m under water" % (wa.x - h), "blocker")
		var b := _building_on(p)
		if b != "":
			_found(sv, "obstructed", p, 0.0, "building %s stands on the lane" % b, "blocker")
	if int(_samples) % 3 == 0:
		_check_signs(sv, p, d)


func _check_signs(sv: Dictionary, p: Vector2, d: Vector2) -> void:
	var ch: Dictionary = sv.chain
	for sg in TrafficSigns.signs_near(p, 8.0):
		if _signs_seen.has(sg.id):
			continue
		_signs_seen[sg.id] = true
		var sp: Vector2 = sg.p
		var ty := str(sg.t)
		# inside a carriageway: of any road round it, by that road's own width
		var a := NpcPlaces._attach_on(sp, DRIVEN)
		if not a.is_empty():
			var e: Array = NpcPlaces._edge(int(a[0]))
			var rd := NpcPlaces._road(int(e[2]))
			var c := NpcPlaces._at(int(e[2]), float(a[1]))
			var c2 := NpcPlaces._at(int(e[2]), float(a[1]) + 0.05)
			var t := Vector2(StationGeo.wrap_ds(c2.x - c.x), c2.y - c.y).normalized()
			var rel := Vector2(StationGeo.wrap_ds(sp.x - c.x), sp.y - c.y)
			var lat := rel.dot(Vector2(-t.y, t.x))
			var half := float(rd.get("hr" if lat > 0.0 else "hl", float(rd.w) * 0.5))
			var dist := rel.length()                       # (not just across: a sign past a road's end isn't in it)
			if dist < half - 0.1:
				_found(sv, "sign_in_road", sp, half - dist, "a %s sign %.1f m inside %s's kerb" % [ty, half - dist, str(rd.get("name", "the road"))], "major", str(sg.id))
		# right behind another, facing the same way (the nearer one hides it from the traffic it faces)
		for o in TrafficSigns.signs_near(sp, 1.2):
			if o.id == sg.id:
				continue
			var face: Vector2 = sg.face
			if face.dot(o.face) > 0.7:
				var rel := Vector2(StationGeo.wrap_ds(sp.x - (o.p as Vector2).x), sp.y - (o.p as Vector2).y)
				if rel.dot(face) < -0.05 and absf(rel.dot(Vector2(-face.y, face.x))) < 0.8:
					_found(sv, "sign_hidden", sp, rel.length(), "a %s sign %.1f m behind a %s sign, facing the same way" % [ty, rel.length(), str(o.t)], "major", str(sg.id))
					break
		if (ty == "stop" or ty == "yield") and TrafficSigns.junctions_near(sp, 30.0).is_empty():
			_found(sv, "sign_no_junction", sp, 0.0, "a %s sign with no junction within 30 m" % ty, "minor", str(sg.id))


func _check_bridge_line(sv: Dictionary, p: Vector2, d: Vector2) -> void:
	## Onto (or off) a deck: is the lane where the deck's lane is? Measured against the deck under (or just behind) the car
	## -- a great bridge's line, or a small crossing's axis -- not the bridge the surveyor was sent to (which had a
	## bridge's surveyor measure every other crossing it met against its own: rounds 1-2's 9-180 m "offsets").
	var off := INF
	for sp in GreatBridges.decks:
		var o := GreatBridges.off_line(sp, p.x, p.y)
		if o < float(sp.hw) + 3.0:
			off = minf(off, o)
	var s := fposmod(p.x, StationGeo.CIRC)
	for it in MapTerrain._items(Vector2i(floori(s / MapTerrain.CELL), floori(p.y / MapTerrain.CELL))):
		if it[0] != "bridge":
			continue
		var bd: Array = MapTerrain._bridges[it[1]]
		if float(bd[9]) <= 0.0:
			continue
		var ds := StationGeo.wrap_ds(s - float(bd[0]))
		var dx: float = p.y - float(bd[1])
		var lx: float = dx * float(bd[2]) + ds * float(bd[3])
		var lz: float = dx * float(bd[3]) - ds * float(bd[2])
		if absf(lz - (float(bd[5]) + float(bd[7])) * 0.5) <= float(bd[9]) * 0.5 + 2.0 and absf(lx - (float(bd[4]) + float(bd[6])) * 0.5) <= float(bd[10]) * 0.5 + 3.0:
			off = minf(off, absf(lx - (float(bd[4]) + float(bd[6])) * 0.5))
	if off == INF:
		return
	var lane: float = sv.lane
	if absf(off - lane) > BRIDGE_OFF:
		_found(sv, "bridge_offset", p, absf(off - lane), "the lane meets a deck %.1f m off the deck's lane" % (off - lane), "major")


func _check_end(sv: Dictionary, p: Vector2, d: Vector2, at_start: bool) -> void:
	## A road that stops close to another without joining it.
	if sv.kind != "road":
		return
	var line: PackedVector2Array = sv.line
	var tip: Vector2 = line[0] if at_start else line[line.size() - 1]
	tip = Vector2(fposmod(tip.x, StationGeo.CIRC), tip.y)
	var best := INF
	for c in [Vector2(-1, -1), Vector2(-1, 1), Vector2(1, -1), Vector2(1, 1), Vector2.ZERO]:
		var a := NpcPlaces._attach_on(tip + c * 4.0, DRIVEN)
		if a.is_empty():
			continue
		var e: Array = NpcPlaces._edge(int(a[0]))
		var och = _road_chain.get(int(e[2]))
		if och != null and int(och.idx) == int(sv.chain.idx):
			continue
		best = minf(best, _dist_to_road(tip, int(e[2]), float(a[1])))
	var hd: Vector2 = d if not at_start else -d
	var toward := false
	for c in [Vector2.ZERO]:
		var a2 := NpcPlaces._attach_on(tip + hd * best, DRIVEN)
		toward = not a2.is_empty()
	if best > 2.5 and best < 12.0 and toward:
		_found(sv, "dangling_end", tip, best, "the road ends %.1f m short of the road beside it, not joined" % best, "major")


func _dist_to_road(p: Vector2, ri: int, u: float) -> float:
	## The true distance from p to road ri's centreline, round its parameter u. (The probe's own attach point is where a
	## point 4 m off p meets the road: at a T-junction that's ~4 m from a tip lying on the road -- round 1 and 2's 2,800
	## false "dangling" ends.)
	var pts: PackedVector2Array = NpcPlaces._road(ri).pts
	var best := INF
	for k in range(maxi(0, int(u) - 4), mini(pts.size() - 1, int(u) + 5)):
		var a := Vector2(float(pts[k][0]), float(pts[k][1]))
		var ab := Vector2(StationGeo.wrap_ds(float(pts[k + 1][0]) - a.x), float(pts[k + 1][1]) - a.y)
		var ap := Vector2(StationGeo.wrap_ds(p.x - a.x), p.y - a.y)
		var t := clampf(ap.dot(ab) / maxf(ab.length_squared(), 1e-9), 0.0, 1.0)
		best = minf(best, (ap - ab * t).length())
	return best


func _building_on(p: Vector2) -> String:
	if _sites.is_empty():
		Placement.load_all()
		for i in Placement.count():
			var cell := Vector2i(floori(Placement.s(i) / 40.0), floori(Placement.x(i) / 40.0))
			if not _sites.has(cell):
				_sites[cell] = PackedInt32Array()
			var arr: PackedInt32Array = _sites[cell]
			arr.append(i)
			_sites[cell] = arr
	var cs := Vector2i(floori(p.x / 40.0), floori(p.y / 40.0))
	for dx in [-1, 0, 1]:
		for dy in [-1, 0, 1]:
			for bi in _sites.get(Vector2i(posmod(cs.x + dx, ceili(StationGeo.CIRC / 40.0)), cs.y + dy), PackedInt32Array()):
				var k := Placement.kind(bi)
				if k == "crossing" or k == "bridge":
					continue
				var rel := Vector2(StationGeo.wrap_ds(p.x - Placement.s(bi)), p.y - Placement.x(bi))
				var yaw := Placement.yaw(bi)
				var lx := rel.dot(Vector2(sin(yaw), cos(yaw)))
				var lz := rel.dot(Vector2(-cos(yaw), sin(yaw)))
				var fmn := Placement.fmin(bi)
				var fmx := Placement.fmax(bi)
				if lx > fmn.x + 0.3 and lx < fmx.x - 0.3 and lz > fmn.y + 0.3 and lz < fmx.y - 0.3:
					return Placement.id(bi)
	return ""


# ------------------------------------------------------------------ the evaluation
func _context(p: Vector2) -> Dictionary:
	## What's round an anomaly (computed only when one is found)
	var c := {}
	c.junction = not TrafficSigns.junctions_near(p, 18.0).is_empty()
	c.deck = GreatBridges.deck_h(p.x, p.y) > -INF
	c.crossing = MapTerrain.on_small_bridge(p.x, p.y, 2.0, 12.0)
	c.bridge_end = false
	for k in [-12.0, 12.0]:
		for dd in [Vector2(k, 0.0), Vector2(0.0, k)]:
			var q: Vector2 = p + dd
			var on_b := GreatBridges.deck_h(q.x, q.y) > -INF or not is_nan(_crossing_deck(q))
			if on_b != (c.deck or c.crossing):
				c.bridge_end = true
	c.pad = _building_near(p, 12.0)
	var g := Vector2(MapTerrain.base_elev(p.x + 10.0, p.y) - MapTerrain.base_elev(p.x - 10.0, p.y),
		MapTerrain.base_elev(p.x, p.y + 10.0) - MapTerrain.base_elev(p.x, p.y - 10.0)).length() / 20.0
	c.natural_slope = g
	c.water = MapTerrain.water_at(p.x, p.y).x > -9000.0
	c.great_bridge_near = false
	for sp in GreatBridges.decks:
		if GreatBridges.off_line(sp, p.x, p.y) < 20.0:
			c.great_bridge_near = true
	return c


func _building_near(p: Vector2, r: float) -> String:
	var cs := Vector2i(floori(p.x / 40.0), floori(p.y / 40.0))
	for dx in [-1, 0, 1]:
		for dy in [-1, 0, 1]:
			for bi in _sites.get(Vector2i(posmod(cs.x + dx, ceili(StationGeo.CIRC / 40.0)), cs.y + dy), PackedInt32Array()):
				if Vector2(StationGeo.wrap_ds(p.x - Placement.s(bi)), p.y - Placement.x(bi)).length() < r + 15.0:
					return Placement.id(bi)
	return ""


func _evaluate(kind: String, value: float, ctx: Dictionary) -> Array:
	## [cause, fix, severity]: the anomaly judged by what's round it, so nobody has to look at it to know what it is.
	match kind:
		"step":
			if ctx.bridge_end:
				return ["deck_vs_approach", "pin the approach's profile to the deck height and ease it over 30 m (road_profile deck pins)", "blocker" if value > 0.3 else "major"]
			if ctx.pad != "":
				return ["pad_edge", "feather the levelled pad (%s) into the road's grade" % ctx.pad, "blocker" if value > 0.3 else "major"]
			if ctx.junction:
				return ["junction_levels", "grade the junction as one level (town_grade)", "blocker" if value > 0.3 else "major"]
			return ["profile_discontinuity", "smooth the road's profile here (road_profile)", "blocker" if value > 0.3 else "major"]
		"grade":
			if ctx.natural_slope > 0.18:
				return ["terrain_steep", "cut/fill or a switchback: the hillside itself is %.0f %%" % (ctx.natural_slope * 100.0), "blocker" if value > GRADE_BLOCK else "minor"]
			return ["profile_not_eased", "regrade to the class limit (road_profile)", "blocker" if value > GRADE_BLOCK else "minor"]
		"crest", "sag":
			if ctx.bridge_end:
				return ["deck_hump", "lengthen the vertical curve onto the deck", "major"]
			return ["short_vertical_curve", "lengthen the vertical curve (K) in the profile", "major"]
		"camber":
			if ctx.pad != "":
				return ["pad_tilt", "level the road across beside pad %s" % ctx.pad, "minor"]
			return ["hillside_camber", "flatten the road's cross-section (cut into the slope)", "minor"]
		"bend":
			if ctx.junction:
				return ["junction_turn", "none: a turn at a junction", "minor"]
			return ["geometry_kink", "ease the centreline to an 8 m+ radius (road_network)", "major"]
		"flooded":
			if ctx.great_bridge_near:
				return ["road_off_deck", "lay the road on its bridge's line (road_fix: straight across the span)", "blocker"]
			return ["below_water", "raise the profile over the water (a causeway) or reroute", "blocker"]
		"obstructed":
			return ["structure_on_road", "move the building off the carriageway (placement clear_of_roads)", "blocker"]
		"sign_in_road":
			return ["sign_misplaced", "move the sign behind the kerb (road_furniture carriageway pass)", "major"]
		"sign_hidden":
			return ["signs_stacked", "space the signs 1.5 m along the kerb, or share a post", "major"]
		"sign_no_junction":
			return ["orphan_control", "drop the sign or put it at its junction", "minor"]
		"bridge_offset":
			return ["deck_misaligned", "snap the crossing onto its road / ease the road straight across", "major"]
		"dangling_end":
			return ["unjoined", "join the end to the road beside it (road_network)", "major"]
	return ["unknown", "look at it", "minor"]


func _found(sv: Dictionary, kind: String, p: Vector2, value: float, what: String, severity := "", key_extra := "") -> void:
	var key := "%s@%d,%d%s" % [kind, floori(fposmod(p.x, StationGeo.CIRC) / 10.0), floori(p.y / 10.0), key_extra]
	var r: Dictionary = anomalies.get(key, {})
	if r.is_empty():
		var ev := _evaluate(kind, value, _context(p))
		r = {"kind": kind, "s": snappedf(fposmod(p.x, StationGeo.CIRC), 0.1), "x": snappedf(p.y, 0.1), "what": what, "value": snappedf(value, 0.01),
			"cause": ev[0], "fix": ev[1], "severity": severity if severity != "" else ev[2], "n": 0, "by": [],
			"road": "%s (%s)" % [sv.name, sv.cls], "town": TrafficReports._town(p)}
		anomalies[key] = r
	r.n = int(r.n) + 1
	r.value = snappedf(maxf(float(r.value), value), 0.01)
	if (r.by as Array).size() < 4 and not (r.by as Array).has(sv.id):
		(r.by as Array).append(sv.id)


# ------------------------------------------------------------------ the end
func _finish() -> void:
	finished = true
	for vc in _visual:
		(vc[0] as Node).queue_free()
	_visual.clear()
	save()
	print("RoadSurvey: done in %d s -- %d surveyors, %d m driven, %s" % [(Time.get_ticks_msec() - _t0) / 1000, surveyors.size(), _samples, summary()])
	if OS.get_cmdline_user_args().has("--quit-after-survey"):
		get_tree().quit()


func save() -> void:
	var f := FileAccess.open(PATH, FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify({"_about": "RoadSurvey: what the surveyors found driving the roads", "saved": Time.get_datetime_string_from_system(),
		"surveyors": surveyors.size(), "metres": _samples, "all_roads": survey_all, "reports": anomalies.values()}, "\t"))
	f.close()


func summary() -> String:
	var by := {}
	for r in anomalies.values():
		var k := "%s/%s" % [r.kind, r.severity]
		by[k] = int(by.get(k, 0)) + 1
	return "%d anomalies: %s" % [anomalies.size(), str(by)]


func _show_near() -> void:
	## The surveyors' cars where the player can see them (the rest drive unseen).
	var pl := get_tree().current_scene.get("player") as Node3D
	if pl == null or Engine.get_process_frames() % 10 != 0:
		return
	var here := Vector2(StationGeo.s_of(pl.global_position), pl.global_position.x)
	for vc in _visual.duplicate():
		var sv: Dictionary = vc[1]
		if float(sv.u) > float(sv.end) or NpcPlaces.dist(_at(sv.line, sv.cum, float(sv.u))[0], here) > 200.0:
			(vc[0] as Node).queue_free()
			_visual.erase(vc)
	if _visual.size() < 6:
		for sv in surveyors:
			if float(sv.u) > float(sv.end) or _visual.any(func(vc): return vc[1] == sv):
				continue
			if NpcPlaces.dist(_at(sv.line, sv.cum, float(sv.u))[0], here) < 150.0:
				var car := RemakeModularCar.new("sedan")
				car.freeze = true
				add_child(car)
				_visual.append([car, sv])
				if _visual.size() >= 6:
					break
	for vc in _visual:
		var sv: Dictionary = vc[1]
		var r := _at(sv.line, sv.cum, float(sv.u))
		var p: Vector2 = r[0]
		var d: Vector2 = r[1]
		(vc[0] as Node3D).global_transform = Transform3D(StationGeo.basis(p.x, atan2(-d.y, d.x)), StationGeo.point(p.x, p.y, _surface(p)[0]))
