extends Node3D
class_name RoadFurniture

## The road standard's signs, traffic signals and railway level crossings (research/roads/
## SSC_ROAD_STANDARD.md §4-5), from remake/road_furniture.json (tools/road_furniture.py).
##   signs     a galvanised post and the face from the sign atlas (remake/textures/road_signs.png,
##             tools/sign_atlas.py), its back a grey silhouette; plates below (ALL WAY, a STOP
##             under a passive crossbuck); town signs and street-name blades are green boards
##             lettered with Label3D
##   xings     P passive: the crossbuck and STOP are in the signs
##             L lights and bell: a mast with the crossbuck, two flashing-light heads, the bell
##             G as L plus a half barrier (red and white boom, held up while no train is near)
##             and concrete panels across the track, rails flush
##   signals   a mast arm over each approach's lane with a three-aspect head
## Merged per CELL m cell and material on a worker thread, like MapRoads.

const CELL := 150.0
const FAR := 420.0
const TEXT_FAR := 90.0
const POST := 0.035                    # post half width
const ATLAS := {                       # name: [cell, back cell, size m]
	"stop": [0, 24, 0.75], "yield": [1, 25, 0.9], "speed_15": [2, 26, 0.75], "speed_40": [3, 26, 0.75],
	"speed_50": [4, 26, 0.75], "speed_60": [5, 26, 0.75], "speed_70": [6, 26, 0.75], "speed_90": [7, 26, 0.75],
	"curve_l": [8, 27, 0.9], "curve_r": [9, 27, 0.9], "junction": [10, 27, 0.9], "rr_ahead": [11, 28, 0.9],
	"stop_ahead": [12, 27, 0.9], "crossbuck": [13, 29, 1.3], "plate_allway": [14, 31, 0.6], "dead_end": [15, 27, 0.9],
	"route_sr14": [16, 30, 0.6], "route_us30": [17, 30, 0.6], "route_coast": [18, 30, 0.6],
	# parking and transit (research/law/04_signs.md): R7 signs are 12 x 18 in (0.3 x 0.45 m) faces on a
	# square cell, so 0.46 m cells; guide signs larger
	"no_parking": [32, 45, 0.46], "no_parking_tram": [33, 45, 0.46], "parking_2h": [34, 45, 0.46], "parking_3h": [35, 45, 0.46],
	"pay_station": [36, 45, 0.46], "tow_away": [37, 45, 0.46], "emergency_route": [38, 26, 0.6], "flood_route": [39, 26, 0.6],
	"accessible": [40, 45, 0.46], "park_ride": [41, 47, 0.9], "parking_guide": [42, 47, 0.6], "no_outlet": [43, 27, 0.75],
	"school": [44, 27, 0.75],
	"tram_port_carrow": [48, 26, 0.6], "tram_kessler": [49, 28, 0.6], "tram_solana_point": [50, 46, 0.65],
	"tram_harrow_falls": [51, 30, 0.65], "tram_brightwater": [52, 28, 0.6], "tram_oceanview": [53, 47, 0.6]}
const STRIPES := 20
const GREEN := 21
const LAMP_RED := 22
const LAMP_OFF := 23

var _d: Dictionary = {}
var _task := -1
var _out: Array = []
var _cells := {}
var _labels: Array = []                # [position, basis, text, size] made on the main thread
var _mats := {}
var _flash: Array = []                 # crossing lamps: none flash until trains run


func setup() -> void:
	if not FileAccess.file_exists("res://remake/road_furniture.json"):
		return
	_d = JSON.parse_string(FileAccess.get_file_as_string("res://remake/road_furniture.json"))
	var atlas := StandardMaterial3D.new()
	atlas.albedo_texture = load("res://remake/textures/road_signs.png")
	atlas.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	atlas.alpha_scissor_threshold = 0.5
	atlas.cull_mode = BaseMaterial3D.CULL_DISABLED
	atlas.roughness = 0.55
	atlas.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	_mats["atlas"] = atlas
	_mats["post"] = _solid(Color(0.62, 0.64, 0.66), 0.35, 0.8)
	_mats["black"] = _solid(Color(0.05, 0.05, 0.05), 0.6)
	_mats["concrete"] = _solid(Color(0.62, 0.61, 0.58), 0.9)
	_mats["steel"] = _solid(Color(0.42, 0.4, 0.38), 0.4, 0.9)
	MapTerrain.elevation(0.0, 0.0)
	_task = WorkerThreadPool.add_task(_build_all, false, "road furniture")
	set_process(true)


