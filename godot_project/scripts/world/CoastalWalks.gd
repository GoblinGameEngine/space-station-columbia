extends Node3D
class_name CoastalWalks

## The coast's walks -- boardwalks, piers and their T-heads, docks, wharves, breakwaters and jetties,
## promenades, dune crossovers, catwalks, ramps (remake/walks.json, from remake/tools/placement.py;
## lines and decks from tools/map_expanded.py, traits from their catalog records) -- built along
## their map lines at load, on the terrain and the water:
##   over water: the deck DECK_H above the water level (a floating dock DOCK_H), on pile bents
##   founded PILE_DEPTH below the bed (spec rule 4: >= 10 m -- nothing floats);
##   on land: the deck lifted off the sand (a boardwalk LIFT_BW, a promenade a kerb's height);
##   a short boardwalk spur is a ramp down from the boardwalk to the beach;
##   a breakwater / jetty (rubble_mound) is a rock mound from the bed to above the water.
## Rails, lamp posts and benches per the traits.  Meshes merge per CELL m cell and material; the
## deck and rails are walkable / solid (a trimesh per cell).  Built on a worker thread.

const DECK_H := 2.5
const DOCK_H := 0.45
const LIFT_BW := 1.2
const PILE_DEPTH := 12.0
const STEP := 3.0
const CELL := 400.0
const FAR := 1600.0
const PILE_EVERY := 3.0
const TEX := {"deck_timber": ["lib/weathered_board", 2.0], "deck_composite": ["lib/wood_dark", 2.0],
	"deck_concrete": ["lib/concrete", 3.0], "pile": ["lib/wood_dark", 2.0], "rock": ["lib/fieldstone", 3.0],
	"rail_timber": ["lib/wood_light", 2.0]}
const SOLID := {"rail_pipe": Color(0.82, 0.83, 0.84), "rail_iron": Color(0.08, 0.08, 0.08), "rail_white": Color(0.93, 0.93, 0.9),
	"lamp": Color(0.15, 0.17, 0.18), "bulb": Color(1.0, 0.92, 0.7), "bench": Color(0.45, 0.33, 0.22)}

var _walks: Array = []
var _task := -1
var _cells := {}                     # [cell key, material] -> SurfaceTool
var _cols := {}                      # cell key -> PackedVector3Array (collision faces)
var _out: Array = []
var _mats := {}


func setup() -> void:
	if not FileAccess.file_exists("res://remake/walks.json"):
		return
	_walks = JSON.parse_string(FileAccess.get_file_as_string("res://remake/walks.json")).walks
	for key in TEX:
		var m := StandardMaterial3D.new()
		var root := "res://remake/textures/%s_" % TEX[key][0]
		m.albedo_texture = load(root + "albedo.webp")
		m.normal_enabled = true
		m.normal_texture = load(root + "normal.webp")
		m.roughness_texture = load(root + "rough.webp")
		m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
		m.cull_mode = BaseMaterial3D.CULL_DISABLED
		_mats[key] = m
	for key in SOLID:
		var m := StandardMaterial3D.new()
		m.albedo_color = SOLID[key]
		m.roughness = 0.5
		m.cull_mode = BaseMaterial3D.CULL_DISABLED
		if key == "bulb":
			m.emission_enabled = true
			m.emission = SOLID[key]
			m.emission_energy_multiplier = 2.0
		_mats[key] = m
	MapTerrain.elevation(0.0, 0.0)
	if ResourceLoader.exists(BAKED):
		_task = WorkerThreadPool.add_task(_load_baked, false, "coastal walks (baked)")
	else:
		_task = WorkerThreadPool.add_task(_build_all, false, "coastal walks")
	set_process(true)


const BAKED := "res://remake/baked/walks.res"
const BAKE_VERSION := 2              # bump when the builder's output changes


