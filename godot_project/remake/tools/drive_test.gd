extends Node
class_name DriveTest

## An automated test driver: a car driven along routes -- every bridge, every street -- with the
## player in the driver's seat (so the world streams round it as it would in play), reporting
## where it gets stuck and what stopped it (RemakeGroundVehicle.blocked_by).  Started from
## DevBridge, e.g.:
##   var t = DriveTest.new(); root.add_child(t); t.start(DriveTest.bridge_routes(root.get_tree()))
## then read t.results (and t.done).  Each route: {name, pts: Array of Vector2 (s, x), lane: m
## right of the line}.  A route passes when the car gets within FINISH m of its end.

const SPEED := 12.0                  # m/s (43 km/h)
const LOOK := 9.0                    # m ahead the driver aims
const STUCK_S := 3.0                 # no headway for this long: stuck
const FINISH := 6.0
const TURN := 2.5                    # rad/s the driver turns the car at, at most

var routes: Array = []
var results: Array = []              # {name, ok, reason, at (s, x), progress, length}
var done := false
var car: RemakeGroundVehicle
var _i := -1
var _pts: PackedVector2Array
var _cum: PackedFloat32Array
var _lane := 0.0
var _best := 0.0
var _best_t := 0.0
var _t := 0.0
var _settle := 0


func _ready() -> void:
	process_physics_priority = -100               # steer before the car moves


func start(r: Array, which: RemakeGroundVehicle = null) -> void:
	routes = r
	results.clear()
	done = false
	car = which if which else _nearest_car()
	var p := get_tree().get_first_node_in_group("player") as StationPlayer
	if car.pilot == null:
		car.take_seat(p)
	_next()


func _nearest_car() -> RemakeGroundVehicle:
	var p := get_tree().get_first_node_in_group("player") as Node3D
	var best: RemakeGroundVehicle = null
	var bd := INF
	for v in get_tree().current_scene.find_children("*", "AnimatableBody3D", true, false):
		if v is RemakeGroundVehicle and not v is RemakeVan:
			var d := (v as Node3D).global_position.distance_to(p.global_position)
			if d < bd:
				bd = d
				best = v
	return best


func _next() -> void:
	_i += 1
	if _i >= routes.size():
		done = true
		set_physics_process(false)
		return
	var r: Dictionary = routes[_i]
	_pts = PackedVector2Array(r.pts)
	_lane = float(r.get("lane", 0.0))
	_cum = PackedFloat32Array([0.0])
	for k in range(1, _pts.size()):
		_cum.append(_cum[k - 1] + _d(_pts[k - 1], _pts[k]).length())
	# on the line's start, facing along it, a little above the ground
	var a := _pts[0]
	var dir := _d(a, _pts[1]).normalized()
	var s := fposmod(a.x, StationGeo.CIRC)
	var up := StationGeo.up(s)
	var f := (StationGeo.forward(s) * dir.x + Vector3.RIGHT * dir.y).normalized()
	var at := a + Vector2(-dir.y, dir.x) * _lane
	var g := _ground(at)
	car.global_transform = Transform3D(Basis(up.cross(-f), up, -f).orthonormalized(), g + up * 0.3)
	car._speed = 0.0
	car._vy = 0.0
	car.blocked_by = ""
	_best = 0.0
	_best_t = 0.0
	_t = 0.0
	_settle = 30                                   # let the ground under it stream in


func _ground(at: Vector2) -> Vector3:
	var s := fposmod(at.x, StationGeo.CIRC)
	var up := StationGeo.up(s)
	var top := StationGeo.point(s, at.y, MapTerrain.elevation(s, at.y) + 60.0)
	var q := PhysicsRayQueryParameters3D.create(top, top - up * 120.0)
	q.exclude = car._excluded()
	var hit := get_viewport().world_3d.direct_space_state.intersect_ray(q)
	return hit.position if not hit.is_empty() else StationGeo.point(s, at.y, MapTerrain.elevation(s, at.y))


static func _d(a: Vector2, b: Vector2) -> Vector2:
	return Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)


