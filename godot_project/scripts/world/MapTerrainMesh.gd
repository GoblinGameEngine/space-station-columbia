extends Node3D
class_name MapTerrainMesh

## The ring floor drawn from MapTerrain (the map's terrain), streamed in tiers round the player:
##   T0  chunk (1/CHUNKS_ROUND of the ring x CHUNK_X m), 2 m grid, with collision -- within NEAR
##   T1  the same chunk on an 8 m grid                               -- the rest of a near group
##   T2  a group (GROUP x GROUP chunks) merged, 8 m grid              -- groups within MID
##   T3  the group on a 32 m grid                                    -- everything else
## Tiles are generated on worker threads (MAX_TASKS at a time; MapTerrain is read-only once
## loaded) and only turned into nodes on the main thread, at most one per frame -- a near tile's
## 1,650 height samples take ~130 ms, which would otherwise stall a frame each.
## Every tier samples the exact height function; coarse grids' points are a subset of the fine
## ones, and each mesh hangs a short skirt below its edges so tier seams never show a crack.
## Vertex colours tint the ground: grass, bank mud and river bed by carved depth, bare earth on
## steep slopes.  Water surfaces (river, lake) are built alongside (build_water).

static var CHUNKS_ROUND := roundi(StationGeo.CIRC / 65.4)   # chunks round the ring (~65 m each)
const CHUNK_X := 100.0
const GROUP := 8                     # chunks per side of a merged group (the mid and far tiers)
const NEAR := 220.0
const MID := 650.0
const SKIRT := 1.5
const TEX_M := 8.0
const BUDGET_USEC := 5000
static var MAX_TASKS := clampi(OS.get_processor_count() - 2, 2, 6)   # tiles generated at once
const BAKED_FAR := "res://remake/baked/terrain_far.res"
const BAKE_VERSION := 1              # bump when the far tier's output changes
const COL_PARTS := 4                 # a streamed near tile's collision goes in this many pieces, a frame each

var half_w := StationGeo.HALF_LEN
var target: Node3D
var material: Material
var far_material: Material            # for the far tier (T3), if set: RemakeFarSide's flat far side
var _n_cs: int                        # chunks round the ring
var _n_cx: int                        # chunks across
var _t0 := {}                         # Vector2i chunk -> MeshInstance3D (with collision)
var _t1 := {}                         # Vector2i chunk -> MeshInstance3D
var _t2 := {}                         # Vector2i group -> MeshInstance3D
var _t3 := {}                         # Vector2i group -> MeshInstance3D
var _queue: Array = []                # pending builds: [tier, key]
var _far_todo: Array = []             # groups whose far tier isn't built yet
var _tasks := {}                      # WorkerThreadPool task id -> [tier, key]
var _done: Array = []                 # finished generations: [tier, key, arrays]
var _done_lock := Mutex.new()
var _col_queue: Array = []            # [MeshInstance3D, faces]: collision pieces still to add
var _pending := {}                    # [tier, key] being generated, so they aren't queued twice
var _t := 0.0
var _far_task := -1                   # loading the baked far tier
var _far_baked: Array = []            # [[key, arrays]] from it, once loaded


func setup(p_target: Node3D, p_material: Material) -> void:
	target = p_target
	material = p_material
	_n_cs = CHUNKS_ROUND
	_n_cx = ceili(StationGeo.LENGTH / CHUNK_X)
	# nothing big here: only the chunks right under the player are built now (they stand on them);
	# the rest -- near tiers nearest first, then every group's far tier -- builds a few per frame
	for gs in range(0, _n_cs, GROUP):
		for gx in range(0, _n_cx, GROUP):
			_far_todo.append(Vector2i(gs / GROUP, gx / GROUP))
	if ResourceLoader.exists(BAKED_FAR):
		_far_task = WorkerThreadPool.add_task(_load_far, false, "terrain far tier (baked)")
	if target:
		_update()
		var n := 0
		# only the tile underfoot now (~0.4 s): the rest generate on the workers behind the loading screen
		while not _queue.is_empty() and _queue[0][0] == 0 and n < 1:
			_do(_queue.pop_front())
			n += 1
	set_process(target != null)


