extends Node3D
class_name MapRoads

## The map's roads, streets and railway (remake/terrain.json, from tools/map_expanded.py), surfaced
## on the graded terrain (MapTerrain grades the ground flat across each road at its centreline).
## Each road is a ribbon of its map width sampled every STEP m, LIFT above the ground; spans over
## the river / lake are left out (the crossings' bridges carry the road there).  Ribbons are merged
## per CELL m cell and surface -- asphalt (highways, county roads, main streets, streets), gravel,
## concrete (alleys), ballast (the railway) -- one mesh each.  The ribbons are built on a worker
## thread; the main thread only makes the mesh nodes, a few a frame.
##
## The road standard (research/roads/SSC_ROAD_STANDARD.md) through remake/road_furniture.json
## (tools/road_furniture.py): each road's context per point (rural / town / core) and junction flags
##   town / core   a concrete gutter pan and a 150 mm barrier curb along both edges (paved roads)
##   rural         soft gravel shoulders, falling away over their outer half
##   markings      the painted lines (centre, edge, parking), stop lines, crosswalks, RXR decals
## and the turning circles where a road ends (terrain.json turns).

const STEP := 3.0
const LIFT := 0.06
const PAINT := 0.03                 # paint over the road surface
const CELL := 400.0
const FAR := 1800.0                  # past this a road is under a pixel wide
const PAINT_FAR := 320.0
const KERB_FAR := 700.0
const SURFACE := {"hwy": "asphalt", "county": "asphalt", "main": "asphalt", "street": "asphalt",
	"gravel": "gravel", "alley": "concrete", "rail": "ballast"}
const TEX := {"asphalt": ["lib/asphalt", 6.0], "gravel": ["p-site/gravel_road", 6.0],
	"concrete": ["lib/concrete", 3.0], "ballast": ["p-site/ballast", 3.0], "shoulder": ["p-site/gravel_road", 4.0],
	"kerb": ["lib/concrete", 2.0]}
const PAVED := ["hwy", "county", "main", "street"]
const SHOULDER := {"hwy": 2.4, "county": 1.5, "street": 0.9, "gravel": 0.6}
const GUTTER := 0.45
const CURB_H := 0.15
const CURB_W := 0.2
const FINE := ["paint_w", "paint_y", "decal", "kerb", "shoulder"]
const FINE_CELL := 100.0
const NEAR_R := 900.0
const RXR_CELL := 19                 # tools/sign_atlas.py: the RXR marking's cell

var _roads: Array = []
var _near := Vector2(INF, INF)
var _pass := 0                       # 0: near the start only, 1: the rest
var near_done := false
var _turns: Array = []
var _fur: Dictionary = {}
var _task := -1
var _out: Array = []                 # [cell key, surface arrays] from the worker
var _cells := {}                     # [cell key, surface] -> SurfaceTool
var _mats := {}


func setup(near := Vector2(INF, INF)) -> void:
	## near (s, x): the roads within NEAR_R of it are built first (the splash waits for those only)
	_near = near
	var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(MapTerrain.PATH))
	_roads = d.roads
	_turns = d.get("turns", [])
	_roads.append({"cls": "rail", "w": 4.0, "pts": d.rail.pts})
	if FileAccess.file_exists("res://remake/road_furniture.json"):
		_fur = JSON.parse_string(FileAccess.get_file_as_string("res://remake/road_furniture.json"))
	for key in TEX:
		var m := StandardMaterial3D.new()
		var root := "res://remake/textures/%s_" % TEX[key][0]
		m.albedo_texture = load(root + "albedo.webp")
		m.normal_enabled = true
		m.normal_texture = load(root + "normal.webp")
		m.roughness_texture = load(root + "rough.webp")
		m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
		m.cull_mode = BaseMaterial3D.CULL_DISABLED        # a ribbon's winding follows its road's direction
		_mats[key] = m
	(_mats["shoulder"] as StandardMaterial3D).albedo_color = Color(1.08, 1.02, 0.92)
	(_mats["kerb"] as StandardMaterial3D).albedo_color = Color(1.15, 1.15, 1.12)
	for key in ["paint_w", "paint_y"]:
		var m := StandardMaterial3D.new()
		m.albedo_color = Color(0.93, 0.93, 0.9) if key == "paint_w" else Color(0.95, 0.72, 0.1)
		m.roughness = 0.7
		m.cull_mode = BaseMaterial3D.CULL_DISABLED
		_mats[key] = m
	var dm := StandardMaterial3D.new()
	dm.albedo_texture = load("res://remake/textures/road_signs.png")
	dm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	dm.alpha_scissor_threshold = 0.5
	dm.cull_mode = BaseMaterial3D.CULL_DISABLED
	dm.roughness = 0.7
	_mats["decal"] = dm
	MapTerrain.elevation(0.0, 0.0)                         # loads the terrain data (_body_profile reads it)
	_task = WorkerThreadPool.add_task(_build_all, false, "roads")
	set_process(true)


