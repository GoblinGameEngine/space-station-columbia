extends SceneTree

## Chooses where the ground vehicles park and writes res://remake/groundcars.json (RemakeStation reads
## it).  Run after the map, the placement or the aerostats change:
##   godot4 --headless --path . --script res://remake/tools/place_ground_vehicles.gd
##
##   towns   kerbside on the town's streets, nearest its middle first, by size (buildings on the
##           map): 120+ -> 8, 80+ -> 6, 30+ -> 4, a village -> 2; pods and vans in turn
##   farms   a van at every farmstead the aerostats skipped (they took every other one), in the yard
## A spot is kerbside: KERB m out from the road's edge, parallel to it; clear of every structure's
## footprint (its own turned rectangle) by CLEAR m, off water, near level, APART m from other
## vehicles and the aerostats.

const OUT := "res://remake/groundcars.json"
const HALF := Vector2(1.05, 2.7)      # the larger vehicle's half width, half length (the van's)
const KERB := 1.2
const CLEAR := 0.6
const APART := 9.0
const STREETS := ["street", "main", "county"]

var _rects: Array = []                # [s, x, yaw, half size] of every structure
var _taken: Array = []                # [s, x, r]


func _init() -> void:
	var entries: Array = (JSON.parse_string(FileAccess.get_file_as_string("res://remake/placement.json")) as Dictionary).structures
	var terrain: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(MapTerrain.PATH))
	MapTerrain.elevation(0.0, 0.0)
	for e in entries:
		var fmin: Array = e.get("fmin", [e.min[0], e.min[2]])
		var fmax: Array = e.get("fmax", [e.max[0], e.max[2]])
		# the footprint's centre in the building's own frame, and its half size
		var c := Vector2((fmin[0] + fmax[0]) * 0.5, (fmin[1] + fmax[1]) * 0.5)
		var hs := Vector2((fmax[0] - fmin[0]) * 0.5, (fmax[1] - fmin[1]) * 0.5)
		var yaw: float = e.yaw
		# local (x, z) -> map (s, x): right = (cos yaw, sin yaw) in (x, s); forward (-z) = (-sin yaw, cos yaw) in (x, s)
		var ds := c.x * sin(yaw) - c.y * cos(yaw)
		var dx := c.x * cos(yaw) + c.y * sin(yaw)
		_rects.append([float(e.s) + ds, float(e.x) + dx, yaw, hs])
	if FileAccess.file_exists("res://remake/aerostats.json"):
		for a in JSON.parse_string(FileAccess.get_file_as_string("res://remake/aerostats.json")).aerostats:
			_taken.append([float(a.s), float(a.x), 10.0])        # keep 10 m from an aerostat
	var out := []
	# towns
	var towns := {}
	for e in entries:
		var t = e.get("settlement")
		if t == null:
			continue
		if not towns.has(t):
			towns[t] = []
		towns[t].append(e)
	var roads: Array = []
	for rd in terrain.roads:
		if STREETS.has(rd.cls):
			roads.append(rd)
	var names := towns.keys()
	names.sort()
	for t in names:
		var bs: Array = towns[t]
		var n := bs.size()
		var want := 8 if n >= 120 else (6 if n >= 80 else (4 if n >= 30 else 2))
		var c := _middle(bs)
		var cands := _kerbside(roads, c, 450.0)
		cands.sort_custom(func(a, b): return a[3] < b[3])
		var got := 0
		for k in cands:
			if got >= want:
				break
			if _clear(k[0], k[1], k[2]):
				_take(k[0], k[1])
				var kind := "pod" if got % 2 == 0 else "van"
				got += 1
				out.append({"id": "CAR-%s-%d" % [str(t).replace(" ", ""), got], "kind": kind, "s": snappedf(fposmod(k[0], StationGeo.CIRC), 0.01),
					"x": snappedf(k[1], 0.01), "yaw": snappedf(k[2], 0.0001), "where": t})
		print("%s (%d buildings): %d of %d" % [t, n, got, want])
	# farms the aerostats skipped: a van in the yard
	var houses := []
	for e in entries:
		if str(e.id).begins_with("FARM-") and str(e.id).ends_with("-house"):
			houses.append(e)
	houses.sort_custom(func(a, b): return str(a.id) < str(b.id))
	var farm_n := 0
	for i in range(1, houses.size(), 2):
		var h: Dictionary = houses[i]
		var found := false
		for r in [12.0, 16.0, 20.0, 25.0, 30.0, 36.0]:
			for k in 16:
				var a := TAU * k / 16.0
				var p: Vector2 = Vector2(float(h.s), float(h.x)) + Vector2(cos(a), sin(a)) * r
				var yaw: float = float(h.yaw) + (PI * 0.5 if k % 2 else 0.0)
				if _clear(p.x, p.y, yaw):
					_take(p.x, p.y)
					out.append({"id": "CAR-%s" % str(h.id).trim_suffix("-house"), "kind": "van",
						"s": snappedf(fposmod(p.x, StationGeo.CIRC), 0.01), "x": snappedf(p.y, 0.01), "yaw": snappedf(yaw, 0.0001),
						"where": str(h.id).trim_suffix("-house")})
					farm_n += 1
					found = true
					break
			if found:
				break
	print("farms: %d of %d" % [farm_n, houses.size() / 2])
	var f := FileAccess.open(OUT, FileAccess.WRITE)
	f.store_string(JSON.stringify({"groundcars": out}, "\t"))
	f.close()
	print("GROUNDCARS_PLACED %d -> %s" % [out.size(), OUT])
	quit()


