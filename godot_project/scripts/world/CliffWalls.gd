extends Node3D
class_name CliffWalls

## The end caps' cliffs: a 150 m sedimentary bluff standing against each end wall (x = +-width/2),
## all the way round the ring, with a scree apron at its foot.  Above 150 m the station wall takes
## over.
##
## The shape is a closed-form function of (end, s, h) -- position round the ring and height above
## the wall foot -- so any piece can be built on its own, in any order, deterministically:
##   * the face leans out from the wall (up to LEAN at its foot, meeting the wall at the top),
##     with bays and headlands along s;
##   * strata 4-9 m thick, each either a proud limestone ledge or a recessed shale band, and
##     the beds dip gently along s;
##   * fine roughness;
##   * talus at SCREE_SLOPE up to ~SCREE_H against the foot.
## The deepest point stays within ~30 m of the wall, the map's no-build margin.
##
## Distance versions:
## all tiled alike, TILES_ROUND tiles (~131 m) round each end:
##   LOD0 (< NEAR m)  2 m x 1.5 m grid, built on demand near the player (one tile per 0.5 s), with
##                    collision (the scree is walkable, the face isn't climbable); hides the tile's
##                    LOD1 while it's loaded
##   LOD1 (< MID m)   6 m grid, same shape
##   LOD2 (>= MID m)  the smooth lean/bay surface only (no ledges or roughness) -- "just the
##                    texture", with the strata's colour bands in the vertex colours
## Materials: remake/textures/cliff/bedrock (face) and scree (talus), both tinted by the strata
## tone in the vertex colour.

const HEIGHT := 150.0
const LEAN := 10.0
const BAY := 5.0
const SCREE_H := 8.0
const SCREE_SLOPE := 34.0
const TEX_M := 24.0                 # bedrock texture tile (its beds read 1-3 m thick)
const SCREE_TEX_M := 4.0
const NEAR := 180.0                 # LOD0 within this of the player (built/freed as they move)
const MID := 700.0                  # LOD1 -> LOD2

var half_w := StationGeo.HALF_LEN
var target: Node3D                  # the player; LOD0 tiles follow it
var _mats := {}
var _lod0 := {}                     # key "end:seg" -> Node3D

static func face_u(end: int, s: float, h: float) -> float:
	## Distance of the cliff surface in from the wall at arc length s, height h above the foot.
	var t := clampf(h / HEIGHT, 0.0, 1.0)
	var ph := 1.7 if end > 0 else 4.1
	var lean := LEAN * pow(1.0 - t, 0.85)
	var bay := (BAY * sin(s / 97.0 + ph) + 2.5 * sin(s / 41.0 + ph * 2.3) + 1.5 * sin(s / 233.0 - ph)) * pow(1.0 - t, 0.5)
	var ledge := _ledge(end, s, h) * (1.0 - t * t)
	var rough := (0.4 * sin(s / 7.1 + h / 5.3 + ph) + 0.2 * sin(s / 3.3 - h / 2.9)) * (1.0 - t)
	return maxf(0.4, lean + bay + ledge + rough)

static func smooth_u(end: int, s: float, h: float) -> float:
	## The same without ledges and roughness (the far version).
	var t := clampf(h / HEIGHT, 0.0, 1.0)
	var ph := 1.7 if end > 0 else 4.1
	return maxf(0.4, LEAN * pow(1.0 - t, 0.85) + (BAY * sin(s / 97.0 + ph) + 2.5 * sin(s / 41.0 + ph * 2.3)
		+ 1.5 * sin(s / 233.0 - ph)) * pow(1.0 - t, 0.5))

static func _bed(end: int, s: float, h: float) -> Vector3:
	## (index, position 0..1 within the bed, thickness) of the stratum at (s, h); beds dip along s.
	var hd := h + 2.2 * sin(s / 173.0 + end) + 1.1 * sin(s / 61.0)
	var k := floori(hd / 6.5)
	var th := 4.0 + 5.0 * _hash(end, k, 1)
	var h0 := k * 6.5
	return Vector3(k, clampf((hd - h0) / th, 0.0, 1.0), th)

