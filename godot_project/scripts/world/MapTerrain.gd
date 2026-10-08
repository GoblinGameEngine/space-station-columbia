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
const ROAD_RUN := 8                  # road segments indexed together

const ROAD_BLEND := 5.0             # a road's grade blends back into the terrain over this, past its shoulder, at least
const SIDE_SLOPE := 2.0             # cut and fill slopes: 2 horizontal to 1 vertical (research/roads/grading.md)
const BLEND_MAX := 14.0             # the widest a cut or fill slope reaches
const PAD_MARGIN := 1.0             # a lot is levelled this far past the building's bounds...
const PAD_BLEND := 4.0              # ...then blends back into the terrain over at least this...
const PAD_SLOPE := 6.0              # ...at 1 in this on average (the smoothstep peaks at 1.5x: about 1 in 4)
const PAD_BLEND_MAX := 18.0
const PLACEMENT := "res://remake/placement.json"

static var _d: Dictionary = {}
const RAMP := 40.0                  # roads ramp to a bridge's deck over this, before its abutments
const CURB_RISE := 0.15             # behind a kerb with a sidewalk the ground stands at the kerb's top (MapRoads CURB_H)
static var _pads := PackedFloat64Array()  # PAD_N a pad: [s, x, cos yaw, sin yaw, min x, min z, max x, max z, height, blend]
const PAD_N := 10
static var _bridges: Array = []      # the same, for crossings: height = the deck
static var _pad_h := PackedFloat32Array()  # placement index -> its pad height (a crossing: its deck); NAN none
static var _prof_step := 4.0         # m between a road's profile heights (terrain.json "prof_step")
static var _grid: Dictionary = {}    # Vector2i -> PackedInt32Array of [kind, index, k0, k1] (KINDS; -1: none) -- _items()
const KINDS := ["seg", "pond", "oxbow", "ditch", "road", "area", "pad", "bridge"]
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
# the water's level and depth: tiles of WT x WT cells, kept only where they aren't all one value (88 MB raw, ~10 sparse)
const WT := 32
static var _wtx := 0                         # tiles across s
static var _lvl_slot := PackedInt32Array()   # tile -> its cells' slot in _lvl_t, or -1: all _lvl_k[tile]
static var _lvl_k := PackedFloat32Array()
static var _lvl_t := PackedByteArray()
static var _dep_slot := PackedInt32Array()
static var _dep_k := PackedFloat32Array()
static var _dep_t := PackedByteArray()
static var _lc_step := 2.0


static func _load() -> void:
	if not _d.is_empty():
		return
	_d = _read_compact()
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
		_wtx = ceili(_nx / float(WT))
		var sp := _sparse(_raster(rs.level))
		_lvl_slot = sp[0]
		_lvl_k = sp[1]
		_lvl_t = sp[2]
		sp = _sparse(_raster(rs.depth))
		_dep_slot = sp[0]
		_dep_k = sp[1]
		_dep_t = sp[2]
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
		var rp: PackedVector2Array = rd.pts
		# arc length at each point, for the graded profile (tools/road_profile.py)
		var cum := PackedFloat32Array([0.0])
		for k in rp.size() - 1:
			cum.append(cum[k] + Vector2(_wrap(rp[k + 1][0] - rp[k][0]), rp[k + 1][1] - rp[k][1]).length())
		rd["cum"] = cum
		rd["zp"] = PackedFloat32Array(rd.get("prof", []))
		# (indexed as far as it can reach: its wider side's kerb, the lawn and walk, the shoulder, the blend)
		var reach: float = maxf(float(rd.get("hr", rd.w * 0.5)), float(rd.get("hl", rd.w * 0.5))) \
			+ float(rd.get("lawn", 0.0)) + float(rd.get("walk", 0.0)) + 0.5 + BLEND_MAX
		# a run of ROAD_RUN segments an entry: their box (one each was ~1.5 M _index calls on the 1:1 map: 80 s to load)
		var k0 := 0
		while k0 < rp.size() - 1:
			var k1 := mini(k0 + ROAD_RUN, rp.size() - 1)
			var lo := Vector2(INF, INF)
			var hi := Vector2(-INF, -INF)
			var s_ref: float = rp[k0][0]
			for k in range(k0, k1 + 1):
				var su: float = s_ref + _wrap(float(rp[k][0]) - s_ref)
				lo = Vector2(minf(lo.x, su), minf(lo.y, rp[k][1]))
				hi = Vector2(maxf(hi.x, su), maxf(hi.y, rp[k][1]))
			_index(["road", i, k0, k1], lo.x, lo.y, hi.x, hi.y, reach)
			k0 = k1
	for i in _d.areas.size():
		var ap: Array = _d.areas[i].poly
		var lo := Vector2(1e9, 1e9)
		var hi := Vector2(-1e9, -1e9)
		for q in ap:
			lo = Vector2(minf(lo.x, q[0]), minf(lo.y, q[1]))
			hi = Vector2(maxf(hi.x, q[0]), maxf(hi.y, q[1]))
		_index(["area", i], lo.x, lo.y, hi.x, hi.y, 1.0)
	_load_pads()


