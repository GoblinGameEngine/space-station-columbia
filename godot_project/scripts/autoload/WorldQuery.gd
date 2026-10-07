extends RefCounted
class_name WorldQuery

## Where things are in the running game, as text -- no rendering (the user, 2026-10-06: "tools for you to know
## precisely where models are without having to render it visually ... very quickly do checks without necessarily
## looking at my output"). DevBridge {"cmd": "query", "op": ...}; tools/gcmd.py query OP ...
##
## Every answer is one thing a line, in map terms: s (m round the ring), x (m along the axis, - is north), h (m up
## from the sea-level datum), agl (m above the ground there), bearing (compass degrees from the camera, 0 = north).
## The things: structures (placement ids), parked vehicles (aerostats, ground vehicles, bicycles), traffic,
## transit, people, the player. Each with its drawn bounds (the geometry actually showing) and its state.
##
##   near S X [R] [CATS]   what is within R m (default 60) of (S, X), nearest first; CATS: structure,vehicle,traffic,transit,npc
##   find TEXT             where everything whose id/kind contains TEXT is (up to 40)
##   ground S X            the ground there: height, water, land cover, area, the road under or nearest, the town
##   view [N]              what the camera sees: its pose, then the N biggest things on screen with their screen boxes,
##                         distance and whether a ray says they're hidden behind something; what's at the centre
##   check S X [R]         problems within R m (default 150): buildings floating / buried / on a road / in water /
##                         overlapping; vehicles and people floating, sunk, or inside a building's footprint
##   here                  the player and the camera, where they are

const CATS := ["structure", "vehicle", "traffic", "transit", "npc", "player"]
static var _pl := {}                      # placement id -> record
static var _road_grid := {}               # Vector2i(s cell, x cell) -> [[a, b, half width, name, cls]]
const RCELL := 50.0


static func run(op: String, a: Dictionary) -> String:
	var args: Array = a.get("args", [])
	match op:
		"near":
			return near(_f(args, 0), _f(args, 1), _f(args, 2, 60.0), _cats(args, 3))
		"find":
			return find(str(args[0]) if args.size() > 0 else "")
		"ground":
			return ground(_f(args, 0), _f(args, 1))
		"view":
			return view(int(_f(args, 0, 25.0)))
		"check":
			return check(_f(args, 0), _f(args, 1), _f(args, 2, 150.0))
		"here":
			return here()
	return "unknown op '%s': near, find, ground, view, check, here" % op


static func _f(args: Array, i: int, dflt := 0.0) -> float:
	return float(args[i]) if args.size() > i and str(args[i]) != "" else dflt


static func _cats(args: Array, i: int) -> Array:
	if args.size() <= i or str(args[i]) == "":
		return CATS
	return str(args[i]).split(",")


static func _sc() -> Node:
	return (Engine.get_main_loop() as SceneTree).current_scene


static func _cam() -> Camera3D:
	return (Engine.get_main_loop() as SceneTree).root.get_viewport().get_camera_3d()


# ------------------------------------------------------------------ the things
static func _placement() -> Dictionary:
	if _pl.is_empty() and FileAccess.file_exists("res://remake/placement.json"):
		for e in JSON.parse_string(FileAccess.get_file_as_string("res://remake/placement.json")).structures:
			_pl[str(e.id)] = e
	return _pl


