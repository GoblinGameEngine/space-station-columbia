extends RefCounted
class_name TransitNet

## The station's public transport network (canon: road trams and the Ring Line railway;
## research/lives/04_travel.md). Built at load from the walking network and the rail line:
##   tram lines   out-and-back loops through a chain of towns, in the right-hand lane of the streets
##                (NpcPlaces.route at TRAM_EDGE), a stop in each town at its civic or main-street door;
##   the train    the Ring Line: the rail round the world, a station where it passes within
##                STATION_REACH of a town's centre.
## A line: {id, name, kind ("tram"/"train"), pts (s, x) closed loop, cum (distance at each point), length,
## stops [{d, name, town}], speed (m/s), dwell (s), count (vehicles), period (s)}.

const TRAM_EDGE := -1.9            # the tram lane: this far inside the road's edge
const TRAM_SPEED := 9.0            # m/s on the streets (32 km/h)
const TRAIN_SPEED := 16.0          # m/s (58 km/h)
const DWELL := 18.0                # s at a stop
const STATION_REACH := 900.0
const HEADWAY := 300.0             # s between vehicles on a line (real time; a game hour is two minutes)
const TRAM_ROADS := ["street", "main", "county", "hwy"]    # stops on these; the trams run on gravel roads too, never alleys
const LOOP_R := 14.0               # the turning loop at each end of a tram line (m)
const FILLET_R := 15.0             # street corners are rounded to this radius where the streets allow (m)

# the tram lines: town chains (bible settlement test-town names), in order round the ring
const LINES := [
	["north_shore", "North Shore Line", ["Haven Point", "Tern Harbor", "Port Carrow", "Brightwater"]],
	["south_shore", "South Shore Line", ["Playa Verde", "Solana Point", "Pelican Cove", "Oceanview"]],
	["kettle", "Kettle Line", ["Victory Bay", "Port Tamsin", "Dunmore Crossing", "Cedar Ford", "Marlowe", "Fenwick", "Loomis Grove", "Haskins Corner"]],
]
const STOP_TYPES := ["town_hall", "post_office", "library", "grocery", "cafe", "diner", "church"]

static var _lines: Array = []
static var loops: Array = []          # the trolley lanes: each turning loop's points (s, x, unwrapped)
static var _sites: Array = []         # buildings as [centre (s, x), radius] for placing the loops


static func lines() -> Array:
	if _lines.is_empty():
		_build()
	return _lines


static func _stop_building(town: String) -> String:
	for t in STOP_TYPES:
		for uid in NpcPlaces.of_type(t):
			var u := NpcPlaces.unit(uid)
			if str(u.settlement) == town:
				return str(u.building)
	return ""


static func _append(pts: PackedVector2Array, more: PackedVector2Array) -> void:
	for i in more.size():
		if pts.size() > 0 and NpcPlaces.dist(pts[pts.size() - 1], more[i]) < 0.5:
			continue
		pts.append(more[i])


static func _finish(line: Dictionary) -> void:
	var pts: PackedVector2Array = line.pts
	var cum := PackedFloat64Array()
	cum.append(0.0)
	for i in range(1, pts.size()):
		cum.append(cum[i - 1] + NpcPlaces.dist(pts[i - 1], pts[i]))
	var closing := NpcPlaces.dist(pts[pts.size() - 1], pts[0])
	line.cum = cum
	line.length = cum[cum.size() - 1] + closing
	line.period = line.length / float(line.speed) + (line.stops as Array).size() * float(line.dwell)
	line.count = maxi(1, int(round(float(line.period) / HEADWAY)))


static func _nearest_d(line: Dictionary, p: Vector2) -> float:
	var pts: PackedVector2Array = line.pts
	var best := INF
	var bd := 0.0
	for i in pts.size():
		var d := NpcPlaces.dist(pts[i], p)
		if d < best:
			best = d
			bd = (line.cum as PackedFloat64Array)[i]
	return bd


