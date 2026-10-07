extends Node3D
class_name MapTrees

## Trees where the map has them: its woods (riparian strips along the creeks, the steep bluff
## faces) and the windbreak grove behind each farmstead (MapTerrain.landcover classes 3 and 5).
## A jittered grid -- every WOODS_STEP / GROVE_STEP m, each tree's offset, size and turn a hash of
## its grid spot, so the same trees come back every time -- skipping roads, water and built land.
## Drawn as MultiMeshes per CELL m cell, one draw call each:
##   near (< NEAR m)  a low-poly deciduous tree, trunk + two-lobed canopy (~130 triangles)
##   far  (< FAR m)   one squat blob (~20 triangles)
##   beyond            the woods' ground tint alone
## Placed on worker threads (MapTerrain is read-only once loaded); the main thread only makes the
## MultiMesh nodes, BUDGET_USEC a frame.
## Collision: the trees within COLLIDE_R m of a player (or of anything in the "tree_collide" group,
## e.g. a summoned aerostat) are solid -- a trunk cylinder and a canopy sphere each, made straight
## on the physics server (no nodes), one static body per SUB m square, and freed past DROP_R.

const WOODS_STEP := 6.0
const GROVE_STEP := 5.0
const CELL := 400.0
const NEAR := 320.0
const FAR := 900.0

const BUDGET_USEC := 4000
const BAKED := "res://remake/baked/trees.res"
const BAKE_VERSION := 1              # bump when the placement changes

var _cells: Array = []
var _task := -1
var _done: Array = []                # [cell, xforms, cols] from the workers
var _lock := Mutex.new()
var _made := 0
var _near_mesh: ArrayMesh
var _far_mesh: ArrayMesh

const SUB := 50.0                    # collider squares
const COLLIDE_R := 140.0
const DROP_R := 200.0
const TRUNK_H := 5.0                 # the near mesh's trunk and main canopy lobe (unscaled)
const TRUNK_R := 0.3
const CANOPY_Y := 6.8
const CANOPY_R := 3.0                # a little inside the lobe, so a brush past the leaves isn't a crash
var _bufs := {}                      # cell -> its instance buffer
var _trees_in := {}                  # cell -> {sub Vector2i: [Transform3D]} (decoded when first needed)
var _bodies := {}                    # Vector2i(sub s, sub x) -> body RID
var _shapes := {}                    # quantised size key -> shape RID
var _next_scan := 0


func setup() -> void:
	MapTerrain.elevation(0.0, 0.0)
	_near_mesh = _tree_mesh(true)
	_far_mesh = _tree_mesh(false)
	for cs in ceili(StationGeo.CIRC / CELL):
		for cx in ceili(StationGeo.LENGTH / CELL):
			_cells.append(Vector2i(cs, cx))
	if ResourceLoader.exists(BAKED):
		_task = WorkerThreadPool.add_task(_load_baked, false, "trees (baked)")
		_single = true
	else:
		_task = WorkerThreadPool.add_group_task(_cell_task, _cells.size(), -1, false, "trees")
	set_process(true)


var _single := false                  # _task is a plain task (the baked load), not a group task


static func stamp() -> String:
	## what the trees stand on: the land cover, the terrain, the roads and water they keep off
	return BakedMeshes.fingerprint([MapTerrain.PATH, "res://remake/terrain_base.bin.gz",
		"res://remake/terrain_level.bin.gz", "res://remake/terrain_depth.bin.gz", "res://remake/placement.json"], BAKE_VERSION)


func _load_baked() -> void:
	## (worker) the baked trees if they're of this map; else place them here after all
	var b := BakedMeshes.load_all(BAKED)
	if b and b.stamp == stamp():
		var cells: Dictionary = b.data.get("cells", {})
		var out := []
		for c in _cells:
			out.append([c, cells.get(c, PackedFloat32Array())])
		_lock.lock()
		_done.append_array(out)
		_lock.unlock()
		return
	push_warning("MapTrees: the baked trees are of other map data -- placing them (rerun remake/tools/bake_world.gd)")
	for i in _cells.size():
		_cell_task(i)


static func buffer_of(xforms: Array, cols: Array) -> PackedFloat32Array:
	## a MultiMesh's instance buffer (3D transforms, colours): 12 floats of transform, 4 of colour each
	var buf := PackedFloat32Array()
	buf.resize(xforms.size() * 16)
	for k in xforms.size():
		var t: Transform3D = xforms[k]
		var c: Color = cols[k]
		var o := k * 16
		var b := t.basis
		var vals := [b.x.x, b.y.x, b.z.x, t.origin.x, b.x.y, b.y.y, b.z.y, t.origin.y, b.x.z, b.y.z, b.z.z, t.origin.z,
			c.r, c.g, c.b, c.a]
		for v in 16:
			buf[o + v] = vals[v]
	return buf