static func entities(cats: Array = CATS, s0 := NAN, x0 := NAN, r := INF) -> Array:
	## [{id, cat, kind, node (null if only a record), pos (Vector3), state}] -- within r of (s0, x0) if given
	var sc := _sc()
	var out := []
	var keep := func(p: Vector3) -> bool:
		return is_nan(s0) or Vector2(StationGeo.wrap_ds(StationGeo.s_of(p) - s0), p.x - x0).length() <= r
	if "structure" in cats and sc.get("streamer") != null:
		var st = sc.streamer
		var pl := _placement()
		for i in st.records.size():
			var rec: Dictionary = st.records[i]
			var root: Node3D = rec.root
			if not is_instance_valid(root) or not keep.call(root.global_position):
				continue
			var p: Dictionary = pl.get(str(rec.id), {})
			var state := "full" if st._loaded.has(i) else "lod1"
			if not root.visible:
				state = "far-side image"
			if rec.get("landmark", false):
				state += ", landmark"
			out.append({"id": str(rec.id), "cat": "structure", "kind": "%s %s" % [p.get("kind", "?"), str(p.get("settlement", ""))],
				"node": root, "pos": root.global_position, "state": state, "rec": p})
	if "vehicle" in cats:
		for nm in ["Aerostats", "GroundVehicles", "Bicycles"]:
			var vs = sc.get_node_or_null(nm)
			if vs == null:
				continue
			for rec in vs.records:
				var n = rec.node
				var pos: Vector3 = (n as Node3D).global_position if n != null and is_instance_valid(n) else (rec.xf as Transform3D).origin
				if not keep.call(pos):
					continue
				var state := "built" if n != null and is_instance_valid(n) else "record only (not built: far)"
				if n != null and is_instance_valid(n) and n.get("pilot") != null:
					state += ", piloted"
				out.append({"id": str(rec.id), "cat": "vehicle", "kind": nm.to_lower().trim_suffix("s"), "node": n if n != null and is_instance_valid(n) else null,
					"pos": pos, "state": state})
	if "traffic" in cats:
		var t = sc.get_node_or_null("NpcTraffic")
		if t != null:
			for id in t.live:
				var e: Dictionary = t.live[id]
				var n: Node3D = e.node
				if not is_instance_valid(n) or not keep.call(n.global_position):
					continue
				var state := "driving" if e.sim != null else ("moving" if e.get("moving", false) else "parked")
				state += ", " + ("no model" if e.model == null else ("merged far mesh" if e.get("lite", false) else "full model"))
				out.append({"id": str(id), "cat": "traffic", "kind": str(e.v.get("type", "car")), "node": n, "pos": n.global_position, "state": state})
	if "transit" in cats:
		var ts = sc.get_node_or_null("TransitSystem")
		if ts != null:
			for k in ts.live:
				var v: Node3D = ts.live[k]
				if is_instance_valid(v) and keep.call(v.global_position):
					out.append({"id": str(k), "cat": "transit", "kind": str(v.line.get("kind", "tram")) if v.get("line") else "tram",
						"node": v, "pos": v.global_position, "state": "%d riders" % (v.riders as Array).size() if v.get("riders") != null else ""})
	if "npc" in cats:
		var pop = sc.get_node_or_null("NpcPopulation")
		if pop != null:
			for pid in pop.live:
				var e: Dictionary = pop.live[pid]
				var n = e.get("npc")
				if n != null and is_instance_valid(n) and keep.call((n as Node3D).global_position):
					out.append({"id": str(pid), "cat": "npc", "kind": "person", "node": n, "pos": (n as Node3D).global_position, "state": ""})
	if "player" in cats and sc.get("player") != null:
		var pn: Node3D = sc.player
		if keep.call(pn.global_position):
			out.append({"id": "player", "cat": "player", "kind": "player", "node": pn, "pos": pn.global_position, "state": ""})
	return out