static func _build() -> void:
	NpcPlaces.load_all()
	for spec in LINES:
		var stops_b := []
		for town in spec[2]:
			var b := _stop_building(town)
			if b != "":
				stops_b.append([town, b])
		if stops_b.size() < 2:
			continue
		var pts := PackedVector2Array()
		var stop_pts := []
		# out along the chain, then back: each leg its own right-hand lane
		var chain: Array = stops_b + stops_b.slice(0, stops_b.size() - 1).duplicate()
		var back: Array = stops_b.duplicate()
		back.reverse()
		chain = stops_b + back.slice(1)
		for i in chain.size() - 1:
			# set off ahead, the way the tram arrived (it goes round the block rather than turn on the spot)
			var came := pts[pts.size() - 2] if pts.size() >= 2 else Vector2.INF
			var r := NpcPlaces.route(chain[i][1], chain[i + 1][1], Vector2.INF, Vector2.INF, TRAM_EDGE, TRAM_ROADS, ["gravel"], came)
			if r.size() < 3:
				continue
			var leg := r.slice(1, r.size() - 1)               # kerb to kerb, not door to door
			stop_pts.append([chain[i][0], leg[0]])
			_append(pts, leg)
		pts = _smooth(pts)
		var line := {"id": spec[0], "name": spec[1], "kind": "tram", "pts": pts, "speed": TRAM_SPEED, "dwell": DWELL, "stops": []}
		_finish(line)
		for sp in stop_pts:
			(line.stops as Array).append({"d": _nearest_d(line, sp[1]), "name": "%s stop" % sp[0], "town": sp[0]})
		(line.stops as Array).sort_custom(func(a, b): return float(a.d) < float(b.d))
		_finish(line)
		_lines.append(line)
	# the Ring Line
	MapTerrain._load()
	var rail: Array = MapTerrain._d.rail.pts
	var rp := PackedVector2Array()
	for p in rail:
		var v := Vector2(fposmod(float(p[0]), StationGeo.CIRC), float(p[1]))
		if rp.size() > 0 and NpcPlaces.dist(rp[rp.size() - 1], v) < 0.5:
			continue
		rp.append(v)
	var train := {"id": "ring", "name": "the Ring Line", "kind": "train", "pts": rp, "speed": TRAIN_SPEED, "dwell": 30.0, "stops": []}
	_finish(train)
	var centres := {}
	var st: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://remake/placement.json"))
	for b in st.structures:
		if b.get("settlement") == null:
			continue
		var k := str(b.settlement)
		if not centres.has(k):
			centres[k] = [Vector2.ZERO, 0, 0.0, 0.0]
		var c: Array = centres[k]
		var a := float(b.s) / StationGeo.CIRC * TAU
		c[2] += cos(a)
		c[3] += sin(a)
		c[0].y += float(b.x)
		c[1] += 1
	for k in centres:
		var c: Array = centres[k]
		var cs := fposmod(atan2(c[3], c[2]) / TAU * StationGeo.CIRC, StationGeo.CIRC)
		var cp := Vector2(cs, c[0].y / c[1])
		var d := _nearest_d(train, cp)
		var i := (train.cum as PackedFloat64Array).bsearch(d)
		var at: Vector2 = (train.pts as PackedVector2Array)[mini(i, (train.pts as PackedVector2Array).size() - 1)]
		if NpcPlaces.dist(at, cp) < STATION_REACH:
			(train.stops as Array).append({"d": d, "name": "%s station" % k, "town": k})
	(train.stops as Array).sort_custom(func(a, b): return float(a.d) < float(b.d))
	_finish(train)
	_lines.append(train)