func bake() -> BakedMeshes:
	## every cell's trees, as MultiMesh buffers (remake/tools/bake_world.gd saves them)
	MapTerrain.elevation(0.0, 0.0)
	var b := BakedMeshes.new()
	b.stamp = stamp()
	var cells := {}
	for cs in ceili(StationGeo.CIRC / CELL):
		for cx in ceili(StationGeo.LENGTH / CELL):
			var c := Vector2i(cs, cx)
			var r := _place(c)
			if not (r[0] as Array).is_empty():
				cells[c] = buffer_of(r[0], r[1])
	b.data["cells"] = cells
	return b


func _cell_task(i: int) -> void:
	var r := _place(_cells[i])
	_lock.lock()
	_done.append([_cells[i], buffer_of(r[0], r[1])])
	_lock.unlock()


func _process(_delta: float) -> void:
	var t0 := Time.get_ticks_usec()
	while Time.get_ticks_usec() - t0 < (60000 if StationGeo.loading else BUDGET_USEC):
		_lock.lock()
		var job: Array = _done.pop_back() if not _done.is_empty() else []
		_lock.unlock()
		if job.is_empty():
			break
		_make(job[0], job[1])
		_made += 1
	if _made >= _cells.size() and _task >= 0:
		_wait()
	if Time.get_ticks_msec() >= _next_scan:
		_next_scan = Time.get_ticks_msec() + 250
		_stream_colliders()


func loaded() -> bool:
	## every cell's trees are drawn (collision streams on after)
	return _made >= _cells.size()


func _wait() -> void:
	if _task < 0:
		return
	if _single:
		WorkerThreadPool.wait_for_task_completion(_task)
	else:
		WorkerThreadPool.wait_for_group_task_completion(_task)
	_task = -1


func _exit_tree() -> void:
	_wait()
	for k in _bodies:
		PhysicsServer3D.free_rid(_bodies[k])
	_bodies.clear()
	for k in _shapes:
		PhysicsServer3D.free_rid(_shapes[k])
	_shapes.clear()


# ------------------------------------------------------------------ collision
func _stream_colliders() -> void:
	## Solid trees near whoever can hit them; the rest none.
	var ns := ceili(StationGeo.CIRC / SUB)
	var want := {}
	var centres: Array = []
	for n in get_tree().get_nodes_in_group("player") + get_tree().get_nodes_in_group("tree_collide"):
		if n is Node3D and (n as Node3D).is_inside_tree():
			centres.append((n as Node3D).global_position)
	for p in centres:
		var s := fposmod(StationGeo.s_of(p), StationGeo.CIRC)
		var x: float = p.x
		var r := ceili(DROP_R / SUB)
		var i0 := floori(s / SUB)
		var j0 := floori((x + StationGeo.HALF_LEN) / SUB)
		for di in range(-r, r + 1):
			for dj in range(-r, r + 1):
				var j := j0 + dj
				if j < 0 or j * SUB >= StationGeo.LENGTH:
					continue
				var i := posmod(i0 + di, ns)
				var ds := absf((i0 + di + 0.5) * SUB - s)
				var dx := absf((j + 0.5) * SUB - (x + StationGeo.HALF_LEN))
				var d := Vector2(maxf(0.0, ds - SUB * 0.5), maxf(0.0, dx - SUB * 0.5)).length()
				var k := Vector2i(i, j)
				if d <= COLLIDE_R:
					want[k] = true
				elif d <= DROP_R and _bodies.has(k) and not want.has(k):
					want[k] = false                  # keep what's there (hysteresis), don't make it
	for k in _bodies.keys():
		if not want.has(k):
			PhysicsServer3D.free_rid(_bodies[k])
			_bodies.erase(k)
	var made := 0
	for k in want:
		if want[k] and not _bodies.has(k) and made < 6:
			_bodies[k] = _make_body(k)
			made += 1
	if made == 6:
		_next_scan = 0                               # more to do: again next frame