static func bounds(n: Node, cam_pos := Vector3.INF) -> Dictionary:
	## The geometry showing under n: {ok, h0, h1 (height range), s0, s1, x0, x1, centre, size, parts, drawn}
	## (drawn: parts within their visibility ranges of cam_pos)
	var out := {"ok": false, "parts": 0, "drawn": 0}
	if n == null:
		return out
	var lo := Vector3(INF, INF, INF)
	var hi := Vector3(-INF, -INF, -INF)
	var ref_s := StationGeo.s_of((n as Node3D).global_position)
	var corners := PackedVector3Array()
	var first := true
	var gs: Array = (n as Node).find_children("*", "GeometryInstance3D", true, false)
	if n is GeometryInstance3D:
		gs.append(n)
	for g in gs:
		var gi := g as GeometryInstance3D
		if not gi.is_visible_in_tree():
			continue
		var lab := gi.get_aabb()
		if lab.size == Vector3.ZERO:
			continue
		out.parts += 1
		var gx := gi.global_transform
		var d := (gx * lab.get_center()).distance_to(cam_pos) if cam_pos != Vector3.INF else 0.0
		if (gi.visibility_range_end <= 0.0 or d <= gi.visibility_range_end) and d >= gi.visibility_range_begin:
			out.drawn += 1
		first = false
		for k in 8:
			var c := gx * lab.get_endpoint(k)          # (its own box's corners: the ring's tilt makes a world box too tall)
			corners.append(c)
			var cs := ref_s + StationGeo.wrap_ds(StationGeo.s_of(c) - ref_s)
			var v := Vector3(cs, c.x, StationGeo.h_of(c))
			lo = lo.min(v)
			hi = hi.max(v)
	if first:
		return out
	out.ok = true
	out.s0 = lo.x
	out.s1 = hi.x
	out.x0 = lo.y
	out.x1 = hi.y
	out.h0 = lo.z
	out.h1 = hi.z
	var cen := Vector3.ZERO
	for c in corners:
		cen += c
	cen /= corners.size()
	var rad := 0.0
	for c in corners:
		rad = maxf(rad, c.distance_to(cen))
	out.corners = corners
	out.centre = cen
	out.radius = rad
	return out


# ------------------------------------------------------------------ the answers
static func _bearing(from: Vector3, to: Vector3) -> float:
	var sf := StationGeo.s_of(from)
	var ds := StationGeo.wrap_ds(StationGeo.s_of(to) - sf)
	var dx := to.x - from.x
	return fposmod(rad_to_deg(atan2(ds, -dx)), 360.0)            # north (-x) 0, east (+s) 90


static func _line(e: Dictionary, from: Vector3, cam_pos: Vector3) -> String:
	var p: Vector3 = e.pos
	var s := StationGeo.s_of(p)
	var g := MapTerrain.elevation(s, p.x)
	var b := bounds(e.node, cam_pos)
	var txt := "%-9s %-26s %-24s s %8.1f x %8.1f h %6.1f agl %5.1f" % [e.cat, str(e.id).left(26), str(e.kind).left(24), s, p.x, StationGeo.h_of(p), StationGeo.h_of(p) - g]
	if from != Vector3.INF:
		txt += "  %5.0f m @%3.0f deg" % [Vector2(StationGeo.wrap_ds(s - StationGeo.s_of(from)), p.x - from.x).length(), _bearing(from, p)]
	if b.ok:
		txt += "  | drawn h %.1f..%.1f (agl %.1f..%.1f) s %.1f..%.1f x %.1f..%.1f, %d/%d parts drawn" % [b.h0, b.h1, b.h0 - g, b.h1 - g,
			b.s0, b.s1, b.x0, b.x1, b.drawn, b.parts]
	elif e.node == null:
		txt += "  | (no node)"
	else:
		txt += "  | nothing drawn"
	if str(e.state) != "":
		txt += "  [" + str(e.state) + "]"
	return txt


static func near(s: float, x: float, r: float, cats: Array) -> String:
	var es := entities(cats, s, x, r)
	var c := StationGeo.point(s, x, MapTerrain.elevation(s, x))
	es.sort_custom(func(a, b): return (a.pos as Vector3).distance_to(c) < (b.pos as Vector3).distance_to(c))
	var cam := _cam()
	var cp := cam.global_position if cam else Vector3.INF
	var lines := ["%d things within %.0f m of s %.1f x %.1f (ground h %.1f); distance/bearing from there:" % [es.size(), r, s, x, MapTerrain.elevation(s, x)]]
	for e in es.slice(0, 120):
		lines.append(_line(e, c, cp))
	if es.size() > 120:
		lines.append("... %d more" % (es.size() - 120))
	return "\n".join(lines)


