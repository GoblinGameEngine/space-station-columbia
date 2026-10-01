extends RefCounted
class_name NpcPlaces

## The places people live their lives in (research/lives/01_building_types.md): the building-type
## registry (npc_places.json -- what a grocery or a cannery is, who works there, who comes and
## when), the baked units every building holds with their procedural type (npc_place_index.json),
## and the walking network between their doors (npc_paths.json).
##
##   NpcPlaces.unit("M-017/0")                 -> {uid, building, settlement, door, shell, type, jobs}
##   NpcPlaces.kind_of("M-017/0")              -> the type's registry entry
##   NpcPlaces.is_open("M-017/0", day, hour)
##   NpcPlaces.route(from_building, to_building) -> PackedVector2Array of (s, x): door, kerb, the
##                                                 streets (right-hand pavement), kerb, door

const PLACES := "res://remake/characters/npc_places.json"
const INDEX := "res://remake/characters/npc_place_index.json"
const PATHS := "res://remake/characters/npc_paths.json"
const DAYS := {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
const PAVEMENT := 1.2            # m beyond the road's edge

static var _types: Dictionary
static var _units: Dictionary    # uid -> unit
static var _of_type: Dictionary  # type -> [uid]
static var _doors: Dictionary    # building id -> Vector2 door (buildings with units, and flats)
static var _paths: Dictionary
static var _attach_cache := {}
static var _edge_cls := PackedStringArray()   # each path edge's road class ("" for a bridge deck)
static var _adj: Array           # node -> [[edge, other node, length]]


static func load_all() -> void:
	if not _types.is_empty():
		return
	_types = (JSON.parse_string(FileAccess.get_file_as_string(PLACES)) as Dictionary).types
	var ix: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(INDEX))
	for u in ix.units:
		_units[u.uid] = u
		if not _of_type.has(u.type):
			_of_type[u.type] = []
		_of_type[u.type].append(u.uid)
		_doors[u.building] = Vector2(float(u.door[0]), float(u.door[1]))
	_paths = JSON.parse_string(FileAccess.get_file_as_string(PATHS))
	_adj.resize((_paths.nodes as Array).size())
	for i in _adj.size():
		_adj[i] = []
	var edges: Array = _paths.edges
	for ei in edges.size():
		var e: Array = edges[ei]
		_adj[int(e[0])].append([ei, int(e[1]), float(e[5])])
		_adj[int(e[1])].append([ei, int(e[0]), float(e[5])])
	MapTerrain._load()
	_edge_cls.resize(edges.size())
	for ei in edges.size():
		var ri := int((edges[ei] as Array)[2])
		_edge_cls[ei] = str(MapTerrain._d.roads[ri].cls) if ri >= 0 else ""


static func types() -> Dictionary:
	load_all()
	return _types


static func unit(uid: String) -> Dictionary:
	load_all()
	return _units.get(uid, {})


static func units() -> Dictionary:
	load_all()
	return _units


static func of_type(t: String) -> Array:
	load_all()
	return _of_type.get(t, [])


static func kind_of(uid: String) -> Dictionary:
	load_all()
	return _types.get(str(_units.get(uid, {}).get("type", "")), {})


static func flats(structures: Array) -> Array:
	## The flats over shops as structures NpcHouseholds can fill (kind "flat", one household each),
	## sharing their building's footprint and street door.
	load_all()
	var by_id := {}
	for b in structures:
		by_id[b.id] = b
	var out := []
	for uid in of_type("residence"):
		var u: Dictionary = _units[uid]
		var b: Dictionary = by_id.get(u.building, {})
		if b.is_empty():
			continue
		var f := b.duplicate()
		f.id = uid
		f.kind = "flat"
		f.settlement = u.settlement
		out.append(f)
	return out


static func door_of(building: String, fallback := Vector2.INF) -> Vector2:
	load_all()
	var b := building.split("/")[0]
	return _doors.get(b, fallback)


static func register_door(building: String, door: Vector2) -> void:
	load_all()
	_doors[building] = door


static func dist(a: Vector2, b: Vector2) -> float:
	return Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y).length()


# -- opening hours ----------------------------------------------------------------------------------

static func hours_of(t: Dictionary) -> Vector2:
	## (open, close) in hours; close may be 24+ (a bar shuts at 01:00 = 25).
	var o: String = t.hours.open
	var c: String = t.hours.close
	var ho := float(o.substr(0, 2)) + float(o.substr(3, 2)) / 60.0
	var hc := float(c.substr(0, 2)) + float(c.substr(3, 2)) / 60.0
	if hc <= ho and not (ho == 0.0 and hc == 0.0):
		hc += 24.0
	return Vector2(ho, hc)


