extends RefCounted
class_name PdaMapTiles

## The PDA's detailed map (tools/pda_detail_map.py): 4 m / px over the whole ring, in TILE px squares
## (ui/pda/detail/d_I_J.png -- the 20 km ring in one image would be 15,708 px wide, past what small GPUs take).
## draw() puts any part of it on a CanvasItem, across the tiles and across the ring's seam.

const M := 4.0
const TILE := 2048
const DIR := "res://ui/pda/detail"

static var _tex := {}                     # Vector2i -> Texture2D (or null: no such tile)


static func tile(i: int, j: int) -> Texture2D:
	var k := Vector2i(i, j)
	if not _tex.has(k):
		var path := DIR + "/d_%d_%d.png" % [i, j]
		_tex[k] = load(path) if ResourceLoader.exists(path) else null
	return _tex[k]


static func draw(ci: CanvasItem, dst: Rect2, s0: float, x0: float, mpp: float) -> void:
	## The map from (s0, x0) (its top-left corner) at mpp metres per destination pixel, into dst.
	var w_m := dst.size.x * mpp
	var s := fposmod(s0, StationGeo.CIRC)
	var done := 0.0
	while done < w_m - 0.01:
		var seg := minf(w_m - done, StationGeo.CIRC - s)
		_span(ci, Vector2(dst.position.x + done / mpp, dst.position.y), s, x0, seg, dst.size.y * mpp, mpp)
		done += seg
		s = 0.0


static func _span(ci: CanvasItem, at: Vector2, s0: float, x0: float, w_m: float, h_m: float, mpp: float) -> void:
	var tm := TILE * M
	var y0 := x0 + StationGeo.HALF_LEN                       # metres down from the north wall
	for i in range(floori(s0 / tm), floori((s0 + w_m - 0.01) / tm) + 1):
		for j in range(maxi(0, floori(y0 / tm)), floori(minf(y0 + h_m, StationGeo.LENGTH) / tm) + 1):
			var t := tile(i, j)
			if t == null:
				continue
			var a := Vector2(maxf(s0, i * tm), maxf(maxf(y0, 0.0), j * tm))
			var b := Vector2(minf(minf(s0 + w_m, (i + 1) * tm), i * tm + t.get_width() * M),
				minf(minf(y0 + h_m, (j + 1) * tm), j * tm + t.get_height() * M))
			if b.x <= a.x or b.y <= a.y:
				continue
			var src := Rect2((a - Vector2(i * tm, j * tm)) / M, (b - a) / M)
			ci.draw_texture_rect_region(t, Rect2(at + (a - Vector2(s0, y0)) / mpp, (b - a) / mpp), src)
