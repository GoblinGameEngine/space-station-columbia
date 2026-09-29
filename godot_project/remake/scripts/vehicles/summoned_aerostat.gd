extends RemakeAerostat
class_name RemakeSummonedAerostat

## An aerostat called with the Communicator's Summon Aerostat app (GameMenu.gd): the fleet's
## aerostat, red where the fleet's is blue.  It appears SPAWN_DIST m from the player, on the side
## they aren't looking at, SPAWN_ALT m up.  It dives toward them down to CRUISE_ALT m, then lets
## itself down onto the nearest clear spot at least MIN_GAP m from them (dry, flat, nothing
## standing on it), turned side-on so a door faces them.  It flies itself, with no ceiling, and
## keeps flying while the Communicator is open, so the app can track it; once down it parks like
## any other aerostat.  One at a time: summon() replaces an empty one that's already down.

const SPAWN_DIST := 100.0
const SPAWN_ALT := 500.0
const CRUISE_ALT := 50.0
const MIN_GAP := 10.0
const DIVE_RATE := 18.0              # m/s down to CRUISE_ALT: rapid, ~65 km/h
const LET_DOWN := 4.0                # m/s from CRUISE_ALT to FLARE_ALT
const FLARE_ALT := 6.0
const TOUCH := 1.2                   # m/s the last FLARE_ALT m (well inside GEAR_MS)
const TURN := 0.9                    # rad/s it turns at
const PAD_HALF := Vector3(3.0, 4.6, 3.0)   # the room it needs: the fans' span, the balloon's top
const SIGHT_R := 60.0                # m: look this far for a spot the player can see
const RED := Color(0.6, 0.06, 0.05)

var phase := "dive"                  # dive, let_down, parked
var pad := Vector3.ZERO              # where it will land (the ground)
var _face := Basis()                 # the heading it lets down at


func _ready() -> void:
	super()
	add_to_group("summoned_aerostat")
	add_to_group("tree_collide")
	process_mode = Node.PROCESS_MODE_ALWAYS     # flies on while the Communicator has the world paused
	var red := StandardMaterial3D.new()
	red.albedo_color = RED
	red.roughness = 0.45
	red.metallic = 0.1
	for m in model.find_children("*", "MeshInstance3D", true, false):
		var mi := m as MeshInstance3D
		for i in mi.mesh.get_surface_count():
			var mat := mi.mesh.surface_get_material(i)
			if mat and mat.resource_name == "body_blue":
				mi.set_surface_override_material(i, red)


static func summon(tree: SceneTree) -> Dictionary:
	## Call one: {ok, message, vehicle}.
	var player := tree.get_first_node_in_group("player") as Node3D
	if player == null:
		return {"ok": false, "message": "No one to pick up."}
	for old in tree.get_nodes_in_group("summoned_aerostat"):
		var a := old as RemakeSummonedAerostat
		if a.phase != "parked" and not a.disabled:
			return {"ok": true, "message": "Your aerostat is already on its way.", "vehicle": a}
		if a.pilot or not a._riders.is_empty():
			return {"ok": false, "message": "You're aboard your aerostat."}
		a.queue_free()
		a.remove_from_group("summoned_aerostat")
	var p := player.global_position
	var s := StationGeo.s_of(p)
	var world := player.get_world_3d()
	var pad := find_pad(world, s, p.x, [player], p + StationGeo.up(s) * 1.6)
	if pad == Vector3.INF:
		return {"ok": false, "message": "No clear place to land near you. Try somewhere more open."}
	# away from where they're looking: behind them, give or take 35 degrees
	var cam := player.get_viewport().get_camera_3d()
	var f := -(cam.global_transform.basis.z if cam else player.global_transform.basis.z)
	var look := atan2(f.x, f.dot(StationGeo.forward(s)))       # 0 = +s, pi/2 = +x
	var a := look + PI + randf_range(-0.6, 0.6)
	var ss := s + cos(a) * SPAWN_DIST
	var sx := p.x + sin(a) * SPAWN_DIST
	if absf(sx) > StationGeo.HALF_LEN - 60.0:
		sx = p.x - sin(a) * SPAWN_DIST                              # the end wall: the other way
	ss = fposmod(ss, StationGeo.CIRC)
	var v := RemakeSummonedAerostat.new()
	v.name = "SummonedAerostat"
	v.pad = pad
	var parent := tree.current_scene.get_node_or_null("Aerostats")
	(parent if parent else tree.current_scene).add_child(v)
	var ground := MapTerrain.elevation(ss, sx)
	v.global_transform = Transform3D(StationGeo.basis(ss, -a + PI * 0.5), StationGeo.point(ss, sx, ground + SPAWN_ALT))
	return {"ok": true, "message": "An aerostat is on its way.", "vehicle": v}


