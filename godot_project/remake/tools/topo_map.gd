extends Node
class_name TopoMap

## Topographic maps of the ground as the game builds it (MapTerrain.elevation: the town grading, the
## roads' cut and fill, the building pads), for finding trenches, embankments and steps (the user,
## 2026-10-01). Run from DevBridge, e.g.:
##   var t = TopoMap.new(); root.add_child(t); t.render(2380, 902, 600, 400, 2.0, "/home/deck/.../hf.png")
## A map is drawn in strips over several frames (the game keeps running); t.done turns true.
## The picture: hillshade (light from the north-west); contours every 1 m, every 5 m bolder; red where
## the grading cuts below the town-graded ground by more than 0.5 m (a trench), blue where it fills
## above it (an embankment); water in slate blue; magenta where the ground is steeper than 30 % (a step or a cliff); roads
## in grey. North (s increasing) is up; x runs left (-) to right (+).

var done := true
var _img: Image
var _h: PackedFloat32Array
var _dev: PackedFloat32Array
var _job := {}


func render(s0: float, x0: float, size_s: float, size_x: float, cell: float, path: String) -> void:
	var w := int(size_x / cell)
	var h := int(size_s / cell)
	_h = PackedFloat32Array()
	_h.resize(w * h)
	_dev = PackedFloat32Array()
	_dev.resize(w * h)
	_job = {"s0": s0, "x0": x0, "cell": cell, "w": w, "h": h, "row": 0, "path": path}
	done = false


func _process(_delta: float) -> void:
	if done or _job.is_empty():
		return
	var w: int = _job.w
	var h: int = _job.h
	var t0 := Time.get_ticks_msec()
	while int(_job.row) < h and Time.get_ticks_msec() - t0 < 40:
		var r: int = _job.row
		var s: float = float(_job.s0) + (float(h) / 2.0 - r) * float(_job.cell)        # north up
		for c in w:
			var x: float = float(_job.x0) + (c - float(w) / 2.0) * float(_job.cell)
			var e := MapTerrain.elevation(s, x)
			_h[r * w + c] = e
			var wl := MapTerrain.water_at(fposmod(s, StationGeo.CIRC), x).x
			_dev[r * w + c] = INF if wl > e + 0.05 else e - MapTerrain.base_elev(s, x)        # INF: under water
		_job.row = r + 1
	if int(_job.row) >= h:
		_finish()


func _finish() -> void:
	var w: int = _job.w
	var h: int = _job.h
	var cell: float = _job.cell
	_img = Image.create(w, h, false, Image.FORMAT_RGB8)
	var light := Vector3(-0.6, 0.7, 0.6).normalized()
	var road := {}
	for y in h:
		for x in w:
			var i := y * w + x
			var e := _h[i]
			var ex := _h[y * w + mini(x + 1, w - 1)] - _h[y * w + maxi(x - 1, 0)]
			var ey := _h[mini(y + 1, h - 1) * w + x] - _h[maxi(y - 1, 0) * w + x]
			var n := Vector3(-ex / (2.0 * cell), 1.0, ey / (2.0 * cell)).normalized()
			var shade := clampf(n.dot(light), 0.0, 1.0)
			var slope := Vector2(ex, ey).length() / (2.0 * cell)
			var base := Color(0.62, 0.70, 0.52).lerp(Color(0.85, 0.80, 0.62), clampf((e + 5.0) / 40.0, 0.0, 1.0))
			var col := base * (0.45 + 0.65 * shade)
			var d := _dev[i]
			if d == INF:
				_img.set_pixel(x, y, Color(0.35, 0.55, 0.75) * (0.8 + 0.2 * shade))
				continue
			if d < -0.5:
				col = col.lerp(Color(0.9, 0.1, 0.1), clampf(-d / 4.0, 0.25, 0.9))
			elif d > 0.5:
				col = col.lerp(Color(0.1, 0.3, 0.95), clampf(d / 4.0, 0.25, 0.9))
			if slope > 0.3:
				col = Color(0.95, 0.1, 0.9)
			# contours
			var e_r := _h[y * w + mini(x + 1, w - 1)]
			var e_d := _h[mini(y + 1, h - 1) * w + x]
			for k in [5.0, 1.0]:
				if floorf(e / k) != floorf(e_r / k) or floorf(e / k) != floorf(e_d / k):
					col = col.darkened(0.55 if k == 5.0 else 0.25)
					break
			_img.set_pixel(x, y, col)
	# the roads, in grey over it
	for rd in MapTerrain._d.roads:
		var pts: Array = rd.pts
		for k in pts.size() - 1:
			var a := Vector2(pts[k][0], pts[k][1])
			var b := Vector2(pts[k + 1][0], pts[k + 1][1])
			var steps := int(Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y).length() / (cell * 0.5)) + 1
			for t in steps + 1:
				var p := a + Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y) * (float(t) / steps)
				var py := int(float(h) / 2.0 - StationGeo.wrap_ds(p.x - float(_job.s0)) / cell)
				var px := int((p.y - float(_job.x0)) / cell + float(w) / 2.0)
				if px >= 0 and px < w and py >= 0 and py < h:
					_img.set_pixel(px, py, _img.get_pixel(px, py).lerp(Color(0.25, 0.25, 0.25), 0.55))
	_img.save_png(str(_job.path))
	done = true
	print("TOPO written %s (%dx%d)" % [_job.path, w, h])