static func find(text: String) -> String:
	var t := text.to_lower()
	var cam := _cam()
	var cp := cam.global_position if cam else Vector3.INF
	var lines := []
	for e in entities():
		if t in str(e.id).to_lower() or t in str(e.kind).to_lower():
			lines.append(_line(e, cp, cp))
			if lines.size() >= 40:
				lines.append("(first 40)")
				break
	# not in the scene: the placement record
	if lines.is_empty():
		for id in _placement():
			if t in id.to_lower():
				var p: Dictionary = _pl[id]
				lines.append("structure %s (%s %s) s %.1f x %.1f yaw %.2f -- placed, not in the scene" % [id, p.kind, str(p.get("settlement", "")), p.s, p.x, p.yaw])
				if lines.size() >= 40:
					break
	return "\n".join(lines) if not lines.is_empty() else "nothing matches '%s'" % text


static func _roads_near(s: float, x: float) -> Array:
	## [[distance from the centreline, half width, name, cls]] of the road segments within RCELL
	MapTerrain._load()
	if _road_grid.is_empty():
		for rd in MapTerrain._d.roads:
			var pts: Array = rd.pts
			var hw := maxf(float(rd.get("hl", float(rd.get("w", 6.0)) / 2.0)), float(rd.get("hr", float(rd.get("w", 6.0)) / 2.0)))
			for k in pts.size() - 1:
				var a := Vector2(float(pts[k][0]), float(pts[k][1]))
				var b := Vector2(float(pts[k + 1][0]), float(pts[k + 1][1]))
				var cell := Vector2i(floori(fposmod(a.x, StationGeo.CIRC) / RCELL), floori(a.y / RCELL))
				for di in [-1, 0, 1]:
					for dj in [-1, 0, 1]:
						var key := cell + Vector2i(di, dj)
						if not _road_grid.has(key):
							_road_grid[key] = []
						_road_grid[key].append([a, b, hw, str(rd.get("name", "")), str(rd.get("cls", ""))])
	var out := []
	var key := Vector2i(floori(fposmod(s, StationGeo.CIRC) / RCELL), floori(x / RCELL))
	for sg in _road_grid.get(key, []):
		var a: Vector2 = sg[0]
		var b: Vector2 = sg[1]
		var bs := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)
		var ps := Vector2(StationGeo.wrap_ds(s - a.x), x - a.y)
		var tt := clampf(ps.dot(bs) / maxf(bs.length_squared(), 1e-6), 0.0, 1.0)
		out.append([(ps - bs * tt).length(), sg[2], sg[3], sg[4]])
	out.sort_custom(func(p, q): return p[0] < q[0])
	return out


const LC := ["grass", "built-up", "meadow", "woods", "field", "grove", "beach", "rock"]


static func ground(s: float, x: float) -> String:
	var smp := MapTerrain.sample(s, x)
	var w := MapTerrain.water_at(s, x)
	var lc := MapTerrain.landcover(s, x)
	var lines := ["ground at s %.1f x %.1f: h %.2f (carved %.2f)" % [s, x, smp.x, smp.y]]
	if w.x > -9000.0:
		lines.append("water: level %.2f, %s" % [w.x, ("%.2f m deep here" % (w.x - smp.x)) if w.x > smp.x else "dry (above the level)"])
	lines.append("land cover: %s%s; area: %s" % [LC[clampi(lc.x, 0, LC.size() - 1)], (" (crop %d)" % lc.y) if lc.x == 4 else "",
		MapTerrain.area_kind(s, x) if MapTerrain.area_kind(s, x) != "" else "-"])
	var rs := _roads_near(s, x)
	if rs.is_empty():
		lines.append("road: none within %.0f m" % RCELL)
	else:
		var r0: Array = rs[0]
		lines.append("road: %s %s, %.1f m from its centreline (half width %.1f) -- %s" % [r0[3], r0[2] if r0[2] != "" else "(unnamed)", r0[0], r0[1],
			"ON it" if r0[0] <= r0[1] else "off it by %.1f m" % (r0[0] - r0[1])])
	var best := ""
	var bd := INF
	for id in _placement():
		var p: Dictionary = _pl[id]
		var d := Vector2(StationGeo.wrap_ds(float(p.s) - s), float(p.x) - x).length()
		if d < bd:
			bd = d
			best = "%s (%s, %s)" % [id, p.kind, str(p.get("settlement", ""))]
	lines.append("nearest structure: %s, %.0f m" % [best, bd])
	return "\n".join(lines)


