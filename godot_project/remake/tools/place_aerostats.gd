extends SceneTree

## Chooses where the aerostats park and writes res://remake/aerostats.json (RemakeStation reads it).
## Run once after the map or the placement changes:
##   godot4 --headless --path . --script res://remake/tools/place_aerostats.gd
##
##   towns     by size (buildings on the map): 120+ -> 4, 80+ -> 3, 30+ -> 2, a village -> 1; on
##             open, level ground as near the town's middle as it can -- a park, lawn, square or
##             school ground first, anywhere clear after that
##   farms     every other farmstead (by id), in its yard or an adjoining field
## A spot is clear when the aerostat's footprint (fans and step included) keeps SPOT_CLEAR m from
## every structure, off roads, water and woods, and the ground under it is level to LEVEL m.
## Aerostats keep APART m from each other.

const OUT := "res://remake/aerostats.json"
const FOOT_R := 3.6                  # the aerostat's plan radius, fans and steps included
const SPOT_CLEAR := 3.0
const LEVEL := 0.6
const APART := 45.0
const OPEN_AREAS := ["park", "lawn", "square", "schoolground", "campus"]

var _foot: Array = []                # [s, x, r] of every structure
var _foot_grid := {}                 # 50 m cell -> [s, x, r] (every spot against all ~64,000 footprints was ~10^9 tests)
var _foot_rmax := 0.0
const FG := 50.0
var _chosen: Array = []              # [s, x]


func _init() -> void:
	var entries: Array = (JSON.parse_string(FileAccess.get_file_as_string("res://remake/placement.json")) as Dictionary).values()[0]
	MapTerrain.elevation(0.0, 0.0)
	for e in entries:
		var fmin: Array = e.get("fmin", e.min)
		var fmax: Array = e.get("fmax", e.max)
		var r := maxf(Vector2(fmin[0], fmin[1]).length(), Vector2(fmax[0], fmax[1]).length())
		_foot.append([float(e.s), float(e.x), r])
		var cell := Vector2i(int(floor(fposmod(float(e.s), StationGeo.CIRC) / FG)), int(floor(float(e.x) / FG)))
		if not _foot_grid.has(cell):
			_foot_grid[cell] = []
		_foot_grid[cell].append([float(e.s), float(e.x), r])
		_foot_rmax = maxf(_foot_rmax, r)
	var out := []
	# towns
	var towns := {}
	for e in entries:
		var t = e.get("settlement")
		if t == null or t == "None":
			continue
		if not towns.has(t):
			towns[t] = []
		towns[t].append(e)
	var names := towns.keys()
	names.sort()
	for t in names:
		var bs: Array = towns[t]
		var n := bs.size()
		var want := 4 if n >= 120 else (3 if n >= 80 else (2 if n >= 30 else 1))
		var c := _middle(bs)
		var got := 0
		for pass_ in 2:
			for spot in _rings(c, 8.0, 420.0, 6.0):
				if got >= want:
					break
				var area := MapTerrain.area_kind(spot.x, spot.y)
				if pass_ == 0 and not OPEN_AREAS.has(area):
					continue
				if _clear(spot):
					_take(spot)
					got += 1
					out.append({"id": "AERO-%s-%d" % [str(t).replace(" ", ""), got], "s": snappedf(fposmod(spot.x, StationGeo.CIRC), 0.01),
						"x": snappedf(spot.y, 0.01), "yaw": 0.0, "where": t})
		print("%s (%d buildings): %d of %d" % [t, n, got, want])
	# farms: every other farmstead
	var houses := []
	for e in entries:
		if str(e.id).begins_with("FARM-") and str(e.id).ends_with("-house"):
			houses.append(e)
	houses.sort_custom(func(a, b): return str(a.id) < str(b.id))
	var farm_n := 0
	for i in range(0, houses.size(), 2):
		var h: Dictionary = houses[i]
		var c := Vector2(float(h.s), float(h.x))
		var found := false
		for spot in _rings(c, 16.0, 150.0, 4.0):
			if _clear(spot):
				_take(spot)
				out.append({"id": "AERO-%s" % str(h.id).trim_suffix("-house"), "s": snappedf(fposmod(spot.x, StationGeo.CIRC), 0.01),
					"x": snappedf(spot.y, 0.01), "yaw": 0.0, "where": str(h.id).trim_suffix("-house")})
				farm_n += 1
				found = true
				break
		if not found:
			print("no spot at ", h.id)
	print("farms: %d of %d" % [farm_n, (houses.size() + 1) / 2])
	var f := FileAccess.open(OUT, FileAccess.WRITE)
	f.store_string(JSON.stringify({"aerostats": out}, "\t"))
	f.close()
	print("AEROSTATS_PLACED %d -> %s" % [out.size(), OUT])
	quit()


func _middle(bs: Array) -> Vector2:
	## The buildings' centroid (the mean of s taken round the ring).
	var cs := 0.0
	var sn := 0.0
	var x := 0.0
	for e in bs:
		var th: float = float(e.s) / StationGeo.R
		cs += cos(th)
		sn += sin(th)
		x += float(e.x)
	return Vector2(fposmod(atan2(sn, cs), TAU) * StationGeo.R, x / bs.size())


func _rings(c: Vector2, r0: float, r1: float, step: float) -> Array:
	var out := []
	var r := r0
	while r <= r1:
		var n := maxi(8, int(TAU * r / step))
		for k in n:
			var a := TAU * (k + 0.5 * (int(r / step) % 2)) / n
			out.append(c + Vector2(cos(a), sin(a)) * r)
		r += step
	return out


func _clear(p: Vector2) -> bool:
	if absf(p.y) > StationGeo.HALF_LEN - 60.0:
		return false
	for q in _chosen:
		if absf(StationGeo.wrap_ds(p.x - q.x)) < APART and absf(p.y - q.y) < APART:
			return false
	var reach := int(ceil((_foot_rmax + FOOT_R + SPOT_CLEAR) / FG))
	var ncol := int(ceil(StationGeo.CIRC / FG))
	var ci := int(floor(fposmod(p.x, StationGeo.CIRC) / FG))
	var cj := int(floor(p.y / FG))
	for i in range(-reach, reach + 1):
		for j in range(-reach, reach + 1):
			for f in _foot_grid.get(Vector2i(posmod(ci + i, ncol), cj + j), []):
				var d := Vector2(StationGeo.wrap_ds(p.x - f[0]), p.y - f[1]).length()
				if d < f[2] + FOOT_R + SPOT_CLEAR:
					return false
	var h0 := MapTerrain.elevation(p.x, p.y)
	for d in [Vector2.ZERO, Vector2(3, 3), Vector2(-3, 3), Vector2(3, -3), Vector2(-3, -3), Vector2(4.5, 0), Vector2(-4.5, 0), Vector2(0, 4.5), Vector2(0, -4.5)]:
		var q: Vector2 = p + d
		if absf(MapTerrain.elevation(q.x, q.y) - h0) > LEVEL:
			return false
		if MapTerrain.road_weight(q.x, q.y) > 0.0 or MapTerrain.water_depth(q.x, q.y) > 0.0:
			return false
		var lc := MapTerrain.landcover(q.x, q.y).x
		if lc == 3 or lc == 5:
			return false
	return true


func _take(p: Vector2) -> void:
	_chosen.append(p)
