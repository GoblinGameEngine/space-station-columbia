extends Node3D
class_name GreatBridges

## The expanded station's great bridges (remake/bridges.json, from remake/tools/placement.py: the
## XBR / XRR catalog records -- Blue Water, Zilwaukee, Leo Frigo, Hoan, Irondequoit Bay, Glass City
## Skyway, Chesapeake Bay, Long Beach Gateway, Al Zampa, Dumbarton, San Joaquin River Viaduct -- on
## the Kettle, Maumee and Miami crossings), built at load between each crossing's ends.
##
## The deck climbs from the road on the bank at GRADE to its crest (the water level plus the record's
## clearance, or as high as the grade allows), its approaches reaching back over the basin up to
## APPROACH_MAX; approach piers every approaches.span_m; the main span's structure by type:
##   suspension     two towers, main cables from anchorages over the tower tops, vertical hangers
##   cable_stayed   a single central pylon or two towers, fans of stays to the deck edges
##   tied_arch      a steel arch rib over the main span each side, vertical hangers
##   deck_truss     a steel truss under the main spans
##   segmental_box / girder_trestle   a haunched box girder on tall piers
##   rail_viaduct_arch   twin concrete arches under a ballasted double-track deck
## Every pier founds FOUND below the bed / ground (the records say 25-30 m; nothing floats).
## The deck and its parapets collide.

const GRADE := 0.05
const APPROACH_MAX := 280.0
const STEP := 5.0
const FOUND := 25.0
const DECK_D := 2.2
const APPROACH_MIN := 30.0
const SMOOTH_R := 20.0

var _mats := {}
static var decks: Array = []         # every great bridge's line (the spans), for the trees to keep out from under
var spans := []                      # each bridge's line, for tests: {id, name, o (s, x), dir, len, hw, rail}


func setup() -> void:
	decks.clear()
	if not FileAccess.file_exists("res://remake/bridges.json"):
		return
	var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://remake/bridges.json"))
	_mats["asphalt"] = _tex_mat("lib/asphalt", 1.0)
	_mats["concrete"] = _tex_mat("lib/concrete", 1.0)
	_mats["line"] = _solid(Color(0.95, 0.95, 0.9))
	_mats["yellow"] = _solid(Color(0.95, 0.72, 0.1))              # the roads' own paint (MapRoads)
	_mats["cable"] = _solid(Color(0.25, 0.25, 0.27))
	_mats["ballast"] = _tex_mat("lib/gravel", 1.0)
	_mats["rail"] = _solid(Color(0.35, 0.3, 0.28))
	_mats["glass"] = _solid(Color(0.55, 0.75, 0.95), true)
	for br in d.bridges:
		_build(br)


func _tex_mat(path: String, _t: float) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	var root := "res://remake/textures/%s_" % path
	m.albedo_texture = load(root + "albedo.webp")
	m.normal_enabled = true
	m.normal_texture = load(root + "normal.webp")
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	return m


func _solid(c: Color, glow := false) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = 0.45
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	if glow:
		m.emission_enabled = true
		m.emission = c
		m.emission_energy_multiplier = 1.5
	return m


# ------------------------------------------------------------------ one bridge
var _st := {}                  # material -> SurfaceTool for the bridge being built
var _col := PackedVector3Array()
var _o := Vector2.ZERO         # map (s, x) of end A
var _dir := Vector2.RIGHT      # unit, A -> B, map units (the main span's line)
var _side := Vector2.UP
var _pp := PackedVector2Array()  # the bridge's line, approach to approach: along the road it carries
var _pc := PackedFloat32Array()  # arc length at each of _pp


func _surf(mat: String) -> SurfaceTool:
	if not _st.has(mat):
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		_st[mat] = st
	return _st[mat]


func _at(u: float) -> Vector2:
	## the bridge's line at u m from end A (map s, x; s may run past the seam)
	if _pp.size() < 2:
		return _o + _dir * u
	if u <= 0.0:
		return _pp[0] + (_pp[1] - _pp[0]).normalized() * u
	var n := _pp.size()
	if u >= _pc[n - 1]:
		return _pp[n - 1] + (_pp[n - 1] - _pp[n - 2]).normalized() * (u - _pc[n - 1])
	var k := _pc.bsearch(u) - 1
	k = clampi(k, 0, n - 2)
	var t := (u - _pc[k]) / maxf(_pc[k + 1] - _pc[k], 1e-6)
	return _pp[k].lerp(_pp[k + 1], t)


