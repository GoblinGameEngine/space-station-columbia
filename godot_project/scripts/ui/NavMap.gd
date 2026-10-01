extends Control
class_name NavMap

## The Navigation app's map (GameMenu "nav"): the station's political map in the Communicator's four
## greys, panned by dragging and zoomed with + / - or the wheel, labelled more finely the closer you
## zoom (the user, 2026-10-01: "Cities will need to be labelled with roads and finer features
## labelled as you zoom in"):
##   64 / 32 m a pixel   the regions, the seas, the cities and towns
##   16 m                every settlement, the highways, the river and the lake
##   8 m                 the main streets, the tram lines, their stops
##   4 / 2 m             every street, parks, schools, beaches, plazas (over the detailed map)
## Fast-travel stops (the two largest tiers, at their tram stops) are boxed "T": tap one to travel.
## North (the bow) is up, as on every station map.

signal travel_requested(dest: Dictionary)

const ZOOMS := [2.0, 4.0, 8.0, 16.0, 32.0, 64.0]        # metres per LCD pixel
const K := Color(0, 0, 0)
const D := Color(0.333, 0.333, 0.333)
const L := Color(0.667, 0.667, 0.667)
const W := Color(1, 1, 1)
const REGIONS := [["NORTH SEA", -3820.0], ["THE NORTH SHORE", -3000.0], ["THE NORTHLAND", -1500.0], ["THE KETTLE VALLEY", 150.0],
	["THE SOUTHLAND", 1500.0], ["THE SOUTH SHORE", 3000.0], ["SOUTH SEA", 3820.0]]
const AREA_NAMES := {"park": "Park", "schoolground": "School", "beach": "Beach", "plaza": "Plaza", "square": "Square",
	"cemetery": "Cemetery", "campus": "College", "promenade": "Promenade", "sportsfield": "Ballfield", "parking": "P", "lot": "P"}

var font: Font
var bold: Font
var view := Vector2.ZERO                  # (s, x) at the centre
var follow := true
var zoom_i := 3
var dests: Array = []                     # {name, tier, s, x, stop, line} (GameMenu fills it)
var _pol: Texture2D
var _det: Texture2D
var _sets: Array = []
var _trams: Array = []                    # [PackedVector2Array of (s, x)]
var _stops: Array = []                    # [(s, x), name]
var _drag := 0.0
var _rects: Array = []
var _set_names := {}                       # settlement names (stops named for their town)


func _ready() -> void:
	clip_contents = true
	mouse_filter = Control.MOUSE_FILTER_STOP
	_pol = load("res://ui/pda/map_political.png")
	_det = load("res://ui/pda/map_detail.png")
	if FileAccess.file_exists("res://remake/law/settlements.json"):
		_sets = JSON.parse_string(FileAccess.get_file_as_string("res://remake/law/settlements.json")).settlements
		for st in _sets:
			_set_names[str(st.name)] = true
	for l in TransitNet.lines():
		var pts := PackedVector2Array()
		var d := 0.0
		while d < float(l.length):
			pts.append(TransitNet.point_at(l, d))
			d += 30.0
		_trams.append([pts, str(l.kind)])
		for st in l.stops:
			var p := TransitNet.point_at(l, float(st.d))
			_stops.append([p, str(st.name), str(l.kind)])


func zoom(step: int) -> void:
	zoom_i = clampi(zoom_i + step, 0, ZOOMS.size() - 1)
	queue_redraw()


func m() -> float:
	return ZOOMS[zoom_i]


func to_px(p: Vector2) -> Vector2:
	return (size * 0.5 + Vector2(StationGeo.wrap_ds(p.x - view.x), p.y - view.y) / m()).floor()


func _gui_input(e: InputEvent) -> void:
	if e is InputEventMouseMotion and (e.button_mask & MOUSE_BUTTON_MASK_LEFT):
		_drag += e.relative.length()
		follow = false
		view -= e.relative * m()
		view.x = fposmod(view.x, StationGeo.CIRC)
		view.y = clampf(view.y, -StationGeo.HALF_LEN, StationGeo.HALF_LEN)
		queue_redraw()
	elif e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT:
		if e.pressed:
			_drag = 0.0
		elif _drag < 4.0:
			for dd in dests:
				if to_px(Vector2(dd.s, dd.x)).distance_to(e.position) < 9.0:
					travel_requested.emit(dd)
					break
	elif e is InputEventMouseButton and e.pressed and e.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
		zoom(-1 if e.button_index == MOUSE_BUTTON_WHEEL_UP else 1)
		accept_event()