# ------------------------------------------------------------------ geometry
func _chunk_rect(c: Vector2i) -> Rect2:
	## (s0, x0, ds, dx) of chunk c
	var cs := StationGeo.CIRC / CHUNKS_ROUND
	return Rect2(c.x * cs, -half_w + c.y * CHUNK_X, cs, minf(CHUNK_X, half_w - (-half_w + c.y * CHUNK_X)))


func _group_rect(g: Vector2i) -> Rect2:
	var a := _chunk_rect(Vector2i(g.x * GROUP, g.y * GROUP))
	var b := _chunk_rect(Vector2i(mini(g.x * GROUP + GROUP, _n_cs) - 1, mini(g.y * GROUP + GROUP, _n_cx) - 1))
	return Rect2(a.position, b.end - a.position)


## Ground colours (sRGB; the terrain texture is a neutral detail with mean 1, so these are the
## colours you see).  Town areas, then the map's land cover, then water banks and steep ground.
const GRASS := Color(0.42, 0.53, 0.27)
const AREA_TINT := {"lawn": Color(0.45, 0.6, 0.3), "park": Color(0.43, 0.58, 0.29), "campus": Color(0.45, 0.6, 0.3),
	"schoolground": Color(0.44, 0.57, 0.3), "sportsfield": Color(0.4, 0.6, 0.27), "cemetery": Color(0.36, 0.5, 0.27),
	"square": Color(0.62, 0.6, 0.55), "promenade": Color(0.66, 0.6, 0.5),
	"parking": Color(0.28, 0.28, 0.28), "lot": Color(0.4, 0.38, 0.34), "culdesac": Color(0.3, 0.3, 0.3)}
## farm fields by crop (landcover G = crop + 8 * variant): corn, soybeans, small grain, hay, pasture, set-aside grass
const FIELD_TINT := [Color(0.28, 0.45, 0.15), Color(0.5, 0.6, 0.24), Color(0.7, 0.6, 0.33), Color(0.4, 0.58, 0.27),
	Color(0.45, 0.53, 0.3), Color(0.56, 0.53, 0.35)]
const FIELD_VAR := [0.9, 0.97, 1.03, 1.1]
const MUD := Color(0.4, 0.34, 0.25)
const BED := Color(0.3, 0.27, 0.22)
const EARTH := Color(0.5, 0.43, 0.32)


static func make_material(detail: Texture2D) -> ShaderMaterial:
	## The ground material: terrain_cover.gdshader (land cover per pixel) over the neutral detail grain.
	var m := ShaderMaterial.new()
	m.shader = load("res://remake/shaders/terrain_cover.gdshader")
	m.set_shader_parameter("detail", detail)
	set_cover_params(m)
	return m


static var _lc_tex: ImageTexture = null


static func set_cover_params(m: ShaderMaterial) -> void:
	## The uniforms of land_cover.gdshaderinc (one landcover texture shared by every material).
	if _lc_tex == null:
		_lc_tex = ImageTexture.create_from_image(MapTerrain.landcover_image())
	m.set_shader_parameter("landcover", _lc_tex)
	m.set_shader_parameter("tex_m", TEX_M)
	m.set_shader_parameter("lc_step", MapTerrain.landcover_step())
	m.set_shader_parameter("circ", StationGeo.CIRC)
	m.set_shader_parameter("half_len", StationGeo.HALF_LEN)


func _cover_tint(lc: Vector2i) -> Color:
	match lc.x:
		2: return Color(0.46, 0.6, 0.32)           # floodplain meadow
		3: return Color(0.2, 0.32, 0.14)           # woods (the floor under the trees)
		4:                                         # farm fields: the crop, a shade per parcel
			var f: Color = FIELD_TINT[mini(lc.y % 8, 5)]
			var k: float = FIELD_VAR[(lc.y / 8) % 4]
			return Color(f.r * k, f.g * k, f.b * k)
		5: return Color(0.22, 0.34, 0.15)          # windbreak grove
		6: return Color(0.83, 0.76, 0.58)          # sandy beach
		7: return Color(0.46, 0.43, 0.39)          # rock: the headland cliffs
	return GRASS


func _tint(depth: float, slope: float, area: String = "", lc := Vector2i.ZERO) -> Color:
	var c: Color = AREA_TINT.get(area, _cover_tint(lc))
	c = c.lerp(MUD, clampf(depth / 0.6, 0.0, 1.0))
	c = c.lerp(BED, clampf((depth - 0.6) / 1.5, 0.0, 1.0))
	return c.lerp(EARTH, clampf((slope - 0.35) / 0.3, 0.0, 1.0))