static func _wet(s: float, x: float, h: float) -> bool:
	## Under water: the rivers, lake and seas, or a creek (not a ditch the land merely dips into).
	var wa := MapTerrain.water_at(s, x)
	return (wa.x > -9000.0 and wa.x > h - 0.05) or MapTerrain.water_depth(s, x) > 0.3


static func find_pad(world: World3D, s: float, x: float, exclude: Array, eye := Vector3.INF) -> Vector3:
	## The nearest clear landing place at least MIN_GAP (+ the hull) from (s, x) -- one in sight of
	## eye if there's one within SIGHT_R -- or Vector3.INF if none.
	var space := world.direct_space_state
	var hidden := Vector3.INF
	var box := BoxShape3D.new()
	box.size = PAD_HALF * 2.0
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = box
	q.collision_mask = 1 | RemakeGroundVehicle.HULL_LAYER
	var ex: Array[RID] = []
	for n in exclude:
		ex.append((n as CollisionObject3D).get_rid())
	q.exclude = ex
	var r := MIN_GAP + PAD_HALF.x + 1.0
	while r <= 150.0:
		var n := maxi(12, int(TAU * r / 5.0))
		var off := randf() * TAU
		for i in n:
			var a := off + TAU * i / n
			var cs := fposmod(s + cos(a) * r, StationGeo.CIRC)
			var cx := x + sin(a) * r
			if absf(cx) > StationGeo.HALF_LEN - 45.0:
				continue
			# dry and flat underfoot
			var h := MapTerrain.elevation(cs, cx)
			var ok := not _wet(cs, cx, h)
			for c in [Vector2(-3, -3), Vector2(3, -3), Vector2(-3, 3), Vector2(3, 3)]:
				var hs := fposmod(cs + c.x, StationGeo.CIRC)
				var hc := MapTerrain.elevation(hs, cx + c.y)
				if not ok or absf(hc - h) > 0.6 or _wet(hs, cx + c.y, hc):
					ok = false
					break
			if not ok:
				continue
			# the ground there as the world has it (a deck, a road), then nothing in the way above it
			var up := StationGeo.up(cs)
			var top := StationGeo.point(cs, cx, h + 40.0)
			var rq := PhysicsRayQueryParameters3D.create(top, StationGeo.point(cs, cx, h - 3.0))
			rq.exclude = ex
			var hit := space.intersect_ray(rq)
			var g: Vector3 = hit.position if not hit.is_empty() else StationGeo.point(cs, cx, h)
			if (g - StationGeo.point(cs, cx, h)).dot(up) > 1.0:
				continue                                         # a roof, a canopy: not ground
			q.transform = Transform3D(StationGeo.basis(cs), g + up * (PAD_HALF.y + 0.4))
			if not space.intersect_shape(q, 1).is_empty():
				continue
			if eye == Vector3.INF:
				return g
			var sight := PhysicsRayQueryParameters3D.create(eye, g + up * 1.5)
			sight.exclude = ex
			if space.intersect_ray(sight).is_empty():
				return g                                     # in view: the one to use
			if hidden == Vector3.INF:
				hidden = g                                   # round a corner: if nothing in view
		if r >= SIGHT_R and hidden != Vector3.INF:
			return hidden
		r += 4.0
	return hidden


# ------------------------------------------------------------------ flying itself
func _flying_self() -> bool:
	return phase != "parked"