static func _smooth(raw: PackedVector2Array) -> PackedVector2Array:
	## A tram path a 24 m articulated tram can follow: each end-of-line reversal (two tight corners
	## the same way round with a lane crossing between) becomes a turning loop, every other corner an
	## arc of FILLET_R (as wide as the streets on either side allow).
	if raw.size() < 4:
		return raw
	# unwrapped, deduplicated, starting mid-way along the longest stretch (never on a corner)
	var p: Array = [raw[0]]
	for i in range(1, raw.size()):
		var q: Vector2 = p[p.size() - 1] + Vector2(StationGeo.wrap_ds(raw[i].x - raw[i - 1].x), raw[i].y - raw[i - 1].y)
		if q.distance_to(p[p.size() - 1]) > 0.5:
			p.append(q)
	var n := p.size()
	var li := 0
	for i in n:
		if (p[(i + 1) % n] as Vector2).distance_to(p[i]) > (p[(li + 1) % n] as Vector2).distance_to(p[li]):
			li = i
	var mid: Vector2 = ((p[li] as Vector2) + (p[(li + 1) % n] as Vector2)) * 0.5
	var r: Array = [mid]
	for k in n:
		r.append(p[(li + 1 + k) % n])
	r.append(mid)
	# 0. the lane offset folds back on itself on the inside of a corner (a "swallowtail"): where a
	# segment crosses one of the next few, the points between go and the crossing point stays
	var clean: Array = [r[0]]
	var k0 := 1
	while k0 < r.size():
		var cut := false
		if clean.size() >= 1 and k0 + 1 < r.size():
			var p0: Vector2 = clean[clean.size() - 1]
			var p1: Vector2 = r[k0]
			for j in range(k0 + 1, mini(k0 + 6, r.size() - 1)):
				var x = Geometry2D.segment_intersects_segment(p0, p1, r[j], r[j + 1])
				if x != null:
					clean.append(x)
					k0 = j + 1
					cut = true
					break
		if not cut:
			clean.append(r[k0])
			k0 += 1
	r = clean
	# 1. reversals -> turning loops: the way 25 m before and 25 m after really is opposite
	var out: Array = [r[0]]
	var i := 1
	while i < r.size() - 1:
		var a: Vector2 = r[i]
		var turned := false
		if i + 2 < r.size():
			var b: Vector2 = r[i + 1]
			var u: Vector2 = (a - _walk(r, i, -1, 25.0)).normalized()
			var v: Vector2 = (_walk(r, i + 1, 1, 25.0) - b).normalized()
			if (b - a).length() < 10.0 and u.dot(v) < -0.8:
				# a trolley lane: the turning loop placed along the street where it crosses fewest buildings
				var k := _best_shift(a, b, u)
				var a2 := a - u * k
				var b2 := b - u * k
				while out.size() > 1 and ((out[out.size() - 1] as Vector2) - a2).dot(u) > -0.1:
					out.pop_back()
				var n0 := out.size()
				_loop(out, a2, b2, u)
				loops.append(out.slice(n0))
				i += 2
				while i < r.size() - 1 and (((r[i] as Vector2) - b2).dot(-u) < 0.1 or (r[i] as Vector2).distance_to(b2) < 25.0):
					i += 1
				turned = true
		if not turned:
			out.append(a)
			i += 1
	out.append(r[r.size() - 1])
	# 2. corners -> arcs
	var res := PackedVector2Array()
	res.append(out[0])
	for k in range(1, out.size() - 1):
		var a0: Vector2 = out[k - 1]
		var c: Vector2 = out[k]
		var b0: Vector2 = out[k + 1]
		var din := c - a0
		var dout := b0 - c
		var th := absf(din.angle_to(dout))
		if th < deg_to_rad(4.0) or th > deg_to_rad(170.0) or din.length() < 0.6 or dout.length() < 0.6:
			res.append(c)
			continue
		var t := minf(FILLET_R * tan(th / 2.0), minf(din.length(), dout.length()) * 0.45)
		var rr := t / tan(th / 2.0)
		var ui := din.normalized()
		var uo := dout.normalized()
		var side := signf(ui.cross(uo))
		var sp := c - ui * t
		var centre := sp + Vector2(-ui.y, ui.x) * side * rr
		var steps := maxi(2, int(ceil(rad_to_deg(th) / 8.0)))
		var a_s := (sp - centre).angle()
		for k2 in steps + 1:
			res.append(centre + Vector2.from_angle(a_s + side * th * k2 / steps) * rr)
	res.append(out[out.size() - 1])
	# 3. what is left (jogs at junctions too short to round) is blurred out: the path resampled every
	# metre and box-filtered three times over (about a Gaussian of 2 m: it irons out the jogs and leaves the corners where they are), round the closed loop
	var even := PackedVector2Array()
	var carry := 0.0
	for k in range(1, res.size()):
		var a1 := res[k - 1]
		var seg := res[k] - a1
		var sl := seg.length()
		var t := carry
		while t < sl:
			even.append(a1 + seg * (t / sl))
			t += 1.0
		carry = t - sl
	var m := even.size()
	var hw := 2
	for pass_ in 3:
		var acc := Vector2.ZERO
		for k in range(-hw, hw + 1):
			acc += even[posmod(k, m)]
		var blurred := PackedVector2Array()
		blurred.resize(m)
		for k in m:
			blurred[k] = acc / float(2 * hw + 1)
			acc += even[posmod(k + hw + 1, m)] - even[posmod(k - hw, m)]
		even = blurred
	for k in m:
		even[k] = Vector2(fposmod(even[k].x, StationGeo.CIRC), even[k].y)
	return even


static func _buildings_near(p: Vector2, reach: float) -> Array:
	if _sites.is_empty():
		var st: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://remake/placement.json"))
		for b in st.structures:
			var fmn: Array = b.get("fmin", [-5, -5])
			var fmx: Array = b.get("fmax", [5, 5])
			_sites.append([Vector2(float(b.s), float(b.x)), 0.5 * Vector2(float(fmx[0]) - float(fmn[0]), float(fmx[1]) - float(fmn[1])).length()])
	var out: Array = []
	for site in _sites:
		if NpcPlaces.dist(site[0], p) < reach + float(site[1]):
			out.append(site)
	return out