static func _ledge(end: int, s: float, h: float) -> float:
	var b := _bed(end, s, h)
	var kind := _hash(end, int(b.x), 2)
	var v := b.y
	if kind < 0.45:
		# proud limestone: stands out, undercut at its base, lip at its top
		return 2.6 * smoothstep(0.0, 0.18, v) * (1.0 - 0.35 * v)
	elif kind < 0.75:
		return -1.6 * smoothstep(0.0, 0.2, v) * smoothstep(1.0, 0.8, v)      # recessed shale band
	return 0.6 * sin(v * PI)

static func tone(end: int, s: float, h: float) -> float:
	## Strata colour band (multiplies the texture): limestone light, shale dark, per-bed jitter.
	var b := _bed(end, s, h)
	var kind := _hash(end, int(b.x), 2)
	var base := 1.05 if kind < 0.45 else (0.72 if kind < 0.75 else 0.92)
	return base * (0.9 + 0.2 * _hash(end, int(b.x), 3)) * (0.93 + 0.07 * sin(s / 29.0 + h / 13.0))

static func scree_top(end: int, s: float) -> float:
	var ph := 0.6 if end > 0 else 2.9
	return SCREE_H + 3.0 * sin(s / 59.0 + ph) + 1.5 * sin(s / 23.0 + 2.0 * ph)

static func surface_u(end: int, s: float, h: float, detailed: bool) -> float:
	## The walkable/visible surface: the face above the scree, the talus below it.
	var sh := scree_top(end, s)
	var fu := face_u(end, s, h) if detailed else smooth_u(end, s, h)
	if h >= sh:
		return fu
	var foot := (face_u(end, s, sh) if detailed else smooth_u(end, s, sh))
	return maxf(fu, foot + (sh - h) / tan(deg_to_rad(SCREE_SLOPE)))

static func _hash(end: int, k: int, salt: int) -> float:
	var x := (k * 374761393 + end * 668265263 + salt * 1274126177) & 0x7fffffff
	x = ((x ^ (x >> 13)) * 1274126177) & 0x7fffffff
	return float(x % 100000) / 100000.0


# ------------------------------------------------------------------ building
static var TILES_ROUND := roundi(StationGeo.CIRC / 131.0)   # tiles round each end (~131 m each; all three versions share them)

func setup(p_target: Node3D) -> void:
	target = p_target
	_mats["face"] = _material("bedrock")
	_mats["scree"] = _material("scree")
	# the tiles build a few per frame (see _process), nothing here
	for end in [-1, 1]:
		for i in range(TILES_ROUND):
			_todo.append([end, i])
	set_process(true)


func _build_tile(end: int, i: int) -> void:
	var tile_s := StationGeo.CIRC / TILES_ROUND
	var s0 := i * tile_s
	# LOD1: detailed on a 6 m grid (hidden while this tile's LOD0 is loaded)
	var mid := _build_mesh(end, s0, s0 + tile_s, 6.0, 6.0, true)
	mid.name = "cliff_mid_%d_%d" % [end, i]
	# (no hysteresis margins, and a 30 m overlap: with margins and no fade, a band opened where neither version
	#  drew -- holes in the bluff a few hundred metres off, 2026-10-05)
	mid.visibility_range_end = MID + 30.0
	mid.visible = not _lod0.has("%d:%d" % [end, i])
	add_child(mid)
	_mid["%d:%d" % [end, i]] = mid
	# LOD2: the smooth surface, just the texture and the strata bands
	var far := _build_mesh(end, s0, s0 + tile_s, tile_s / 4.0, HEIGHT / 10.0, false)
	far.name = "cliff_far_%d_%d" % [end, i]
	far.visibility_range_begin = MID - 30.0
	add_child(far)


func _material(tex: String) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	var root := "res://remake/textures/cliff/%s_" % tex
	m.albedo_texture = load(root + "albedo.webp")
	m.normal_enabled = true
	m.normal_texture = load(root + "normal.webp")
	m.roughness_texture = load(root + "rough.webp")
	m.roughness = 1.0
	m.vertex_color_use_as_albedo = true
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	return m