func _physics_process(delta: float) -> void:
	if phase != "parked" and (pilot != null or disabled):
		_park()
	if phase == "parked":
		super(delta)
		return
	var pos := global_position
	var s := StationGeo.s_of(pos)
	var up := StationGeo.up(s)
	var ps := StationGeo.s_of(pad)
	var alt := StationGeo.h_of(pos) - StationGeo.h_of(pad)
	var ds := StationGeo.wrap_ds(ps - s)
	var dx := pad.x - pos.x
	var dist := Vector2(ds, dx).length()
	var dir := (StationGeo.forward(s) * ds + Vector3.RIGHT * dx).normalized() if dist > 0.01 else Vector3.ZERO
	var vh := 0.0
	var vy := 0.0
	if phase == "dive":
		# down fast to CRUISE_ALT, timing the run in to be over the pad as it gets there
		var above := alt - CRUISE_ALT
		vy = -minf(DIVE_RATE, above * 0.9 + 0.5) if above > 0.0 else 0.0
		var t_left := maxf(above / DIVE_RATE, 1.0)
		vh = minf(max_speed, maxf(dist / t_left, minf(dist * 0.6, 12.0)))
		vh = minf(vh, dist * 1.5)
		if above < 1.5 and dist < 2.0:
			phase = "let_down"
			_face = _side_on(s, up)
	else:
		vh = minf(3.0, dist * 1.2)
		vy = -(LET_DOWN if alt > FLARE_ALT else TOUCH)
	var vel := dir * vh + up * vy
	# heading: into the run while it's quick; side-on to the player for the let-down
	var b := _unswung(global_transform.basis.orthonormalized())
	b = Basis(Quaternion(b.y, up)) * b
	var want := _face if phase == "let_down" else (_facing(dir, up) if vh > 2.0 else b)
	var q0 := b.get_rotation_quaternion()
	var q1 := want.get_rotation_quaternion()
	var ang := q0.angle_to(q1)
	var nb := Basis(q0.slerp(q1, minf(1.0, TURN * delta / ang))) if ang > 1e-4 else want
	_yaw_rate = 0.0
	_lv = nb.inverse() * vel
	var before := global_position
	_move(Transform3D(_swung(nb, delta), pos), vel * delta)
	_animate(clampf(vh / 10.0, 0.0, 1.0), 0.0, -1.0 if vy < 0.0 else 0.0, delta)
	_carry(delta)
	# down: the descent stopped short by the ground
	if phase == "let_down" and alt < FLARE_ALT and (global_position - before).dot(up) > vy * delta * 0.5:
		_park()


func _facing(dir: Vector3, up: Vector3) -> Basis:
	var f := (dir - up * dir.dot(up)).normalized()
	return Basis(up.cross(-f), up, -f).orthonormalized()


func _side_on(s: float, up: Vector3) -> Basis:
	## The heading that puts a doorway toward the player: their bearing along the vehicle's x.
	var p := get_tree().get_first_node_in_group("player") as Node3D
	if p == null:
		return _facing(StationGeo.forward(s), up)
	var to := p.global_position - pad
	to -= up * to.dot(up)
	if to.length() < 0.1:
		return _facing(StationGeo.forward(s), up)
	return _facing(to.normalized().cross(up), up)          # nose 90 degrees off the bearing: side-on


func _park() -> void:
	phase = "parked"
	_lv = Vector3.ZERO
	process_mode = Node.PROCESS_MODE_INHERIT
	remove_from_group("tree_collide")


func status() -> Dictionary:
	## For the app: {phase, dist (m, to the player), alt (m above the pad), eta (s)}.
	var p := get_tree().get_first_node_in_group("player") as Node3D
	var d := p.global_position.distance_to(global_position) if p else 0.0
	var alt := StationGeo.h_of(global_position) - StationGeo.h_of(pad)
	var eta := 0.0
	if phase == "dive":
		eta = maxf(alt - CRUISE_ALT, 0.0) / DIVE_RATE + (CRUISE_ALT - FLARE_ALT) / LET_DOWN + FLARE_ALT / TOUCH + 2.0
	elif phase == "let_down":
		eta = maxf(alt - FLARE_ALT, 0.0) / LET_DOWN + minf(alt, FLARE_ALT) / TOUCH
	return {"phase": phase, "dist": d, "alt": alt, "eta": eta, "disabled": disabled}
