extends Node3D
class_name CapMountains

## The end caps' mountains (the user, 2026-10-05: "a mountain range running up 1.5 km, then sky blue filling the
## centre ... like a curved canyon ... only the sheer cliffs, staggered for effect ... natural and unclimbable ...
## attractive"). Above CliffWalls' 150 m bluff, each end cap rises as TIERS of sheer cliffs, each set back from the
## one below by a bench, to a jagged crest about 1.5 km up; behind them the cap is pushed out by DEPTH so the tiers
## can recede without taking land from the floor. The sky disc fills the centre (RemakeStation._build_shell).
##
## Like CliffWalls, the shape is a closed-form function of (end, s, tier, f) -- so any tile can be built alone, in any
## order, deterministically:
##   * tier k spans h_k(s) .. h_k+1(s); its face is near-vertical (a slight lean back), fluted by gullies and
##     buttresses along s; its top steps back by a bench of width w_k(s) (narrow ledges, wide terraces, a few
##     prows where the bench vanishes and two tiers join into one taller wall);
##   * big headlands along s push whole tier stacks out (the canyon's spurs), coves pull them back;
##   * the crest is the last tier's top: peaks and saddles along s, up to ~CREST_VAR above 1.5 km;
##   * strata bands, darker gullies, greener benches and lighter high rock in the vertex colours.
##
## Distance versions, TILES_ROUND tiles round each end (~200 m of floor arc each):
##   LOD0 (< NEAR)   8 m along s, fine rows per face -- built near the player (one tile per tick)
##   LOD1 (< MID)    24 m, 6 rows per face
##   LOD2 (>= MID)   80 m, 2 rows per face: the silhouette, the benches and the colour bands only
## No collision above the bluff: it is out of reach (the bluff below is sheer -- CliffWalls).

const BASE_H := 140.0               # starts just under the bluff's top (CliffWalls.HEIGHT 150), overlapping it
const TOP_H := 1500.0
const CREST_VAR := 160.0
const DEPTH := 620.0                # the cap is pushed out this far behind the mountains (RemakeStation)
const TIERS := 5
const NEAR := 1400.0
const MID := 4200.0
const TEX_M := 110.0

var half_w := StationGeo.HALF_LEN
var target: Node3D
var _mat: StandardMaterial3D
var _todo := []
var _mid := {}
var _lod0 := {}
var _t := 0.0
static var TILES_ROUND := roundi(StationGeo.CIRC / 200.0)


# ------------------------------------------------------------------ the shape
static func _n(end: int, s: float, f: float, ph: float) -> float:
	## smooth 1-D noise round the ring (sum of sines with incommensurate periods; periodic in CIRC)
	var k := TAU / StationGeo.CIRC
	var e := 1.3 if end > 0 else 3.7
	return (sin(s * k * roundf(StationGeo.CIRC / f) + ph + e) * 0.6
		+ sin(s * k * roundf(StationGeo.CIRC / (f * 0.53)) + ph * 1.7 + e * 2.1) * 0.3
		+ sin(s * k * roundf(StationGeo.CIRC / (f * 0.29)) - ph + e * 0.7) * 0.1)


static func tier_h(end: int, s: float, k: int) -> float:
	## the height of tier k's foot (k = 0 at the bluff, k = TIERS at the crest)
	if k <= 0:
		return BASE_H
	var pk := maxf(0.0, _n(end, s, 640.0, 2.2))              # (broad peaks and saddles, no needles)
	var crest := TOP_H + CREST_VAR * (0.6 * _n(end, s, 1300.0, 0.3) + 0.7 * pk * pk - 0.15)
	if k >= TIERS:
		return crest
	var frac := float(k) / TIERS
	var jitter := 0.09 * _n(end, s, 700.0 + 130.0 * k, k * 1.9)
	return BASE_H + (crest - BASE_H) * clampf(pow(frac, 0.92) + jitter * 0.5, 0.05, 0.97)


static func bench_w(end: int, s: float, k: int) -> float:
	## the setback at the top of tier k (k = 0..TIERS-1); a prow where it drops to ~0
	var w := 70.0 + 60.0 * _n(end, s, 520.0 + 90.0 * k, 0.7 + k)
	var prow := smoothstep(0.55, 0.85, _n(end, s, 1500.0, 4.0 + k * 0.5))
	return maxf(4.0, w * (1.0 - 0.9 * prow))