static func stamp() -> String:
	## what the walks are built from: their lines, the water levels and the ground they meet
	return BakedMeshes.fingerprint(["res://remake/walks.json", MapTerrain.PATH, "res://remake/terrain_base.bin.gz",
		"res://remake/terrain_level.bin.gz", "res://remake/terrain_depth.bin.gz", "res://remake/placement.json"], BAKE_VERSION)


func _load_baked() -> void:
	## (worker) the baked walks, if they're of this map; else build them here after all
	var b := ResourceLoader.load(BAKED) as BakedMeshes
	if b and b.stamp == stamp():
		_out = b.data.get("out", [])
		return
	push_warning("CoastalWalks: the baked walks are of other map data -- building them (rerun remake/tools/bake_world.gd)")
	_build_all()


func bake() -> BakedMeshes:
	## every walk as mesh arrays and collision faces (remake/tools/bake_world.gd saves them)
	_walks = JSON.parse_string(FileAccess.get_file_as_string("res://remake/walks.json")).walks
	MapTerrain.elevation(0.0, 0.0)
	_build_all()
	var b := BakedMeshes.new()
	b.stamp = stamp()
	b.data["out"] = _out
	_out = []
	return b


func _process(_delta: float) -> void:
	if _task < 0 or not WorkerThreadPool.is_task_completed(_task):
		return
	WorkerThreadPool.wait_for_task_completion(_task)
	_task = -1
	_commit()
	set_process(false)


func _exit_tree() -> void:
	if _task >= 0:
		WorkerThreadPool.wait_for_task_completion(_task)


# ------------------------------------------------------------------ heights
static func _water(s: float, x: float) -> float:
	## the water level at (s, x), or NAN on dry land (or water too shallow to count)
	var w := MapTerrain.water_at(fposmod(s, StationGeo.CIRC), x)
	if w.x < -9000.0 or w.y < 0.25:
		return NAN
	return w.x


static func _deck_z(kind: String, s: float, x: float) -> float:
	var lv := _water(s, x)
	var g := MapTerrain.elevation(s, x)
	var wet := not is_nan(lv)
	if kind == "dock":
		return lv + DOCK_H if wet else g + 0.5
	if kind in ["promenade", "ramp"]:
		return maxf(g + 0.15, lv + DECK_H) if wet else g + 0.15
	if wet:
		return lv + DECK_H
	return g + (LIFT_BW if kind in ["boardwalk", "crossover", "catwalk"] else 1.0)


# ------------------------------------------------------------------ building
func _build_all() -> void:
	for w in _walks:
		if w.get("pts") != null:
			_add_line(w)
		elif w.get("rect") != null:
			_add_deck(w)
	var out := []
	for key in _cells:
		out.append([key, (_cells[key] as SurfaceTool).commit_to_arrays(), null])
	for ck in _cols:
		out.append([[ck, "_col"], null, _cols[ck]])
	_cells.clear()
	_cols.clear()
	_out = out


func _st(c: Vector2, mat: String) -> SurfaceTool:
	var key := [Vector2i(floori(fposmod(c.x, StationGeo.CIRC) / CELL), floori(c.y / CELL)), mat]
	var st: SurfaceTool = _cells.get(key)
	if st == null:
		st = SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		_cells[key] = st
	return st


func _col(c: Vector2, tris: Array) -> void:
	var ck := Vector2i(floori(fposmod(c.x, StationGeo.CIRC) / CELL), floori(c.y / CELL))
	if not _cols.has(ck):
		_cols[ck] = PackedVector3Array()
	var a: PackedVector3Array = _cols[ck]
	a.append_array(PackedVector3Array(tris))
	_cols[ck] = a


static func _p(c: Vector2, h: float) -> Vector3:
	return StationGeo.point(c.x, c.y, h)


func _quad(c: Vector2, mat: String, a: Vector3, b: Vector3, cc: Vector3, d: Vector3, uv := [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)],
		collide := false) -> void:
	var st := _st(c, mat)
	var n := (b - a).cross(d - a).normalized()
	var q := [a, b, cc, d]
	for j in [0, 1, 2, 0, 2, 3]:
		st.set_normal(n)
		st.set_uv(uv[j])
		st.add_vertex(q[j])
	if collide:
		_col(c, [a, b, cc, a, cc, d])