func _build(r: Rect2, step: float, collide: bool, name: String) -> MeshInstance3D:
	return _make(_gen(r, step), collide, name)


func _gen(r: Rect2, step: float) -> Array:
	## The tile's surface arrays (thread-safe: touches no nodes or servers).
	var ns := maxi(1, roundi(r.size.x / step))
	var nx := maxi(1, roundi(r.size.y / step))
	var ups := []
	for i in ns + 1:
		ups.append(StationGeo.up(r.position.x + r.size.x * i / float(ns)))
	var pts := []
	var hs := []
	for i in ns + 1:
		var s := r.position.x + r.size.x * i / float(ns)
		var row_p := []
		var row_h := []
		for j in nx + 1:
			var x := r.position.y + r.size.y * j / float(nx)
			var smp := MapTerrain.sample(s, x)
			row_p.append(StationGeo.point(s, x, smp.x))
			row_h.append([smp.x, smp.y, MapTerrain.area_kind(s, x) if step <= 8.0 else "", MapTerrain.landcover(s, x)])
		pts.append(row_p)
		hs.append(row_h)
	# normals from the grid itself (central differences), so a skirt can carry the ground's normal:
	# the outline pass then sees no edge where tiles meet
	var nrm := []
	for i in ns + 1:
		var row_n := []
		for j in nx + 1:
			var ps: Vector3 = pts[mini(i + 1, ns)][j] - pts[maxi(i - 1, 0)][j]
			var px: Vector3 = pts[i][mini(j + 1, nx)] - pts[i][maxi(j - 1, 0)]
			var n := px.cross(ps).normalized()
			if n.dot(ups[i]) < 0.0:
				n = -n
			row_n.append(n)
		nrm.append(row_n)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in ns:
		for j in nx:
			var q := [[i, j], [i + 1, j], [i + 1, j + 1], [i, j + 1]]
			var slope := absf(hs[i + 1][j][0] - hs[i][j][0]) / (r.size.x / ns) + absf(hs[i][j + 1][0] - hs[i][j][0]) / (r.size.y / nx)
			for k in [0, 1, 2, 0, 2, 3]:            # counter-clockwise seen from above (toward the axis)
				var a: int = q[k][0]
				var b: int = q[k][1]
				# alpha 1: the vertex colour wins (town areas, water beds, steep earth); 0: the shader's
				# per-pixel land cover (sharp field and shore edges)
				var own: bool = hs[a][b][2] != "" or hs[a][b][1] > 0.01 or slope > 0.35
				var col := _tint(hs[a][b][1], slope, hs[a][b][2], hs[a][b][3])
				col.a = 1.0 if own else 0.0
				st.set_color(col)
				st.set_normal(nrm[a][b])
				st.set_uv2(StationGeo.farside_uv(r.position.x + r.size.x * a / float(ns), r.position.y + r.size.y * b / float(nx)))
				st.set_uv(Vector2((r.position.y + r.size.y * b / float(nx)) / TEX_M, (r.position.x + r.size.x * a / float(ns)) / TEX_M))
				st.add_vertex(pts[a][b])
	# skirts: hang each border edge SKIRT m down (along -up), hiding cracks against coarser tiers
	var border := []
	for i in ns:
		border.append([[i, 0], [i + 1, 0]])
		border.append([[i + 1, nx], [i, nx]])
	for j in nx:
		border.append([[ns, j], [ns, j + 1]])
		border.append([[0, j + 1], [0, j]])
	for e in border:
		var a: Array = e[0]
		var b: Array = e[1]
		var pa: Vector3 = pts[a[0]][a[1]]
		var pb: Vector3 = pts[b[0]][b[1]]
		var da: Vector3 = ups[a[0]] * SKIRT
		var db: Vector3 = ups[b[0]] * SKIRT
		var na: Vector3 = nrm[a[0]][a[1]]
		var nb: Vector3 = nrm[b[0]][b[1]]
		for v in [[pa, na], [pb - db, nb], [pb, nb], [pa, na], [pa - da, na], [pb - db, nb]]:
			st.set_color(MUD)
			st.set_normal(v[1])
			st.set_uv(Vector2.ZERO)
			st.add_vertex(v[0])
	return st.commit_to_arrays()