func _progress(p: Vector2) -> Vector2:
	## (distance along the route of p's nearest point, p's distance off it)
	var best := Vector2(0.0, INF)
	for k in _pts.size() - 1:
		var ab := _d(_pts[k], _pts[k + 1])
		var ap := _d(_pts[k], p)
		var t := clampf(ap.dot(ab) / maxf(ab.length_squared(), 1e-6), 0.0, 1.0)
		var off := (ap - ab * t).length()
		if off < best.y:
			best = Vector2(_cum[k] + ab.length() * t, off)
	return best


func _point_at(u: float) -> Vector2:
	u = clampf(u, 0.0, _cum[_cum.size() - 1])
	for k in _pts.size() - 1:
		if u <= _cum[k + 1] or k == _pts.size() - 2:
			var seg := _cum[k + 1] - _cum[k]
			var t := (u - _cum[k]) / maxf(seg, 1e-6)
			return _pts[k] + _d(_pts[k], _pts[k + 1]) * t
	return _pts[_pts.size() - 1]


func _physics_process(delta: float) -> void:
	if car == null or _i < 0 or done:
		return
	if _settle > 0:
		_settle -= 1
		car._speed = 0.0
		return
	_t += delta
	var pos := car.global_position
	var here := Vector2(StationGeo.s_of(pos), pos.x)
	var pr := _progress(here)
	var total := _cum[_cum.size() - 1]
	if pr.x > _best + 0.5:
		_best = pr.x
		_best_t = _t
	var r: Dictionary = routes[_i]
	if pr.x >= total - FINISH:
		results.append({"name": r.name, "ok": true, "reason": "", "at": here, "progress": pr.x, "length": total})
		_next()
		return
	if _t - _best_t > STUCK_S or _t > total / SPEED * 3.0 + 20.0 or pr.y > 25.0:
		var why: String = car.blocked_by if car.blocked_by != "" else ("off the route" if pr.y > 25.0 else "no headway")
		results.append({"name": r.name, "ok": false, "reason": why, "at": here, "progress": pr.x, "length": total,
			"h": StationGeo.h_of(pos)})
		_next()
		return
	# aim LOOK m ahead, _lane m to the right of the line
	var u := pr.x + LOOK
	var tgt := _point_at(u)
	var ahead := _d(_point_at(u - 1.0), _point_at(u + 1.0)).normalized()
	tgt += Vector2(-ahead.y, ahead.x) * _lane           # the driver's right (facing +s, +x)
	var s := fposmod(here.x, StationGeo.CIRC)
	var up := StationGeo.up(s)
	var dv := _d(here, tgt)
	var want := (StationGeo.forward(s) * dv.x + Vector3.RIGHT * dv.y)
	want = (want - up * want.dot(up)).normalized()
	var b := car.global_transform.basis
	var fwd := -b.z
	fwd = (fwd - up * fwd.dot(up)).normalized()
	var ang := fwd.signed_angle_to(want, up)
	var turn := clampf(ang, -TURN * delta, TURN * delta)
	car.global_transform.basis = b.rotated(up, turn).orthonormalized()
	car._speed = SPEED


static func bridge_routes(tree: SceneTree) -> Array:
	## Every bridge, each way: the great bridges (GreatBridges.spans) and the road crossings
	## (placement.json's kind "crossing"), from just before one end to just past the other.
	var out := []
	var gb := tree.current_scene.find_child("GreatBridges", true, false) as GreatBridges
	if gb == null:
		for n in tree.current_scene.get_children():
			if n is GreatBridges:
				gb = n
	if gb:
		for sp in gb.spans:
			if sp.rail:
				continue
			var o: Vector2 = sp.o
			var dir: Vector2 = sp.dir
			var a := o - dir * 15.0                  # (onto the road each end: beyond, it may bend away)
			var b := o + dir * (float(sp.len) + 15.0)
			out.append({"name": "%s %s A-B" % [sp.id, sp.name], "pts": [a, b], "lane": 1.8})
			out.append({"name": "%s %s B-A" % [sp.id, sp.name], "pts": [b, a], "lane": 1.8})
	var pl: Array = JSON.parse_string(FileAccess.get_file_as_string("res://remake/placement.json")).structures
	for e in pl:
		if e.kind != "crossing":
			continue
		# along the road that crosses it, as a driver would -- from before its deck to past it
		var reach: float = (float(e.fmax[1]) - float(e.fmin[1])) * 0.5 + 40.0
		var pts := _road_through(Vector2(float(e.s), float(e.x)), reach)
		if pts.is_empty():
			var c := cos(float(e.yaw))
			var sn := sin(float(e.yaw))
			var lx: float = (e.fmin[0] + e.fmax[0]) * 0.5
			for lz in [float(e.fmin[1]) - 40.0, float(e.fmax[1]) + 40.0]:
				pts.append(Vector2(float(e.s) + lx * sn - lz * c, float(e.x) + lx * c + lz * sn))
		var back := pts.duplicate()
		back.reverse()
		out.append({"name": "%s A-B" % e.id, "pts": pts, "lane": 0.0})
		out.append({"name": "%s B-A" % e.id, "pts": back, "lane": 0.0})
	return out