# terrain.json is ~44 MB of JSON, ~510 MB parsed -- 1.5 million road points as [s, x] Arrays (2026-10-08).  The
# roads' points and profiles are kept packed (PackedVector2Array / PackedFloat32Array: rd.pts[k][0] still reads), baked
# to terrain.bin (bake_world.gd pads) so the JSON isn't parsed at all.
const BIN := "res://remake/terrain.bin"


static func data() -> Dictionary:
	## the terrain data (one copy for everyone: MapWater, WaterAmbience...)
	_load()
	return _d


static func _bin_stamp() -> String:
	return BakedMeshes.fingerprint([PATH], 1)


static func _read_compact() -> Dictionary:
	if FileAccess.file_exists(BIN):
		var f := FileAccess.open(BIN, FileAccess.READ)
		var d = f.get_var()
		f.close()
		if typeof(d) == TYPE_DICTIONARY and str(d.get("_stamp", "")) == _bin_stamp():
			return d
	return _pack(JSON.parse_string(FileAccess.get_file_as_string(PATH)))


static func _pack(d: Dictionary) -> Dictionary:
	for rd in d.get("roads", []):
		rd["pts"] = _packed_pts(rd.pts)
		if rd.has("prof"):
			rd["prof"] = PackedFloat32Array(rd.prof)
	if d.has("rail"):
		d.rail["pts"] = _packed_pts(d.rail.pts)
		if d.rail.has("prof"):
			d.rail["prof"] = PackedFloat32Array(d.rail.prof)
	return d


static func _packed_pts(a: Array) -> PackedVector2Array:
	var out := PackedVector2Array()
	out.resize(a.size())
	for k in a.size():
		out[k] = Vector2(float(a[k][0]), float(a[k][1]))
	return out


static func bake_bin() -> void:
	## (remake/tools/bake_world.gd pads) terrain.json packed, as terrain.bin
	var d := _pack(JSON.parse_string(FileAccess.get_file_as_string(PATH)))
	d["_stamp"] = _bin_stamp()
	var f := FileAccess.open(BIN, FileAccess.WRITE)
	f.store_var(d)
	f.close()


static func _raster(file: String) -> PackedByteArray:
	var raw := FileAccess.get_file_as_bytes("res://remake/" + file)
	return raw.decompress(_nx * _ny * 2, FileAccess.COMPRESSION_GZIP)