static func here() -> String:
	var sc := _sc()
	var lines := []
	if sc.get("player") != null:
		var p: Vector3 = sc.player.global_position
		var s := StationGeo.s_of(p)
		lines.append("player: s %.1f x %.1f h %.1f agl %.1f" % [s, p.x, StationGeo.h_of(p), StationGeo.h_of(p) - MapTerrain.elevation(s, p.x)])
	var cam := _cam()
	if cam:
		var c := cam.global_position
		var s := StationGeo.s_of(c)
		var f := -cam.global_transform.basis.z
		var up := StationGeo.up(s)
		var pitch := rad_to_deg(asin(clampf(f.dot(up), -1.0, 1.0)))
		lines.append("camera %s: s %.1f x %.1f h %.1f agl %.1f, heading %.0f deg, pitch %.0f deg, fov %.0f" % [cam.name, s, c.x, StationGeo.h_of(c),
			StationGeo.h_of(c) - MapTerrain.elevation(s, c.x), _bearing(c, c + f * 10.0), pitch, cam.fov])
	var sky = sc.get_node_or_null("DaySkySystem")
	if sky:
		lines.append("time of day %.3f (%02d:%02d)" % [sky.time_of_day, int(sky.time_of_day * 24.0), int(fmod(sky.time_of_day * 1440.0, 60.0))])
	return "\n".join(lines)


static func _owner_of(n: Node) -> String:
	## the thing a collider belongs to: its ancestor just under a known container (or the scene)
	var sc := _sc()
	var p := n
	while p != null and p.get_parent() != null:
		var par := p.get_parent()
		if par == sc or str(par.name) in ["World", "NpcTraffic", "TransitSystem", "Aerostats", "GroundVehicles", "Bicycles", "NpcPopulation", "Terrain", "Walks", "GreatBridges", "RoadFurniture"]:
			return "%s/%s" % [par.name, p.name]
		p = par
	return str(n.name)


static func view(n: int) -> String:
	var cam := _cam()
	if cam == null:
		return "no camera"
	var vp := cam.get_viewport()
	var vs := vp.get_visible_rect().size
	var cp := cam.global_position
	var space := cam.get_world_3d().direct_space_state
	var rows := []
	for e in entities(CATS, StationGeo.s_of(cp), cp.x, 1600.0):
		if e.node != null and (e.node == cam or (e.node as Node).is_ancestor_of(cam)):
			continue                                  # (the camera's own body: a first-person view is inside it)
		var b := bounds(e.node, cp)
		if not b.ok or b.drawn == 0:
			continue
		var lo := Vector2(INF, INF)
		var hi := Vector2(-INF, -INF)
		var any := false
		for c in b.corners:
			if cam.is_position_behind(c):
				continue
			var q := cam.unproject_position(c)
			lo = lo.min(q)
			hi = hi.max(q)
			any = true
		if not any:
			continue
		lo = lo.clamp(Vector2.ZERO, vs)
		hi = hi.clamp(Vector2.ZERO, vs)
		var area := (hi.x - lo.x) * (hi.y - lo.y)
		if area < 4.0:
			continue
		var centre: Vector3 = b.centre
		var dist := cp.distance_to(centre)
		var hid := ""
		var hit := space.intersect_ray(PhysicsRayQueryParameters3D.create(cp, centre))
		if not hit.is_empty() and cp.distance_to(hit.position) < dist - float(b.radius):
			var who := _owner_of(hit.collider)
			if not who.ends_with("/" + str(e.id)):
				hid = "  (centre hidden behind %s)" % who
		rows.append([area, "%-9s %-26s %-22s screen %4.0f,%4.0f..%4.0f,%4.0f (%4.1f%% of it)  %6.0f m%s" % [e.cat, str(e.id).left(26), str(e.kind).left(22),
			lo.x, lo.y, hi.x, hi.y, 100.0 * area / (vs.x * vs.y), dist, hid]])
	rows.sort_custom(func(a, b): return a[0] > b[0])
	var lines := [here(), "screen %dx%d; the biggest things in view (box = their drawn bounds' projection):" % [vs.x, vs.y]]
	for r in rows.slice(0, n):
		lines.append(r[1])
	# the centre of the screen: what a ray from it hits first
	var o := cam.project_ray_origin(vs * 0.5)
	var d := cam.project_ray_normal(vs * 0.5)
	var hc := space.intersect_ray(PhysicsRayQueryParameters3D.create(o, o + d * 5000.0))
	if hc.is_empty():
		lines.append("screen centre: no collider within 5 km (sky, or terrain not yet solid there)")
	else:
		var hp: Vector3 = hc.position
		lines.append("screen centre hits %s at s %.1f x %.1f h %.1f, %.0f m away" % [_owner_of(hc.collider), StationGeo.s_of(hp), hp.x, StationGeo.h_of(hp), o.distance_to(hp)])
	return "\n".join(lines)