func _draw() -> void:
	_rects.clear()
	var sz := size
	draw_rect(Rect2(Vector2.ZERO, sz), W)
	var mm := m()
	# the base map: the political map, or the detailed one when close
	var tex: Texture2D = _det if mm <= 4.0 and _det else _pol
	if tex:
		# (the detailed map is in the far-side bake's padded frame; the political map in the ring's own)
		var det := tex == _det
		var ppm: float = tex.get_width() / (StationGeo.FARSIDE_W if det else StationGeo.CIRC)
		var y_off: float = StationGeo.FARSIDE_H * 0.5 if det else 4000.0
		var tw := StationGeo.CIRC * ppm
		var src := Rect2(fposmod(view.x - sz.x * 0.5 * mm, StationGeo.CIRC) * ppm, (view.y - sz.y * 0.5 * mm + y_off) * ppm, sz.x * mm * ppm, sz.y * mm * ppm)
		var first := minf(src.size.x, tw - src.position.x)
		draw_texture_rect_region(tex, Rect2(0, 0, sz.x * first / src.size.x, sz.y), Rect2(src.position, Vector2(first, src.size.y)))
		if first < src.size.x:
			var dx := sz.x * first / src.size.x
			draw_texture_rect_region(tex, Rect2(dx, 0, sz.x - dx, sz.y), Rect2(0, src.position.y, src.size.x - first, src.size.y))
	# the tram lines (dotted) and stops, from 16 m in
	if mm <= 16.0:
		for tl in _trams:
			var pts: PackedVector2Array = tl[0]
			var stepk := maxi(1, int(mm / 4.0))
			for i in range(0, pts.size(), stepk):
				var q := to_px(pts[i])
				if Rect2(Vector2(-2, -2), sz + Vector2(4, 4)).has_point(q):
					draw_rect(Rect2(q, Vector2(2, 2)), K if tl[1] == "tram" else D)
		for st in _stops:
			var q := to_px(st[0])
			if Rect2(Vector2.ZERO, sz).has_point(q):
				draw_rect(Rect2(q - Vector2(2, 2), Vector2(5, 5)), K)
				draw_rect(Rect2(q - Vector2(1, 1), Vector2(3, 3)), W)
	# labels, finest last (the coarse ones claim their space first); the fast-travel boxes and you
	# claim theirs before any
	for dd in dests:
		_rects.append(Rect2(to_px(Vector2(dd.s, dd.x)) - Vector2(7, 7), Vector2(15, 15)))
	_rects.append(Rect2(sz.x - 52, sz.y - 22, 52, 22))           # the scale
	_rects.append(Rect2(0, 0, 16, 19))                           # the north mark
	var me := _player()
	_rects.append(Rect2(to_px(Vector2(me.x, me.y)) - Vector2(9, 9), Vector2(19, 19)))
	_label_regions(mm)
	_label_settlements(mm)
	_label_water(mm)
	_label_roads(mm)
	if mm <= 4.0:
		_label_areas()
	if mm <= 8.0:
		for st in _stops:
			var sn := str(st[1]).replace(" stop", "")
			if mm > 4.0 and _set_names.has(sn):
				continue                                # (the town's own name is already on it)
			_text(sn, to_px(st[0]) + Vector2(5, -4), font, 16, false, 0.0)
	# fast-travel stops, boxed T
	for dd in dests:
		var q := to_px(Vector2(dd.s, dd.x))
		if Rect2(Vector2(-8, -8), sz + Vector2(16, 16)).has_point(q):
			draw_rect(Rect2(q - Vector2(6, 6), Vector2(13, 13)), K)
			draw_rect(Rect2(q - Vector2(5, 5), Vector2(11, 11)), W)
			draw_string(bold, q + Vector2(-3, 4), "T", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, K)
	# you
	var p := _player()
	var u := to_px(Vector2(p.x, p.y))
	var d := Vector2(cos(p.z), sin(p.z))
	var side := Vector2(-d.y, d.x)
	if Rect2(Vector2.ZERO, sz).has_point(u):
		var blink := int(Time.get_ticks_msec() / 400) % 2 == 0
		draw_colored_polygon(PackedVector2Array([u + d * 9, u - d * 5 + side * 6, u - d * 2, u - d * 5 - side * 6]), K if blink else D)
	# the frame, the north mark and the scale
	draw_rect(Rect2(Vector2.ZERO, sz), K, false)
	draw_rect(Rect2(2, 2, 12, 15), W)
	draw_string(bold, Vector2(4, 14), "N", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, K)
	var bar := 40.0
	var metres := bar * mm
	var txt := ("%d m" % int(metres)) if metres < 1000.0 else ("%.1f km" % (metres / 1000.0))
	draw_rect(Rect2(sz.x - bar - 6, sz.y - 8, bar, 3), K)
	draw_string_outline(font, Vector2(sz.x - bar - 6, sz.y - 11), txt, HORIZONTAL_ALIGNMENT_LEFT, -1, 16, 3, W)
	draw_string(font, Vector2(sz.x - bar - 6, sz.y - 11), txt, HORIZONTAL_ALIGNMENT_LEFT, -1, 16, K)


