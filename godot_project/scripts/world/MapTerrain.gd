extends RefCounted
class_name MapTerrain

## The ring floor's terrain as tools/map_preview.py draws it -- the map the remake world is built
## to (settlements, structures, roads and water all come from it).  A pure leaf: no other
## class_name script is called from here, so TerrainHeight can delegate to it without a cycle.
##
## Closed-form (ported from map_preview.py, same parameters):
##   river centreline  rx(s)        A1/A2/A3 harmonic stack (identical to TerrainHeight.river_x)
##   Lake Tamsin       lake_params  1,000 m x 300 m, necked 130 m at both ends, centred s = pi/4 R
##   bluffs            base_elev    asymmetric: cut-bank side steep and close, point-bar side
##                                  far and gentle; the lake's +x (Harrow Falls) shore is bluff;
##                                  a k=1 regional tilt; gentle noise (periodic here -- the
##                                  preview's isn't, and would step 2 m at s = 0)
## Data (res://remake/terrain.json, written by map_preview.py --terrain): creeks and spurs
## (polylines), ponds (ellipses), oxbow lakes (polygons), field ditches (runs along s), roads and
## streets, the railway, the towns' areas; and each placed structure's lot (placement.json) --
## the terrain is graded to the roads and levelled under every building.
##
## elevation(s, x) = base_elev - water_depth: + up (toward the axis), metres.

const PATH := "res://remake/terrain.json"
const CELL := 64.0                   # spatial grid for the polyline/polygon features

const ROAD_BLEND := 5.0             # a road's grade blends back into the terrain over this, past its shoulder, at least
const SIDE_SLOPE := 2.0             # cut and fill slopes: 2 horizontal to 1 vertical (research/roads/grading.md)
const BLEND_MAX := 14.0             # the widest a cut or fill slope reaches
const PAD_MARGIN := 1.0             # a lot is levelled this far past the building's bounds...
const PAD_BLEND := 4.0              # ...then blends back into the terrain over this
const PLACEMENT := "res://remake/placement.json"

static var _d: Dictionary = {}
const RAMP := 40.0                  # roads ramp to a bridge's deck over this, before its abutments
static var _pads: Array = []         # [s, x, cos yaw, sin yaw, min x, min z, max x, max z, height]
static var _bridges: Array = []      # the same, for crossings: height = the deck
static var _pad_by_id: Dictionary = {}
static var _prof_step := 4.0         # m between a road's profile heights (terrain.json "prof_step")
static var _grid: Dictionary = {}    # Vector2i -> Array of [kind, index]
static var R := 500.0
static var C := TAU * 500.0
# version 2 (tools/map_expanded.py --game-data): the terrain as rasters sampled directly -- the base
# ground before water (bilinear), and the rivers', lake's and seas' water level and bed depth
static var _v2 := false
static var _nx := 0
static var _ny := 0
static var _step := 4.0
static var _x0 := 0.0
static var _base := PackedByteArray()
static var _lvl := PackedByteArray()
static var _dep := PackedByteArray()
static var _lc_step := 2.0