func _build_all() -> void:
	var ctx: Array = _fur.get("ctx", [])
	var jn: Array = _fur.get("jn", [])
	var dup: Array = _fur.get("dup", [])
	for i in _roads.size():
		_add_road(_roads[i], ctx[i] if i < ctx.size() else "", jn[i] if i < jn.size() else "",
			dup[i] if i < dup.size() else "")
	for t in _turns:
		_add_turn(t)
	for ln in _fur.get("lines", []):
		_add_line(ln)
	for b in _fur.get("bars", []):
		_add_bar(b)
	for dc in _fur.get("decals", []):
		_add_decal(dc)
	var out := []
	for key in _cells:
		var arr := (_cells[key] as SurfaceTool).commit_to_arrays()
		if arr[Mesh.ARRAY_VERTEX] != null and (arr[Mesh.ARRAY_VERTEX] as PackedVector3Array).size() > 0:
			out.append([key, arr])
	_cells.clear()
	_out = out


func _process(_delta: float) -> void:
	if _task < 0 or not WorkerThreadPool.is_task_completed(_task):
		return
	WorkerThreadPool.wait_for_task_completion(_task)
	_task = -1
	_commit()
	if _pass == 0 and _near.x != INF:
		near_done = true
		_pass = 1
		_task = WorkerThreadPool.add_task(_build_all, false, "roads (the rest)")
		return
	near_done = true
	set_process(false)


func _exit_tree() -> void:
	if _task >= 0:
		WorkerThreadPool.wait_for_task_completion(_task)


func _in_pass(c: Vector2) -> bool:
	if _near.x == INF:
		return _pass == 0
	var near := Vector2(StationGeo.wrap_ds(c.x - _near.x), c.y - _near.y).length() < NEAR_R
	return near if _pass == 0 else not near


func _st(c: Vector2, surf: String) -> SurfaceTool:
	# the fine detail (paint, kerbs, shoulders) in smaller cells: they fade out much nearer
	var cell := CELL if not FINE.has(surf) else FINE_CELL
	var key := [Vector2i(floori(fposmod(c.x, StationGeo.CIRC) / cell), floori(c.y / cell)), surf]
	var st: SurfaceTool = _cells.get(key)
	if st == null:
		st = SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		_cells[key] = st
	return st


func _quad(st: SurfaceTool, v: Array, uv: Array, up: Vector3) -> void:
	## Two triangles over v[0..3] (in order round the quad); the normal faces up / outward.
	var n: Vector3 = (v[1] - v[0]).cross(v[3] - v[0])
	if n.length_squared() < 1e-10:
		n = up
	n = n.normalized()
	if n.dot(up) < -0.05:
		n = -n
	for j in [0, 2, 1, 0, 3, 2]:
		st.set_normal(n)
		st.set_uv(uv[j])
		st.add_vertex(v[j])


func _pt(p: Vector2, h: float) -> Vector3:
	return StationGeo.point(p.x, p.y, MapTerrain.elevation(p.x, p.y) + h)


