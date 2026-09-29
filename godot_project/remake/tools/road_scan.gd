extends RefCounted
class_name RoadScan

## A quick check of every road's driving surface (MapTerrain.elevation, which the ribbons and the
## ground are built from): each lane sampled every STEP m, flagging any rise or drop steeper than
## MAX_LOCAL over a metre -- a step or small cliff no car could take -- and grades past the class
## limit over a car's length.  Run from DevBridge: return RoadScan.scan()

const STEP := 1.0
const MAX_LOCAL := 0.25              # m per m: a kerb-sized step within a metre
const LIMIT := {"hwy": 0.05, "county": 0.07, "gravel": 0.10, "main": 0.07, "street": 0.08, "alley": 0.08, "rail": 0.015}


static func scan(max_report := 60, spans: Array = []) -> Dictionary:
	## spans: GreatBridges.spans -- the roads' surface there is the bridge deck, not the ground
	MapTerrain.elevation(0.0, 0.0)
	var roads: Array = MapTerrain._d.roads
	var bad := []
	var steep := 0
	var steep_at := []
	var samples := 0
	for ri in roads.size():
		var rd: Dictionary = roads[ri]
		if rd.cls == "rail":
			continue
		var pts: Array = rd.pts
		var lane: float = float(rd.w) * 0.25
		var prev_h := NAN
		var hist := []                           # the last few heights, for the grade over a car's length
		for k in pts.size() - 1:
			var a := Vector2(pts[k][0], pts[k][1])
			var b := Vector2(pts[k + 1][0], pts[k + 1][1])
			var d := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)
			var L := d.length()
			if L < 0.01:
				continue
			var dir := d / L
			var right := Vector2(-dir.y, dir.x)                # the driver's right (facing +s it is +x): we drive on the right
			var n := ceili(L / STEP)
			for i in n:
				var p := a + dir * (L * i / n) + right * lane
				if _on_bridge(p, spans):
					prev_h = NAN
					hist.clear()
					continue
				var h := MapTerrain.elevation(fposmod(p.x, StationGeo.CIRC), p.y)
				samples += 1
				if not is_nan(prev_h):
					var dh := absf(h - prev_h) / (L / n)
					if dh > MAX_LOCAL and bad.size() < max_report:
						bad.append({"road": ri, "cls": rd.cls, "name": str(rd.get("name", rd.get("town", ""))),
							"s": snappedf(fposmod(p.x, StationGeo.CIRC), 0.1), "x": snappedf(p.y, 0.1), "dh": snappedf(h - prev_h, 0.01)})
				hist.append(h)
				if hist.size() > 5:
					hist.pop_front()
					if absf(hist[4] - hist[0]) / (4.0 * L / n) > float(LIMIT.get(rd.cls, 0.1)) * 1.5:
						steep += 1
						if steep_at.size() < 20:
							steep_at.append([ri, rd.cls, snappedf(fposmod(p.x, StationGeo.CIRC), 0.1), snappedf(p.y, 0.1),
								snappedf((hist[4] - hist[0]) / (4.0 * L / n), 0.001)])
				prev_h = h
	return {"samples": samples, "steps": bad.size(), "steep_4m_over_1.5x_limit": steep, "steep_at": steep_at, "first": bad}


static func _on_bridge(p: Vector2, spans: Array) -> bool:
	## Over a great bridge (its deck from end to end) or a small crossing's deck.
	for sp in spans:
		var o: Vector2 = sp.o
		var d: Vector2 = sp.dir
		var v := Vector2(StationGeo.wrap_ds(p.x - o.x), p.y - o.y)
		var u := v.dot(d)
		if u > -1.0 and u < float(sp.len) + 1.0 and absf(v.x * d.y - v.y * d.x) < 100.0:
			return true
	for bd in MapTerrain._grid.get(Vector2i(floori(fposmod(p.x, StationGeo.CIRC) / MapTerrain.CELL), floori(p.y / MapTerrain.CELL)), []):
		if bd[0] != "bridge":
			continue
		var b: Array = MapTerrain._bridges[bd[1]]
		var ds := StationGeo.wrap_ds(p.x - b[0])
		var dx: float = p.y - b[1]
		var lx: float = dx * b[2] + ds * b[3]
		var lz: float = dx * b[3] - ds * b[2]
		if lx > b[4] - 1.0 and lx < b[6] + 1.0 and lz > b[5] - 1.0 and lz < b[7] + 1.0:
			return true
	return false



static func explain(s: float, x: float) -> Dictionary:
	## What makes the ground at (s, x): the roads near it (and their graded heights), the pads, the
	## crossings, the water.
	s = fposmod(s, StationGeo.CIRC)
	var base := MapTerrain.base_elev(s, x)
	var pg := MapTerrain._pad_grade(s, x, base)
	var rg := MapTerrain._road_grade(s, x, pg)
	var roads := []
	for it in MapTerrain._grid.get(Vector2i(floori(s / MapTerrain.CELL), floori(x / MapTerrain.CELL)), []):
		if it[0] == "road":
			var rd: Dictionary = MapTerrain._d.roads[it[1]]
			var q: Array = rd.pts[it[2]]
			var r: Array = rd.pts[it[2] + 1]
			var pr := MapTerrain._seg_proj(s, x, q[0], q[1], r[0], r[1])
			if pr.x < float(rd.w) * 0.5 + 3.0:
				var zp: PackedFloat32Array = rd.zp
				var cum: PackedFloat32Array = rd.cum
				var u: float = lerpf(cum[it[2]], cum[it[2] + 1], pr.y) / 4.0
				var k := clampi(floori(u), 0, zp.size() - 1)
				roads.append([it[1], rd.cls, str(rd.get("name", rd.get("town", ""))), snappedf(pr.x, 0.1), snappedf(zp[k] if zp.size() else NAN, 0.01)])
		elif it[0] == "bridge":
			roads.append(["crossing", it[1], MapTerrain._bridges[it[1]][8]])
		elif it[0] == "pad":
			roads.append(["pad", snappedf(MapTerrain._pads[it[1]][8], 0.01)])
	return {"elev": snappedf(MapTerrain.elevation(s, x), 0.01), "base": snappedf(base, 0.01), "pad": snappedf(pg, 0.01),
		"road": [snappedf(rg.x, 0.01), snappedf(rg.y, 0.01)], "water": MapTerrain.water_at(s, x),
		"small": snappedf(MapTerrain._small_depth(s, x), 0.01), "near": roads}