static func _sparse(buf: PackedByteArray) -> Array:
	## [slot per tile, value per tile, the non-uniform tiles' cells (WT rows of WT halves each)]
	var nty := ceili(_ny / float(WT))
	var slot := PackedInt32Array()
	var k := PackedFloat32Array()
	var tiles := PackedByteArray()
	slot.resize(_wtx * nty)
	k.resize(_wtx * nty)
	var rowb := WT * 2
	var n := 0
	for tj in nty:
		for ti in _wtx:
			var tile := PackedByteArray()
			for r in WT:
				var j := mini(tj * WT + r, _ny - 1)
				var a := (j * _nx + ti * WT) * 2
				var row := buf.slice(a, a + mini(rowb, (_nx - ti * WT) * 2))
				if row.size() < rowb:
					row.resize(rowb)                     # (past the edge: never read)
				tile.append_array(row)
			var v := tile.decode_half(0)
			var one := PackedByteArray()
			one.resize(2)
			one.encode_half(0, v)
			var uni := tile.slice(0, 2)
			while uni.size() < tile.size():
				uni.append_array(uni)
			if uni == tile:
				slot[tj * _wtx + ti] = -1
				k[tj * _wtx + ti] = v
			else:
				slot[tj * _wtx + ti] = n
				tiles.append_array(tile)
				n += 1
	return [slot, k, tiles]


static func _sv(slot: PackedInt32Array, k: PackedFloat32Array, tiles: PackedByteArray, i: int, j: int) -> float:
	var ti := (j / WT) * _wtx + i / WT
	var sl := slot[ti]
	if sl < 0:
		return k[ti]
	return tiles.decode_half((sl * WT * WT + (j % WT) * WT + i % WT) * 2)


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
	var lv := _sv(_lvl_slot, _lvl_k, _lvl_t, i, j)
	if lv < -9000.0:
		return Vector2(-9999.0, 0.0)
	# (the depth, bilinear)
	var i0 := floori(f.x)
	var j0 := clampi(floori(f.y), 0, _ny - 2)
	var tx := f.x - i0
	var ty := clampf(f.y - j0, 0.0, 1.0)
	i0 = posmod(i0, _nx)
	var i1 := (i0 + 1) % _nx
	var a := lerpf(_sv(_dep_slot, _dep_k, _dep_t, i0, j0), _sv(_dep_slot, _dep_k, _dep_t, i1, j0), tx)
	var b := lerpf(_sv(_dep_slot, _dep_k, _dep_t, i0, j0 + 1), _sv(_dep_slot, _dep_k, _dep_t, i1, j0 + 1), tx)
	return Vector2(lv, lerpf(a, b, ty))


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
	var kind := KINDS.find(item[0])
	var rec := PackedInt32Array([kind, item[1], item[2] if item.size() > 2 else -1, item[3] if item.size() > 3 else -1])
	_gmx.lock()
	for key in keys:
		var a: PackedInt32Array = _grid.get(key, PackedInt32Array())
		a.append_array(rec)
		_grid[key] = a
		_gcache.erase(key)
		_gcache_old.erase(key)
	_gmx.unlock()


# The grid was ~968,000 little Arrays on the 1:1 map (~200 MB): it's packed, and a cell's items are made as they're
# asked for (kept a while, two generations of GCACHE_MAX cells: the lookups round the player ask for the same ones).
static var _gcache := {}
static var _gcache_old := {}
static var _gmx := Mutex.new()
const GCACHE_MAX := 16384


static func _items(key: Vector2i) -> Array:
	## a grid cell's items: ["road", i, k0, k1], ["seg", i, k], [kind, i]
	_gmx.lock()
	var got = _gcache.get(key)
	if got == null:
		got = _gcache_old.get(key)
		if got == null:
			got = []
			var a: PackedInt32Array = _grid.get(key, PackedInt32Array())
			for j in range(0, a.size(), 4):
				if a[j + 3] >= 0:
					got.append([KINDS[a[j]], a[j + 1], a[j + 2], a[j + 3]])
				elif a[j + 2] >= 0:
					got.append([KINDS[a[j]], a[j + 1], a[j + 2]])
				else:
					got.append([KINDS[a[j]], a[j + 1]])
		if _gcache.size() >= GCACHE_MAX:
			_gcache_old = _gcache
			_gcache = {}
		_gcache[key] = got
	_gmx.unlock()
	return got


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