func _make(arrays: Array, collide: bool, name: String, streamed := false) -> MeshInstance3D:
	## streamed: the collision is added over the next COL_PARTS frames (building it is ~10 ms).
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh.surface_set_material(0, material)
	var mi := MeshInstance3D.new()
	mi.name = name
	mi.mesh = mesh
	add_child(mi)
	if collide:
		var faces: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]   # unindexed triangles: the vertices are the faces
		if not streamed:
			_add_collision(mi, faces)
		else:
			var tris := faces.size() / 3
			for k in COL_PARTS:
				_col_queue.append([mi, faces.slice(tris * k / COL_PARTS * 3, tris * (k + 1) / COL_PARTS * 3)])
	return mi


func _add_collision(mi: MeshInstance3D, faces: PackedVector3Array) -> void:
	var body := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	var shape := ConcavePolygonShape3D.new()
	shape.set_faces(faces)
	shape.backface_collision = true          # a ground you can't fall through from either side
	cs.shape = shape
	body.add_child(cs)
	mi.add_child(body)


# ------------------------------------------------------------------ streaming
func _process(delta: float) -> void:
	_ground_under_target()
	_t -= delta
	if _t <= 0.0:
		_t = 0.5
		_update()
	# pieces of near tiles' collision, then finished tiles into nodes, within BUDGET_USEC a frame
	# (always at least one, so a busy frame can't stall it)
	var t0 := Time.get_ticks_usec()
	var first := true
	while first or Time.get_ticks_usec() - t0 < (60000 if StationGeo.loading else BUDGET_USEC):
		first = false
		if not _col_queue.is_empty():
			var c: Array = _col_queue.pop_front()
			if is_instance_valid(c[0]):
				_add_collision(c[0], c[1])
			continue
		_done_lock.lock()
		var res: Array = _done.pop_front() if not _done.is_empty() else []
		_done_lock.unlock()
		if res.is_empty():
			break
		_pending.erase([res[0], res[1]])
		_finish(res[0], res[1], res[2])
	if _far_task >= 0 and WorkerThreadPool.is_task_completed(_far_task):
		WorkerThreadPool.wait_for_task_completion(_far_task)
		_far_task = -1
		if not _far_baked.is_empty():
			_done_lock.lock()
			for kv in _far_baked:
				_pending[[3, kv[0]]] = true
				_done.append([3, kv[0], kv[1]])
			_done_lock.unlock()
			_far_todo.clear()
			_far_baked = []
	for id in _tasks.keys():
		if WorkerThreadPool.is_task_completed(id):
			WorkerThreadPool.wait_for_task_completion(id)
			_tasks.erase(id)
	# start more, nearest first; the far tier fills in when the near work is done
	while _tasks.size() < MAX_TASKS:
		var job: Array = []
		if not _queue.is_empty():
			job = _queue.pop_front()
		elif not _far_todo.is_empty() and _far_task < 0:
			job = [3, _far_todo.pop_front()]
		else:
			break
		var jk := [job[0], job[1]]
		if _pending.has(jk) or _has_tile(job[0], job[1]):
			continue
		_pending[jk] = true
		var r: Rect2 = _chunk_rect(job[1]) if job[0] <= 1 else _group_rect(job[1])
		var step: float = [2.0, 8.0, 8.0, 32.0][job[0]]
		var id := WorkerThreadPool.add_task(_gen_task.bind(job[0], job[1], r, step), false, "terrain tile")
		_tasks[id] = jk


func _ground_under_target() -> void:
	## The tile the player is over must be solid now -- after a teleport, or if streaming fell
	## behind -- so it's built here and then, collision and all (a one-off ~130 ms).
	var p := target.global_position
	var key := Vector2i(posmod(floori(StationGeo.s_of(p) / (StationGeo.CIRC / CHUNKS_ROUND)), _n_cs),
		clampi(floori((p.x + half_w) / CHUNK_X), 0, _n_cx - 1))
	if not _t0.has(key):
		_t0[key] = _build(_chunk_rect(key), 2.0, true, "t0_%d_%d" % [key.x, key.y])
		_apply_visibility(_vis_state[0], _vis_state[1], _vis_state[2])
		return
	var mi: MeshInstance3D = _t0[key]
	var rest := []
	for c in _col_queue:
		if c[0] == mi:
			_add_collision(mi, c[1])
		else:
			rest.append(c)
	_col_queue = rest


