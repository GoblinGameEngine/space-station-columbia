extends RefCounted
class_name RoadSurface

## What a wheel is rolling on, and how rough it is (research/physics/vehicle_dynamics.md):
##   the road it's on (remake/terrain.json roads: class and width), else the map's land cover
##   (MapTerrain.landcover). Each surface has a peak tyre-road friction mu, a rolling-resistance
##   coefficient crr (Wong, Theory of Ground Vehicles; Gillespie) and an ISO 8608 roughness class.
## bump(): a profile height (m) with the class's spectrum, Gd(n) = Gd(n0) (n / n0)^-2, n0 = 0.1
## cycles/m, synthesised as plane waves over 1-25 m wavelengths -- the same at a place every time.

const N0 := 0.1
# ISO 8608 classes, Gd(n0) in m^3 (the class's geometric mean)
const ISO := {"A": 16e-6, "B": 64e-6, "C": 256e-6, "D": 1024e-6, "E": 4096e-6, "F": 16384e-6, "G": 65536e-6}
const SURF := {
	# name: [mu (peak, dry), crr, ISO class]
	"asphalt": [0.9, 0.013, "A"],
	"street": [0.88, 0.014, "B"],
	"gravel": [0.6, 0.025, "D"],
	"lawn": [0.45, 0.06, "D"],
	"meadow": [0.45, 0.08, "E"],
	"field": [0.5, 0.15, "E"],
	"woods": [0.45, 0.1, "F"],
	"dirt": [0.55, 0.05, "D"],
}
const ROAD_CLASS := {"hwy": "asphalt", "main": "asphalt", "county": "asphalt", "street": "street", "alley": "street", "gravel": "gravel"}
const CELL := 32.0

static var _grid := {}
static var _loaded := false
static var _waves: Array = []        # [n (cycles/m), direction (unit), phase, share of the band's amplitude]


static func _load() -> void:
	if _loaded:
		return
	_loaded = true
	MapTerrain._load()
	var roads: Array = MapTerrain._d.roads
	for ri in roads.size():
		var r: Dictionary = roads[ri]
		var pts: Array = r.pts
		var hw := float(r.get("w", 7.0)) * 0.5 + 0.4
		for k in pts.size() - 1:
			var a := Vector2(float(pts[k][0]), float(pts[k][1]))
			var b := Vector2(float(pts[k + 1][0]), float(pts[k + 1][1]))
			var seg := [a, b, hw, str(r.get("cls", "street"))]
			var d := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)
			var n := maxi(1, ceili(d.length() / CELL))
			var seen := {}
			for i in n + 1:
				var q := a + d * (float(i) / n)
				for dx in [-1, 0, 1]:
					for dy in [-1, 0, 1]:
						var c := Vector2i(posmod(floori(fposmod(q.x, StationGeo.CIRC) / CELL) + dx, ceili(StationGeo.CIRC / CELL)), floori(q.y / CELL) + dy)
						if not seen.has(c):
							seen[c] = true
							if not _grid.has(c):
								_grid[c] = []
							(_grid[c] as Array).append(seg)
	# the waves: 10 bands from 25 m to 1 m wavelength, 3 directions each
	var rng := RandomNumberGenerator.new()
	rng.seed = 8608
	var n_lo := 0.04
	var n_hi := 1.0
	var bands := 10
	for i in bands:
		var a0 := n_lo * pow(n_hi / n_lo, float(i) / bands)
		var a1 := n_lo * pow(n_hi / n_lo, float(i + 1) / bands)
		var nc := sqrt(a0 * a1)
		for j in 3:
			var ang := rng.randf() * TAU
			_waves.append([nc, Vector2(cos(ang), sin(ang)), rng.randf() * TAU, a1 - a0])


static func at(p: Vector2) -> String:
	## The surface at (s, x).
	_load()
	var c := Vector2i(floori(fposmod(p.x, StationGeo.CIRC) / CELL), floori(p.y / CELL))
	var best := ""
	var bd := INF
	for seg in _grid.get(c, []):
		var a: Vector2 = seg[0]
		var ab := Vector2(StationGeo.wrap_ds(seg[1].x - a.x), seg[1].y - a.y)
		var ap := Vector2(StationGeo.wrap_ds(p.x - a.x), p.y - a.y)
		var t := clampf(ap.dot(ab) / maxf(ab.length_squared(), 1e-6), 0.0, 1.0)
		var dd := (ap - ab * t).length()
		if dd < float(seg[2]) and dd < bd:
			bd = dd
			best = ROAD_CLASS.get(seg[3], "street")
	if best != "":
		return best
	match MapTerrain.landcover(p.x, p.y).x:
		1:
			return "lawn"
		2:
			return "meadow"
		3:
			return "woods"
		4:
			return "field"
		5:
			return "woods"
	return "dirt" if MapTerrain.area_kind(p.x, p.y) in ["parking", "schoolground"] else "lawn"


static func props(name: String) -> Array:
	return SURF.get(name, SURF.lawn)


static func bump(p: Vector2, name: String) -> float:
	## The profile height (m) at (s, x) for this surface's roughness class.
	_load()
	var gd: float = ISO.get(props(name)[2], ISO.B)
	var h := 0.0
	for w in _waves:
		var n: float = w[0]
		var amp := sqrt(2.0 * gd * pow(n / N0, -2.0) * float(w[3]) / 3.0)
		h += amp * cos(TAU * n * (w[1] as Vector2).dot(p) + float(w[2]))
	return h