func _make_body(k: Vector2i) -> RID:
	var body := PhysicsServer3D.body_create()
	PhysicsServer3D.body_set_mode(body, PhysicsServer3D.BODY_MODE_STATIC)
	PhysicsServer3D.body_set_space(body, get_world_3d().space)
	PhysicsServer3D.body_set_collision_layer(body, 1)
	PhysicsServer3D.body_set_collision_mask(body, 0)
	# the square's own cell, and across a cell edge the next one (a tree's jitter can take it over)
	var trees: Array = []
	var cells := {}
	for e in [Vector2(-3, -3), Vector2(-3, 3), Vector2(SUB + 3, -3), Vector2(SUB + 3, SUB + 3), Vector2(-3, SUB + 3),
			Vector2(SUB * 0.5, SUB * 0.5)]:
		var cs := posmod(floori((k.x * SUB + e.x) / CELL), ceili(StationGeo.CIRC / CELL))
		var cx := floori((k.y * SUB + e.y) / CELL)
		cells[Vector2i(cs, cx)] = true
	for cell in cells:
		trees.append_array(_sub_trees(cell).get(k, []))
	for t: Transform3D in trees:
		var sx := t.basis.x.length()
		var sy := t.basis.y.length()
		var b := t.basis.orthonormalized()
		var trunk := _shape("t", sx, sy)
		PhysicsServer3D.body_add_shape(body, trunk, Transform3D(b, t.origin + b.y * (TRUNK_H * 0.5 * sy)))
		var canopy := _shape("c", sx, sy)
		PhysicsServer3D.body_add_shape(body, canopy, Transform3D(b, t.origin + b.y * (CANOPY_Y * sy)))
	return body


func _sub_trees(cell: Vector2i) -> Dictionary:
	## A cell's trees sorted into collider squares (decoded from its buffer once).
	if _trees_in.has(cell):
		return _trees_in[cell]
	var out := {}
	var buf: PackedFloat32Array = _bufs.get(cell, PackedFloat32Array())
	for o in range(0, buf.size(), 16):
		var t := Transform3D(Basis(Vector3(buf[o], buf[o + 4], buf[o + 8]), Vector3(buf[o + 1], buf[o + 5], buf[o + 9]),
			Vector3(buf[o + 2], buf[o + 6], buf[o + 10])), Vector3(buf[o + 3], buf[o + 7], buf[o + 11]))
		var s := fposmod(StationGeo.s_of(t.origin), StationGeo.CIRC)
		var k := Vector2i(mini(floori(s / SUB), ceili(StationGeo.CIRC / SUB) - 1), floori((t.origin.x + StationGeo.HALF_LEN) / SUB))
		if not out.has(k):
			out[k] = []
		out[k].append(t)
	_trees_in[cell] = out
	return out


func _shape(kind: String, sx: float, sy: float) -> RID:
	## Shared shapes, by size to the nearest 5 %.
	var qx := roundi(sx * 20.0)
	var qy := roundi(sy * 20.0)
	var key := "%s%d_%d" % [kind, qx, qy]
	if _shapes.has(key):
		return _shapes[key]
	var rid: RID
	if kind == "t":
		rid = PhysicsServer3D.cylinder_shape_create()
		PhysicsServer3D.shape_set_data(rid, {"radius": TRUNK_R * qx / 20.0, "height": TRUNK_H * qy / 20.0})
	else:
		rid = PhysicsServer3D.sphere_shape_create()
		PhysicsServer3D.shape_set_data(rid, CANOPY_R * qx / 20.0)
	_shapes[key] = rid
	return rid


func _place(c: Vector2i) -> Array:
	## The cell's trees: [transforms, colours] (thread-safe: touches no nodes).
	var s0 := c.x * CELL
	var x0 := -StationGeo.HALF_LEN + c.y * CELL
	var xforms: Array[Transform3D] = []
	var cols: Array[Color] = []
	var step := minf(WOODS_STEP, GROVE_STEP)
	var i := 0
	while i * step < CELL:
		var j := 0
		while j * step < CELL:
			var s := s0 + i * step
			var x := x0 + j * step
			j += 1
			if s >= StationGeo.CIRC or absf(x) > StationGeo.HALF_LEN - 35.0:     # clear of the cliffs' scree
				continue
			var lc := MapTerrain.landcover(s, x)
			if lc.x != 3 and lc.x != 5:
				continue
			var gs := GROVE_STEP if lc.x == 5 else WOODS_STEP
			# thin the finer grid to this cover's spacing, deterministically
			if lc.x == 3 and _hash(floori(s / step), floori(x / step), 0) > (step / gs) * (step / gs):
				continue
			var js := s + (_hash(floori(s), floori(x), 1) - 0.5) * gs * 0.8
			var jx := x + (_hash(floori(s), floori(x), 2) - 0.5) * gs * 0.8
			if MapTerrain.road_weight(js, jx) > 0.05 or MapTerrain.water_depth(js, jx) > 0.1:
				continue
			var h := MapTerrain.elevation(js, jx)
			var sc := 0.75 + 0.6 * _hash(floori(s), floori(x), 3)
			var b := StationGeo.basis(js, TAU * _hash(floori(s), floori(x), 4)).scaled(Vector3(sc, sc * (0.9 + 0.25 * _hash(floori(s), floori(x), 5)), sc))
			xforms.append(Transform3D(b, StationGeo.point(js, jx, h - 0.2)))
			var g := 0.85 + 0.3 * _hash(floori(s), floori(x), 6)
			cols.append(Color(g * (0.95 + 0.1 * _hash(floori(s), floori(x), 7)), g, g * 0.9))
		i += 1
	return [xforms, cols]