static func _load() -> void:
	if not _d.is_empty():
		return
	_d = JSON.parse_string(FileAccess.get_file_as_string(PATH))
	R = _d.R
	C = TAU * R
	if int(_d.get("version", 1)) >= 2:
		var rs: Dictionary = _d.raster
		_nx = int(rs.nx)
		_ny = int(rs.ny)
		_step = rs.step_m
		_x0 = rs.x0
		_lc_step = _d.get("landcover_step_m", 2.0)
		_base = _raster(rs.base)
		_lvl = _raster(rs.level)
		_dep = _raster(rs.depth)
		_v2 = true
	# index every feature's bounding box (grown by its bank) into the grid
	for i in _d.creeks.size():
		var cr: Dictionary = _d.creeks[i]
		var pts: Array = cr.pts
		for k in pts.size() - 1:
			_index(["seg", i, k], pts[k][0], pts[k][1], pts[k + 1][0], pts[k + 1][1], cr.hw + 4.0)
	for i in _d.ponds.size():
		var p: Dictionary = _d.ponds[i]
		_index(["pond", i], p.s - p.a, p.x - p.a, p.s + p.a, p.x + p.a, 8.0)
	for i in _d.oxbows.size():
		var poly: Array = _d.oxbows[i].poly
		var lo := Vector2(1e9, 1e9)
		var hi := Vector2(-1e9, -1e9)
		for q in poly:
			lo = Vector2(minf(lo.x, q[0]), minf(lo.y, q[1]))
			hi = Vector2(maxf(hi.x, q[0]), maxf(hi.y, q[1]))
		_index(["oxbow", i], lo.x, lo.y, hi.x, hi.y, 8.0)
	for i in _d.ditches.size():
		var dt: Dictionary = _d.ditches[i]
		_index(["ditch", i], dt.s0, dt.x, dt.s1, dt.x, dt.hw + 2.0)
	# the railway is graded like a road (its bed), drawn apart (MapRoads)
	_d.roads.append({"cls": "rail", "w": 6.0, "pts": _d.rail.pts, "prof": _d.rail.get("prof", [])})
	_prof_step = float(_d.get("prof_step", 4.0))
	for i in _d.roads.size():
		var rd: Dictionary = _d.roads[i]
		var rp: Array = rd.pts
		# arc length at each point, for the graded profile (tools/road_profile.py)
		var cum := PackedFloat32Array([0.0])
		for k in rp.size() - 1:
			cum.append(cum[k] + Vector2(_wrap(rp[k + 1][0] - rp[k][0]), rp[k + 1][1] - rp[k][1]).length())
		rd["cum"] = cum
		rd["zp"] = PackedFloat32Array(rd.get("prof", []))
		for k in rp.size() - 1:
			_index(["road", i, k], rp[k][0], rp[k][1], rp[k + 1][0], rp[k + 1][1], rd.w * 0.5 + 0.5 + BLEND_MAX)
	for i in _d.areas.size():
		var ap: Array = _d.areas[i].poly
		var lo := Vector2(1e9, 1e9)
		var hi := Vector2(-1e9, -1e9)
		for q in ap:
			lo = Vector2(minf(lo.x, q[0]), minf(lo.y, q[1]))
			hi = Vector2(maxf(hi.x, q[0]), maxf(hi.y, q[1]))
		_index(["area", i], lo.x, lo.y, hi.x, hi.y, 1.0)
	_load_pads()


static func _raster(file: String) -> PackedByteArray:
	var raw := FileAccess.get_file_as_bytes("res://remake/" + file)
	return raw.decompress(_nx * _ny * 2, FileAccess.COMPRESSION_GZIP)


static func _cell(s: float, x: float) -> Vector2:
	## Raster coordinates (fractional, cell centres at .5) of (s, x).
	return Vector2(fposmod(s, C) / _step - 0.5, (x - _x0) / _step - 0.5)


static func _bil(buf: PackedByteArray, s: float, x: float) -> float:
	var f := _cell(s, x)
	var i0 := floori(f.x)
	var j0 := clampi(floori(f.y), 0, _ny - 2)
	var tx := f.x - i0
	var ty := clampf(f.y - j0, 0.0, 1.0)
	i0 = posmod(i0, _nx)
	var i1 := (i0 + 1) % _nx
	var r0 := j0 * _nx
	var r1 := r0 + _nx
	var a := lerpf(buf.decode_half((r0 + i0) * 2), buf.decode_half((r0 + i1) * 2), tx)
	var b := lerpf(buf.decode_half((r1 + i0) * 2), buf.decode_half((r1 + i1) * 2), tx)
	return lerpf(a, b, ty)


static func water_at(s: float, x: float) -> Vector2:
	## (water level, bed depth below it) of the rivers, the lake and the seas at (s, x); level
	## -9999 where there's none.
	_load()
	if not _v2:
		return Vector2(-9999.0, 0.0)
	var f := _cell(s, x)
	var i := posmod(roundi(f.x), _nx)
	var j := clampi(roundi(f.y), 0, _ny - 1)
	var lv := _lvl.decode_half((j * _nx + i) * 2)
	if lv < -9000.0:
		return Vector2(-9999.0, 0.0)
	return Vector2(lv, _bil(_dep, s, x))