func _solid(c: Color, rough: float, metal := 0.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = rough
	m.metallic = metal
	m.cull_mode = BaseMaterial3D.CULL_DISABLED            # (windings vary between the builders' faces)
	return m


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


# ------------------------------------------------------------------ geometry
func _st(s: float, x: float, mat: String) -> SurfaceTool:
	var key := [Vector2i(floori(fposmod(s, StationGeo.CIRC) / CELL), floori(x / CELL)), mat]
	var st: SurfaceTool = _cells.get(key)
	if st == null:
		st = SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		_cells[key] = st
	return st


func _box(st: SurfaceTool, c: Vector3, b: Basis, he: Vector3, uv_cell := -1) -> void:
	## A box at c, axes b (unit columns), half extents he; all faces, outward normals.
	var ax := [b.x, b.y, b.z]
	for a in 3:
		for sg in [-1.0, 1.0]:
			var n: Vector3 = ax[a] * sg
			var u: Vector3 = ax[(a + 1) % 3] * he[(a + 1) % 3]
			var v: Vector3 = ax[(a + 2) % 3] * he[(a + 2) % 3]
			var o: Vector3 = c + n * he[a]
			var q := [o - u - v, o + u - v, o + u + v, o - u + v]
			var uvs := _cell_uv(uv_cell) if uv_cell >= 0 else [Vector2.ZERO, Vector2.ZERO, Vector2.ZERO, Vector2.ZERO]
			var order := [0, 1, 2, 0, 2, 3] if sg > 0 else [0, 2, 1, 0, 3, 2]
			for j in order:
				st.set_normal(n)
				st.set_uv(uvs[j])
				st.add_vertex(q[j])


func _cell_uv(cell: int) -> Array:
	var u0 := (cell % 8) / 8.0
	var v0 := (cell / 8) / 8.0                  # (8 x 8 cells: tools/sign_atlas.py)
	var eps := 0.002
	return [Vector2(u0 + eps, v0 + 0.125 - eps), Vector2(u0 + 0.125 - eps, v0 + 0.125 - eps),
		Vector2(u0 + 0.125 - eps, v0 + eps), Vector2(u0 + eps, v0 + eps)]


func _face(st: SurfaceTool, c: Vector3, b: Basis, size: Vector2, cell: int, back := false) -> void:
	## A sign face centred on c in the plane of b.x / b.y, looking along -b.z (or +b.z for a back).
	var n := -b.z if not back else b.z
	var r := b.x * size.x * 0.5 * (-1.0 if not back else 1.0)     # the viewer's right
	var u := b.y * size.y * 0.5
	var q := [c - r - u, c + r - u, c + r + u, c - r + u]           # bottom-left, bottom-right, top-right, top-left
	var uvs := _cell_uv(cell)
	for j in [0, 1, 2, 0, 2, 3]:
		st.set_normal(n)
		st.set_uv(uvs[j])
		st.add_vertex(q[j])


func _ground(s: float, x: float) -> float:
	return MapTerrain.elevation(s, x)


# ------------------------------------------------------------------ builders
func _build_all() -> void:
	for sg in _d.get("signs", []):
		_sign(sg)
	for xg in _d.get("xings", []):
		_xing(xg)
	for sig in _d.get("signals", []):
		_signal(sig)
	var out := []
	for key in _cells:
		var arr := (_cells[key] as SurfaceTool).commit_to_arrays()
		if arr[Mesh.ARRAY_VERTEX] != null and (arr[Mesh.ARRAY_VERTEX] as PackedVector3Array).size() > 0:
			out.append([key, arr])
	_cells.clear()
	_out = out


func _sign(sg: Dictionary) -> void:
	var s: float = sg.s
	var x: float = sg.x
	var t: String = sg.t
	var h: float = sg.h
	var g := _ground(s, x)
	var b := StationGeo.basis(s, float(sg.yaw))
	var base := StationGeo.point(s, x, g)
	var up := b.y
	if t == "town" or t == "blade":
		var w := 2.6 if t == "town" else 1.3
		var hh := 1.1 if t == "town" else 0.22
		var top := h + hh
		# posts (two for a town sign) and the green board
		var posts := [-w * 0.35, w * 0.35] if t == "town" else [0.0]
		for px in posts:
			_box(_st(s, x, "post"), base + b.x * px + up * (top * 0.5 - 0.15), b, Vector3(POST * 1.4, top * 0.5 + 0.15, POST * 1.4))
		var c := base + up * (h + hh * 0.5) - b.z * 0.05
		if t == "blade":
			c = base + up * (h + 0.3)
		_box(_st(s, x, "atlas"), c, b, Vector3(w * 0.5, hh * 0.5, 0.02), GREEN)
		_labels.append([c - b.z * 0.03, b, str(sg.get("txt", "")), 0.3 if t == "town" else 0.13, false])
		if t == "blade":
			_labels.append([c + b.z * 0.03, b, str(sg.get("txt", "")), 0.13, true])
		return
	if not ATLAS.has(t):
		return
	var a: Array = ATLAS[t]
	var size: float = a[2]
	var face_c := base + up * (h + size * 0.5) - b.z * 0.05
	var plate: String = sg.get("plate", "")
	var top := h + size
	_box(_st(s, x, "post"), base + up * (top * 0.5 - 0.3), b, Vector3(POST, top * 0.5 + 0.3 - 0.02, POST))
	var st := _st(s, x, "atlas")
	_face(st, face_c, b, Vector2(size, size), a[0])
	_face(st, face_c + b.z * 0.006, b, Vector2(size, size), a[1], true)
	if plate == "allway":
		var pc := base + up * (h - 0.2) - b.z * 0.05
		_face(st, pc, b, Vector2(0.6, 0.6), ATLAS.plate_allway[0])
		_face(st, pc + b.z * 0.006, b, Vector2(0.6, 0.6), ATLAS.plate_allway[1], true)
	elif plate == "stop":
		# a passive crossing: the STOP sign below the crossbuck
		var pc := base + up * (h - 0.55) - b.z * 0.05
		_face(st, pc, b, Vector2(0.75, 0.75), ATLAS.stop[0])
		_face(st, pc + b.z * 0.006, b, Vector2(0.75, 0.75), ATLAS.stop[1], true)


func _xing(xg: Dictionary) -> void:
	var p := Vector2(xg.s, xg.x)
	var u := Vector2(xg.u[0], xg.u[1])
	var ru := Vector2(xg.ru[0], xg.ru[1])
	var w: float = xg.w
	var hw := w * 0.5
	var lvl: String = xg.level
	# the concrete panels across the track (road width, 2.6 m along the road each side of the rail),
	# the rails flush in them
	var n := Vector2(-ru.y, ru.x)                      # across the rail
	var st := _st(p.x, p.y, "concrete")
	# along the rail the road's width is stretched by the skew: w / sin(angle) = w / |u . n|
	var half_along := minf((hw + 0.5) / maxf(0.35, absf(u.dot(n))), w * 1.6)
	var upv := StationGeo.up(p.x)
	var N := 4                                          # a grid, so the panel lies on the graded road
	for i in N:
		for j in N:
			var q := []
			for c in [[i, j], [i + 1, j], [i + 1, j + 1], [i, j + 1]]:
				var g: Vector2 = p + ru * lerpf(-half_along, half_along, c[0] / float(N)) + n * lerpf(-2.6, 2.6, c[1] / float(N))
				q.append(StationGeo.point(g.x, g.y, _ground(g.x, g.y) + 0.1))
			for k in [0, 2, 1, 0, 3, 2]:
				st.set_normal(upv)
				st.set_uv(Vector2.ZERO)
				st.add_vertex(q[k])
	var rs := _st(p.x, p.y, "steel")
	for g in [-0.72, 0.72]:
		for i in N * 2:
			var a0: Vector2 = p + n * g + ru * lerpf(-half_along, half_along, i / float(N * 2))
			var a1: Vector2 = p + n * g + ru * lerpf(-half_along, half_along, (i + 1) / float(N * 2))
			var h0 := _ground(a0.x, a0.y) + 0.125
			var h1 := _ground(a1.x, a1.y) + 0.125
			var q := [StationGeo.point(a0.x - n.x * 0.04, a0.y - n.y * 0.04, h0), StationGeo.point(a1.x - n.x * 0.04, a1.y - n.y * 0.04, h1),
				StationGeo.point(a1.x + n.x * 0.04, a1.y + n.y * 0.04, h1), StationGeo.point(a0.x + n.x * 0.04, a0.y + n.y * 0.04, h0)]
			for k in [0, 2, 1, 0, 3, 2]:
				rs.set_normal(upv)
				rs.set_uv(Vector2.ZERO)
				rs.add_vertex(q[k])
	if lvl == "P":
		return
	for sgn in [1.0, -1.0]:
		var arm: Vector2 = u * sgn                               # away from the crossing, toward the approaching traffic
		var travel: Vector2 = -arm
		var right := Vector2(-travel.y, travel.x)
		var back := 4.2 / maxf(0.35, absf(arm.dot(n)))
		var m: Vector2 = p + arm * back + right * (hw + 1.1)
		var yaw := atan2(-arm.y, arm.x)                  # the faces look back along the arm, at the traffic
		var b := StationGeo.basis(m.x, yaw)
		var base := StationGeo.point(m.x, m.y, _ground(m.x, m.y))
		var up := b.y
		# the mast, its foundation, the crossbuck, the light cross-arm, two light heads, the bell
		_box(_st(m.x, m.y, "concrete"), base + up * 0.1, b, Vector3(0.35, 0.2, 0.35))
		_box(_st(m.x, m.y, "post"), base + up * 2.1, b, Vector3(0.07, 2.1, 0.07))
		var at := _st(m.x, m.y, "atlas")
		var cb := base + up * 3.65 - b.z * 0.09
		_face(at, cb, b, Vector2(1.3, 1.3), ATLAS.crossbuck[0])
		_face(at, cb + b.z * 0.006, b, Vector2(1.3, 1.3), ATLAS.crossbuck[1], true)
		_box(_st(m.x, m.y, "black"), base + up * 2.55, b, Vector3(0.75, 0.05, 0.05))
		for lx in [-0.62, 0.62]:
			var lc: Vector3 = base + b.x * lx + up * 2.55 - b.z * 0.12
			_box(_st(m.x, m.y, "black"), lc + b.z * 0.02, b, Vector3(0.32, 0.32, 0.03))
			_face(at, lc - b.z * 0.02, b, Vector2(0.28, 0.28), LAMP_OFF)
			_box(_st(m.x, m.y, "black"), lc - b.z * 0.14 + up * 0.15, b, Vector3(0.16, 0.02, 0.12))     # the hood
			_flash.append([lc - b.z * 0.025, b])
		_box(_st(m.x, m.y, "black"), base + up * 4.45, b, Vector3(0.14, 0.1, 0.14))                   # the bell
		if lvl == "G":
			# the half barrier: a mechanism box behind the mast and the boom, held upright
			var gm := base - b.z * 0.4 + up * 0.7
			_box(_st(m.x, m.y, "post"), gm, b, Vector3(0.25, 0.7, 0.2))
			var boom_len := hw + 0.8
			_box(_st(m.x, m.y, "atlas"), gm + up * (0.8 + boom_len * 0.5) - b.x * 0.3, b,
				Vector3(0.06, boom_len * 0.5, 0.06), STRIPES)


func _signal(sig: Dictionary) -> void:
	var p := Vector2(sig.s, sig.x)
	for arm in sig.arms:
		var a := Vector2(arm[0], arm[1])
		var hw: float = float(arm[2]) * 0.5
		var travel := -a
		var right := Vector2(-travel.y, travel.x)
		var m := p + a * (hw + 6.0) + right * (hw + 1.0)
		var yaw := atan2(-a.y, a.x)
		var b := StationGeo.basis(m.x, yaw)
		var base := StationGeo.point(m.x, m.y, _ground(m.x, m.y))
		var up := b.y
		_box(_st(m.x, m.y, "post"), base + up * 2.9, b, Vector3(0.1, 2.9, 0.1))
		# the mast arm reaches over the approach's lane (toward the road's middle: the viewer's left)
		var reach := hw * 0.5 + 1.0
		var arm_c := base + up * 5.6 + b.x * (reach * 0.5)
		_box(_st(m.x, m.y, "post"), arm_c, b, Vector3(reach * 0.5, 0.06, 0.06))
		var head := base + up * 5.0 + b.x * reach
		_box(_st(m.x, m.y, "black"), head, b, Vector3(0.18, 0.5, 0.14))
		var at := _st(m.x, m.y, "atlas")
		for k in 3:
			_face(at, head + up * (0.3 - 0.3 * k) - b.z * 0.15, b, Vector2(0.22, 0.22), LAMP_OFF)


# ------------------------------------------------------------------ knocked down
var _removed := {}                   # sign indices no longer standing


func _cell_of(s: float, x: float) -> Vector2i:
	return Vector2i(floori(fposmod(s, StationGeo.CIRC) / CELL), floori(x / CELL))


func remove_sign(i: int) -> void:
	## A sign knocked down: its cell's meshes are built again without it.
	var signs: Array = _d.get("signs", [])
	if i < 0 or i >= signs.size() or _removed.has(i):
		return
	_removed[i] = true
	var cell := _cell_of(float(signs[i].s), float(signs[i].x))
	_cells.clear()
	for k in signs.size():
		if not _removed.has(k) and _cell_of(float(signs[k].s), float(signs[k].x)) == cell:
			_sign(signs[k])
	for xg in _d.get("xings", []):
		if _cell_of(float(xg.s), float(xg.x)) == cell:
			_xing(xg)
	for sig in _d.get("signals", []):
		if _cell_of(float(sig.s), float(sig.x)) == cell:
			_signal(sig)
	for mat in ["post", "atlas"]:
		var old := get_node_or_null("furniture_%d_%d_%s" % [cell.x, cell.y, mat])
		if old:
			old.free()
	var built: Dictionary = _cells.duplicate()
	_cells.clear()
	for key in built:
		if (key as Array)[0] != cell:
			continue
		var arr := (built[key] as SurfaceTool).commit_to_arrays()
		if arr[Mesh.ARRAY_VERTEX] != null and (arr[Mesh.ARRAY_VERTEX] as PackedVector3Array).size() > 0:
			_out.append([key, arr])
	var labels := _labels
	_labels = []
	_commit()
	_labels = labels


func sign_mesh(i: int) -> Array:
	## [ArrayMesh in the sign's own frame, its base transform]: the sign alone, to put on a body.
	var signs: Array = _d.get("signs", [])
	var sg: Dictionary = signs[i]
	var s: float = sg.s
	var x: float = sg.x
	var xf := Transform3D(StationGeo.basis(s, float(sg.yaw)), StationGeo.point(s, x, MapTerrain.elevation(s, x)))
	var inv := xf.affine_inverse()
	_cells.clear()
	_sign(sg)
	var mesh := ArrayMesh.new()
	for key in _cells:
		var arr := (_cells[key] as SurfaceTool).commit_to_arrays()
		var vs: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
		if vs == null or vs.size() == 0:
			continue
		var ns: PackedVector3Array = arr[Mesh.ARRAY_NORMAL]
		for k in vs.size():
			vs[k] = inv * vs[k]
			if ns != null and k < ns.size():
				ns[k] = inv.basis * ns[k]
		arr[Mesh.ARRAY_VERTEX] = vs
		if ns != null:
			arr[Mesh.ARRAY_NORMAL] = ns
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
		mesh.surface_set_material(mesh.get_surface_count() - 1, _mats[(key as Array)[1]])
	_cells.clear()
	return [mesh, xf]


func _commit() -> void:
	for job in _out:
		var key: Array = job[0]
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, job[1])
		mesh.surface_set_material(0, _mats[key[1]])
		var mi := MeshInstance3D.new()
		mi.name = "furniture_%d_%d_%s" % [key[0].x, key[0].y, key[1]]
		mi.mesh = mesh
		mi.visibility_range_end = FAR
		mi.visibility_range_end_margin = FAR * 0.1
		add_child(mi)
	_out.clear()
	var font: Font = load("res://ui/pda/DejaVuSans-Bold.ttf")
	for lb in _labels:
		var l := Label3D.new()
		l.text = lb[2]
		l.font = font
		l.pixel_size = 0.001
		l.font_size = int(lb[3] * 1000.0)
		l.outline_size = 0
		l.modulate = Color(0.97, 0.97, 0.95)
		l.shaded = true
		l.double_sided = false
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.visibility_range_end = TEXT_FAR
		var b: Basis = lb[1]
		# a Label3D reads toward its +z: turn it to face the sign's front (-b.z), or its back
		l.transform = Transform3D(b if lb[4] else b.rotated(b.y, PI), lb[0])
		add_child(l)
	_labels.clear()