static var _water_cells := {}         # Vector2i -> the coarse cell's small-water items only
static var _pad_cells := {}           # Vector2i -> its pads only


static var _cache_mx := Mutex.new()     # the lazily built cells are asked for from worker threads (terrain tiles)


static func _kind_cell(cache: Dictionary, key: Vector2i, kinds: Array) -> Array:
	## The coarse cell's items of these kinds (filtered once, on first use).
	_cache_mx.lock()
	var got = cache.get(key)
	_cache_mx.unlock()
	if got != null:
		return got
	var out: Array = []
	for it in _items(key):
		if kinds.has(it[0]):
			out.append(it)
	_cache_mx.lock()
	cache[key] = out
	_cache_mx.unlock()
	return out


static func _small_depth(s: float, x: float) -> float:
	## Carved depth of the small water (creeks, spurs, ponds, oxbows, ditches) below the terrain.
	var dep := 0.0
	var key := Vector2i(floori(s / CELL), floori(x / CELL))
	for it in _kind_cell(_water_cells, key, ["seg", "pond", "oxbow", "ditch"]):
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


const RCELL := 16.0                   # the roads' own fine grid (_road_cell)
const RSTRIDE := 11                  # per segment: a.s a.x b.s b.x kerb_r kerb_l verge cum0 cum1 road k
static var _rcells := {}             # Vector2i -> PackedFloat32Array, built on first use
static var _rcells_old := {}         # (two generations of RCELLS_MAX: 82,000 cells in a minute in a 1:1 city, unbounded)
const RCELLS_MAX := 12000


static func _road_cell(key: Vector2i) -> PackedFloat32Array:
	## The road segments that can reach into a RCELL cell (its share of the coarse grid's, as packed
	## numbers: the height lookup's inner loop then touches no Dictionary).
	_cache_mx.lock()
	var got = _rcells.get(key)
	if got == null:
		got = _rcells_old.get(key)
		if got != null:
			_rcells[key] = got
	_cache_mx.unlock()
	if got != null:
		return got
	var out := PackedFloat32Array()
	var cs := (key.x + 0.5) * RCELL
	var cx := (key.y + 0.5) * RCELL
	var half_diag := RCELL * 0.7072
	for it in _items(Vector2i(floori(cs / CELL), floori(cx / CELL))):
		if it[0] != "road":
			continue
		var rd: Dictionary = _d.roads[it[1]]
		var kr: float = rd.get("hr", rd.w * 0.5)
		var kl: float = rd.get("hl", rd.w * 0.5)
		var verge: float = float(rd.get("lawn", 0.0)) + float(rd.get("walk", 0.0))
		var cum: PackedFloat32Array = rd.cum
		for k in range(it[2], it[3]):
			var a: Vector2 = rd.pts[k]
			var bq: Vector2 = rd.pts[k + 1]
			if _seg_dist(cs, cx, a[0], a[1], bq[0], bq[1]) > maxf(kr, kl) + verge + 0.5 + BLEND_MAX + half_diag:
				continue
			out.append_array(PackedFloat32Array([a[0], a[1], bq[0], bq[1], kr, kl, verge, cum[k], cum[k + 1], it[1], k]))
	_cache_mx.lock()
	if _rcells.size() >= RCELLS_MAX:
		_rcells_old = _rcells
		_rcells = {}
	_rcells[key] = out
	_cache_mx.unlock()
	return out


