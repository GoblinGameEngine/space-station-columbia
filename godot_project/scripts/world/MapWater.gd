extends RefCounted
class_name MapWater

## Water surfaces for the map's terrain (MapTerrain): the Kettle River and Lake Tamsin as one
## surface at the bank-full MapTerrain.water_level(s), in STEP m strips round the ring across the
## whole depression (MapTerrain.outline + OVERLAP, which the banks hide), with the game's
## scrolling water material (LakeWater.gd).
## build_small(): the creeks, spurs, ponds and oxbow lakes, filled FILL of their depth.

const STEP := 4.0
const OVERLAP := 1.5                 # past the rim, under the bank


const CHUNKS := 24                   # the river / lake surface in this many pieces round the ring


const RECT_CELL := 400.0             # v2: the merged water rectangles, grouped per this much of the ring
const RECT_SEG := 32.0               # ... each split this often along the ring (it's a cylinder)


static func build(root: Node3D) -> void:
	## The river / lake surface, in CHUNKS pieces (the far side hides its own).
	if FileAccess.file_exists("res://remake/water_rects.json"):
		_build_rects(root)
		return
	for i in CHUNKS:
		_build_range(root, StationGeo.CIRC * i / CHUNKS, StationGeo.CIRC * (i + 1) / CHUNKS).name = "map_water_%d" % i


static func _build_range(root: Node3D, s0: float, s1: float) -> MeshInstance3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_texture = load("res://assets/textures/water_tinted_0.png")
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.albedo_color = Color(1.0, 1.0, 1.0, 0.9)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n := ceili((s1 - s0) / STEP)
	var prev := []
	for i in n + 1:
		var s := s0 + (s1 - s0) * i / float(n)
		var e := MapTerrain.outline(s)                     # the whole depression, rim to rim
		var lvl := MapTerrain.water_level(s)
		var up := StationGeo.up(s)
		var row := []
		for x in [e.x - OVERLAP, (e.x + e.y) * 0.5, e.y + OVERLAP]:
			row.append([StationGeo.point(s, x, lvl), Vector2(x / 20.0, s / 20.0), up])
		if not prev.is_empty():
			for j in 2:
				for v in [prev[j], row[j], row[j + 1], prev[j], row[j + 1], prev[j + 1]]:
					st.set_normal(v[2])
					st.set_uv(v[1])
					st.add_vertex(v[0])
		prev = row
	st.set_material(mat)
	var mi := MeshInstance3D.new()
	mi.name = "map_water_surface"
	mi.mesh = st.commit()
	mi.set_script(load("res://scripts/world/LakeWater.gd"))
	root.add_child(mi)
	return mi


static func _build_rects(root: Node3D) -> void:
	## Version 2: every river, lake, sea and harbour surface from tools/map_expanded.py's merged
	## rectangles (s0, s1, x0, x1, level), OVERLAP past each side (under the banks), per RECT_CELL.
	var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://remake/water_rects.json"))
	var mat := StandardMaterial3D.new()
	mat.albedo_texture = load("res://assets/textures/water_tinted_0.png")
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.albedo_color = Color(1.0, 1.0, 1.0, 0.9)
	var cells := {}
	for r in d.rects:
		var s0: float = r[0] - OVERLAP
		var s1: float = r[1] + OVERLAP
		var x0: float = r[2] - OVERLAP
		var x1: float = r[3] + OVERLAP
		var lvl: float = r[4]
		var key := floori(fposmod((s0 + s1) * 0.5, StationGeo.CIRC) / RECT_CELL)
		if not cells.has(key):
			var st0 := SurfaceTool.new()
			st0.begin(Mesh.PRIMITIVE_TRIANGLES)
			cells[key] = st0
		var st: SurfaceTool = cells[key]
		var n := maxi(1, ceili((s1 - s0) / RECT_SEG))
		for i in n:
			var sa := s0 + (s1 - s0) * i / n
			var sb := s0 + (s1 - s0) * (i + 1) / n
			var ua := StationGeo.up(sa)
			var ub := StationGeo.up(sb)
			var q := [[StationGeo.point(sa, x0, lvl), ua, Vector2(x0, sa)], [StationGeo.point(sb, x0, lvl), ub, Vector2(x0, sb)],
				[StationGeo.point(sb, x1, lvl), ub, Vector2(x1, sb)], [StationGeo.point(sa, x1, lvl), ua, Vector2(x1, sa)]]
			for k in [0, 1, 2, 0, 2, 3]:
				st.set_normal(q[k][1])
				st.set_uv(q[k][2] / 20.0)
				st.add_vertex(q[k][0])
	for key in cells:
		var st: SurfaceTool = cells[key]
		st.set_material(mat)
		var mi := MeshInstance3D.new()
		mi.name = "map_water_%d" % key
		mi.mesh = st.commit()
		mi.set_script(load("res://scripts/world/LakeWater.gd"))
		root.add_child(mi)


const FILL := 0.75                   # the small water stands at this fraction of its carved depth


const SMALL_CELL := 400.0


const BAKED_SMALL := "res://remake/baked/small_water.res"
const BAKE_VERSION := 1              # bump when the small water's output changes


static func stamp() -> String:
	## what the small water is made from: the map's creeks, ponds and oxbows on the graded terrain
	return BakedMeshes.fingerprint([MapTerrain.PATH, "res://remake/terrain_base.bin.gz", "res://remake/terrain_level.bin.gz",
		"res://remake/terrain_depth.bin.gz", "res://remake/placement.json"], BAKE_VERSION)