func _box(c: Vector2, mat: String, s: float, x: float, dir: Vector2, half_along: float, half_across: float, z0: float, z1: float,
		collide := false) -> void:
	## an upright box on the ring at (s, x), its long axis along dir (map units), from z0 to z1
	var side := Vector2(-dir.y, dir.x)
	var corners := []
	for k in [[-1, -1], [1, -1], [1, 1], [-1, 1]]:
		var m: Vector2 = Vector2(s, x) + dir * half_along * k[0] + side * half_across * k[1]
		corners.append(m)
	for i in 4:
		var m0: Vector2 = corners[i]
		var m1: Vector2 = corners[(i + 1) % 4]
		var L := m0.distance_to(m1)
		_quad(c, mat, _p(m0, z0), _p(m1, z0), _p(m1, z1), _p(m0, z1), [Vector2(0, z0 / 2.0), Vector2(L / 2.0, z0 / 2.0),
			Vector2(L / 2.0, z1 / 2.0), Vector2(0, z1 / 2.0)], collide)
	_quad(c, mat, _p(corners[0], z1), _p(corners[1], z1), _p(corners[2], z1), _p(corners[3], z1))


func _deck_mat(tr: Dictionary) -> String:
	var d: String = str(tr.get("deck", "timber_plank"))
	if d == "concrete":
		return "deck_concrete"
	if d == "composite":
		return "deck_composite"
	return "deck_timber"


static func _on_road(ca: Vector2, cb: Vector2, sa: Vector2, sb: Vector2, hw: float) -> bool:
	## Does this stretch of walk (its centre and both edges, each end and the middle) lie on a road's
	## carriageway?
	for t: float in [0.0, 0.5, 1.0]:
		var c := ca.lerp(cb, t)
		var sd := sa.lerp(sb, t)
		for k: float in [-1.0, 0.0, 1.0]:
			var p := c + sd * hw * k
			if MapTerrain.road_weight(fposmod(p.x, StationGeo.CIRC), p.y) > 0.999:
				return true
	return false