# ------------------------------------------------------------------ problems
static func _footprint(p: Dictionary) -> PackedVector2Array:
	## a structure's footprint corners in (s, x), from its placement record (fmin / fmax in its own frame)
	var c := cos(float(p.yaw))
	var sn := sin(float(p.yaw))
	var fmin: Array = p.get("fmin", p.get("min", [0, 0, 0]))
	var fmax: Array = p.get("fmax", p.get("max", [0, 0, 0]))
	var zi := 1 if fmin.size() == 2 else 2
	var out := PackedVector2Array()
	for lc in [[fmin[0], fmin[zi]], [fmax[0], fmin[zi]], [fmax[0], fmax[zi]], [fmin[0], fmax[zi]]]:
		var lx := float(lc[0])
		var lz := float(lc[1])
		out.append(Vector2(float(p.s) + lx * sn - lz * c, float(p.x) + lx * c + lz * sn))
	return out


static func _shrunk(poly: PackedVector2Array, by: float) -> PackedVector2Array:
	## the footprint pulled in by `by` m (row buildings share a wall: touching isn't overlapping)
	var ref := poly[0].x
	var c := Vector2.ZERO
	var pl := PackedVector2Array()
	for v in poly:
		var q := Vector2(ref + StationGeo.wrap_ds(v.x - ref), v.y)
		pl.append(q)
		c += q
	c /= pl.size()
	for i in pl.size():
		var d := pl[i] - c
		pl[i] = c + d * maxf(0.0, 1.0 - by / maxf(d.length(), 0.01))
	return pl


static func _in_poly(q: Vector2, poly: PackedVector2Array) -> bool:
	var ref := poly[0].x
	var pl := PackedVector2Array()
	for v in poly:
		pl.append(Vector2(ref + StationGeo.wrap_ds(v.x - ref), v.y))
	return Geometry2D.is_point_in_polygon(Vector2(ref + StationGeo.wrap_ds(q.x - ref), q.y), pl)