func _add_road(rd: Dictionary, ctx: String, jn: String, dup: String) -> void:
	## dup: "1" where another road owns the stretch (a highway on a town's main street): no ribbon there
	var pts: Array = rd.pts
	var cls: String = rd.cls
	var surf: String = SURFACE.get(cls, "asphalt")
	var hw: float = rd.w * 0.5
	var tile: float = TEX[surf][1]
	var run := 0.0
	var prev := []
	var prev_edge := []                                   # [side -> profile points] at the previous sample
	for k in pts.size() - 1:
		var a := Vector2(pts[k][0], pts[k][1])
		var b := Vector2(pts[k + 1][0], pts[k + 1][1])
		var dv := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)
		var seg_len := dv.length()
		if seg_len < 0.01:
			continue
		if not _in_pass(a):
			prev = []
			prev_edge = []
			run += seg_len
			continue
		var dirv := dv / seg_len
		var side := Vector2(-dirv.y, dirv.x)
		var n: int = maxi(1, ceili(seg_len / STEP))
		# the edge treatment over this segment: curb (town / core), shoulder (rural), or none
		var edge := ""
		if cls != "rail" and ctx.length() > k + 1 and jn.length() > k + 1 and jn[k] == "0" and jn[k + 1] == "0":
			var c_: String = ctx[k]
			if c_ != "r" and PAVED.has(cls):
				edge = "curb"
			elif c_ == "r" and SHOULDER.has(cls):
				edge = "shoulder"
		for i in range(0 if k == 0 else 1, n + 1):
			var c := a + dv * (i / float(n))
			var hidden := dup.length() > k + 1 and dup[k] == "1" and dup[k + 1] == "1"
			var over_water := hidden or MapTerrain._body_profile(fposmod(c.x, StationGeo.CIRC), c.y) > 0.05
			var l := c + side * hw
			var r := c - side * hw
			var up := StationGeo.up(c.x)
			var hl := 0.0
			var hr := 0.0
			if not over_water:
				hl = MapTerrain.elevation(l.x, l.y) + LIFT
				hr = MapTerrain.elevation(r.x, r.y) + LIFT
			var row := [] if over_water else [StationGeo.point(l.x, l.y, hl), StationGeo.point(r.x, r.y, hr), run / tile, up]
			if not prev.is_empty() and not row.is_empty():
				var st := _st(c, surf)
				_quad(st, [prev[0], row[0], row[1], prev[1]],
					[Vector2(0.0, prev[2]), Vector2(0.0, row[2]), Vector2(rd.w / tile, row[2]), Vector2(rd.w / tile, prev[2])], up)
			# the edges: a cross-section profile each side, joined to the previous sample's
			var edge_now := []
			if edge != "" and not over_water and i > 0:
				for sg in [1.0, -1.0]:
					var e: Vector2 = c + side * hw * sg
					var he := hl if sg > 0.0 else hr               # the ribbon's own edge height
					var prof := []                             # [point, u (across, m)]
					if edge == "curb":
						var o: Vector2 = side * sg
						prof = [[StationGeo.point(e.x - o.x * GUTTER, e.y - o.y * GUTTER, he + 0.012), 0.0],
							[StationGeo.point(e.x, e.y, he + 0.012), GUTTER],
							[StationGeo.point(e.x, e.y, he + CURB_H), GUTTER + CURB_H],
							[StationGeo.point(e.x + o.x * CURB_W, e.y + o.y * CURB_W, he + CURB_H), GUTTER + CURB_H + CURB_W],
							[StationGeo.point(e.x + o.x * CURB_W, e.y + o.y * CURB_W, he - 0.1), GUTTER + CURB_H * 2 + CURB_W + 0.1]]
					else:
						var sw: float = SHOULDER[cls]
						var m1: Vector2 = e + side * sg * sw * 0.5
						var m2: Vector2 = e + side * sg * sw
						var h2 := MapTerrain.elevation(m2.x, m2.y) + LIFT
						prof = [[StationGeo.point(e.x, e.y, he - 0.01), 0.0],
							[StationGeo.point(m1.x, m1.y, lerpf(he, h2, 0.5) - 0.01), sw * 0.5],
							[StationGeo.point(m2.x, m2.y, h2 - 0.04 * sw * 0.5 - 0.02), sw]]
					edge_now.append(prof)
				if prev_edge.size() == 2 and edge_now.size() == 2:
					var esurf := "kerb" if edge == "curb" else "shoulder"
					var et: float = TEX[esurf][1]
					var st2 := _st(c, esurf)
					for sgi in 2:
						var p0: Array = prev_edge[sgi]
						var p1: Array = edge_now[sgi]
						if p0.size() != p1.size():
							continue                           # a curb turning into a shoulder: start afresh
						for j in p1.size() - 1:
							_quad(st2, [p0[j][0], p1[j][0], p1[j + 1][0], p0[j + 1][0]],
								[Vector2(p0[j][1] / et, (run - seg_len / n) / et), Vector2(p1[j][1] / et, run / et),
								Vector2(p1[j + 1][1] / et, run / et), Vector2(p0[j + 1][1] / et, (run - seg_len / n) / et)], up)
			prev_edge = edge_now
			prev = row
			run += seg_len / n


