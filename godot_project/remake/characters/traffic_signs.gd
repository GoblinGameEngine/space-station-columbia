extends RefCounted
class_name TrafficSigns

## What a driver can see on the road: the signs, stop bars, signals, centre-line markings, rail
## crossings and junctions, as the world has them (remake/road_furniture.json, the same data
## RoadFurniture draws; junctions from the road network). Drivers (RoadDriver) read only this --
## nothing about any particular road is baked into how they drive (research/traffic/01): change a
## sign and they obey the new sign; change the markings and they pass where the markings allow.
##
## Runtime edits: add_sign / remove_sign / set_sign, set_line_kind. A sign is
## {id, t, p (s, x), face (s, x): the way its face looks -- at the traffic it governs}.
## Signals: each one's arms (outward directions); opposite arms share a phase, phases turn by the
## clock (GREEN + AMBER + ALL_RED each).

const CELL := 32.0
const GREEN := 22.0
const AMBER := 4.0
const ALL_RED := 2.0

static var _loaded := false
static var _signs := {}                  # id -> sign
static var _grid := {}                   # Vector2i -> [sign id]
static var _bars: Array = []             # [{c (s, x), across (s, x) unit, half}]
static var _bar_grid := {}
static var _signals: Array = []          # [{p, arms [Vector2], phases [[arm index]]}]
static var _sig_grid := {}
static var _lines := {}                  # Vector2i -> [[a, b, kind ("solid"/"dashed")]]
static var _xings: Array = []            # [{p, u}]
static var _junctions: Array = []        # [Vector2]
static var _jn_grid := {}
static var _next_id := 1


static func load_all() -> void:
	if _loaded:
		return
	_loaded = true
	if not FileAccess.file_exists("res://remake/road_furniture.json"):
		return
	var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://remake/road_furniture.json"))
	for s in d.get("signs", []):
		add_sign(str(s.t), Vector2(float(s.s), float(s.x)), float(s.yaw))
	for b in d.get("bars", []):
		var q: Array = b.q
		var p0 := Vector2(float(q[0][0]), float(q[0][1]))
		var p1 := Vector2(float(q[1][0]), float(q[1][1]))
		var p2 := Vector2(float(q[2][0]), float(q[2][1]))
		var p3 := Vector2(float(q[3][0]), float(q[3][1]))
		var c := (p0 + p1 + p2 + p3) * 0.25
		var e1 := _d(p0, p1)
		var e2 := _d(p1, p2)
		var across := e1 if e1.length() > e2.length() else e2           # the bar's long side
		var bar := {"c": Vector2(fposmod(c.x, StationGeo.CIRC), c.y), "across": across.normalized(), "half": across.length() * 0.5}
		_bars.append(bar)
		_put(_bar_grid, bar.c, _bars.size() - 1)
	for g in d.get("signals", []):
		var arms: Array = []
		for a in g.arms:
			arms.append(Vector2(float(a[0]), float(a[1])).normalized())
		var phases: Array = []
		var used := {}
		for i in arms.size():
			if used.has(i):
				continue
			var ph := [i]
			used[i] = true
			for j in range(i + 1, arms.size()):
				if not used.has(j) and (arms[i] as Vector2).dot(arms[j]) < -0.8:
					ph.append(j)
					used[j] = true
			phases.append(ph)
		_signals.append({"p": Vector2(float(g.s), float(g.x)), "arms": arms, "phases": phases})
		_put(_sig_grid, _signals[_signals.size() - 1].p, _signals.size() - 1)
	for x in d.get("xings", []):
		_xings.append({"p": Vector2(float(x.s), float(x.x)), "u": Vector2(float(x.u[0]), float(x.u[1]))})
	# centre lines: yellow, dashed (passing allowed) or solid / double (no passing)
	MapTerrain._load()
	var roads: Array = MapTerrain._d.roads
	for l in d.get("lines", []):
		if str(l.c) != "y":
			continue
		var r: Dictionary = roads[int(l.r)]
		var pts: Array = r.pts
		var kind := "dashed" if l.has("dash") else "solid"
		var off := float(l.off)
		for k in range(int(l.a), mini(int(l.b), pts.size() - 1)):
			var a := Vector2(float(pts[k][0]), float(pts[k][1]))
			var b := Vector2(float(pts[k + 1][0]), float(pts[k + 1][1]))
			var t := _d(a, b).normalized()
			var n := Vector2(-t.y, t.x) * off
			_put_seg(a + n, b + n, kind)
	# junctions: where three or more ways meet, from the road network
	NpcPlaces.load_all()
	for i in NpcPlaces._adj.size():
		if (NpcPlaces._adj[i] as Array).size() >= 3:
			var nd: Array = NpcPlaces._paths.nodes[i]
			var jp := Vector2(float(nd[0]), float(nd[1]))
			_junctions.append(jp)
			_put(_jn_grid, jp, _junctions.size() - 1)
	print("TrafficSigns: %d signs, %d stop bars, %d signals, %d crossings, %d junctions" % [_signs.size(), _bars.size(), _signals.size(), _xings.size(), _junctions.size()])


