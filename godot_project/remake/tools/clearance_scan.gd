extends Node

## Is every lane of every road clear for a car?  A car's hull (RemakeGroundVehicle's swept box,
## lifted CLEAR m off the ground as it drives) placed along each lane every STEP m -- both
## directions, facing along the road -- and tested against the world (buildings, furniture, parked
## cars...).  Over the great bridges and small crossings the drive test (drive_test.gd) is the
## check instead.  Buildings' collision streams in near the player, so the sweep goes cell by cell
## (CELL m square), taking the player to each first and waiting WAIT frames.  From DevBridge:
##   var c = load("res://remake/tools/clearance_scan.gd").new(); root.add_child(c)   then read c.done, c.hits

const STEP := 2.0
const HULL := Vector3(1.85, 1.95, 3.9)       # the pod's (the narrower car); the van's is 1.95 x 2.0 x 5.1
const CLEAR := 0.5
const PER_FRAME := 400
const CELL := 200.0                            # (buildings get their collision within 180 m of the player)
const SETTLE := 40                             # frames the building streamer must be idle before a cell is swept
const WAIT_MAX := 900

var done := false
var hits: Array = []                          # {road, cls, name, s, x, what}
var checked := 0
var _jobs: Array = []                         # [road index, (s, x), heading (s, x)], sorted by cell
var _i := 0
var _cell := Vector2i(-99999, 0)
var _wait := 0
var _idle := 0
var _rs: GDScript
var _q := PhysicsShapeQueryParameters3D.new()
var _spans: Array = []


func _ready() -> void:
	var box := BoxShape3D.new()
	box.size = HULL
	_q.shape = box
	_q.collision_mask = 1 | RemakeGroundVehicle.HULL_LAYER
	_rs = load("res://remake/tools/road_scan.gd")
	var pl := get_tree().get_first_node_in_group("player") as StationPlayer
	if pl._vehicle:
		pl._vehicle.leave_seat()
	var gb := get_tree().current_scene.get_node_or_null("GreatBridges")
	if gb:
		_spans = gb.spans
	var roads: Array = MapTerrain._d.roads
	for ri in roads.size():
		var rd: Dictionary = roads[ri]
		if rd.cls == "rail":
			continue
		var pts: Array = rd.pts
		var lanes := [0.0] if float(rd.w) < 5.0 else [float(rd.w) * 0.25, -float(rd.w) * 0.25]
		for k in pts.size() - 1:
			var a := Vector2(pts[k][0], pts[k][1])
			var b := Vector2(pts[k + 1][0], pts[k + 1][1])
			var d := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y)
			var L := d.length()
			if L < 0.01:
				continue
			var dir := d / L
			var n := maxi(1, ceili(L / STEP))
			for i in n:
				for lane in lanes:
					var c: Vector2 = a + dir * (L * i / n)
					_jobs.append([ri, c + Vector2(-dir.y, dir.x) * lane, dir, c])
	_jobs.sort_custom(func(a, b): return _key(a[1]) < _key(b[1]))
	set_process(true)


static func _key(p: Vector2) -> int:
	return floori(fposmod(p.x, StationGeo.CIRC) / CELL) * 1000 + floori((p.y + 4000.0) / CELL)


func progress() -> String:
	return "%d / %d placements, %d blocked" % [_i, _jobs.size(), hits.size()]


func _process(_delta: float) -> void:
	if done:
		return
	var space := get_viewport().world_3d.direct_space_state
	if _wait > 0:
		# until the buildings round the player are in (the streamer idle a while), or WAIT_MAX frames
		_wait -= 1
		var st = get_tree().current_scene.get("streamer")
		_idle = _idle + 1 if st == null or st._inflight.is_empty() else 0
		if _idle < SETTLE and _wait > 0:
			return
		_wait = 0
	var end := mini(_i + PER_FRAME, _jobs.size())
	while _i < end:
		var j: Array = _jobs[_i]
		var p: Vector2 = j[1]
		# a new cell: take the player there and let its buildings' collision stream in
		var ck := Vector2i(floori(fposmod(p.x, StationGeo.CIRC) / CELL), floori((p.y + 4000.0) / CELL))
		if ck != _cell:
			_cell = ck
			var pl := get_tree().get_first_node_in_group("player") as Node3D
			var cs := (ck.x + 0.5) * CELL
			var cx := (ck.y + 0.5) * CELL - 4000.0
			pl.global_position = StationGeo.point(cs, cx, MapTerrain.elevation(cs, cx) + 40.0)
			pl.velocity = Vector3.ZERO
			_wait = WAIT_MAX
			_idle = 0
			return
		_i += 1
		if _rs._on_bridge(p, _spans):
			continue
		var dir: Vector2 = j[2]
		var s := fposmod(p.x, StationGeo.CIRC)
		var up := StationGeo.up(s)
		var f := (StationGeo.forward(s) * dir.x + Vector3.RIGHT * dir.y).normalized()
		var h := MapTerrain.elevation(s, p.y)
		_q.transform = Transform3D(Basis(up.cross(-f), up, -f).orthonormalized(),
			StationGeo.point(s, p.y, h + CLEAR + HULL.y * 0.5))
		checked += 1
		var res := space.intersect_shape(_q, 1)
		if not res.is_empty():
			# something at the lane's edge (a car parked at the kerb, a guardrail's end where two
			# roads part at a creek): the road is still passable if its middle is clear -- a driver
			# goes round it
			var cm: Vector2 = j[3]
			var sm := fposmod(cm.x, StationGeo.CIRC)
			_q.transform = Transform3D(Basis(up.cross(-f), up, -f).orthonormalized(),
				StationGeo.point(sm, cm.y, MapTerrain.elevation(sm, cm.y) + CLEAR + HULL.y * 0.5))
			res = space.intersect_shape(_q, 1)
		if not res.is_empty() and res[0].collider is StationPlayer:
			res = []                                   # (the player the sweep carries about)
		if not res.is_empty():
			var c: Object = res[0].collider
			var rd: Dictionary = MapTerrain._d.roads[j[0]]
			hits.append({"road": j[0], "cls": rd.cls, "name": str(rd.get("name", rd.get("town", ""))),
				"s": snappedf(s, 0.1), "x": snappedf(p.y, 0.1), "what": str((c as Node).get_path()) if c is Node else str(res[0].rid)})
	if _i >= _jobs.size():
		done = true


func summary(limit := 60) -> String:
	## Hits grouped by what was hit (one line per thing, with where first).
	var by := {}
	for h in hits:
		var key: String = h.what
		if not by.has(key):
			by[key] = [h, 0]
		by[key][1] += 1
	var lines := ["checked %d placements, %d blocked, %d things in the way" % [checked, hits.size(), by.size()]]
	for key in by:
		if lines.size() > limit:
			break
		var h: Dictionary = by[key][0]
		lines.append("%s (%s, %s) s %.0f x %.0f  x%d  %s" % [h.name, h.cls, h.road, h.s, h.x, by[key][1], key])
	return "\n".join(lines)