static func stamp() -> String:
	## what the far tier is made from: the terrain, its land cover and the pads levelled into it
	return BakedMeshes.fingerprint([MapTerrain.PATH, "res://remake/terrain_base.bin.gz", "res://remake/terrain_level.bin.gz",
		"res://remake/terrain_depth.bin.gz", "res://remake/landcover.png", "res://remake/placement.json"], BAKE_VERSION)


func _load_far() -> void:
	## (worker) the baked far tier, if it's of this terrain
	var b := ResourceLoader.load(BAKED_FAR) as BakedMeshes
	if b == null or b.stamp != stamp():
		push_warning("MapTerrainMesh: the baked far tier is of other data -- building it (rerun remake/tools/bake_world.gd)")
		return
	var out := []
	var far: Dictionary = b.data.get("far", {})
	for key in far:
		out.append([key, far[key]])
	_far_baked = out


func bake_far() -> BakedMeshes:
	## every group's far tier (T3) as vertex arrays (remake/tools/bake_world.gd saves them)
	_n_cs = CHUNKS_ROUND
	_n_cx = ceili(StationGeo.LENGTH / CHUNK_X)
	MapTerrain.elevation(0.0, 0.0)
	var b := BakedMeshes.new()
	b.stamp = stamp()
	var far := {}
	for gs in range(0, _n_cs, GROUP):
		for gx in range(0, _n_cx, GROUP):
			var key := Vector2i(gs / GROUP, gx / GROUP)
			far[key] = _gen(_group_rect(key), 32.0)
	b.data["far"] = far
	return b


func _gen_task(tier: int, key: Vector2i, r: Rect2, step: float) -> void:
	var arrays := _gen(r, step)
	_done_lock.lock()
	_done.append([tier, key, arrays])
	_done_lock.unlock()


func busy() -> bool:
	## Anything still to build or being built (the far-side bake waits on this).
	return not _queue.is_empty() or not _tasks.is_empty() or not _pending.is_empty() or not _col_queue.is_empty() \
		or _far_task >= 0


func _has_tile(tier: int, key: Vector2i) -> bool:
	return [_t0, _t1, _t2, _t3][tier].has(key)


func _finish(tier: int, key: Vector2i, arrays: Array) -> void:
	## A generated tile, if it's still wanted (the player may have moved on).
	if _has_tile(tier, key):
		return
	var want0: Dictionary = _vis_state[0]
	var near_groups: Dictionary = _vis_state[1]
	var want2: Dictionary = _vis_state[2]
	match tier:
		0:
			if want0.has(key):
				_t0[key] = _make(arrays, true, "t0_%d_%d" % [key.x, key.y], true)
		1:
			if near_groups.has(Vector2i(key.x / GROUP, key.y / GROUP)):
				_t1[key] = _make(arrays, false, "t1_%d_%d" % [key.x, key.y])
		2:
			if want2.has(key):
				_t2[key] = _make(arrays, false, "t2_%d_%d" % [key.x, key.y])
		3:
			_t3[key] = _make(arrays, false, "t3_%d_%d" % [key.x, key.y])
			if far_material:
				_t3[key].material_override = far_material
	_apply_visibility(want0, near_groups, want2)


func _exit_tree() -> void:
	for id in _tasks:
		WorkerThreadPool.wait_for_task_completion(id)
	_tasks.clear()
	if _far_task >= 0:
		WorkerThreadPool.wait_for_task_completion(_far_task)
		_far_task = -1