static func open_on(t: Dictionary, day: int) -> bool:
	var d: String = t.hours.days
	var wd := posmod(day, 7)
	match d:
		"daily":
			return true
		"never":
			return false
		"seasonal":
			return posmod(day, 364) < 182 or wd >= 5           # the season, and weekends out of it
	var p := d.split("-")
	if p.size() == 2 and DAYS.has(p[0]) and DAYS.has(p[1]):
		return wd >= int(DAYS[p[0]]) and wd <= int(DAYS[p[1]])
	return true


static func is_open(uid: String, day: int, hour: float) -> bool:
	var t := kind_of(uid)
	if t.is_empty():
		return false
	var h := hours_of(t)
	if open_on(t, day) and hour >= h.x and hour < h.y:
		return true
	return open_on(t, day - 1) and hour + 24.0 < h.y           # after midnight, from yesterday


# -- routes ---------------------------------------------------------------------------------------------

static func _road(ri: int) -> Dictionary:
	MapTerrain._load()
	return MapTerrain._d.roads[ri]


static func _at(ri: int, u: float) -> Vector2:
	var p: Array = _road(ri).pts
	var k := mini(int(u), p.size() - 2)
	var t := u - k
	var a := Vector2(float(p[k][0]), float(p[k][1]))
	var b := Vector2(float(p[k + 1][0]), float(p[k + 1][1]))
	return Vector2(a.x + StationGeo.wrap_ds(b.x - a.x) * t, a.y + (b.y - a.y) * t)


static func _stretch(ri: int, u0: float, u1: float) -> PackedVector2Array:
	## The road's centreline from parameter u0 to u1 (either direction).
	var out := PackedVector2Array()
	out.append(_at(ri, u0))
	if u1 >= u0:
		for k in range(floori(u0) + 1, ceili(u1)):
			out.append(_at(ri, float(k)))
	else:
		for k in range(ceili(u0) - 1, floori(u1), -1):
			out.append(_at(ri, float(k)))
	out.append(_at(ri, u1))
	return out


static func _stretch_len(ri: int, u0: float, u1: float) -> float:
	var pts := _stretch(ri, u0, u1)
	var n := 0.0
	for i in pts.size() - 1:
		n += dist(pts[i], pts[i + 1])
	return n


static func _edge_pts(ei: int, from_node: int) -> PackedVector2Array:
	var e: Array = _paths.edges[ei]
	var fwd := int(e[0]) == from_node
	if int(e[2]) < 0:                                            # a bridge deck: straight
		var n0: Array = _paths.nodes[int(e[0])]
		var n1: Array = _paths.nodes[int(e[1])]
		var a := Vector2(float(n0[0]), float(n0[1]))
		var b := Vector2(float(n1[0]), float(n1[1]))
		return PackedVector2Array([a, b] if fwd else [b, a])
	return _stretch(int(e[2]), float(e[3]), float(e[4])) if fwd else _stretch(int(e[2]), float(e[4]), float(e[3]))


static func _heap_push(h: Array, item: Array) -> void:
	h.append(item)
	var i := h.size() - 1
	while i > 0:
		var p := (i - 1) >> 1
		if float(h[p][0]) <= float(item[0]):
			break
		h[i] = h[p]
		i = p
	h[i] = item


static func _heap_pop(h: Array) -> Array:
	var top: Array = h[0]
	var last: Array = h.pop_back()
	if h.is_empty():
		return top
	var i := 0
	var n := h.size()
	while true:
		var c := 2 * i + 1
		if c >= n:
			break
		if c + 1 < n and float(h[c + 1][0]) < float(h[c][0]):
			c += 1
		if float(h[c][0]) >= float(last[0]):
			break
		h[i] = h[c]
		i = c
	h[i] = last
	return top


static var _routes := {}         # "from>to" -> route (the same trips recur every day)


const BIKE_EDGE := -0.9          # cyclists ride inside the road, this far from its edge