func _add_turn(t: Dictionary) -> void:
	## A turning circle: a disc of the road's surface, just under the road's own ribbon.
	var c := Vector2(t.s, t.x)
	if not _in_pass(c):
		return
	var r: float = t.r
	var surf: String = SURFACE.get(t.cls, "asphalt")
	var tile: float = TEX[surf][1]
	var st := _st(c, surf)
	var up := StationGeo.up(c.x)
	var mid := _pt(c, LIFT - 0.012)
	var n := 20
	for k in n:
		var a0 := TAU * k / n
		var a1 := TAU * (k + 1) / n
		var q0 := c + Vector2(cos(a0), sin(a0)) * r
		var q1 := c + Vector2(cos(a1), sin(a1)) * r
		var v := [mid, _pt(q0, LIFT - 0.012), _pt(q1, LIFT - 0.012)]
		var uv := [Vector2.ZERO, Vector2(cos(a0), sin(a0)) * r / tile, Vector2(cos(a1), sin(a1)) * r / tile]
		for j in [0, 2, 1]:
			st.set_normal(up)
			st.set_uv(uv[j])
			st.add_vertex(v[j])


func _add_line(ln: Dictionary) -> void:
	## A painted line along road ln.r from point a to b, off m to the side, dashed if ln.dash.
	var pts: Array = _roads[int(ln.r)].pts
	var off: float = ln.off
	var hwid: float = float(ln.w) * 0.5
	var surf := "paint_y" if ln.c == "y" else "paint_w"
	var dash: Array = ln.get("dash", [])
	var period := 0.0 if dash.is_empty() else float(dash[0]) + float(dash[1])
	var along := 0.0
	for k in range(int(ln.a), int(ln.b)):
		var a := Vector2(pts[k][0], pts[k][1])
		var b := Vector2(pts[k + 1][0], pts[k + 1][1])
		var dv := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)
		var L := dv.length()
		if L < 0.01:
			continue
		if not _in_pass(a):
			along += L
			continue
		var u := dv / L
		var side := Vector2(-u.y, u.x)
		# pieces: the whole segment, or the dashes' painted parts within it
		var pieces := []
		if period == 0.0:
			pieces.append([0.0, L])
		else:
			var t0 := along
			var t := 0.0
			while t < L:
				var ph := fposmod(t0 + t, period)
				if ph < float(dash[0]):
					var e := minf(L, t + float(dash[0]) - ph)
					if e - t > 0.05:
						pieces.append([t, e])
					t = maxf(e, t + 0.01)                  # (a phase a hair short of the gap must still move on)
				else:
					t += maxf(period - ph, 0.01)
		for pc in pieces:
			# short pieces, so the paint follows the ribbon's 3 m rows instead of cutting under them
			var m := maxi(1, ceili((pc[1] - pc[0]) / 1.5))
			var h_prev := 0.0
			for q in m:
				var t0: float = lerpf(pc[0], pc[1], q / float(m))
				var t1: float = lerpf(pc[0], pc[1], (q + 1) / float(m))
				var p0: Vector2 = a + u * t0 + side * off
				var p1: Vector2 = a + u * t1 + side * off
				if MapTerrain._body_profile(fposmod(p0.x, StationGeo.CIRC), p0.y) > 0.05:
					continue
				var up := StationGeo.up(p0.x)
				var h0 := h_prev if q > 0 else MapTerrain.elevation(p0.x, p0.y) + LIFT + PAINT
				var h1 := MapTerrain.elevation(p1.x, p1.y) + LIFT + PAINT
				h_prev = h1
				var e0: Vector2 = p0 + side * hwid
				var e1: Vector2 = p1 + side * hwid
				var f0: Vector2 = p0 - side * hwid
				var f1: Vector2 = p1 - side * hwid
				var v := [StationGeo.point(e0.x, e0.y, h0), StationGeo.point(e1.x, e1.y, h1),
					StationGeo.point(f1.x, f1.y, h1), StationGeo.point(f0.x, f0.y, h0)]
				_quad(_st(p0, surf), v, [Vector2.ZERO, Vector2.ZERO, Vector2.ZERO, Vector2.ZERO], up)
		along += L