static func _index(item: Array, s0: float, x0: float, s1: float, x1: float, grow: float) -> void:
	# the cells a lookup would use (floori(wrapped s / CELL)) -- walked in wrapped s, since the ring's
	# circumference isn't a whole number of cells: s past C (a road run on over the seam) mapped by
	# posmod of its unwrapped cell landed up to a cell off
	var lo := minf(s0, s1) - grow
	var hi := maxf(s0, s1) + grow
	var keys := {}
	var u := lo
	while true:
		var cs := floori(fposmod(minf(u, hi), C) / CELL)
		for cx in range(floori((minf(x0, x1) - grow) / CELL), floori((maxf(x0, x1) + grow) / CELL) + 1):
			keys[Vector2i(cs, cx)] = true
		if u >= hi:
			break
		u += CELL * 0.5
	for key in keys:
		if not _grid.has(key):
			_grid[key] = []
		_grid[key].append(item)


static func _wrap(ds: float) -> float:
	return fposmod(ds + C * 0.5, C) - C * 0.5


# ------------------------------------------------------------------ river and lake
static func rx(s: float) -> float:
	_load()
	var r: Dictionary = _d.river
	var th := s / R
	var env: float = r.A[0] * (1.0 + 0.3 * sin(2.0 * th + r.phi[3]))
	return env * sin(6.0 * th + r.phi[0]) + r.A[1] * sin(13.0 * th + r.phi[1]) + r.A[2] * sin(th + r.phi[2])


static func lake_params(s: float) -> Vector4:
	## (taper t 0..1, centre x, half-width toward -x, half-width toward +x); t = 0 away from the lake
	_load()
	var lk: Dictionary = _d.lake
	var ch: float = _d.river.ch_half
	var d := _wrap(s - lk.s)
	var t := clampf((lk.half_len - absf(d)) / lk.neck, 0.0, 1.0)
	t = t * t * (3.0 - 2.0 * t)
	var cx := rx(s) * (1.0 - t)
	var ht: float = ch + (lk.hw - ch + 22.0 * sin(d / 41.0) + 12.0 * sin(d / 17.0 + 1.3)) * t
	var hb: float = ch + (lk.hw - ch + 6.0 * sin(d / 63.0 + 0.4)) * t
	return Vector4(t, cx, ht, hb)


static func water_edges(s: float) -> Vector2:
	## (-x edge, +x edge) of the river / lake at s
	var lp := lake_params(s)
	var ch: float = _d.river.ch_half
	if lp.x > 0.0:
		return Vector2(minf(lp.y - ch, lp.y - lp.z), maxf(lp.y + ch, lp.y + lp.w))
	return Vector2(lp.y - ch, lp.y + ch)


# ------------------------------------------------------------------ terrain
static func base_elev(s: float, x: float) -> float:
	## The bluff / floodplain terrain before any water is carved.
	_load()
	if _v2:
		return _bil(_base, s, x)
	var r: Dictionary = _d.river
	var th := s / R
	var lp := lake_params(s)
	var t := lp.x
	var b := tanh(1.5 * sin(6.0 * th + r.phi[0])) / tanh(1.5)
	b = b * (1.0 - t) + t                          # the lake: bluff on the +x shore
	var side := -1.0 if x < lp.y else 1.0
	var e := water_edges(s)
	var dist := (e.x - x) if x < e.x else ((x - e.y) if x > e.y else 0.0)
	var w_cut := 0.5 * (1.0 + b * side)
	var d0_cut := 60.0 * (1.0 - t) + 140.0 * t
	var d0 := 230.0 - (230.0 - d0_cut) * w_cut
	var lb := 160.0 - 85.0 * w_cut
	var hgt: float = _d.bluff.H * (1.0 + 0.3 * sin(2.0 * th + r.phi[3]))
	# the preview's noise, made periodic round the ring (5 and 15 cycles ~ its 97 m / 211 m waves)
	var noise := 1.2 * sin(TAU * 5.0 * s / C + x / 131.0) + 0.8 * sin(x / 53.0 - TAU * 15.0 * s / C)
	return hgt * maxf(0.0, tanh((dist - d0) / lb)) - _d.bluff.Z1 * cos(th - PI * 0.25) + noise