static func route(from_b: String, to_b: String, from_door := Vector2.INF, to_door := Vector2.INF, edge := PAVEMENT, classes: Array = [], via_cls: Array = [], ahead_of := Vector2.INF) -> PackedVector2Array:
	## Door to door along the streets, on the right-hand side: the pavement (edge = PAVEMENT beyond the
	## road's edge) or, for cyclists, the road itself (edge = BIKE_EDGE). Straight across if either
	## door has no street within reach, or the network doesn't join them. classes: joined at the nearest
	## road of these terrain classes and kept to them and the `via_cls` classes (trams: stops on streets,
	## along gravel roads too, never alleys).
	## ahead_of: set off away from this point (a vehicle that doesn't turn round where it stands).
	var key := "%s>%s>%.1f>%s>%s>%s" % [from_b, to_b, edge, ",".join(classes), ",".join(via_cls), str(ahead_of)]
	if from_door == Vector2.INF and to_door == Vector2.INF and _routes.has(key):
		return _routes[key]
	var r := _route(from_b, to_b, from_door, to_door, edge, classes, via_cls, ahead_of)
	if from_door == Vector2.INF and to_door == Vector2.INF:
		if _routes.size() > 512:
			_routes.clear()
		_routes[key] = r
	return r


static func _attach_on(p: Vector2, classes: Array) -> Array:
	## [edge, u] of the nearest point to p on a road of one of these classes.
	var key := "%.1f,%.1f>%s" % [p.x, p.y, ",".join(classes)]
	if _attach_cache.has(key):
		return _attach_cache[key]
	var best := INF
	var out: Array = []
	var edges: Array = _paths.edges
	for ei in edges.size():
		var e: Array = edges[ei]
		var ri := int(e[2])
		if ri < 0 or not classes.has(_edge_cls[ei]):
			continue
		var n0: Array = _paths.nodes[int(e[0])]
		if dist(p, Vector2(float(n0[0]), float(n0[1]))) - float(e[5]) > best:
			continue                                # no point of this edge can be nearer
		var u0 := float(e[3])
		var u1 := float(e[4])
		var k := floori(u0)
		while float(k) < u1:
			var ua := maxf(u0, float(k))
			var ub := minf(u1, float(k + 1))
			var a := _at(ri, ua)
			var b := _at(ri, ub)
			var ab := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)
			var ap := Vector2(StationGeo.wrap_ds(p.x - a.x), p.y - a.y)
			var t := clampf(ap.dot(ab) / maxf(ab.length_squared(), 1e-6), 0.0, 1.0)
			var dd := (ap - ab * t).length()
			if dd < best:
				best = dd
				out = [ei, ua + (ub - ua) * t]
			k += 1
	_attach_cache[key] = out
	return out