static func spur(end: int, s: float) -> float:
	## headlands and coves: how far a whole stack stands out (+) or back (-)
	return 110.0 * _n(end, s, 1800.0, 1.1) + 40.0 * _n(end, s, 610.0, 2.6)


static func face_d(end: int, s: float, k: int, f: float, detailed: bool) -> float:
	## distance of the surface out from the back plane, on tier k, f (0 foot .. 1 top of the face). The stack's foot is
	## flush with the bluff's top (it never overhangs the floor); headlands keep the tiers forward (narrow benches),
	## coves let them step far back (wide benches).
	var d := DEPTH - 0.5
	var m := clampf(1.0 - spur(end, s) / 180.0, 0.3, 1.8)
	for j in k:
		d -= bench_w(end, s, j) * m
	var hk := tier_h(end, s, k)
	var hk1 := tier_h(end, s, k + 1)
	d -= (hk1 - hk) * f * 0.06                                # (the face leans back ~3.5 deg: sheer)
	var flute := 16.0 * sin(s / 57.0 + k * 2.1) + 8.0 * sin(s / 21.0 + k) + 4.0 * sin(s / 9.7 - k)   # (buttresses)
	var fine := 3.0 * sin(s / 4.1 - f * 3.0)
	var gully := -22.0 * pow(maxf(0.0, _n(end, s, 140.0, k * 0.9)), 3.0)
	d += flute + gully + (fine if detailed else 0.0)          # (every LOD shares the big shape: no cracks between them)
	return clampf(d, 6.0, DEPTH - 0.5)


static func point(end: int, s: float, h: float, d: float) -> Vector3:
	var x := end * (StationGeo.HALF_LEN + DEPTH - d)
	return StationGeo.point(s, x, h)


static func tone(end: int, s: float, h: float, bench: bool) -> Color:
	## warm sandstone below, paler limestone above; irregular strata (beds of uneven thickness that dip and pinch),
	## iron stains in the gullies; green scrub on the benches thinning with height
	var dip := 30.0 * _n(end, s, 1700.0, 0.9) + 8.0 * _n(end, s, 380.0, 2.3)
	var hb := h + dip
	var bed := sin(hb / 61.0) * 0.5 + sin(hb / 23.0 + 1.3) * 0.3 + sin(hb / 9.0 + s / 300.0) * 0.2
	var band := 0.94 + 0.07 * bed
	var hi := clampf((h - BASE_H) / (TOP_H - BASE_H), 0.0, 1.0)
	var warm := Color(0.86, 0.66, 0.50).lerp(Color(0.78, 0.58, 0.46), 0.5 + 0.5 * _n(end, s, 2100.0, 4.4))
	var rock := warm.lerp(Color(0.88, 0.84, 0.78), smoothstep(0.35, 0.9, hi)) * band
	var stain := maxf(0.0, _n(end, s, 140.0, 0.4))
	rock = rock.lerp(Color(0.55, 0.38, 0.30), 0.35 * stain * stain)
	if bench:
		return rock.lerp(Color(0.40, 0.50, 0.30), 0.7 * (1.0 - hi * 0.7))
	return rock


# ------------------------------------------------------------------ building
func setup(p_target: Node3D) -> void:
	target = p_target
	_mat = StandardMaterial3D.new()
	var root := "res://remake/cliffs/mountain_"      # (tools/assets/mountain_rock.py: vertical joints and streaks)
	_mat.albedo_texture = load(root + "albedo.webp")
	_mat.normal_enabled = true
	_mat.normal_texture = load(root + "normal.webp")
	_mat.normal_scale = 0.6
	_mat.roughness_texture = load(root + "rough.webp")
	_mat.roughness = 1.0
	_mat.vertex_color_use_as_albedo = true
	_mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	for end in [-1, 1]:
		for i in range(TILES_ROUND):
			_todo.append([end, i])
	set_process(true)