static func _best_shift(a: Vector2, b: Vector2, u: Vector2) -> float:
	## How far back along the street (m; negative: beyond its end) to put the turning loop so that
	## it crosses the fewest buildings (each kept 2 m clear of the tram), the nearest such place.
	var near := _buildings_near(a, 120.0)
	var best_k := 0.0
	var best := INF
	for step in range(-4, 13):
		var k := step * 5.0
		var pts: Array = []
		_loop(pts, a - u * k, b - u * k, u)
		var hits := 0
		for q in pts:
			var qq := Vector2(fposmod((q as Vector2).x, StationGeo.CIRC), (q as Vector2).y)
			for site in near:
				if NpcPlaces.dist(site[0], qq) < float(site[1]) + 3.3:
					hits += 1
					break
		var score := hits * 100.0 + absf(k)
		if score < best:
			best = score
			best_k = k
	return best_k


static func _walk(r: Array, i: int, step: int, dist: float) -> Vector2:
	## The point `dist` metres along the polyline from point i, backwards (step -1) or forwards.
	var left := dist
	var j := i
	while j + step >= 0 and j + step < r.size():
		var seg := (r[j + step] as Vector2).distance_to(r[j])
		if seg >= left:
			return (r[j] as Vector2).lerp(r[j + step], left / maxf(seg, 1e-6))
		left -= seg
		j += step
	return r[j]


static func _loop(out: Array, a: Vector2, b: Vector2, u: Vector2) -> void:
	## A balloon loop from the end a of the incoming lane (heading u) round to b, the start of the lane
	## back: a right turn out, round the loop to the left, a right turn into the lane back.
	var l := Vector2(-u.y, u.x)
	var w := (b - a).dot(l)
	if w < 0.0:
		l = -l
		w = -w
	var f0 := maxf(0.0, (b - a).dot(u))
	var o := a + u * f0
	var R := LOOP_R
	var al := acos(clampf((w / (2.0 * R) + 1.0) / 2.0, -1.0, 1.0))
	var pts: Array = []
	for k in 7:                                     # right turn out
		var ph := al * k / 6.0
		pts.append(Vector2(R * sin(ph), R * cos(ph) - R))
	var c2 := Vector2(2.0 * R * sin(al), w / 2.0)
	var p1: Vector2 = pts[pts.size() - 1]
	var b1 := (p1 - c2).angle()
	var sweep := TAU - 2.0 * al                     # the loop less its throat
	for k in range(1, 37):                          # round the loop, to the left
		pts.append(c2 + Vector2.from_angle(b1 + sweep * k / 36.0) * R)
	for k in range(5, -1, -1):                      # right turn into the lane back
		var ph := al * k / 6.0
		pts.append(Vector2(R * sin(ph), w - (R * cos(ph) - R)))
	out.append(a)
	for q in pts:
		out.append(o + u * (q as Vector2).x + l * (q as Vector2).y)
	out.append(b)


static func point_at(line: Dictionary, d: float) -> Vector2:
	## The (s, x) point at distance d along the loop.
	var L: float = line.length
	d = fposmod(d, L)
	var cum: PackedFloat64Array = line.cum
	var pts: PackedVector2Array = line.pts
	var i := cum.bsearch(d) - 1
	if i < 0:
		i = 0
	if i >= pts.size() - 1:
		var a := pts[pts.size() - 1]
		var b := pts[0]
		var t := (d - cum[cum.size() - 1]) / maxf(NpcPlaces.dist(a, b), 1e-6)
		return Vector2(fposmod(a.x + StationGeo.wrap_ds(b.x - a.x) * t, StationGeo.CIRC), a.y + (b.y - a.y) * t)
	var a2 := pts[i]
	var b2 := pts[i + 1]
	var t2 := (d - cum[i]) / maxf(cum[i + 1] - cum[i], 1e-6)
	return Vector2(fposmod(a2.x + StationGeo.wrap_ds(b2.x - a2.x) * t2, StationGeo.CIRC), a2.y + (b2.y - a2.y) * t2)


static func state(line: Dictionary, t: float) -> Dictionary:
	## Where a vehicle is at time t (s) into its loop: {d, dwelling, stop (index or -1)}.
	var stops: Array = line.stops
	var v: float = line.speed
	var dw: float = line.dwell
	var L: float = line.length
	t = fposmod(t, float(line.period))
	if stops.is_empty():
		return {"d": fposmod(t * v, L), "dwelling": false, "stop": -1}
	var d0: float = stops[0].d
	for i in stops.size():
		var a: float = stops[i].d
		var b: float = stops[(i + 1) % stops.size()].d
		var gap := fposmod(b - a, L)
		if gap < 1e-3:
			gap = L if stops.size() == 1 else gap
		if t < dw:
			return {"d": a, "dwelling": true, "stop": i}
		t -= dw
		var run := gap / v
		if t < run:
			return {"d": a + t * v, "dwelling": false, "stop": -1}
		t -= run
	return {"d": d0, "dwelling": true, "stop": 0}