func _left(u: float) -> Vector2:
	## the unit vector to the line's left at u (the tangent over a few metres, so a curve's sides are smooth)
	var t := (_at(u + 2.0) - _at(u - 2.0)).normalized()
	return Vector2(-t.y, t.x)


func _P(u: float, v: float, h: float) -> Vector3:
	## a point at u m along the bridge from end A, v m to its left, h m above the floor datum
	var m := _at(u) + _left(u) * v
	return StationGeo.point(m.x, m.y, h)


func _tri_quad(mat: String, a: Vector3, b: Vector3, c: Vector3, d: Vector3, collide := false, uv_scale := 4.0) -> void:
	var st := _surf(mat)
	var n := (b - a).cross(d - a).normalized()
	var la := a.distance_to(b) / uv_scale
	var lb := a.distance_to(d) / uv_scale
	var uvs := [Vector2(0, 0), Vector2(la, 0), Vector2(la, lb), Vector2(0, lb)]
	var q := [a, b, c, d]
	for j in [0, 1, 2, 0, 2, 3]:
		st.set_normal(n)
		st.set_uv(uvs[j])
		st.add_vertex(q[j])
	if collide:
		_col.append_array(PackedVector3Array([a, b, c, a, c, d]))


func _beam(mat: String, p: Vector3, q: Vector3, r: float) -> void:
	## a square member of half-width r between two world points (cables, hangers, stays, truss bars)
	var ax := (q - p)
	if ax.length() < 0.01:
		return
	var u := ax.normalized()
	var ref := Vector3.UP if absf(u.dot(Vector3.UP)) < 0.9 else Vector3.RIGHT
	var s1 := u.cross(ref).normalized() * r
	var s2 := u.cross(s1).normalized() * r
	var c := [s1 + s2, s1 - s2, -s1 - s2, -s1 + s2]
	for i in 4:
		_tri_quad(mat, p + c[i], q + c[i], q + c[(i + 1) % 4], p + c[(i + 1) % 4])


func _column(mat: String, u: float, v: float, z0: float, z1: float, hw: float, hd: float) -> void:
	## an upright box centred (u, v) on the bridge line, hw along the bridge, hd across
	var cs := [[-1, -1], [1, -1], [1, 1], [-1, 1]]
	for i in 4:
		var a: Array = cs[i]
		var b: Array = cs[(i + 1) % 4]
		_tri_quad(mat, _P(u + hw * a[0], v + hd * a[1], z0), _P(u + hw * b[0], v + hd * b[1], z0),
			_P(u + hw * b[0], v + hd * b[1], z1), _P(u + hw * a[0], v + hd * a[1], z1))
	_tri_quad(mat, _P(u - hw, v - hd, z1), _P(u + hw, v - hd, z1), _P(u + hw, v + hd, z1), _P(u - hw, v + hd, z1))


static func off_line(sp: Dictionary, s: float, x: float) -> float:
	## How far (s, x) is from a bridge's line (spans / decks entries), to one side -- INF beyond its ends.
	var line: PackedVector2Array = sp.line
	var best := INF
	for k in line.size() - 1:
		var a := line[k]
		var d := Vector2(line[k + 1].x - a.x, line[k + 1].y - a.y)
		var L2 := d.length_squared()
		if L2 < 1e-9:
			continue
		var v := Vector2(StationGeo.wrap_ds(s - a.x), x - a.y)
		var t := v.dot(d) / L2
		if (t < 0.0 and k > 0) or (t > 1.0 and k < line.size() - 2):
			continue
		if t < -0.2 or t > 1.2:
			continue                                     # (just past an end still counts, a little)
		best = minf(best, (v - d * clampf(t, 0.0, 1.0)).length())
	return best