static func _road_grade(s: float, x: float, base: float) -> Vector2:
	## (terrain graded to the nearest road, that road's weight 0..1): flat across the carriageway
	## and a 0.5 m shoulder at the centreline's height, blending back over ROAD_BLEND.
	var best_w := 0.0
	var best_h := base
	var best_d := INF
	var best_rise := 0.0
	var on_carriageway := false
	var on_road := {}                     # road -> [distance, height] of its nearest segment, where it weighs 1
	var seg := _road_cell(Vector2i(floori(s / RCELL), floori(x / RCELL)))
	for j in range(0, seg.size(), RSTRIDE):
		# the nearest point of the segment (its distance; t along it)
		var a0: float = seg[j]
		var a1: float = seg[j + 1]
		var ds := fposmod(seg[j + 2] - a0 + C * 0.5, C) - C * 0.5
		var dx: float = seg[j + 3] - a1
		var ps := fposmod(s - a0 + C * 0.5, C) - C * 0.5
		var px := x - a1
		var L2 := ds * ds + dx * dx
		var t := clampf((ps * ds + px * dx) / L2, 0.0, 1.0) if L2 > 1e-9 else 0.0
		var dist := Vector2(ps - ds * t, px - dx * t).length()
		# the right of way: each side's kerb (a parking lane widens its side), then the tree lawn and
		# the sidewalk (tools/street_rules.py) -- all of it graded flat with the road
		var kr: float = seg[j + 4]
		var kl: float = seg[j + 5]
		var verge: float = seg[j + 6]
		var hw: float = maxf(kr, kl) + verge
		if dist > hw + 0.5 + BLEND_MAX:
			continue
		var right_side: bool = (ds * px - dx * ps) > 0.0          # (right of the way along the points: (-dx, ds))
		var kerb: float = kr if right_side else kl
		if dist <= kerb:
			on_carriageway = true
		var ri := int(seg[j + 9])
		var rd: Dictionary = _d.roads[ri]
		var h: float
		var zp: PackedFloat32Array = rd.zp
		if zp.is_empty():
			h = base_elev(a0 + ds * t, a1 + dx * t)
		else:
			# the road's graded profile at the nearest point of its centreline
			var u: float = lerpf(seg[j + 7], seg[j + 8], t) / _prof_step
			var k := clampi(floori(u), 0, zp.size() - 1)
			var k1 := mini(k + 1, zp.size() - 1)
			if zp[k] < -9000.0 or zp[k1] < -9000.0:
				continue                                 # over a great river: the great bridge carries it
			h = lerpf(zp[k], zp[k1], clampf(u - k, 0.0, 1.0))
		# the cut or fill slope reaches out SIDE_SLOPE m for every metre the road is off the ground
		var blend := clampf(absf(h - base) * SIDE_SLOPE, ROAD_BLEND, BLEND_MAX)
		var w := 1.0 - smoothstep(hw + 0.5, hw + 0.5 + blend, dist)
		# the strongest road; between equals (every nearby segment of a road weighs 1 on its
		# carriageway), the nearest segment -- not one whose clamped end happens to come first
		if w > best_w + 1e-6 or (w > best_w - 1e-6 and dist < best_d):
			best_w = w
			best_h = h
			best_d = dist
			best_rise = CURB_RISE * clampf((dist - kerb) / 0.25, 0.0, 1.0) if verge > 0.0 else 0.0
		# where carriageways overlap (a junction), each road's nearest segment, to blend between
		if w > 0.999 and dist < float(on_road.get(ri, [INF])[0]):
			on_road[ri] = [dist, h]
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
	if not on_carriageway:
		best_h += best_rise                          # the lawn and the sidewalk, at the kerb's top
	return Vector2(lerpf(base, best_h, best_w), best_w)