func build_mesh(end: int, s0: float, s1: float, ds: float, face_rows: int, detailed: bool) -> MeshInstance3D:
	## a tile: for each tier, face_rows rows up the face then the bench back to the next tier's foot
	var cols := maxi(1, ceili((s1 - s0) / ds))
	var pad := (s1 - s0) / cols * 0.5                          # (tiles overlap: no cracks where neighbours differ in LOD)
	s0 -= pad
	s1 += pad
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	# the profile as rows: (tier, f, is_bench); f runs 0..1 up the face, the bench row sits at the next foot
	var rows := []
	for k in TIERS:
		for r in face_rows + 1:
			rows.append([k, float(r) / face_rows, false])
		if k < TIERS - 1:
			rows.append([k + 1, 0.0, true])
	var grid := []
	for row in rows:
		var line := []
		for c in cols + 1:
			var s := s0 + (s1 - s0) * c / float(cols)
			var k: int = row[0]
			var f: float = row[1]
			var h := lerpf(tier_h(end, s, k) + (2.0 if k > 0 else 0.0), tier_h(end, s, k + 1), f)
			var d: float
			if row[2]:                                         # (the bench's back: the next tier's foot, 2 m up)
				h = tier_h(end, s, k) + 2.0
				d = face_d(end, s, k, 0.0, detailed)
			else:
				d = face_d(end, s, k, f, detailed)
			line.append([point(end, s, h, d), s, h, tone(end, s, h, row[2] or (f >= 0.999 and k < TIERS - 1))])
		grid.append(line)
	# the crest: a last row pulled back into the plane behind the peaks
	var crest := []
	for c in cols + 1:
		var s := s0 + (s1 - s0) * c / float(cols)
		var h := tier_h(end, s, TIERS) + 6.0
		crest.append([point(end, s, h, 0.0), s, h, tone(end, s, h, false)])
	grid.append(crest)
	for r in grid.size() - 1:
		for c in cols:
			var q := [grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]]
			var order := [0, 1, 2, 0, 2, 3] if end > 0 else [0, 2, 1, 0, 3, 2]
			for i in order:
				var v: Array = q[i]
				st.set_color(v[3])
				st.set_uv(Vector2(v[1] / TEX_M, -v[2] / TEX_M))
				st.add_vertex(v[0])
	st.generate_normals()
	st.generate_tangents()
	st.set_material(_mat)
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF      # (a 1.5 km wall's shadow over the town would
	return mi                                                          #  swing with the one sun -- off)


func _build_tile(end: int, i: int) -> void:
	var tile_s := StationGeo.CIRC / TILES_ROUND
	var s0 := i * tile_s
	var mid := build_mesh(end, s0, s0 + tile_s, 24.0, 6, true)
	mid.name = "mtn_mid_%d_%d" % [end, i]
	mid.visibility_range_end = MID + 60.0                     # (no margins; overlap -- see CliffWalls: no holes)
	mid.visible = not _lod0.has("%d:%d" % [end, i])
	add_child(mid)
	_mid["%d:%d" % [end, i]] = mid
	var far := build_mesh(end, s0, s0 + tile_s, tile_s / 2.5, 2, false)
	far.name = "mtn_far_%d_%d" % [end, i]
	far.visibility_range_begin = MID - 60.0
	add_child(far)


func loaded() -> bool:
	return _todo.is_empty()


func _process(delta: float) -> void:
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
	var want := {}
	for end in [-1, 1]:
		if absf(p.x - end * half_w) > NEAR:
			continue
		var reach := ceili(NEAR * 0.6 / tile_s)
		var i0 := floori(s_here / tile_s)
		for i in range(i0 - reach, i0 + reach + 1):
			want["%d:%d" % [end, posmod(i, TILES_ROUND)]] = [end, posmod(i, TILES_ROUND)]
	for key in _lod0.keys():
		if not want.has(key):
			_lod0[key].queue_free()
			_lod0.erase(key)
			if _mid.has(key):
				_mid[key].visible = true
	for key in want:
		if _lod0.has(key):
			continue
		var tile := build_mesh(want[key][0], want[key][1] * tile_s, (want[key][1] + 1) * tile_s, 8.0, 16, true)
		tile.name = "mtn_near_" + key
		add_child(tile)
		_lod0[key] = tile
		if _mid.has(key):
			_mid[key].visible = false
		return                                                 # (one tile per tick)