func _add_bar(b: Dictionary) -> void:
	var q: Array = b.q
	var c := Vector2(q[0][0], q[0][1])
	if not _in_pass(c):
		return
	var v := []
	for p in q:
		v.append(_pt(Vector2(p[0], p[1]), LIFT + PAINT + 0.002))
	_quad(_st(c, "paint_w"), v, [Vector2.ZERO, Vector2.ZERO, Vector2.ZERO, Vector2.ZERO], StationGeo.up(c.x))


func _add_decal(dc: Dictionary) -> void:
	## RXR: the atlas cell stretched over w x l m, its top toward the crossing (the driver reads it upright).
	var c := Vector2(dc.s, dc.x)
	if not _in_pass(c):
		return
	var yaw: float = dc.yaw
	var fwd := Vector2(cos(yaw), -sin(yaw))            # (s, x) the decal's "up" faces (away from the crossing)
	var rgt := Vector2(-fwd.y, fwd.x)
	var hw: float = float(dc.w) * 0.5
	var hl: float = float(dc.l) * 0.5
	var col := RXR_CELL % 8
	var row := RXR_CELL / 8
	var u0 := col / 8.0
	var u1 := (col + 1) / 8.0
	var v0 := row / 4.0
	var v1 := (row + 1) / 4.0
	# the driver approaches along -fwd: the letters' top is toward the crossing (-fwd side)
	var v := [_pt(c - fwd * hl - rgt * hw, LIFT + PAINT), _pt(c - fwd * hl + rgt * hw, LIFT + PAINT),
		_pt(c + fwd * hl + rgt * hw, LIFT + PAINT), _pt(c + fwd * hl - rgt * hw, LIFT + PAINT)]
	_quad(_st(c, "decal"), v, [Vector2(u0, v0), Vector2(u1, v0), Vector2(u1, v1), Vector2(u0, v1)], StationGeo.up(c.x))


func _commit() -> void:
	for job in _out:
		var key: Array = job[0]
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, job[1])
		mesh.surface_set_material(0, _mats[key[1]])
		var mi := MeshInstance3D.new()
		mi.name = "roads_%d_%d_%s" % [key[0].x, key[0].y, key[1]]
		if FINE.has(key[1]):
			mi.name += "_f"
		mi.mesh = mesh
		var far := FAR
		if key[1] in ["paint_w", "paint_y", "decal"]:
			far = PAINT_FAR
		elif key[1] in ["kerb", "shoulder"]:
			far = KERB_FAR
		mi.visibility_range_end = far
		mi.visibility_range_end_margin = far * 0.08
		if far < FAR:
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mi)
	_out.clear()