static func _route(from_b: String, to_b: String, from_door: Vector2, to_door: Vector2, edge := PAVEMENT, classes: Array = [], via_cls: Array = [], ahead_of := Vector2.INF) -> PackedVector2Array:
	load_all()
	var d0 := from_door if from_door != Vector2.INF else door_of(from_b)
	var d1 := to_door if to_door != Vector2.INF else door_of(to_b)
	var a0: Array = _paths.attach.get(from_b.split("/")[0], [])
	var a1: Array = _paths.attach.get(to_b.split("/")[0], [])
	if not classes.is_empty() and d0 != Vector2.INF and d1 != Vector2.INF:
		a0 = _attach_on(d0, classes)
		a1 = _attach_on(d1, classes)
	if a0.is_empty() or a1.is_empty() or d0 == Vector2.INF or d1 == Vector2.INF:
		return PackedVector2Array([d0, d1])
	var e0: Array = _paths.edges[int(a0[0])]
	var e1: Array = _paths.edges[int(a1[0])]
	var centre := PackedVector2Array()
	var same := int(a0[0]) == int(a1[0])
	if same and ahead_of != Vector2.INF and int(e0[2]) >= 0:
		# a vehicle only takes the direct stretch if it lies ahead; behind it, it goes round
		var here := _at(int(e0[2]), float(a0[1]))
		var there := _at(int(e0[2]), float(a1[1]))
		var fwd := Vector2(StationGeo.wrap_ds(here.x - ahead_of.x), here.y - ahead_of.y)
		same = Vector2(StationGeo.wrap_ds(there.x - here.x), there.y - here.y).dot(fwd) >= 0.0
	if same:
		centre = _stretch(int(e0[2]), float(a0[1]), float(a1[1]))
	else:
		# Dijkstra from both ends of the start edge (costs: along the edge to each end)
		var n := _adj.size()
		var best := PackedFloat64Array()
		best.resize(n)
		best.fill(INF)
		var prev := PackedInt32Array()
		prev.resize(n)
		prev.fill(-1)
		var via := PackedInt32Array()
		via.resize(n)
		via.fill(-1)
		var h := []
		var found := -1
		# a vehicle (ahead_of set) first looks for a way that never doubles back at a junction; only a
		# dead end makes it turn there
		for no_u in ([true, false] if ahead_of != Vector2.INF else [false]):
			best.fill(INF)
			prev.fill(-1)
			via.fill(-1)
			h.clear()
			var ends := [0, 1]
			if ahead_of != Vector2.INF and int(e0[2]) >= 0:     # only the end of the start edge ahead
				var here := _at(int(e0[2]), float(a0[1]))
				var t0 := _at(int(e0[2]), float(e0[3]))
				var t1 := _at(int(e0[2]), float(e0[4]))
				var fwd := Vector2(StationGeo.wrap_ds(here.x - ahead_of.x), here.y - ahead_of.y)
				var g0 := Vector2(StationGeo.wrap_ds(t0.x - here.x), t0.y - here.y)
				var g1 := Vector2(StationGeo.wrap_ds(t1.x - here.x), t1.y - here.y)
				ends = [0] if g0.dot(fwd) > g1.dot(fwd) else [1]
			for end in ends:
				var node := int(e0[end])
				var c := _stretch_len(int(e0[2]), float(a0[1]), float(e0[3 + end]))
				if c < best[node]:
					best[node] = c
					via[node] = int(a0[0])              # arrived along the start edge
					_heap_push(h, [c, node])
			var goal := {int(e1[0]): _stretch_len(int(e1[2]), float(e1[3]), float(a1[1])), int(e1[1]): _stretch_len(int(e1[2]), float(e1[4]), float(a1[1]))}
			found = -1
			var found_cost := INF
			while not h.is_empty():
				var top := _heap_pop(h)
				var c: float = top[0]
				var node: int = top[1]
				if c > best[node] or c >= found_cost:
					continue
				# (not having come along the goal's own edge: that would double back to reach it)
				if goal.has(node) and c + float(goal[node]) < found_cost and not (no_u and via[node] == int(a1[0])):
					found_cost = c + float(goal[node])
					found = node
				for adj in _adj[node]:
					if no_u and int(adj[0]) == via[node]:  # no turning back the way it came
						continue
					if not classes.is_empty():
						var ec := _edge_cls[int(adj[0])]
						if ec != "" and not classes.has(ec) and not via_cls.has(ec):
							continue
					var nc: float = c + float(adj[2])
					if nc < best[int(adj[1])]:
						best[int(adj[1])] = nc
						prev[int(adj[1])] = node
						via[int(adj[1])] = int(adj[0])
						_heap_push(h, [nc, int(adj[1])])
			if found >= 0:
				break
		if found < 0:
			return PackedVector2Array([d0, d1])
		var chain: Array = []                                    # [edge, from node] back to the start
		var at := found
		while prev[at] >= 0:
			chain.push_front([via[at], prev[at]])
			at = prev[at]
		centre = _stretch(int(e0[2]), float(a0[1]), float(e0[3] if at == int(e0[0]) else e0[4]))
		for step in chain:
			var pts := _edge_pts(int(step[0]), int(step[1]))
			for i in range(1, pts.size()):
				centre.append(pts[i])
		var tail := _stretch(int(e1[2]), float(e1[3] if found == int(e1[0]) else e1[4]), float(a1[1]))
		for i in range(1, tail.size()):
			centre.append(tail[i])
	# the pavement: offset to the right of the way of travel by half the road and a step
	var out := PackedVector2Array([d0])
	var w0 := float(_road(int(e0[2])).w) * 0.5 + edge
	for i in centre.size():
		var a := centre[maxi(i - 1, 0)]
		var b := centre[mini(i + 1, centre.size() - 1)]
		var t := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)
		if t.length() < 0.01:
			continue
		t = t.normalized()
		var right := Vector2(-t.y, t.x)          # (s, x) axes: facing +s, +x is to the right
		var p := centre[i] + right * w0
		if out.size() > 0 and dist(out[out.size() - 1], p) < 0.5:
			continue
		out.append(Vector2(fposmod(p.x, StationGeo.CIRC), p.y))
	out.append(d1)
	return out


static func route_length(pts: PackedVector2Array) -> float:
	var n := 0.0
	for i in pts.size() - 1:
		n += dist(pts[i], pts[i + 1])
	return n