func _smooth_line() -> void:
	## The line resampled every 2 m and rounded (a running mean over SMOOTH_R m either side, shrinking
	## to nothing at the two ends, which stay on the road): the bend where an approach that follows
	## the road meets the straight span becomes a curve, not a corner.
	var L := _pc[_pc.size() - 1]
	var n := maxi(2, ceili(L / 2.0))
	var pts := PackedVector2Array()
	for i in n + 1:
		pts.append(_at(L * i / float(n)))
	var r := int(SMOOTH_R / 2.0)
	var out := pts.duplicate()
	for i in range(1, n):
		var k := mini(r, mini(i, n - i))
		var acc := Vector2.ZERO
		for j in range(i - k, i + k + 1):
			acc += pts[j]
		out[i] = acc / float(2 * k + 1)
	_pp = out
	_pc = PackedFloat32Array([0.0])
	for i in range(1, _pp.size()):
		_pc.append(_pc[i - 1] + _pp[i].distance_to(_pp[i - 1]))


func _carried_road(a: Vector2, b: Vector2, rail: bool) -> Dictionary:
	## The road (the railway, for a rail bridge) passing both inventory ends: {road, ua, ub, a, b} --
	## its arc lengths at the points nearest a and b, and those points -- or {} if none passes both.
	MapTerrain.elevation(0.0, 0.0)
	var roads: Array = MapTerrain._d.roads
	var best := {}
	var best_d := 160.0
	for ri in roads.size():
		var rd: Dictionary = roads[ri]
		if (rd.cls == "rail") != rail:
			continue
		var pa := _nearest_on(rd, a)
		var pb := _nearest_on(rd, b)
		if pa.x + pb.x < best_d:
			best_d = pa.x + pb.x
			best = {"road": ri, "ua": pa.y, "ub": pb.y}
	if best.is_empty():
		return {}
	var rd: Dictionary = roads[best.road]
	best["a"] = _road_point(rd, best.ua)
	var pb := _road_point(rd, best.ub)
	best["b"] = Vector2(best.a.x + StationGeo.wrap_ds(pb.x - best.a.x), pb.y)
	return best


func _nearest_on(rd: Dictionary, p: Vector2) -> Vector2:
	## (distance, arc length) of the point of road rd nearest p
	var pts: Array = rd.pts
	var cum: PackedFloat32Array = rd.cum
	var best := Vector2(INF, 0.0)
	for k in pts.size() - 1:
		var pr := MapTerrain._seg_proj(p.x, p.y, pts[k][0], pts[k][1], pts[k + 1][0], pts[k + 1][1])
		if pr.x < best.x:
			best = Vector2(pr.x, lerpf(cum[k], cum[k + 1], pr.y))
	return best


static func _road_point(rd: Dictionary, u: float) -> Vector2:
	## road rd at arc length u (past either end, straight on along its last segment)
	var pts: Array = rd.pts
	var cum: PackedFloat32Array = rd.cum
	var n := pts.size()
	var k := 0
	if u <= 0.0:
		k = 0
	elif u >= cum[n - 1]:
		k = n - 2
	else:
		k = clampi(cum.bsearch(u) - 1, 0, n - 2)
	var a := Vector2(pts[k][0], pts[k][1])
	var b := Vector2(pts[k + 1][0], pts[k + 1][1])
	var d := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)
	return a + d * ((u - cum[k]) / maxf(cum[k + 1] - cum[k], 1e-6))


func _road_from(c: Dictionary, back: bool, t: float) -> Vector2:
	## The carried road t m out from the bank end: back (from a, away from b) or forward (from b).
	var rd: Dictionary = MapTerrain._d.roads[c.road]
	var sgn := 1.0 if c.ub > c.ua else -1.0
	var u: float = (c.ua - sgn * t) if back else (c.ub + sgn * t)
	return _road_point(rd, u)


func _wet(m: Vector2) -> bool:
	## Is (s, x) under the river / lake / sea (or its carved bed)?
	var s := fposmod(m.x, StationGeo.CIRC)
	var wa := MapTerrain.water_at(s, m.y)
	return wa.x > -9000.0 and wa.x > MapTerrain.elevation(s, m.y) - 0.05