static func _ramp_to_bridge(s: float, x: float, h: float) -> float:
	## A road near a crossing ramps to its deck over RAMP m (so both approaches meet the deck).
	for it in _items(Vector2i(floori(s / CELL), floori(x / CELL))):
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
	for it in _kind_cell(_pad_cells, Vector2i(floori(s / CELL), floori(x / CELL)), ["pad"]):
		var pd := _pads.slice(it[1] * PAD_N, it[1] * PAD_N + PAD_N)
		var ds := _wrap(s - pd[0])
		var dx: float = x - pd[1]
		var lx: float = dx * pd[2] + ds * pd[3]             # into the building's own frame
		var lz: float = dx * pd[3] - ds * pd[2]
		var ox := maxf(0.0, maxf(pd[4] - PAD_MARGIN - lx, lx - pd[6] - PAD_MARGIN))
		var oz := maxf(0.0, maxf(pd[5] - PAD_MARGIN - lz, lz - pd[7] - PAD_MARGIN))
		var w := 1.0 - smoothstep(0.0, float(pd[9]), Vector2(ox, oz).length())
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
	Placement.load_all()
	_pad_h.resize(Placement.count())
	_pad_h.fill(NAN)
	# the pads come baked (remake/tools/bake_world.gd pads): working out ~64,000 of them here, five road grades
	# each, took a minute at every launch on the 1:1 map (2026-10-08)
	var baked := _read_pads_baked()
	var bv: PackedFloat64Array = baked.get("v", PackedFloat64Array())
	var brow: Dictionary = baked.get("row", {})
	for pi in Placement.count():
		if Placement.kind(pi) == "crossing":
			_load_bridge(Placement.entry(pi))
			continue
		var row: int = brow.get(Placement.id(pi), -1)
		if row >= 0:
			var pb := bv.slice(row * PAD_N, row * PAD_N + PAD_N)
			_pad_h[pi] = pb[8]
			var np := _pads.size() / PAD_N
			_pads.append_array(pb)
			var rch := Vector2(maxf(absf(pb[4]), absf(pb[6])), maxf(absf(pb[5]), absf(pb[7]))).length()
			_index(["pad", np], pb[0] - rch, pb[1] - rch, pb[0] + rch, pb[1] + rch, PAD_MARGIN + float(pb[9]))
			continue
		var e := Placement.entry(pi)
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
		# how far the lot must blend back: 1 in PAD_SLOPE from the pad to the ground at its corners
		var diff := 0.0
		for cx in [e.min[0], e.max[0]]:
			for cz in [e.min[2], e.max[2]]:
				var cs_: float = s0 + float(cx) * sn - float(cz) * c
				var cx_: float = x0 + float(cx) * c + float(cz) * sn
				diff = maxf(diff, absf(hpad - _road_grade(fposmod(cs_, C), cx_, base_elev(cs_, cx_)).x))
		var blend := clampf(diff * PAD_SLOPE, PAD_BLEND, PAD_BLEND_MAX)
		var pd := PackedFloat64Array([s0, x0, c, sn, e.min[0], e.min[2], e.max[0], e.max[2], hpad, blend])
		_pad_h[pi] = hpad
		var np := _pads.size() / PAD_N
		_pads.append_array(pd)
		var reach := Vector2(maxf(absf(e.min[0]), absf(e.max[0])), maxf(absf(e.min[2]), absf(e.max[2]))).length()
		_index(["pad", np], s0 - reach, x0 - reach, s0 + reach, x0 + reach, PAD_MARGIN + blend)


const PADS_BAKED := "res://remake/baked/pads.bin"
const PADS_VERSION := 1


static func pads_stamp() -> String:
	return BakedMeshes.fingerprint([PATH, PLACEMENT, "res://remake/terrain_base.bin.gz", "res://remake/terrain_level.bin.gz",
		"res://remake/terrain_depth.bin.gz"], PADS_VERSION)


static func _read_pads_baked() -> Dictionary:
	## {row: id -> its row in v, v: PAD_N a pad}, if the baked pads are of this data
	if not FileAccess.file_exists(PADS_BAKED):
		return {}
	var f := FileAccess.open(PADS_BAKED, FileAccess.READ)
	var d: Variant = f.get_var()
	f.close()
	if typeof(d) != TYPE_DICTIONARY or str(d.get("stamp", "")) != pads_stamp():
		push_warning("MapTerrain: the baked pads are of other data -- working them out (rerun remake/tools/bake_world.gd pads)")
		return {}
	var row := {}
	var ids: PackedStringArray = d.ids
	for i in ids.size():
		row[ids[i]] = i
	return {"row": row, "v": d.v}