func _add_line(w: Dictionary) -> void:
	var tr: Dictionary = w.get("traits", {}) if w.get("traits") != null else {}
	var kind: String = w.kind
	var hw: float = float(w.w) * 0.5
	var pts: Array = w.pts
	var rubble: bool = str(tr.get("substructure", "")) == "rubble_mound" or kind in ["breakwater", "jetty"]
	# sample the line
	var samples := []                           # [centre (s, x), dir]
	var total := 0.0
	for k in pts.size() - 1:
		var a := Vector2(pts[k][0], pts[k][1])
		var b := Vector2(pts[k + 1][0], pts[k + 1][1])
		var dv := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)
		var L := dv.length()
		if L < 0.01:
			continue
		var n := maxi(1, ceili(L / STEP))
		for i in range(0 if samples.is_empty() else 1, n + 1):
			samples.append([a + dv * (i / float(n)), dv / L])
		total += L
	if samples.size() < 2:
		return
	# deck heights, smoothed along the line; a short boardwalk spur ramps down to the beach
	var z := []
	for smp in samples:
		z.append(_deck_z(kind, smp[0].x, smp[0].y))
	var zs := z.duplicate()
	for i in z.size():
		var acc := 0.0
		var cnt := 0
		for j in range(maxi(0, i - 3), mini(z.size(), i + 4)):
			acc += z[j]
			cnt += 1
		zs[i] = acc / cnt
	if kind == "boardwalk" and total < 25.0:
		var z0: float = zs[0]
		var c1: Vector2 = samples[-1][0]
		var z1 := MapTerrain.elevation(c1.x, c1.y) + 0.15
		for i in zs.size():
			zs[i] = lerpf(z0, z1, i / float(zs.size() - 1))
	for i in zs.size():
		var c: Vector2 = samples[i][0]
		zs[i] = maxf(zs[i], MapTerrain.elevation(c.x, c.y) + 0.12)
	var dmat := _deck_mat(tr)
	var rail: String = str(tr.get("rail", "none" if kind == "dock" else "pipe"))
	var rmat: String = {"pipe": "rail_pipe", "timber": "rail_timber", "ornamental_iron": "rail_iron"}.get(rail, "")
	var pile_d: float = maxf(10.0, float(tr.get("pile_depth_m", 10.0) if tr.get("pile_depth_m") != null else 10.0))
	var run := 0.0
	var next_pile := 0.0
	var next_lamp := 12.0
	var next_bench := 20.0
	for i in samples.size() - 1:
		var ca: Vector2 = samples[i][0]
		var cb: Vector2 = samples[i + 1][0]
		var da: Vector2 = samples[i][1]
		var db: Vector2 = samples[i + 1][1]
		var sa := Vector2(-da.y, da.x)
		var sb := Vector2(-db.y, db.x)
		var za: float = zs[i]
		var zb: float = zs[i + 1]
		var seg := ca.distance_to(cb)
		if _on_road(ca, cb, sa, sb, hw + (4.0 if rubble else 0.0)):      # (a rock mound's sides reach out past its crest)
			# where the walk meets a road it stops at the kerb (a path crossing a street does so at
			# grade): no deck, rails or piles standing in the carriageway
			run += seg
			next_pile = maxf(next_pile, run)
			next_lamp = maxf(next_lamp, run)
			next_bench = maxf(next_bench, run)
			continue
		var tile: float = TEX[dmat][1] if not rubble else 3.0
		var u0 := run / tile
		var u1 := (run + seg) / tile
		if rubble:
			# a rock mound: a flat crest hw wide, sides at 1:1.5 down to the bed
			var ba := minf(MapTerrain.elevation(ca.x, ca.y), za - 1.0) - 0.5
			var bb := minf(MapTerrain.elevation(cb.x, cb.y), zb - 1.0) - 0.5
			var wa := hw + (za - ba) * 1.5
			var wb := hw + (zb - bb) * 1.5
			_quad(ca, "rock", _p(ca + sa * hw, za), _p(cb + sb * hw, zb), _p(cb - sb * hw, zb), _p(ca - sa * hw, za),
				[Vector2(0, u0), Vector2(0, u1), Vector2(hw * 2 / tile, u1), Vector2(hw * 2 / tile, u0)], true)
			for sg in [1.0, -1.0]:
				_quad(ca, "rock", _p(ca + sa * wa * sg, ba), _p(cb + sb * wb * sg, bb), _p(cb + sb * hw * sg, zb), _p(ca + sa * hw * sg, za),
					[Vector2(0, u0), Vector2(0, u1), Vector2(2, u1), Vector2(2, u0)], true)
		else:
			# the deck: top (walkable), fascia both sides, underside
			_quad(ca, dmat, _p(ca + sa * hw, za), _p(cb + sb * hw, zb), _p(cb - sb * hw, zb), _p(ca - sa * hw, za),
				[Vector2(0, u0), Vector2(0, u1), Vector2(hw * 2 / tile, u1), Vector2(hw * 2 / tile, u0)], true)
			for sg in [1.0, -1.0]:
				_quad(ca, dmat, _p(ca + sa * hw * sg, za - 0.35), _p(cb + sb * hw * sg, zb - 0.35), _p(cb + sb * hw * sg, zb), _p(ca + sa * hw * sg, za))
			_quad(ca, dmat, _p(ca - sa * hw, za - 0.35), _p(cb - sb * hw, zb - 0.35), _p(cb + sb * hw, zb - 0.35), _p(ca + sa * hw, za - 0.35))
			# rails: posts every 2 m, top and mid rails, both edges (solid)
			if rmat != "":
				for sg in [1.0, -1.0]:
					var ea: Vector2 = ca + sa * (hw - 0.05) * sg
					var eb: Vector2 = cb + sb * (hw - 0.05) * sg
					for rz in [1.05, 0.55]:
						_quad(ca, rmat, _p(ea, za + rz - 0.07), _p(eb, zb + rz - 0.07), _p(eb, zb + rz), _p(ea, za + rz), [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)], rz > 1.0)
					_col(ca, [_p(ea, za), _p(eb, zb), _p(eb, zb + 1.05), _p(ea, za), _p(eb, zb + 1.05), _p(ea, za + 1.05)])
			# pile bents, founded pile_d below the ground or the bed
			while next_pile <= run + seg:
				var t := clampf((next_pile - run) / maxf(seg, 0.001), 0.0, 1.0)
				var c := ca.lerp(cb, t)
				var d := da.lerp(db, t).normalized()
				var sd := Vector2(-d.y, d.x)
				var zt := lerpf(za, zb, t) - 0.35
				var bed := MapTerrain.elevation(c.x, c.y)
				var nrow := 2 if hw < 5.0 else 3
				for k in nrow:
					var off := -hw + 0.25 + (2.0 * hw - 0.5) * k / float(nrow - 1)
					var pc := c + sd * off
					_box(c, "pile", pc.x, pc.y, d, 0.15, 0.15, bed - pile_d, zt)
					if rmat != "" and absf(off) > hw - 0.5:
						_box(c, rmat, (c + sd * (hw - 0.05) * signf(off)).x, (c + sd * (hw - 0.05) * signf(off)).y, d, 0.05, 0.05, zt + 0.35, zt + 1.4)
				# a cross-beam cap on the bent
				_box(c, "pile", c.x, c.y, sd, hw, 0.15, zt - 0.3, zt)
				next_pile += PILE_EVERY
			# lamp posts and benches
			if str(tr.get("lighting", "none")) == "lamp_posts":
				while next_lamp <= run + seg:
					var t := clampf((next_lamp - run) / maxf(seg, 0.001), 0.0, 1.0)
					var c := ca.lerp(cb, t)
					var d := da.lerp(db, t).normalized()
					var sd := Vector2(-d.y, d.x)
					var lc := c + sd * (hw - 0.3) * (1.0 if int(next_lamp / 24.0) % 2 == 0 else -1.0)
					var zl := lerpf(za, zb, t)
					_box(c, "lamp", lc.x, lc.y, d, 0.07, 0.07, zl, zl + 4.2)
					_box(c, "bulb", lc.x, lc.y, d, 0.22, 0.22, zl + 4.2, zl + 4.6)
					next_lamp += 24.0
			if tr.get("benches", false) and hw >= 1.8:
				while next_bench <= run + seg:
					var t := clampf((next_bench - run) / maxf(seg, 0.001), 0.0, 1.0)
					var c := ca.lerp(cb, t)
					var d := da.lerp(db, t).normalized()
					var sd := Vector2(-d.y, d.x)
					var bc := c + sd * (hw - 0.8)
					var zl := lerpf(za, zb, t)
					_box(c, "bench", bc.x, bc.y, d, 0.9, 0.22, zl + 0.4, zl + 0.46)
					_box(c, "bench", (bc + sd * 0.22).x, (bc + sd * 0.22).y, d, 0.9, 0.04, zl + 0.46, zl + 0.85)
					for e in [-0.8, 0.8]:
						_box(c, "bench", (bc + d * e).x, (bc + d * e).y, d, 0.04, 0.2, zl, zl + 0.4)
					next_bench += 30.0
		run += seg