static func bake_small() -> BakedMeshes:
	## (remake/tools/bake_world.gd) the small water's cells as mesh arrays
	var b := BakedMeshes.new()
	b.stamp = stamp()
	b.data["cells"] = small_arrays()
	return b


static func build_small(root: Node3D) -> void:
	## The small water, merged per SMALL_CELL m of s (the far side hides its own) -- baked, or made now.
	var cells := {}
	if ResourceLoader.exists(BAKED_SMALL):
		var b := ResourceLoader.load(BAKED_SMALL) as BakedMeshes
		if b and b.stamp == stamp():
			cells = b.data.get("cells", {})
	if cells.is_empty():
		cells = small_arrays()
	var mat := _small_material()
	for key in cells:
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, cells[key])
		mesh.surface_set_material(0, mat)
		var mi := MeshInstance3D.new()
		mi.name = "map_small_water_%d" % key
		mi.mesh = mesh
		mi.set_script(load("res://scripts/world/LakeWater.gd"))
		root.add_child(mi)


static func small_arrays() -> Dictionary:
	## cell -> mesh arrays of the creeks, spurs, ponds and oxbows in it
	var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(MapTerrain.PATH))
	MapTerrain.elevation(0.0, 0.0)                        # loads the terrain data
	var cells := {}
	# creeks and spurs: a ribbon along the line at the bank-full level; broken where a road crosses
	# (it runs through a culvert under the road there)
	for cr in d.creeks:
		var pts: Array = cr.pts
		var hw: float = cr.hw + 0.8
		var prev := []
		for k in pts.size():
			var c := Vector2(pts[k][0], pts[k][1])
			var nb := Vector2(pts[mini(k + 1, pts.size() - 1)][0], pts[mini(k + 1, pts.size() - 1)][1])
			var pb := Vector2(pts[maxi(k - 1, 0)][0], pts[maxi(k - 1, 0)][1])
			var dv := Vector2(StationGeo.wrap_ds(nb.x - pb.x), nb.y - pb.y).normalized()
			var side := Vector2(-dv.y, dv.x)
			var row := []
			if MapTerrain.road_weight(c.x, c.y) < 0.3 and MapTerrain._body_profile(fposmod(c.x, StationGeo.CIRC), c.y) <= 0.0:
				var lvl := MapTerrain.elevation(c.x, c.y) + FILL * float(cr.depth)
				var l := c + side * hw
				var r := c - side * hw
				row = [StationGeo.point(l.x, l.y, lvl), StationGeo.point(r.x, r.y, lvl), c, StationGeo.up(c.x)]
			if not prev.is_empty() and not row.is_empty():
				_quad(_cell_st(cells, c.x), prev[0], row[0], row[1], prev[1], prev[3], row[3], prev[2], row[2])
			prev = row
	# ponds: filled ellipses
	for p in d.ponds:
		var lvl := MapTerrain.elevation(p.s, p.x) + FILL * float(p.depth)
		var ring := []
		for k in 33:
			var t := TAU * k / 32.0
			var u: float = p.a * 1.08 * cos(t)
			var v: float = p.b * 1.08 * sin(t)
			var ds: float = u * cos(float(p.rot)) - v * sin(float(p.rot))
			var dx: float = u * sin(float(p.rot)) + v * cos(float(p.rot))
			ring.append(Vector2(p.s + ds, p.x + dx))
		_fan(_cell_st(cells, p.s), Vector2(p.s, p.x), ring, lvl)
	# oxbow lakes: their outlines, triangulated
	for ox in d.oxbows:
		var poly := PackedVector2Array()
		var lo := 1e9
		for q in ox.poly:
			poly.append(Vector2(q[0], q[1]))
		var tris := Geometry2D.triangulate_polygon(poly)
		var cen := Vector2.ZERO
		for q in poly:
			cen += q
		cen /= poly.size()
		lo = MapTerrain.elevation(cen.x, cen.y) + FILL * float(ox.depth)
		var st := _cell_st(cells, cen.x)
		for i in range(0, tris.size(), 3):
			for j in [0, 2, 1]:
				var q: Vector2 = poly[tris[i + j]]
				st.set_normal(StationGeo.up(q.x))
				st.set_uv(q / 20.0)
				st.add_vertex(StationGeo.point(q.x, q.y, lo))
	var out := {}
	for key in cells:
		out[key] = (cells[key] as SurfaceTool).commit_to_arrays()
	return out


static func _cell_st(cells: Dictionary, s: float) -> SurfaceTool:
	var key := floori(fposmod(s, StationGeo.CIRC) / SMALL_CELL)
	if not cells.has(key):
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		cells[key] = st
	return cells[key]


static func _quad(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, d: Vector3, n0: Vector3, n1: Vector3, m0: Vector2, m1: Vector2) -> void:
	var q := [[a, n0, m0], [b, n1, m1], [c, n1, m1], [d, n0, m0]]
	for j in [0, 1, 2, 0, 2, 3]:
		st.set_normal(q[j][1])
		st.set_uv(q[j][2] / 20.0)
		st.add_vertex(q[j][0])


static func _fan(st: SurfaceTool, c: Vector2, ring: Array, lvl: float) -> void:
	for k in ring.size() - 1:
		var a: Vector2 = ring[k]
		var b: Vector2 = ring[k + 1]
		for q in [c, b, a]:
			st.set_normal(StationGeo.up(q.x))
			st.set_uv(q / 20.0)
			st.add_vertex(StationGeo.point(q.x, q.y, lvl))


static func _small_material() -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_texture = load("res://assets/textures/water_tinted_0.png")
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.albedo_color = Color(0.9, 0.95, 0.9, 0.88)
	return mat