static func under_bridge(p: Vector3) -> bool:
	## Is p under a great bridge's deck (its approaches climb over woods)?  No tree grows through it.
	var s := StationGeo.s_of(p)
	for sp in GreatBridges.decks:
		if GreatBridges.off_line(sp, s, p.x) < float(sp.hw) + 5.0:
			return true
	return false


func _clear_of_bridges(c: Vector2i, buf: PackedFloat32Array) -> PackedFloat32Array:
	## The cell's trees less any under a great bridge (only cells a bridge's line passes near are looked at).
	var mid := Vector2((c.x + 0.5) * CELL, -StationGeo.HALF_LEN + (c.y + 0.5) * CELL)
	var near := false
	for sp in GreatBridges.decks:
		for q: Vector2 in sp.line:
			if absf(StationGeo.wrap_ds(q.x - mid.x)) < CELL * 0.5 + 20.0 and absf(q.y - mid.y) < CELL * 0.5 + 20.0:
				near = true
				break
	if not near:
		return buf
	var out := PackedFloat32Array()
	for k in range(0, buf.size(), 16):
		if not under_bridge(Vector3(buf[k + 3], buf[k + 7], buf[k + 11])):
			out.append_array(buf.slice(k, k + 16))
	return out


func _make(c: Vector2i, buf: PackedFloat32Array) -> void:
	buf = _clear_of_bridges(c, buf)
	if buf.is_empty():
		return
	_bufs[c] = buf
	for version in [[_near_mesh, 0.0, NEAR], [_far_mesh, NEAR, FAR]]:
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_colors = true
		mm.mesh = version[0]
		mm.instance_count = buf.size() / 16
		mm.buffer = buf
		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.visibility_range_begin = version[1]
		mmi.visibility_range_begin_margin = version[1] * 0.08
		mmi.visibility_range_end = version[2]
		mmi.visibility_range_end_margin = version[2] * 0.08
		mmi.name = "trees_%d_%d_%s" % [c.x, c.y, "near" if version[1] == 0.0 else "far"]
		add_child(mmi)


static func _hash(a: int, b: int, salt: int) -> float:
	var h := (a * 73856093) ^ (b * 19349663) ^ (salt * 83492791)
	h = ((h ^ (h >> 13)) * 1274126177) & 0x7fffffff
	return float(h % 100000) / 100000.0


func _tree_mesh(near: bool) -> ArrayMesh:
	## A deciduous tree about 11 m tall (local y up): trunk and a two-lobed canopy -- or, far, one
	## squat blob.  Leaves and bark take the instance colour (a per-tree tint).
	var mesh := ArrayMesh.new()
	var bark := StandardMaterial3D.new()
	bark.albedo_color = Color(0.3, 0.24, 0.18)
	bark.vertex_color_use_as_albedo = true
	var leaf := StandardMaterial3D.new()
	leaf.albedo_color = Color(0.26, 0.4, 0.17)
	leaf.vertex_color_use_as_albedo = true
	leaf.roughness = 0.95
	var bark_st := SurfaceTool.new()
	var leaf_st := SurfaceTool.new()
	if near:
		var trunk := CylinderMesh.new()
		trunk.top_radius = 0.18
		trunk.bottom_radius = 0.3
		trunk.height = 5.0
		trunk.radial_segments = 6
		trunk.rings = 1
		bark_st.append_from(trunk, 0, Transform3D(Basis(), Vector3(0, 2.5, 0)))
		var lobe := SphereMesh.new()
		lobe.radius = 3.4
		lobe.height = 5.6
		lobe.radial_segments = 8
		lobe.rings = 4
		leaf_st.append_from(lobe, 0, Transform3D(Basis(), Vector3(0, 6.8, 0)))
		var lobe2 := SphereMesh.new()
		lobe2.radius = 2.4
		lobe2.height = 4.0
		lobe2.radial_segments = 7
		lobe2.rings = 3
		leaf_st.append_from(lobe2, 0, Transform3D(Basis(), Vector3(0.9, 9.0, -0.4)))
		bark_st.set_material(bark)
		bark_st.commit(mesh)
	else:
		var blob := SphereMesh.new()
		blob.radius = 3.6
		blob.height = 8.0
		blob.radial_segments = 5
		blob.rings = 2
		leaf_st.append_from(blob, 0, Transform3D(Basis(), Vector3(0, 6.0, 0)))
	leaf_st.set_material(leaf)
	leaf_st.commit(mesh)
	return mesh