static func check(s: float, x: float, r: float) -> String:
	var cam := _cam()
	var cp := cam.global_position if cam else Vector3.INF
	var es := entities(CATS, s, x, r)
	var issues := []
	var foot := []                                   # [id, polygon] of the structures here
	var n_struct := 0
	for e in es:
		if e.cat != "structure":
			continue
		n_struct += 1
		var p: Dictionary = e.rec
		if p.is_empty() or str(p.get("kind", "")) == "crossing":
			continue
		var fp := _footprint(p)
		foot.append([e.id, fp])
		var gmin := INF
		var gmax := -INF
		var wet := 0
		var on_road := ""
		for q in fp:
			var g := MapTerrain.elevation(q.x, q.y)
			gmin = minf(gmin, g)
			gmax = maxf(gmax, g)
			if MapTerrain.water_at(q.x, q.y).x > g + 0.05:
				wet += 1
			var rs := _roads_near(q.x, q.y)
			if not rs.is_empty() and rs[0][0] < float(rs[0][1]) - 0.3 and on_road == "":
				on_road = "%s %s" % [rs[0][3], rs[0][2]]
		var b := bounds(e.node, cp)
		if b.ok:
			if b.h0 > gmin + 0.3:
				issues.append("FLOATING  structure %s (%s): its lowest drawn point h %.2f is %.2f m above the lowest ground under it (%.2f)" % [e.id, e.kind, b.h0, b.h0 - gmin, gmin])
			if b.h1 < gmax + 1.0:
				issues.append("BURIED    structure %s (%s): its top h %.2f is under / at the ground (%.2f)" % [e.id, e.kind, b.h1, gmax])
		if wet > 0:
			issues.append("IN WATER  structure %s (%s): %d of its 4 corners are under water" % [e.id, e.kind, wet])
		if on_road != "":
			issues.append("ON ROAD   structure %s (%s): a corner is on %s" % [e.id, e.kind, on_road])
	# overlapping footprints (corners inside another's)
	for i in foot.size():
		for j in range(i + 1, foot.size()):
			var a: PackedVector2Array = _shrunk(foot[i][1], 1.0)    # (1 m: drawn bounds take in cornices, awnings, stoops)
			var bpoly: PackedVector2Array = _shrunk(foot[j][1], 1.0)
			if absf(StationGeo.wrap_ds(a[0].x - bpoly[0].x)) > 300.0:
				continue
			var hit := false
			for q in a:
				if _in_poly(q, bpoly):
					hit = true
					break
			if not hit:
				for q in bpoly:
					if _in_poly(q, a):
						hit = true
						break
			if hit:
				issues.append("OVERLAP   structures %s and %s: their footprints overlap" % [foot[i][0], foot[j][0]])
	# things that stand on the ground: their lowest drawn point against it, and not inside a building
	for e in es:
		if e.cat in ["structure", "transit"] or e.node == null:
			continue
		var b := bounds(e.node, cp)
		if not b.ok:
			continue
		var pos: Vector3 = e.pos
		var ps := StationGeo.s_of(pos)
		var g := MapTerrain.elevation(ps, pos.x)
		var flying: bool = e.cat == "vehicle" and "aerostat" in str(e.kind) and b.h0 - g > 3.0
		var parked_or_still: bool = e.cat != "traffic" or "parked" in str(e.state)
		if not flying and b.h0 - g > 0.6 and parked_or_still:
			issues.append("FLOATING  %s %s (%s): lowest drawn point %.2f m above the ground" % [e.cat, e.id, e.kind, b.h0 - g])
		if b.h0 - g < -0.5 and e.cat != "npc":
			issues.append("SUNK      %s %s (%s): lowest drawn point %.2f m below the ground" % [e.cat, e.id, e.kind, g - b.h0])
		if e.cat == "npc" and absf(StationGeo.h_of(pos) - g) > 0.5:
			issues.append("%s npc %s: feet %.2f m %s the ground" % ["FLOATING " if StationGeo.h_of(pos) > g else "SUNK     ", e.id,
				absf(StationGeo.h_of(pos) - g), "above" if StationGeo.h_of(pos) > g else "below"])
		for f in foot:
			if _in_poly(Vector2(ps, pos.x), f[1]):
				issues.append("INSIDE    %s %s (%s) stands inside structure %s's footprint" % [e.cat, e.id, e.kind, f[0]])
				break
	# vehicles standing in one another (two parked in one bay, a car in a bus)
	var vs := []
	for e in es:
		if e.cat in ["traffic", "vehicle"] and e.node != null:
			vs.append(e)
	for i in vs.size():
		for j in range(i + 1, vs.size()):
			var pa: Vector3 = vs[i].pos
			var pb: Vector3 = vs[j].pos
			var d := pa.distance_to(pb)
			if d < 1.5:
				issues.append("STACKED   %s %s (%s) and %s %s (%s): %.2f m apart" % [vs[i].cat, vs[i].id, vs[i].kind, vs[j].cat, vs[j].id, vs[j].kind, d])
	var head := "checked %d things (%d structures) within %.0f m of s %.1f x %.1f: %d problems" % [es.size(), n_struct, r, s, x, issues.size()]
	return head + ("\n" + "\n".join(issues) if not issues.is_empty() else "")