func _add_deck(w: Dictionary) -> void:
	## a pier's T-head, an amusement pier or a waterfront deck: a rectangle (s, x, w along s, d along x)
	var tr: Dictionary = w.get("traits", {}) if w.get("traits") != null else {}
	var r: Array = w.rect
	var cs: float = r[0]
	var cx: float = r[1]
	var hs: float = float(r[2]) * 0.5
	var hx: float = float(r[3]) * 0.5
	var c := Vector2(cs, cx)
	var z := -INF
	for k in [[-1, -1], [1, -1], [1, 1], [-1, 1], [0, 0]]:
		z = maxf(z, _deck_z(str(w.kind), cs + hs * k[0], cx + hx * k[1]))
	var dmat := _deck_mat(tr)
	var tile: float = TEX[dmat][1]
	var q := [Vector2(cs - hs, cx - hx), Vector2(cs + hs, cx - hx), Vector2(cs + hs, cx + hx), Vector2(cs - hs, cx + hx)]
	_quad(c, dmat, _p(q[0], z), _p(q[1], z), _p(q[2], z), _p(q[3], z),
		[Vector2(0, 0), Vector2(hs * 2 / tile, 0), Vector2(hs * 2 / tile, hx * 2 / tile), Vector2(0, hx * 2 / tile)], true)
	for i in 4:
		var a: Vector2 = q[i]
		var b: Vector2 = q[(i + 1) % 4]
		_quad(c, dmat, _p(a, z - 0.4), _p(b, z - 0.4), _p(b, z), _p(a, z))
	var rail: String = str(tr.get("rail", "pipe"))
	var rmat: String = {"pipe": "rail_pipe", "timber": "rail_timber", "ornamental_iron": "rail_iron"}.get(rail, "")
	if rmat != "":
		for i in 4:
			var a: Vector2 = q[i]
			var b: Vector2 = q[(i + 1) % 4]
			_quad(c, rmat, _p(a, z + 0.98), _p(b, z + 0.98), _p(b, z + 1.05), _p(a, z + 1.05), [Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)])
			_col(c, [_p(a, z), _p(b, z), _p(b, z + 1.05), _p(a, z), _p(b, z + 1.05), _p(a, z + 1.05)])
	var pile_d := 10.0
	var ns := maxi(1, int(hs * 2 / PILE_EVERY))
	var nx := maxi(1, int(hx * 2 / PILE_EVERY))
	for i in ns + 1:
		for j in nx + 1:
			var ps := cs - hs + 0.3 + (hs * 2 - 0.6) * i / float(ns)
			var px := cx - hx + 0.3 + (hx * 2 - 0.6) * j / float(nx)
			var bed := MapTerrain.elevation(ps, px)
			_box(c, "pile", ps, px, Vector2(1, 0), 0.15, 0.15, bed - pile_d, z - 0.4)
	if str(tr.get("lighting", "none")) == "lamp_posts":
		for k in [[-1, -1], [1, -1], [1, 1], [-1, 1]]:
			var lc := Vector2(cs + (hs - 0.5) * k[0], cx + (hx - 0.5) * k[1])
			_box(c, "lamp", lc.x, lc.y, Vector2(1, 0), 0.07, 0.07, z, z + 4.2)
			_box(c, "bulb", lc.x, lc.y, Vector2(1, 0), 0.22, 0.22, z + 4.2, z + 4.6)


func _commit() -> void:
	for job in _out:
		var key: Array = job[0]
		if job[2] != null:
			var body := StaticBody3D.new()
			body.name = "walks_col_%d_%d" % [key[0].x, key[0].y]
			var shape := ConcavePolygonShape3D.new()
			shape.backface_collision = true
			shape.set_faces(job[2])
			var cs := CollisionShape3D.new()
			cs.shape = shape
			body.add_child(cs)
			add_child(body)
			continue
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, job[1])
		mesh.surface_set_material(0, _mats[key[1]])
		var mi := MeshInstance3D.new()
		mi.name = "walks_%d_%d_%s" % [key[0].x, key[0].y, key[1]]
		mi.mesh = mesh
		mi.visibility_range_end = FAR
		mi.visibility_range_end_margin = FAR * 0.08
		add_child(mi)
	_out.clear()