static func _trap(au: float, bed_hw: float, bank_w: float, depth: float) -> float:
	if au <= bed_hw:
		return depth
	if au >= bed_hw + bank_w:
		return 0.0
	var f := (au - bed_hw) / bank_w
	return depth * (1.0 - f * f * (3.0 - 2.0 * f))


const BANK := 4.0                   # the carved depression reaches this far past the mapped water edge

static func outline(s: float) -> Vector2:
	## (-x rim, +x rim) of the river / lake depression at s: the mapped water edges plus BANK.
	var e := water_edges(s)
	return Vector2(e.x - BANK, e.y + BANK)


static func water_level(s: float) -> float:
	## The river / lake surface at s: bank-full (the rainy-season water table) -- just under the
	## lower of the depression's two rims, so the water fills it right to the brim.
	var o := outline(s)
	return minf(base_elev(s, o.x - 1.5), base_elev(s, o.y + 1.5)) - 0.12


static func _body_profile(s: float, x: float) -> float:
	## Depth below the water level of the river / lake bed at (s, x): the channel's trapezoid (bed
	## 12 m either side of the line, sloping to 0 at the rim) and the lake's shelving floor; 0
	## outside the depression.
	if _v2:
		return water_at(s, x).y
	var r: Dictionary = _d.river
	var lp := lake_params(s)
	var dep := _trap(absf(x - lp.y), r.bed_half, r.ch_half - r.bed_half + BANK, r.depth)
	if lp.x > 0.0:
		var lk: Dictionary = _d.lake
		var lo := lp.y - lp.z
		var hi := lp.y + lp.w
		if x > lo - BANK and x < hi + BANK:
			var inside := minf(x - lo, hi - x)                  # metres in from the mapped shore
			dep = maxf(dep, lk.depth * lp.x * smoothstep(-BANK, lk.shelf, inside))
	return dep


static func _small_depth(s: float, x: float) -> float:
	## Carved depth of the small water (creeks, spurs, ponds, oxbows, ditches) below the terrain.
	var dep := 0.0
	var key := Vector2i(floori(s / CELL), floori(x / CELL))
	for it in _grid.get(key, []):
		match it[0]:
			"seg":
				var cr: Dictionary = _d.creeks[it[1]]
				var a: Array = cr.pts[it[2]]
				var bq: Array = cr.pts[it[2] + 1]
				dep = maxf(dep, _trap(_seg_dist(s, x, a[0], a[1], bq[0], bq[1]), cr.hw, 3.0, cr.depth))
			"pond":
				var p: Dictionary = _d.ponds[it[1]]
				var ds := _wrap(s - p.s)
				var dx: float = x - p.x
				var rot: float = p.rot
				var u: float = (ds * cos(rot) + dx * sin(rot)) / p.a
				var v: float = (-ds * sin(rot) + dx * cos(rot)) / p.b
				var rr := sqrt(u * u + v * v)                      # 1 at the shore
				dep = maxf(dep, p.depth * smoothstep(1.15, 0.7, rr))
			"oxbow":
				var ox: Dictionary = _d.oxbows[it[1]]
				var inside := _poly_inside_dist(ox.poly, s, x)
				dep = maxf(dep, ox.depth * smoothstep(-4.0, 10.0, inside))
			"ditch":
				var dt: Dictionary = _d.ditches[it[1]]
				if s >= dt.s0 - 1.0 and s <= dt.s1 + 1.0:
					dep = maxf(dep, _trap(absf(x - dt.x), dt.hw, 1.5, dt.depth))
	return dep


static func sample(s: float, x: float) -> Vector2:
	## (elevation, carved depth below the undisturbed terrain) at (s, x).  The terrain is graded
	## first -- each building's lot levelled to its pad, then flat across every road at its
	## centreline's height -- then the small water is carved (not under a road: that's a culvert), then the
	## river / lake: inside its depression the bed is cut down from the bank-full water level, so
	## the water fills it to the brim (and a road meets it at a bridge).
	_load()
	s = fposmod(s, C)
	var base := base_elev(s, x)
	# lots first, then the roads over them: a carriageway is exactly at its own grade even where a
	# neighbouring lot's pad blends up to it
	var rg := _road_grade(s, x, _pad_grade(s, x, base))
	var h := rg.x
	if rg.y < 0.5:
		h -= _small_depth(s, x)
	if _v2:
		var w := water_at(s, x)
		if w.x > -9000.0 and not (rg.y >= 0.5 and h > w.x):
			h = minf(h, w.x - w.y)             # (a road's own bed above the water isn't cut away: a causeway)
		return Vector2(h, maxf(0.0, base - h))
	var bp := _body_profile(s, x)
	if bp > 0.0:
		h = minf(h, water_level(s) - bp)
	return Vector2(h, maxf(0.0, base - h))