static func bake_pads() -> int:
	## (remake/tools/bake_world.gd) every pad worked out afresh and saved
	_load()
	var ids := PackedStringArray()
	var v := PackedFloat64Array()
	var k := 0
	for pi in Placement.count():
		if Placement.kind(pi) == "crossing":
			continue
		ids.append(Placement.id(pi))
		v.append_array(_pads.slice(k * PAD_N, k * PAD_N + PAD_N))
		k += 1
	var f := FileAccess.open(PADS_BAKED, FileAccess.WRITE)
	f.store_var({"stamp": pads_stamp(), "ids": ids, "v": v})
	f.close()
	return ids.size()


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
	var dk: Array = e.get("deck", [0.0, 0.0])            # the bridge proper's length and width (placement.py)
	_bridges.append([s0, x0, c, sn, e.fmin[0], e.fmin[1], e.fmax[0], e.fmax[1], deck, float(dk[0]), float(dk[1])])
	_pad_h[Placement.index(e.id)] = deck
	var reach := Vector2(maxf(absf(e.fmin[0]), absf(e.fmax[0])), maxf(absf(e.fmin[1]), absf(e.fmax[1]))).length()
	_index(["bridge", _bridges.size() - 1], s0 - reach, x0 - reach, s0 + reach, x0 + reach, RAMP)


static func on_small_bridge(s: float, x: float, reach := 8.0, before := 0.0) -> bool:
	## Is (s, x) on a small crossing's deck -- between its abutments (and before m short of them),
	## within reach m of its middle across (a road wider than the bridge is cut there too)?  The roads' own surface stops there:
	## the bridge model carries them.
	_load()
	s = fposmod(s, C)
	for it in _items(Vector2i(floori(s / CELL), floori(x / CELL))):
		if it[0] != "bridge":
			continue
		var bd: Array = _bridges[it[1]]
		if bd[9] <= 0.0:
			continue
		var ds := _wrap(s - bd[0])
		var dx: float = x - bd[1]
		var lx: float = dx * bd[2] + ds * bd[3]
		var lz: float = dx * bd[3] - ds * bd[2]
		if absf(lz - (bd[5] + bd[7]) * 0.5) <= bd[9] * 0.5 + before and absf(lx - (bd[4] + bd[6]) * 0.5) <= bd[10] * 0.5 + reach:
			return true
	return false


static func pad_height(id: String) -> float:
	## The height a placed structure stands at (its pad, or a crossing's deck).
	_load()
	var i := Placement.index(id)
	return NAN if i < 0 else _pad_h[i]


static var _lc: Image = null


static func landcover_image() -> Image:
	if _lc == null:
		_load_lc()
	return _lc


static func _load_lc() -> void:
	_load()
	var im: Image = load("res://remake/landcover.png")
	# (class and field id only: RG, not the PNG's RGB -- 44 MB, not 66 here and 88 as an RGBA texture)
	if im.get_format() != Image.FORMAT_RG8:
		im = im.duplicate()
		im.convert(Image.FORMAT_RG8)
	_lc = im


static func landcover_step() -> float:
	_load()
	return _lc_step


static func landcover(s: float, x: float) -> Vector2i:
	## (class, field id) of the map's land cover at (s, x) -- remake/landcover.png, 2 m / px:
	## 1 built-up, 2 floodplain meadow, 3 woods, 4 farm field (id picks its crop), 5 windbreak grove,
	## 0 anything else.
	if _lc == null:
		_load_lc()
	var px := clampi(floori(fposmod(s, C) / _lc_step), 0, _lc.get_width() - 1)
	var py := clampi(floori((x + StationGeo.HALF_LEN) / _lc_step), 0, _lc.get_height() - 1)
	var c := _lc.get_pixel(px, py)
	return Vector2i(roundi(c.r * 255.0), roundi(c.g * 255.0))


static func area_kind(s: float, x: float) -> String:
	## The town area at (s, x) -- "lawn", "parking", "square", "schoolground"... -- or "".
	_load()
	s = fposmod(s, C)
	for it in _items(Vector2i(floori(s / CELL), floori(x / CELL))):
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