func _player() -> Vector3:
	var pl := get_tree().get_first_node_in_group("player") as Node3D
	if pl == null:
		return Vector3.ZERO
	var s := StationGeo.s_of(pl.global_position)
	var cam := pl.get_viewport().get_camera_3d()
	var f := -(cam.global_transform.basis.z if cam else pl.global_transform.basis.z)
	return Vector3(s, pl.global_position.x, atan2(f.x, f.dot(StationGeo.forward(s))))


func _text(t: String, at: Vector2, f: Font, fs: int, centre: bool, ang: float) -> bool:
	## A label with a white halo, unless it would land on one already drawn. at: baseline left (or
	## centre when centre). Returns whether it was drawn.
	var w := f.get_string_size(t, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
	var h := float(fs) * 0.7
	var off := Vector2(-w * 0.5, 0.0) if centre else Vector2.ZERO
	var r: Rect2
	if absf(ang) < 0.01:
		r = Rect2(at + off + Vector2(-2, -h - 1), Vector2(w + 4, h + 4))
	else:
		var c := at
		var ext := Vector2(absf(cos(ang)) * w + absf(sin(ang)) * h, absf(sin(ang)) * w + absf(cos(ang)) * h)
		r = Rect2(c - ext * 0.5, ext)
	if not Rect2(Vector2.ZERO, size).encloses(r.grow(-1)):
		return false
	for q in _rects:
		if (q as Rect2).intersects(r):
			return false
	_rects.append(r)
	if absf(ang) < 0.01:
		draw_string_outline(f, (at + off).floor(), t, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, 3, W)
		draw_string(f, (at + off).floor(), t, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, K)
	else:
		draw_set_transform(at.floor(), ang, Vector2.ONE)
		draw_string_outline(f, Vector2(-w * 0.5, h * 0.5), t, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, 3, W)
		draw_string(f, Vector2(-w * 0.5, h * 0.5), t, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, K)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	return true


func _label_regions(mm: float) -> void:
	if mm < 32.0:
		return
	for rg in REGIONS:
		var q := to_px(Vector2(view.x, rg[1]))
		for dx in [0.0, -70.0, 70.0, -130.0, 130.0, -190.0, 190.0]:
			if _text(rg[0], Vector2(size.x * 0.5 + dx, q.y + 4), font, 16, true, 0.0):
				break


func _label_settlements(mm: float) -> void:
	for st in _sets:
		var t := str(st.tier)
		if mm > 16.0 and not t in ["city", "town"]:
			continue
		if not st.get("centre"):
			continue
		var c: Array = st.centre
		var q := to_px(Vector2(float(c[0]), float(c[1])))
		var big := t in ["city", "town"]
		var nm := str(st.name).to_upper() if t == "city" else str(st.name)
		for o in [Vector2(0, -8), Vector2(0, 18), Vector2(0, -20), Vector2(0, 30)]:
			if _text(nm, q + o, bold if big else font, 12 if big else 16, true, 0.0):
				break


func _label_water(mm: float) -> void:
	if mm > 16.0 or mm < 4.0:
		return
	# the Kettle River down the middle of the world, named every few hundred pixels' worth
	var span := 260.0 * mm
	var s0 := view.x - size.x * 0.5 * mm
	var s := ceilf(s0 / span) * span
	while s < view.x + size.x * 0.5 * mm:
		var e := _river_across(fposmod(s, StationGeo.CIRC))
		if e.y - e.x > 30.0:
			_text("Kettle River", to_px(Vector2(s, (e.x + e.y) * 0.5)) + Vector2(0, 4), font, 16, true, 0.0)
		s += span


func _river_across(s: float) -> Vector2:
	## (-x edge, +x edge) of the widest stretch of water within 1.5 km of the middle at s (the Kettle)
	var best := Vector2.ZERO
	var start := INF
	var x := -1500.0
	while x <= 1500.0:
		var wet := MapTerrain.water_at(s, x).x > -9000.0
		if wet and start == INF:
			start = x
		if (not wet or x >= 1500.0) and start != INF:
			if x - start > best.y - best.x:
				best = Vector2(start, x)
			start = INF
		x += 20.0
	return best


func _label_roads(mm: float) -> void:
	if mm > 16.0:
		return
	for rd in MapTerrain._d.roads:
		var nm := str(rd.get("name", ""))
		if nm == "":
			continue
		var cls := str(rd.cls)
		if mm > 8.0 and not cls in ["hwy"]:
			continue
		if mm > 4.0 and not cls in ["hwy", "main", "county"]:
			continue
		var pts: Array = rd.pts
		# the longest on-screen run of the road; the name at its middle, along the chord the name spans
		var run := PackedVector2Array()
		var best := PackedVector2Array()
		var best_len := 0.0
		var run_len := 0.0
		var box := Rect2(Vector2.ZERO, size).grow(-4)
		for k in pts.size() + 1:
			var q := to_px(Vector2(pts[k][0], pts[k][1])) if k < pts.size() else Vector2(-1e6, -1e6)
			if k < pts.size() and box.has_point(q) and (run.is_empty() or run[-1].distance_to(q) < 200.0):
				if not run.is_empty():
					run_len += run[-1].distance_to(q)
				run.append(q)
				continue
			if run_len > best_len:
				best_len = run_len
				best = run
			run = PackedVector2Array()
			run_len = 0.0
			if k < pts.size() and box.has_point(q):
				run.append(q)
		var w := font.get_string_size(nm, HORIZONTAL_ALIGNMENT_LEFT, -1, 16).x
		if best.size() < 2 or best_len < w + 12.0:
			continue                                    # (too little of it on screen for its name)
		# the point half way along, and the chord w/2 either side of it
		var half := best_len * 0.5
		var acc := 0.0
		var mid := best[0]
		var mk := 0
		for k in best.size() - 1:
			var sl := best[k].distance_to(best[k + 1])
			if acc + sl >= half:
				mid = best[k].lerp(best[k + 1], (half - acc) / maxf(sl, 0.001))
				mk = k
				break
			acc += sl
		var a0 := best[0]
		var a1 := best[best.size() - 1]
		for k in range(mk, -1, -1):
			if best[k].distance_to(mid) >= w * 0.5:
				a0 = best[k]
				break
		for k in range(mk + 1, best.size()):
			if best[k].distance_to(mid) >= w * 0.5:
				a1 = best[k]
				break
		var ba := atan2(a1.y - a0.y, a1.x - a0.x)
		var bp := mid
		if ba > PI * 0.5:
			ba -= PI
		elif ba < -PI * 0.5:
			ba += PI
		_text(nm, bp, font, 16, true, ba)


func _label_areas() -> void:
	for a in MapTerrain._d.areas:
		var nm: String = AREA_NAMES.get(str(a.kind), "")
		if nm == "":
			continue
		var poly: Array = a.poly
		var c := Vector2.ZERO
		for p in poly:
			c += Vector2(float(p[0]), float(p[1]))
		c /= float(poly.size())
		_text(nm, to_px(c) + Vector2(0, 4), font, 16, true, 0.0)