static func _road_grade(s: float, x: float, base: float) -> Vector2:
	## (terrain graded to the nearest road, that road's weight 0..1): flat across the carriageway
	## and a 0.5 m shoulder at the centreline's height, blending back over ROAD_BLEND.
	var best_w := 0.0
	var best_h := base
	var best_d := INF
	var on_road := {}                     # road -> [distance, height] of its nearest segment, where it weighs 1
	for it in _grid.get(Vector2i(floori(s / CELL), floori(x / CELL)), []):
		if it[0] != "road":
			continue
		var rd: Dictionary = _d.roads[it[1]]
		var a: Array = rd.pts[it[2]]
		var bq: Array = rd.pts[it[2] + 1]
		var pr := _seg_proj(s, x, a[0], a[1], bq[0], bq[1])
		var hw: float = rd.w * 0.5
		if pr.x > hw + 0.5 + BLEND_MAX:
			continue
		var h: float
		var zp: PackedFloat32Array = rd.zp
		if zp.is_empty():
			h = base_elev(a[0] + _wrap(bq[0] - a[0]) * pr.y, a[1] + (bq[1] - a[1]) * pr.y)
		else:
			# the road's graded profile at the nearest point of its centreline
			var cum: PackedFloat32Array = rd.cum
			var u: float = lerpf(cum[it[2]], cum[it[2] + 1], pr.y) / _prof_step
			var k := clampi(floori(u), 0, zp.size() - 1)
			var k1 := mini(k + 1, zp.size() - 1)
			if zp[k] < -9000.0 or zp[k1] < -9000.0:
				continue                                 # over a great river: the great bridge carries it
			h = lerpf(zp[k], zp[k1], clampf(u - k, 0.0, 1.0))
		# the cut or fill slope reaches out SIDE_SLOPE m for every metre the road is off the ground
		var blend := clampf(absf(h - base) * SIDE_SLOPE, ROAD_BLEND, BLEND_MAX)
		var w := 1.0 - smoothstep(hw + 0.5, hw + 0.5 + blend, pr.x)
		# the strongest road; between equals (every nearby segment of a road weighs 1 on its
		# carriageway), the nearest segment -- not one whose clamped end happens to come first
		if w > best_w + 1e-6 or (w > best_w - 1e-6 and pr.x < best_d):
			best_w = w
			best_h = h
			best_d = pr.x
		# where carriageways overlap (a junction), each road's nearest segment, to blend between
		if w > 0.999 and pr.x < float(on_road.get(it[1], [INF])[0]):
			on_road[it[1]] = [pr.x, h]
	if on_road.size() > 1:
		# a junction: the roads' heights (one at the junction itself, tools/road_profile.py) blended by
		# nearness, so the surface doesn't step where one road's carriageway gives way to the next's
		var sk := 0.0
		var sh := 0.0
		for r in on_road.values():
			var kk := 1.0 / pow(0.5 + float(r[0]), 2.0)
			sk += kk
			sh += kk * float(r[1])
		best_h = sh / sk
	if best_w > 0.0 and not _bridges.is_empty() and not _d.has("decks"):
		best_h = _ramp_to_bridge(s, x, best_h)       # (graded roads already ramp to their decks)
	return Vector2(lerpf(base, best_h, best_w), best_w)


static func _ramp_to_bridge(s: float, x: float, h: float) -> float:
	## A road near a crossing ramps to its deck over RAMP m (so both approaches meet the deck).
	for it in _grid.get(Vector2i(floori(s / CELL), floori(x / CELL)), []):
		if it[0] != "bridge":
			continue
		var bd: Array = _bridges[it[1]]
		var ds := _wrap(s - bd[0])
		var dx: float = x - bd[1]
		var lx: float = dx * bd[2] + ds * bd[3]
		var lz: float = dx * bd[3] - ds * bd[2]
		var ox := maxf(0.0, maxf(bd[4] - lx, lx - bd[6]))
		var oz := maxf(0.0, maxf(bd[5] - lz, lz - bd[7]))
		var w := 1.0 - smoothstep(0.0, RAMP, Vector2(ox, oz).length())
		if w > 0.0:
			return lerpf(h, bd[8], w)
	return h