func _build_mesh(end: int, s0: float, s1: float, ds: float, dh: float, detailed: bool) -> MeshInstance3D:
	var cols := maxi(1, ceili((s1 - s0) / ds))
	var rows := maxi(1, ceili((HEIGHT + 1.0) / dh))
	var st := {"face": SurfaceTool.new(), "scree": SurfaceTool.new()}
	for k in st:
		st[k].begin(Mesh.PRIMITIVE_TRIANGLES)
	# per column: the station's up there and the terrain height at the wall foot (the cliff
	# stands on it); rows start 1 m below the foot so the talus sinks into the ground
	var col_info := []
	for c in cols + 1:
		var s := s0 + (s1 - s0) * c / float(cols)
		col_info.append([s, MapTerrain.elevation(s, end * (half_w - 1.0))])
	var grid := []
	for r in rows + 1:
		var h := -1.0 + (HEIGHT + 1.0) * r / float(rows)
		var row := []
		for c in cols + 1:
			var s: float = col_info[c][0]
			var u := surface_u(end, s, h, detailed) if h >= 0.0 else surface_u(end, s, 0.0, detailed) + 1.2
			var e_foot: float = col_info[c][1]
			var p := StationGeo.point(s, end * (half_w - u), e_foot + h)
			row.append([p, s, h, tone(end, s, h)])
		grid.append(row)
	for r in rows:
		for c in cols:
			var q := [grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]]
			var hm: float = (q[0][2] + q[2][2]) * 0.5
			var key := "scree" if hm < scree_top(end, (q[0][1] + q[1][1]) * 0.5) else "face"
			var tm := SCREE_TEX_M if key == "scree" else TEX_M
			# wind so the front faces point away from the wall, into the station
			var order := [0, 1, 2, 0, 2, 3] if end > 0 else [0, 2, 1, 0, 3, 2]
			for i in order:
				var v: Array = q[i]
				st[key].set_color(Color(v[3], v[3], v[3]))
				st[key].set_uv(Vector2(v[1] / tm, -v[2] / tm))
				st[key].add_vertex(v[0])
	var mesh := ArrayMesh.new()
	for key in ["face", "scree"]:
		st[key].generate_normals()
		st[key].generate_tangents()
		st[key].set_material(_mats[key])
		st[key].commit(mesh)
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	return mi


# ------------------------------------------------------------------ LOD0 streaming
var _t := 0.0
var _mid := {}
var _todo := []                     # [end, tile] still to build (mid + far)

func _process(delta: float) -> void:
	# a tile a frame (as many as fit in 60 ms while the loading screen is up)
	var t0 := Time.get_ticks_usec()
	while not _todo.is_empty():
		var job: Array = _todo.pop_front()
		_build_tile(job[0], job[1])
		if not StationGeo.loading or Time.get_ticks_usec() - t0 > 60000:
			break
	_t -= delta
	if _t > 0.0 or target == null:
		return
	_t = 0.5
	var p := target.global_position
	var s_here := StationGeo.s_of(p)
	var tile_s := StationGeo.CIRC / TILES_ROUND
	var n_tiles := TILES_ROUND
	var want := {}
	for end in [-1, 1]:
		if absf(p.x - end * half_w) > NEAR + 40.0:
			continue
		for i in range(floori((s_here - NEAR) / tile_s), floori((s_here + NEAR) / tile_s) + 1):
			want["%d:%d" % [end, posmod(i, n_tiles)]] = [end, posmod(i, n_tiles)]
	for key in _lod0.keys():
		if not want.has(key):
			_lod0[key].queue_free()
			_lod0.erase(key)
			if _mid.has(key):
				_mid[key].visible = true
	for key in want:
		if _lod0.has(key):
			continue
		var end: int = want[key][0]
		var i: int = want[key][1]
		var tile := _build_mesh(end, i * tile_s, (i + 1) * tile_s, 2.0, 1.5, true)
		tile.name = "cliff_near_%d_%d" % [end, i]
		var body := StaticBody3D.new()
		var cs := CollisionShape3D.new()
		var shape := tile.mesh.create_trimesh_shape()
		shape.backface_collision = true
		cs.shape = shape
		body.add_child(cs)
		tile.add_child(body)
		add_child(tile)
		_lod0[key] = tile
		if _mid.has(key):
			_mid[key].visible = false
		return                       # one tile per tick