func _ground_across(u: float, hw: float) -> float:
	## The highest ground under the deck's width at u.
	var h := -INF
	for v: float in [-hw, -hw * 0.5, 0.0, hw * 0.5, hw]:
		var m := _at(u) + _left(u) * v
		h = maxf(h, MapTerrain.elevation(m.x, m.y))
	return h


func _ground(u: float) -> float:
	var m := _at(u)
	return MapTerrain.elevation(m.x, m.y)


func _build(br: Dictionary) -> void:
	_st.clear()
	_col = PackedVector3Array()
	var tr: Dictionary = br.traits
	var ends: Array = br.ends
	var a := Vector2(ends[0][0], ends[0][1])
	var b := Vector2(ends[1][0], ends[1][1])
	_pp = PackedVector2Array()
	_pc = PackedFloat32Array()
	# the road (or railway) the bridge carries: its line is where the approaches go, so they meet it.
	# The span runs straight between the road's points at the two banks.
	var carried := _carried_road(a, b, str(br.get("road_class")) == "rail" or str(tr.get("type", "")) == "rail_viaduct_arch")
	if not carried.is_empty():
		a = carried.a
		b = carried.b
	var dv := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)
	var span := dv.length()
	_dir = dv / span
	_side = Vector2(-_dir.y, _dir.x)
	var typ: String = str(tr.get("type", "girder_trestle"))
	var rail: bool = typ == "rail_viaduct_arch" or str(br.get("road_class")) == "rail"
	var lanes: int = int(tr.get("lanes", 2)) if tr.get("lanes") != null else 2
	var hw: float = 5.5 if rail else (lanes * 3.6 + (3.0 if tr.get("shoulders", false) else 1.0) + (2.5 if tr.get("walkway", false) else 0.0)) * 0.5
	# the water level at mid-span and the bank heights
	var mid := a + dv * 0.5
	var lv := MapTerrain.water_at(fposmod(mid.x, StationGeo.CIRC), mid.y).x
	var bank_a := MapTerrain.elevation(a.x, a.y)
	var bank_b := MapTerrain.elevation(b.x, b.y)
	if lv < -9000.0:
		lv = minf(bank_a, bank_b) - 1.0
	var clearance: float = float(tr.get("clearance_m", 20.0)) if tr.get("clearance_m") != null else 20.0
	var top := minf(lv + clearance, minf(bank_a, bank_b) + GRADE * (span * 0.5 + APPROACH_MAX))
	top = maxf(top, lv + 6.0)
	var ext_a := clampf((top - bank_a) / GRADE - span * 0.5, 0.0, APPROACH_MAX)
	var ext_b := clampf((top - bank_b) / GRADE - span * 0.5, 0.0, APPROACH_MAX)
	# each approach starts on dry ground -- the graded road -- never out in the basin: the deck's
	# first metre then meets the road's surface exactly
	# at least APPROACH_MIN of approach each end (along the road), however short the climb: the line
	# eases from the road's heading onto the span's over it
	ext_a = maxf(ext_a, APPROACH_MIN)
	ext_b = maxf(ext_b, APPROACH_MIN)
	var back := func(dd: float) -> Vector2: return _road_from(carried, true, dd) if not carried.is_empty() else a - _dir * dd
	var fwd := func(dd: float) -> Vector2: return _road_from(carried, false, dd) if not carried.is_empty() else b + _dir * dd
	while ext_a < APPROACH_MAX + 300.0 and _wet(back.call(ext_a)):
		ext_a += 4.0
	while ext_b < APPROACH_MAX + 300.0 and _wet(fwd.call(ext_b)):
		ext_b += 4.0
	# the line: approach A along the road (toward the bank), the span straight across, approach B along
	# the road; u runs from the start of approach A to L
	var lay_a := ext_a
	while lay_a > 0.0:
		_pp.append(back.call(lay_a))
		lay_a -= 2.0
	var ia := _pp.size()
	_pp.append(a)
	_pp.append(a + dv)                                   # (b, kept continuous across the seam)
	var lay_b := 2.0
	while lay_b <= ext_b + 0.01:
		var q: Vector2 = fwd.call(minf(lay_b, ext_b))
		_pp.append(Vector2(_pp[_pp.size() - 1].x + StationGeo.wrap_ds(q.x - _pp[_pp.size() - 1].x), q.y))
		lay_b += 2.0
	for i in range(_pp.size() - 2, -1, -1):             # (continuous s back from a, too)
		_pp[i] = Vector2(_pp[i + 1].x - StationGeo.wrap_ds(_pp[i + 1].x - _pp[i].x), _pp[i].y)
	_pc.append(0.0)
	for i in range(1, _pp.size()):
		_pc.append(_pc[i - 1] + _pp[i].distance_to(_pp[i - 1]))
	var span_start := _pc[ia]
	_smooth_line()
	_o = _pp[0]
	var L := _pc[_pc.size() - 1]
	# where the span starts along the line (the approach as laid, not the planned ext_a)
	ext_a = span_start
	ext_b = L - ext_a - span
	var line := PackedVector2Array()
	var u_ := 0.0
	while u_ < L:
		line.append(_at(u_))
		u_ += 5.0
	line.append(_at(L))
	spans.append({"id": br.id, "name": br.get("name", br.id), "o": _o, "dir": _dir, "len": L, "hw": hw, "rail": rail, "line": line})
	decks.append(spans[-1])
	var z0 := _ground(0.0) + MapRoads.LIFT                # level with the road's own surface there
	var z1 := _ground(L) + MapRoads.LIFT
	var n := maxi(2, ceili(L / STEP))
	var us := []
	var zs := []
	for i in n + 1:
		var u := L * i / float(n)
		us.append(u)
		zs.append(minf(top, minf(z0 + GRADE * u, z1 + GRADE * (L - u))))
	# round the crest and the sags (a vertical curve)
	var zz := zs.duplicate()
	for i in range(1, n):
		var acc := 0.0
		var cnt := 0
		for j in range(maxi(0, i - 6), mini(n + 1, i + 7)):
			acc += zs[j]
			cnt += 1
		zz[i] = acc / cnt
	zz[0] = z0
	zz[n] = z1
	# never below the ground it crosses: where the graded road under an approach climbs faster than
	# the deck's GRADE, the deck follows it up (else the ground stands through the deck -- a step)
	# -- across the whole deck: the bridge's straight line needn't follow the road's, and beside the
	# road the ground may be a cutting's side slope
	for i in range(1, n):
		zz[i] = maxf(zz[i], _ground_across(us[i], hw) + 0.05)
		var gm := _ground_across((us[i - 1] + us[i]) * 0.5, hw) + 0.05
		zz[i] = maxf(zz[i], gm - (zz[i - 1] - gm))            # the ground between samples, too
	var deck_mat := "ballast" if rail else "asphalt"
	var col := Color.html(str(tr.get("color", "#b8b4ac"))) if tr.get("color") is String else Color(0.72, 0.72, 0.7)
	if tr.get("color") is Dictionary:
		col = Color.html(str(tr.color.get("girders", "#8a8a8a")))
		_mats["arch_" + br.id] = _solid(Color.html(str(tr.color.get("arch", "#e0b43a"))))
	_mats["steel_" + br.id] = _solid(col)
	var steel: String = "steel_" + br.id
	var arch_mat: String = "arch_" + br.id if _mats.has("arch_" + br.id) else steel
	# ---- the deck: surface, girder sides and soffit, parapets, lane lines
	for i in n:
		var ua: float = us[i]
		var ub: float = us[i + 1]
		var za: float = zz[i]
		var zb: float = zz[i + 1]
		_tri_quad(deck_mat, _P(ua, hw, za), _P(ub, hw, zb), _P(ub, -hw, zb), _P(ua, -hw, za), true, 6.0)
		for sg in [1.0, -1.0]:
			_tri_quad("concrete", _P(ua, hw * sg, za - DECK_D), _P(ub, hw * sg, zb - DECK_D), _P(ub, hw * sg, zb + 1.0), _P(ua, hw * sg, za + 1.0), true)
			_tri_quad("concrete", _P(ua, (hw - 0.4) * sg, za), _P(ub, (hw - 0.4) * sg, zb), _P(ub, (hw - 0.4) * sg, zb + 1.0), _P(ua, (hw - 0.4) * sg, za + 1.0), true)
			_tri_quad("concrete", _P(ua, (hw - 0.4) * sg, za + 1.0), _P(ub, (hw - 0.4) * sg, zb + 1.0), _P(ub, hw * sg, zb + 1.0), _P(ua, hw * sg, za + 1.0))
		_tri_quad("concrete", _P(ua, -hw, za - DECK_D), _P(ub, -hw, zb - DECK_D), _P(ub, hw, zb - DECK_D), _P(ua, hw, za - DECK_D))
		if not rail:
			# white edge lines, and the two-way road's double yellow down the middle, as on the road
			for lv_ in [hw - 1.2, -hw + 1.2]:
				_tri_quad("line", _P(ua, lv_ + 0.08, za + 0.02), _P(ub, lv_ + 0.08, zb + 0.02), _P(ub, lv_ - 0.08, zb + 0.02), _P(ua, lv_ - 0.08, za + 0.02))
			for lv_ in [0.12, -0.12]:
				_tri_quad("yellow", _P(ua, lv_ + 0.05, za + 0.02), _P(ub, lv_ + 0.05, zb + 0.02), _P(ub, lv_ - 0.05, zb + 0.02), _P(ua, lv_ - 0.05, za + 0.02))
		else:
			for tv in [-2.2, -0.7, 0.7, 2.2]:
				_tri_quad("rail", _P(ua, tv + 0.04, za + 0.35), _P(ub, tv + 0.04, zb + 0.35), _P(ub, tv - 0.04, zb + 0.35), _P(ua, tv - 0.04, za + 0.35))
	var zat := func(u: float) -> float:
		var f := clampf(u / L * n, 0.0, float(n) - 0.001)
		var i := int(f)
		return lerpf(zz[i], zz[i + 1], f - i)
	# ---- the main span: centred on the channel, as long as the record's (within the water span)
	var main: float = minf(float(tr.get("main_span_m", 150.0)) if tr.get("main_span_m") != null else 150.0, span * 0.92)
	var m0 := ext_a + span * 0.5 - main * 0.5
	var m1 := m0 + main
	var appr: Dictionary = tr.get("approaches", {}) if tr.get("approaches") is Dictionary else {}
	var pier_every: float = float(appr.get("span_m", 45.0))
	# ---- piers: every pier_every along the approaches and side spans (not in the main span)
	var u := pier_every
	while u < L - 5.0:
		if u < m0 - 3.0 or u > m1 + 3.0:
			var zd: float = zat.call(u) - DECK_D
			var gz := _ground(u)
			if zd - gz > 1.0:
				for pv in ([0.0] if hw < 7.0 else [-hw * 0.55, hw * 0.55]):
					_column("concrete", u, pv, gz - FOUND, zd, 0.9, 1.2)
				_column("concrete", u, 0.0, zd - 1.2, zd, 1.0, hw)
		u += pier_every
	# ---- the main span's structure
	var zm: float = zat.call((m0 + m1) * 0.5)
	var towers: Dictionary = tr.get("towers", {}) if tr.get("towers") is Dictionary else {}
	var th: float = float(towers.get("height_m", 80.0)) if not towers.is_empty() else 0.0
	if typ == "suspension":
		var ztop := zm + maxf(th * 0.6, main * 0.12)
		for tu in [m0, m1]:
			var gz := _ground(tu)
			for sg in [1.0, -1.0]:
				_column(steel if str(towers.get("material", "steel")) == "steel" else "concrete", tu, (hw + 1.2) * sg, gz - FOUND, ztop, 1.4, 1.4)
			for k in 3:
				var zc: float = zat.call(tu) + 4.0 + (ztop - zat.call(tu) - 6.0) * k / 2.0
				_column(steel, tu, 0.0, zc, zc + 2.0, 1.2, hw + 1.2)
		# main cables: anchorage at each end of the side spans, over the tower tops, sagging to the deck mid-span
		for sg in [1.0, -1.0]:
			var v: float = (hw + 1.2) * sg
			var pts := []
			var anc_a := maxf(0.0, m0 - main * 0.35)
			var anc_b := minf(L, m1 + main * 0.35)
			pts.append([anc_a, zat.call(anc_a) + 1.0])
			pts.append([m0, ztop])
			for k in range(1, 12):
				var t := k / 12.0
				var uu := lerpf(m0, m1, t)
				pts.append([uu, ztop - (ztop - zm - 3.0) * (1.0 - pow(2.0 * t - 1.0, 2.0))])
			pts.append([m1, ztop])
			pts.append([anc_b, zat.call(anc_b) + 1.0])
			for k in pts.size() - 1:
				_beam("cable", _P(pts[k][0], v, pts[k][1]), _P(pts[k + 1][0], v, pts[k + 1][1]), 0.35)
			var hu := m0 + 12.0
			while hu < m1 - 6.0:
				var t := (hu - m0) / main
				var zc := ztop - (ztop - zm - 3.0) * (1.0 - pow(2.0 * t - 1.0, 2.0))
				_beam("cable", _P(hu, v, zat.call(hu)), _P(hu, v, zc), 0.06)
				hu += 12.0
			for anc in [anc_a, anc_b]:
				_column("concrete", anc, v, _ground(anc) - FOUND, zat.call(anc) + 2.0, 4.0, 3.0)
	elif typ == "cable_stayed":
		var single: bool = str(towers.get("form", "")) == "single_pylon" and str(tr.get("stays", "")).contains("single")
		var pylons: Array = [(m0 + m1) * 0.5] if single else [m0 + main * 0.12, m1 - main * 0.12]
		var reach: float = main * (0.5 if single else 0.45)
		for pu in pylons:
			var ztop: float = zat.call(pu) + maxf(th * 0.7, main * 0.3)
			var gz := _ground(pu)
			var pv := [0.0] if single else [hw + 1.0, -hw - 1.0]
			for v in pv:
				_column("concrete", pu, v, gz - FOUND, ztop, 2.0, 1.6)
			if str(towers.get("top", "")) == "glass_lit":
				_column("glass", pu, 0.0, ztop, ztop + 12.0, 2.2, 1.8)
			if not single:
				_column("concrete", pu, 0.0, zat.call(pu) + 3.0, zat.call(pu) + 5.0, 1.2, hw + 1.0)
			for k in range(1, 11):
				for dirn in [-1.0, 1.0]:
					var du: float = pu + dirn * reach * k / 10.0
					if du < 0.0 or du > L:
						continue
					for v in ([0.0] if single else [hw + 0.6, -hw - 0.6]):
						var anchor_v: float = 0.0 if single else v
						_beam("cable", _P(pu, v, ztop - k * 1.2), _P(du, anchor_v, zat.call(du) + 0.5), 0.1)
	elif typ == "tied_arch":
		var arch: Dictionary = tr.get("arch", {}) if tr.get("arch") is Dictionary else {}
		var rise: float = float(arch.get("rise_m", main * 0.18))
		for sg in [1.0, -1.0]:
			var v: float = (hw + 0.8) * sg
			var prev := Vector3.ZERO
			for k in 25:
				var t := k / 24.0
				var uu := lerpf(m0, m1, t)
				var zc: float = zat.call(uu) + 1.0 + rise * 4.0 * t * (1.0 - t)
				var p := _P(uu, v, zc)
				if k > 0:
					_beam(arch_mat, prev, p, 1.0)
				if k % 2 == 0 and k > 0 and k < 24:
					_beam("cable", _P(uu, v, zat.call(uu)), p, 0.08)
				prev = p
			for k in range(3, 22, 3):
				var t := k / 24.0
				var uu := lerpf(m0, m1, t)
				var zc: float = zat.call(uu) + 1.0 + rise * 4.0 * t * (1.0 - t)
				_beam(arch_mat, _P(uu, hw + 0.8, zc), _P(uu, -hw - 0.8, zc), 0.4)
		for tu in [m0, m1]:
			_column("concrete", tu, 0.0, _ground(tu) - FOUND, zat.call(tu) - DECK_D, 3.0, hw + 1.0)
	elif typ == "deck_truss":
		var depth := 8.0
		var nb := int(main / 10.0)
		for sg in [1.0, -1.0]:
			var v: float = (hw - 0.5) * sg
			for k in nb:
				var ua := lerpf(m0, m1, k / float(nb))
				var ub := lerpf(m0, m1, (k + 1) / float(nb))
				var za: float = zat.call(ua) - DECK_D
				var zb: float = zat.call(ub) - DECK_D
				_beam(steel, _P(ua, v, za - depth), _P(ub, v, zb - depth), 0.35)
				_beam(steel, _P(ua, v, za), _P(ub, v, zb - depth) if k % 2 == 0 else _P(ub, v, zb), 0.25)
				_beam(steel, _P(ub, v, zb), _P(ub, v, zb - depth), 0.25)
		for tu in [m0, (m0 + m1) * 0.5, m1]:
			_column("concrete", tu, 0.0, _ground(tu) - FOUND, zat.call(tu) - DECK_D - depth, 2.5, hw)
	elif typ == "rail_viaduct_arch":
		var arch: Dictionary = tr.get("arch", {}) if tr.get("arch") is Dictionary else {}
		var rise: float = float(arch.get("rise_m", 20.0))
		for sg in [1.0, -1.0]:
			var v: float = (hw - 1.0) * sg
			var prev := Vector3.ZERO
			for k in 25:
				var t := k / 24.0
				var uu := lerpf(m0, m1, t)
				var zc: float = zat.call(uu) - DECK_D - rise * (1.0 - 4.0 * t * (1.0 - t))
				var p := _P(uu, v, zc)
				if k > 0:
					_beam("concrete", prev, p, 1.2)
				if k % 3 == 0:
					_beam("concrete", p, _P(uu, v, zat.call(uu) - DECK_D), 0.4)
				prev = p
		for tu in [m0, m1]:
			_column("concrete", tu, 0.0, _ground(tu) - FOUND, zat.call(tu) - DECK_D - rise, 3.0, hw)
	else:
		# segmental box / girder trestle: a haunched girder over the channel on two tall river piers
		for tu in [m0, m1]:
			_column("concrete", tu, 0.0, _ground(tu) - FOUND, zat.call(tu) - DECK_D, 2.0, hw * 0.7)
		var nb := 20
		for k in nb:
			var ua := lerpf(m0, m1, k / float(nb))
			var ub := lerpf(m0, m1, (k + 1) / float(nb))
			var ta := absf(k / float(nb) - 0.5) * 2.0
			var tb := absf((k + 1) / float(nb) - 0.5) * 2.0
			var ha := DECK_D + 5.0 * ta * ta
			var hb := DECK_D + 5.0 * tb * tb
			for sg in [1.0, -1.0]:
				_tri_quad("concrete", _P(ua, hw * 0.8 * sg, zat.call(ua) - ha), _P(ub, hw * 0.8 * sg, zat.call(ub) - hb),
					_P(ub, hw * 0.8 * sg, zat.call(ub) - DECK_D), _P(ua, hw * 0.8 * sg, zat.call(ua) - DECK_D))
			_tri_quad("concrete", _P(ua, -hw * 0.8, zat.call(ua) - ha), _P(ub, -hw * 0.8, zat.call(ub) - hb),
				_P(ub, hw * 0.8, zat.call(ub) - hb), _P(ua, hw * 0.8, zat.call(ua) - ha))
	# ---- commit the bridge
	var node := Node3D.new()
	node.name = str(br.id)
	add_child(node)
	for mat in _st:
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, (_st[mat] as SurfaceTool).commit_to_arrays())
		mesh.surface_set_material(0, _mats[mat])
		var mi := MeshInstance3D.new()
		mi.name = mat
		mi.mesh = mesh
		node.add_child(mi)
	var body := StaticBody3D.new()
	body.name = "deck_col"
	var shape := ConcavePolygonShape3D.new()
	shape.backface_collision = true
	shape.set_faces(_col)
	var cs := CollisionShape3D.new()
	cs.shape = shape
	body.add_child(cs)
	node.add_child(body)