static func _pad_grade(s: float, x: float, h: float) -> float:
	## The terrain levelled to the pad of the nearest building's lot.
	var best_w := 0.0
	var best_h := h
	for it in _grid.get(Vector2i(floori(s / CELL), floori(x / CELL)), []):
		if it[0] != "pad":
			continue
		var pd: Array = _pads[it[1]]
		var ds := _wrap(s - pd[0])
		var dx: float = x - pd[1]
		var lx: float = dx * pd[2] + ds * pd[3]             # into the building's own frame
		var lz: float = dx * pd[3] - ds * pd[2]
		var ox := maxf(0.0, maxf(pd[4] - PAD_MARGIN - lx, lx - pd[6] - PAD_MARGIN))
		var oz := maxf(0.0, maxf(pd[5] - PAD_MARGIN - lz, lz - pd[7] - PAD_MARGIN))
		var w := 1.0 - smoothstep(0.0, PAD_BLEND, Vector2(ox, oz).length())
		if w > best_w:
			best_w = w
			best_h = pd[8]
	return lerpf(h, best_h, best_w)


static func _load_pads() -> void:
	## Every placed structure's lot (its visual bounds, turned by its yaw) and pad height (the height
	## RemakeWorld stands it at).  Crossings have no pad (a bridge spans its water): their deck
	## height instead, which the roads ramp to.
	if not FileAccess.file_exists(PLACEMENT):
		return
	var pl: Array = JSON.parse_string(FileAccess.get_file_as_string(PLACEMENT)).structures
	for e in pl:
		if e.kind == "crossing":
			_load_bridge(e)
			continue
		var s0: float = e.s
		var x0: float = e.x
		var c := cos(float(e.yaw))
		var sn := sin(float(e.yaw))
		# the pad: the graded ground at the middle of the massing's front edge (local -z, the street
		# side) -- a building on a slope keeps its front at street grade and cuts its lot into the
		# hill behind, as hill towns do, instead of standing on the slope's high corner
		var lx: float = (e.fmin[0] + e.fmax[0]) * 0.5
		var lz: float = e.fmin[1]
		var ss: float = s0 + lx * sn - lz * c
		var xx: float = x0 + lx * c + lz * sn
		var hpad := _road_grade(fposmod(ss, C), xx, base_elev(ss, xx)).x
		var pd := [s0, x0, c, sn, e.min[0], e.min[2], e.max[0], e.max[2], hpad]
		_pad_by_id[e.id] = hpad
		_pads.append(pd)
		var reach := Vector2(maxf(absf(e.min[0]), absf(e.max[0])), maxf(absf(e.min[2]), absf(e.max[2]))).length()
		_index(["pad", _pads.size() - 1], s0 - reach, x0 - reach, s0 + reach, x0 + reach, PAD_MARGIN + PAD_BLEND)


static func _load_bridge(e: Dictionary) -> void:
	## A crossing's deck: the higher of its two road ends (the road runs along its local z), before
	## any ramping -- the lower approach then ramps up to it.
	var s0: float = e.s
	var x0: float = e.x
	var c := cos(float(e.yaw))
	var sn := sin(float(e.yaw))
	var lx: float = (e.fmin[0] + e.fmax[0]) * 0.5
	var deck := -1e9
	for lz in [e.fmin[1] - 2.0, e.fmax[1] + 2.0]:
		var ss: float = s0 + lx * sn - lz * c
		var xx: float = x0 + lx * c + lz * sn
		deck = maxf(deck, _road_grade(fposmod(ss, C), xx, base_elev(ss, xx)).x)
	# the graded deck (tools/road_profile.py pins each crossing level at its higher approach)
	deck = float(_d.get("decks", {}).get(e.id, deck))
	_bridges.append([s0, x0, c, sn, e.fmin[0], e.fmin[1], e.fmax[0], e.fmax[1], deck])
	_pad_by_id[e.id] = deck
	var reach := Vector2(maxf(absf(e.fmin[0]), absf(e.fmax[0])), maxf(absf(e.fmin[1]), absf(e.fmax[1]))).length()
	_index(["bridge", _bridges.size() - 1], s0 - reach, x0 - reach, s0 + reach, x0 + reach, RAMP)