func _update() -> void:
	var p := target.global_position
	var s_here := StationGeo.s_of(p)
	var x_here := p.x
	var cs := StationGeo.CIRC / CHUNKS_ROUND
	var want0 := {}
	var want_near_groups := {}
	var want2 := {}
	for c in range(floori((s_here - NEAR) / cs), floori((s_here + NEAR) / cs) + 1):
		for cx in range(maxi(0, floori((x_here + half_w - NEAR) / CHUNK_X)), mini(_n_cx - 1, floori((x_here + half_w + NEAR) / CHUNK_X)) + 1):
			var key := Vector2i(posmod(c, _n_cs), cx)
			var rc := _chunk_rect(key)
			var dx := maxf(0.0, maxf(rc.position.y - x_here, x_here - rc.end.y))
			var ds := maxf(0.0, absf(_wrap_s(rc.get_center().x - s_here)) - rc.size.x * 0.5)
			if Vector2(ds, dx).length() < NEAR:
				want0[key] = true
				want_near_groups[Vector2i(key.x / GROUP, key.y / GROUP)] = true
	# groups by distance from their nearest point: MID -> merged 8 m tier
	for g in _all_groups():
		var rg := _group_rect(g)
		var dx := maxf(0.0, maxf(rg.position.y - x_here, x_here - rg.end.y))
		var ds := maxf(0.0, absf(_wrap_s(rg.get_center().x - s_here)) - rg.size.x * 0.5)
		if not want_near_groups.has(g) and Vector2(ds, dx).length() < MID:
			want2[g] = true
	# retire what's no longer wanted
	for key in _t0.keys():
		if not want0.has(key):
			_t0[key].queue_free()
			_t0.erase(key)
	for key in _t1.keys():
		if not want_near_groups.has(Vector2i(key.x / GROUP, key.y / GROUP)):
			_t1[key].queue_free()
			_t1.erase(key)
	for g in _t2.keys():
		if not want2.has(g):
			_t2[g].queue_free()
			_t2.erase(g)
	# queue what's missing, nearest first
	_queue.clear()
	var jobs := []
	for key in want0:
		if not _t0.has(key):
			jobs.append([0, key, _chunk_rect(key).get_center()])
	for g in want_near_groups:
		for i in GROUP:
			for j in GROUP:
				var key := Vector2i(g.x * GROUP + i, g.y * GROUP + j)
				if key.x < _n_cs and key.y < _n_cx and not _t1.has(key):
					jobs.append([1, key, _chunk_rect(key).get_center()])
	for g in want2:
		if not _t2.has(g):
			jobs.append([2, g, _group_rect(g).get_center()])
	jobs.sort_custom(func(a, b): return _jobdist(a, s_here, x_here) < _jobdist(b, s_here, x_here))
	_queue = jobs
	_apply_visibility(want0, want_near_groups, want2)


func _all_groups() -> Array:
	var out := []
	for gs in range(0, _n_cs, GROUP):
		for gx in range(0, _n_cx, GROUP):
			out.append(Vector2i(gs / GROUP, gx / GROUP))
	return out


func _jobdist(j: Array, s_here: float, x_here: float) -> float:
	var c: Vector2 = j[2]
	return Vector2(_wrap_s(c.x - s_here), c.y - x_here).length() + j[0] * 50.0


func _wrap_s(ds: float) -> float:
	return StationGeo.wrap_ds(ds)


func _do(job: Array) -> void:
	var tier: int = job[0]
	var key: Vector2i = job[1]
	match tier:
		0:
			if not _t0.has(key):
				_t0[key] = _build(_chunk_rect(key), 2.0, true, "t0_%d_%d" % [key.x, key.y])
		1:
			if not _t1.has(key):
				_t1[key] = _build(_chunk_rect(key), 8.0, false, "t1_%d_%d" % [key.x, key.y])
		2:
			if not _t2.has(key):
				_t2[key] = _build(_group_rect(key), 8.0, false, "t2_%d_%d" % [key.x, key.y])
	_apply_visibility(_vis_state[0], _vis_state[1], _vis_state[2])


var _vis_state := [{}, {}, {}]

func _apply_visibility(want0: Dictionary, near_groups: Dictionary, want2: Dictionary) -> void:
	_vis_state = [want0, near_groups, want2]
	for g in _t3:
		_t3[g].visible = not near_groups.has(g) and not (want2.has(g) and _t2.has(g))
	for g in _t2:
		_t2[g].visible = want2.has(g)
	for key in _t1:
		_t1[key].visible = not (want0.has(key) and _t0.has(key))
	# a near group whose T1 chunks aren't all built yet keeps its T3 until they are
	for g in near_groups:
		var ready := true
		for i in GROUP:
			for j in GROUP:
				var key := Vector2i(g.x * GROUP + i, g.y * GROUP + j)
				if key.x < _n_cs and key.y < _n_cx and not _t1.has(key) and not _t0.has(key):
					ready = false
		if not ready and _t3.has(g):
			_t3[g].visible = true
			for i in GROUP:
				for j in GROUP:
					var key := Vector2i(g.x * GROUP + i, g.y * GROUP + j)
					if _t1.has(key):
						_t1[key].visible = false
					if _t0.has(key):
						_t0[key].visible = true