func _middle(bs: Array) -> Vector2:
	var cs := 0.0
	var sn := 0.0
	var x := 0.0
	for e in bs:
		var th: float = float(e.s) / StationGeo.R
		cs += cos(th)
		sn += sin(th)
		x += float(e.x)
	return Vector2(fposmod(atan2(sn, cs), TAU) * StationGeo.R, x / bs.size())


func _kerbside(roads: Array, c: Vector2, reach: float) -> Array:
	## [s, x, yaw, distance to c] every 14 m along both kerbs of every street near c.
	var out := []
	for rd in roads:
		var pts: Array = rd.pts
		var off: float = float(rd.w) * 0.5 + KERB + HALF.x
		for k in pts.size() - 1:
			var a := Vector2(pts[k][0], pts[k][1])
			var b := Vector2(pts[k + 1][0], pts[k + 1][1])
			var dv := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)
			var L := dv.length()
			if L < 1.0:
				continue
			var mid := a + dv * 0.5
			if Vector2(StationGeo.wrap_ds(mid.x - c.x), mid.y - c.y).length() > reach + L:
				continue
			var u := dv / L
			var side := Vector2(-u.y, u.x)
			var yaw := atan2(-u.y, u.x)
			var t := 10.0
			while t < L - 10.0:
				for sg in [1.0, -1.0]:
					var p: Vector2 = a + u * t + side * off * sg
					var d := Vector2(StationGeo.wrap_ds(p.x - c.x), p.y - c.y).length()
					if d < reach:
						# kerbside cars face the traffic's way on their side
						out.append([p.x, p.y, yaw if sg < 0.0 else yaw + PI, d])
				t += 14.0
	return out


func _clear(s: float, x: float, yaw: float) -> bool:
	if absf(x) > StationGeo.HALF_LEN - 60.0:
		return false
	for q in _taken:
		if Vector2(StationGeo.wrap_ds(s - q[0]), x - q[1]).length() < float(q[2]):
			return false
	# the vehicle's corners and centre against every structure's rectangle
	var fwd := Vector2(cos(yaw), -sin(yaw))                   # (s, x) of the vehicle's forward
	var right := Vector2(sin(yaw), cos(yaw))
	var pts := [Vector2(s, x)]
	for i in [-1.0, 1.0]:
		for j in [-1.0, 1.0]:
			pts.append(Vector2(s, x) + fwd * HALF.y * i + right * HALF.x * j)
	for r in _rects:
		for p in pts:
			var ds := StationGeo.wrap_ds(p.x - r[0])
			if absf(ds) > 60.0 or absf(p.y - r[1]) > 60.0:
				break
			var yw: float = r[2]
			# into the structure's frame: its right (x, s) = (cos, sin); its forward = (-sin, cos)
			var lx: float = (p.y - r[1]) * cos(yw) + ds * sin(yw)
			var lz: float = -((p.y - r[1]) * -sin(yw) + ds * cos(yw))
			var hs: Vector2 = r[3]
			if absf(lx) < hs.x + CLEAR and absf(lz) < hs.y + CLEAR:
				return false
	var h0 := MapTerrain.elevation(s, x)
	for p in pts:
		if absf(MapTerrain.elevation(p.x, p.y) - h0) > 0.5:
			return false
		if MapTerrain.water_depth(p.x, p.y) > 0.0:
			return false
	return true


func _take(s: float, x: float) -> void:
	_taken.append([s, x, APART])