static func pad_height(id: String) -> float:
	## The height a placed structure stands at (its pad, or a crossing's deck).
	_load()
	return _pad_by_id.get(id, NAN)


static var _lc: Image = null


static func landcover_image() -> Image:
	if _lc == null:
		_load()
		_lc = load("res://remake/landcover.png")
	return _lc


static func landcover_step() -> float:
	_load()
	return _lc_step


static func landcover(s: float, x: float) -> Vector2i:
	## (class, field id) of the map's land cover at (s, x) -- remake/landcover.png, 2 m / px:
	## 1 built-up, 2 floodplain meadow, 3 woods, 4 farm field (id picks its crop), 5 windbreak grove,
	## 0 anything else.
	if _lc == null:
		_load()
		_lc = load("res://remake/landcover.png")
	var px := clampi(floori(fposmod(s, C) / _lc_step), 0, _lc.get_width() - 1)
	var py := clampi(floori((x + StationGeo.HALF_LEN) / _lc_step), 0, _lc.get_height() - 1)
	var c := _lc.get_pixel(px, py)
	return Vector2i(roundi(c.r * 255.0), roundi(c.g * 255.0))


static func area_kind(s: float, x: float) -> String:
	## The town area at (s, x) -- "lawn", "parking", "square", "schoolground"... -- or "".
	_load()
	s = fposmod(s, C)
	for it in _grid.get(Vector2i(floori(s / CELL), floori(x / CELL)), []):
		if it[0] == "area" and _poly_inside_dist(_d.areas[it[1]].poly, s, x) > 0.0:
			return _d.areas[it[1]].kind
	return ""


static func road_weight(s: float, x: float) -> float:
	_load()
	return _road_grade(fposmod(s, C), x, 0.0).y


static func water_depth(s: float, x: float) -> float:
	## How far the floor is carved down at (s, x) by any water feature (0 on dry land).
	return sample(s, x).y


static func elevation(s: float, x: float) -> float:
	return sample(s, x).x


# ------------------------------------------------------------------ geometry helpers
static func _seg_dist(s: float, x: float, s0: float, x0: float, s1: float, x1: float) -> float:
	var ps := _wrap(s - s0)
	var bs := _wrap(s1 - s0)
	var px := x - x0
	var bx := x1 - x0
	var l2 := bs * bs + bx * bx
	var t := 0.0 if l2 < 1e-6 else clampf((ps * bs + px * bx) / l2, 0.0, 1.0)
	return Vector2(ps - bs * t, px - bx * t).length()


static func _seg_proj(s: float, x: float, s0: float, x0: float, s1: float, x1: float) -> Vector2:
	## (distance to the segment, parameter 0..1 of the nearest point on it)
	var ps := _wrap(s - s0)
	var bs := _wrap(s1 - s0)
	var px := x - x0
	var bx := x1 - x0
	var l2 := bs * bs + bx * bx
	var t := 0.0 if l2 < 1e-6 else clampf((ps * bs + px * bx) / l2, 0.0, 1.0)
	return Vector2(Vector2(ps - bs * t, px - bx * t).length(), t)


static func _poly_inside_dist(poly: Array, s: float, x: float) -> float:
	## Signed distance to a polygon's edge: + inside, - outside.
	var inside := false
	var dmin := 1e9
	var n := poly.size()
	for i in n:
		var a: Array = poly[i]
		var bq: Array = poly[(i + 1) % n]
		dmin = minf(dmin, _seg_dist(s, x, a[0], a[1], bq[0], bq[1]))
		var sa := _wrap(a[0] - s)
		var sb := _wrap(bq[0] - s)
		if ((a[1] > x) != (bq[1] > x)) and (0.0 < sa + (sb - sa) * (x - a[1]) / (bq[1] - a[1])):
			inside = not inside
	return dmin if inside else -dmin
