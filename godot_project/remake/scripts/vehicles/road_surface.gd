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

static var _loaded := false
static var _waves: Array = []        # [n (cycles/m), direction (unit), phase, share of the band's amplitude]


static func _load() -> void:
	if _loaded:
		return
	_loaded = true
	MapTerrain._load()
	# (the roads come from MapTerrain's own road cells: a grid of every segment here as well was ~700 MB on the 1:1 map)
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
	var seg := MapTerrain._road_cell(Vector2i(floori(fposmod(p.x, StationGeo.CIRC) / MapTerrain.RCELL), floori(p.y / MapTerrain.RCELL)))
	var roads: Array = MapTerrain._d.roads
	var best := ""
	var bd := INF
	for j in range(0, seg.size(), MapTerrain.RSTRIDE):
		var a := Vector2(seg[j], seg[j + 1])
		var ab := Vector2(StationGeo.wrap_ds(seg[j + 2] - a.x), seg[j + 3] - a.y)
		var ap := Vector2(StationGeo.wrap_ds(p.x - a.x), p.y - a.y)
		var t := clampf(ap.dot(ab) / maxf(ab.length_squared(), 1e-6), 0.0, 1.0)
		var dd := (ap - ab * t).length()
		var hw := maxf(seg[j + 4], seg[j + 5]) + 0.4
		if dd < hw and dd < bd:
			bd = dd
			best = ROAD_CLASS.get(str(roads[int(seg[j + 9])].get("cls", "street")), "street")
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


static func stand_h(space: PhysicsDirectSpaceState3D, p: Vector2, was := -INF, exclude: Array[RID] = []) -> float:
	## The height a vehicle stands at, at (s, x): a great bridge's deck (GreatBridges.deck_h, its
	## approaches too); else the ground -- or, where the ground is a river or lake bed, a smaller
	## bridge's deck over it: a ray down from just above where it was (was: its last
	## height, so the ray starts under any arch or truss overhead). With no deck there (not built
	## yet), the water's surface: never along the bottom.
	var known := was > -1000.0 and was < 1000.0          # (-INF, or a new body still at the origin: unknown)
	var deck := GreatBridges.deck_h(p.x, p.y)
	if deck > -INF and (not known or absf(deck - was) < 2.5):   # on it -- not on a road passing under it
		return deck
	var g := MapTerrain.elevation(p.x, p.y)
	var wa := MapTerrain.water_at(p.x, p.y)
	if wa.x < -9000.0 or wa.x <= g + 0.05:
		return g
	var from_h := was + 2.5 if known and was > g + 0.1 and was < wa.x + 20.0 else wa.x + 25.0
	var q := PhysicsRayQueryParameters3D.create(StationGeo.point(p.x, p.y, from_h), StationGeo.point(p.x, p.y, g - 0.5), 1)
	q.exclude = exclude
	var hit := space.intersect_ray(q)
	if hit.is_empty() or StationGeo.h_of(hit.position) < wa.x:
		return wa.x
	return StationGeo.h_of(hit.position)