static func street_routes(every := 1, max_len := 1000.0) -> Array:
	## Roads to drive end to end in the right-hand lane (alleys down the middle): every every-th road,
	## each at most max_len m (from its middle, a long highway's stretch).
	MapTerrain.elevation(0.0, 0.0)
	var out := []
	var roads: Array = MapTerrain._d.roads
	for ri in range(0, roads.size(), every):
		var rd: Dictionary = roads[ri]
		if rd.cls == "rail":
			continue
		var cum: PackedFloat32Array = rd.cum
		var total := cum[cum.size() - 1]
		if total < 20.0:
			continue
		var mid := _point_on(rd, total * 0.5)
		var pts := _road_through(mid, minf(total, max_len) * 0.5)
		if pts.size() < 2:
			continue
		var lane := 0.0 if float(rd.w) < 5.0 else float(rd.w) * 0.25
		out.append({"name": "road %d %s %s" % [ri, rd.cls, str(rd.get("name", rd.get("town", "")))], "pts": pts, "lane": lane})
	return out


static func _point_on(rd: Dictionary, u: float) -> Vector2:
	var rp: Array = rd.pts
	var cum: PackedFloat32Array = rd.cum
	var k := 0
	while k < rp.size() - 2 and cum[k + 1] < u:
		k += 1
	var L := cum[k + 1] - cum[k]
	var t := 0.0 if L < 1e-6 else (u - cum[k]) / L
	var a := Vector2(rp[k][0], rp[k][1])
	var b := Vector2(rp[k + 1][0], rp[k + 1][1])
	return a + Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y) * t


static func _road_through(c: Vector2, reach: float) -> Array:
	## The polyline of the road nearest c (within 12 m), from reach m before c to reach m after.
	var roads: Array = MapTerrain._d.roads
	var best := 12.0
	var ri := -1
	var seg := -1
	var tt := 0.0
	for i in roads.size():
		if roads[i].cls == "rail":
			continue
		var pts: Array = roads[i].pts
		for k in pts.size() - 1:
			var pr := MapTerrain._seg_proj(c.x, c.y, pts[k][0], pts[k][1], pts[k + 1][0], pts[k + 1][1])
			if pr.x < best:
				best = pr.x
				ri = i
				seg = k
				tt = pr.y
	if ri < 0:
		return []
	var rp: Array = roads[ri].pts
	var cum: PackedFloat32Array = roads[ri].cum
	var u0: float = lerpf(cum[seg], cum[seg + 1], tt)
	var out := []
	var u := maxf(0.0, u0 - reach)
	var u1 := minf(cum[cum.size() - 1], u0 + reach)
	while true:
		# the point at arc length u
		var k := 0
		while k < rp.size() - 2 and cum[k + 1] < u:
			k += 1
		var L := cum[k + 1] - cum[k]
		var t := 0.0 if L < 1e-6 else (u - cum[k]) / L
		var a := Vector2(rp[k][0], rp[k][1])
		var b := Vector2(rp[k + 1][0], rp[k + 1][1])
		out.append(a + Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y) * t)
		if u >= u1:
			break
		u = minf(u + 4.0, u1)
	return out


func summary() -> String:
	var bad := results.filter(func(r): return not r.ok)
	var lines := ["%d / %d passed" % [results.size() - bad.size(), results.size()]]
	for r in bad:
		lines.append("%s: %s at s %.0f x %.0f (%.0f of %.0f m)" % [r.name, r.reason, r.at.x, r.at.y, r.progress, r.length])
	return "\n".join(lines)