# -- edits ------------------------------------------------------------------------------------------

static func add_sign(t: String, p: Vector2, yaw: float) -> int:
	var id := _next_id
	_next_id += 1
	var s := {"id": id, "t": t, "p": Vector2(fposmod(p.x, StationGeo.CIRC), p.y), "face": Vector2(cos(yaw), -sin(yaw))}
	_signs[id] = s
	_put(_grid, s.p, id)
	return id


static func remove_sign(id: int) -> void:
	var s: Dictionary = _signs.get(id, {})
	if s.is_empty():
		return
	var k := _cell(s.p)
	if _grid.has(k):
		(_grid[k] as Array).erase(id)
	_signs.erase(id)


static func set_sign(id: int, t: String) -> void:
	if _signs.has(id):
		_signs[id].t = t


# -- what a driver sees -----------------------------------------------------------------------------

static func signs_near(p: Vector2, r: float) -> Array:
	var out: Array = []
	for k in _cells(p, r):
		for id in _grid.get(k, []):
			var s: Dictionary = _signs[id]
			if NpcPlaces.dist(s.p, p) <= r:
				out.append(s)
	return out


static func bars_near(p: Vector2, r: float) -> Array:
	var out: Array = []
	for k in _cells(p, r):
		for i in _bar_grid.get(k, []):
			if NpcPlaces.dist(_bars[i].c, p) <= r:
				out.append(_bars[i])
	return out


static func junctions_near(p: Vector2, r: float) -> Array:
	var out: Array = []
	for k in _cells(p, r):
		for i in _jn_grid.get(k, []):
			if NpcPlaces.dist(_junctions[i], p) <= r:
				out.append(_junctions[i])
	return out


static func signal_near(p: Vector2, r: float) -> Dictionary:
	for k in _cells(p, r):
		for i in _sig_grid.get(k, []):
			if NpcPlaces.dist(_signals[i].p, p) <= r:
				return _signals[i]
	return {}


static func signal_state(g: Dictionary, approach_dir: Vector2, t: float) -> String:
	## "green", "amber" or "red" for traffic approaching the signal along approach_dir.
	var arms: Array = g.arms
	var best := -1
	var bd := 2.0
	for i in arms.size():
		var c := (arms[i] as Vector2).dot(approach_dir)          # the approach comes in along -arm
		if c < bd:
			bd = c
			best = i
	var phases: Array = g.phases
	var per := GREEN + AMBER + ALL_RED
	var cyc := fposmod(t + float(hash(g.p) % 50), per * phases.size())
	var ph := int(cyc / per)
	var inph := cyc - ph * per
	if not (phases[ph] as Array).has(best):
		return "red"
	return "green" if inph < GREEN else ("amber" if inph < GREEN + AMBER else "red")


static func crossing_near(p: Vector2, r: float) -> Dictionary:
	for x in _xings:
		if NpcPlaces.dist(x.p, p) <= r:
			return x
	return {}


static func centre_line(p: Vector2) -> String:
	## The centre-line marking beside the driver: "solid" (double yellow), "dashed", or "" (none).
	var best := ""
	var bd := 4.0
	for k in _cells(p, 4.0):
		for seg in _lines.get(k, []):
			var a: Vector2 = seg[0]
			var ab := _d(a, seg[1])
			var ap := _d(a, p)
			var t := clampf(ap.dot(ab) / maxf(ab.length_squared(), 1e-6), 0.0, 1.0)
			var dd := (ap - ab * t).length()
			if dd < bd:
				bd = dd
				best = seg[2]
	return best


# -- grid -------------------------------------------------------------------------------------------

static func _d(a: Vector2, b: Vector2) -> Vector2:
	return Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)


static func _cell(p: Vector2) -> Vector2i:
	return Vector2i(floori(fposmod(p.x, StationGeo.CIRC) / CELL), floori(p.y / CELL))


static func _cells(p: Vector2, r: float) -> Array:
	var c := _cell(p)
	var n := ceili(r / CELL)
	var wrap := ceili(StationGeo.CIRC / CELL)
	var out: Array = []
	for dx in range(-n, n + 1):
		for dy in range(-n, n + 1):
			out.append(Vector2i(posmod(c.x + dx, wrap), c.y + dy))
	return out


static func _put(g: Dictionary, p: Vector2, v: Variant) -> void:
	var k := _cell(p)
	if not g.has(k):
		g[k] = []
	(g[k] as Array).append(v)


static func _put_seg(a: Vector2, b: Vector2, kind: String) -> void:
	var seg := [Vector2(fposmod(a.x, StationGeo.CIRC), a.y), Vector2(fposmod(b.x, StationGeo.CIRC), b.y), kind]
	var n := maxi(1, ceili(_d(a, b).length() / CELL))
	var seen := {}
	for i in n + 1:
		var q := a + _d(a, b) * (float(i) / n)
		var k := _cell(q)
		if not seen.has(k):
			seen[k] = true
			if not _lines.has(k):
				_lines[k] = []
			(_lines[k] as Array).append(seg)
