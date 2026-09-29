extends RemakeAirVehicle
class_name RemakeGroundVehicle

## A drivable ground vehicle -- the template for every car of this kind.  It shares the air
## vehicles' doors, driver's seat, passenger carrying and readout (RemakeAirVehicle); a subclass
## gives the model (remake/blender/vehicles/groundcar.py) and its hull.  The model's rig:
##   wheel_{FL,FR,BL,BR}   the wheels (spin about local X; the front pair steer about Y)
##   steering_wheel        turns with the steering, about its column (local Z)
##   door_*, seat_pilot, exit_*   as the air vehicles'
##
## Controls (the player's own actions):
##   move_forward / move_back   drive / brake, and reverse from a stop
##   move_left / move_right     steer (less lock the faster it goes)
##   jump                       the brake        interact   leave the driver's seat
##
## Driving is kinematic, on the station's curved floor: each tick it turns by the bicycle model
## (yaw rate = speed x tan(steer) / wheelbase), sweeps its hull along the ground's tangent (lifted
## CLEAR m so kerbs and slopes don't snag it; buildings and walls stop it), then finds the ground
## under each wheel -- a ray down (roads, bridge decks, the terrain near the player), MapTerrain
## where no collision is built yet -- and sits on it: the four contacts set its height, pitch and
## roll; over a drop it falls.  It won't drive into water deeper than WADE m.

@export var wheelbase := 2.6
@export var track := 1.6
@export var wheel_r := 0.36
@export var max_steer := 0.6         # rad at walking pace
@export var steer_rate := 1.6        # rad/s
@export var coast := 0.8             # m/s^2 rolling to a stop
@export var motor_sound := "res://remake/audio/car_motor.wav"

const CLEAR := 0.5                   # the hull's box starts this far above the ground (kerbs and slopes pass under it)
const HULL_LAYER := 1 << 8           # the swept hull's own layer: vehicles see it, people don't (they're inside it)
const WADE := 0.45
const STEP := 0.4                    # the most a wheel climbs in one go (a kerb); more is a wall

@export var hull_size := Vector3(1.9, 1.9, 4.0)   # the one box swept against the world (its bottom at CLEAR)

var wheels: Array = []               # [Node3D, base Basis, front?, local x]
var steer_node: Node3D
var _steer_base := Basis()
var _speed := 0.0
var _steer := 0.0
var _spin_a := 0.0
var _vy := 0.0
var _motor: AudioStreamPlayer3D
var _ramps: StaticBody3D
var _cabin: StaticBody3D             # the walls, floor, seats and roof people walk among (not swept)


func add_box(size: Vector3, at: Vector3, roll := 0.0) -> void:
	## The cabin's shapes go on their own body (people collide with it; the drive sweeps only the
	## one hull box -- a full cabin against detailed buildings every tick is far too slow).
	if _cabin == null:
		_cabin = StaticBody3D.new()
		_cabin.name = "Cabin"
		add_child(_cabin)
	var cs := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	cs.shape = box
	cs.position = at
	cs.rotation.z = roll
	_cabin.add_child(cs)


func _ready() -> void:
	super()
	var hull := CollisionShape3D.new()
	hull.name = "Hull"
	var hb := BoxShape3D.new()
	hb.size = hull_size
	hull.shape = hb
	hull.position = Vector3(0, CLEAR + hull_size.y * 0.5, 0)
	add_child(hull)
	collision_layer = HULL_LAYER
	collision_mask = 1 | HULL_LAYER
	var snd: AudioStreamWAV = load(motor_sound)
	snd.loop_mode = AudioStreamWAV.LOOP_FORWARD
	snd.loop_end = snd.data.size() / 2
	_motor = AudioStreamPlayer3D.new()
	_motor.stream = snd
	_motor.unit_size = 5.0
	_motor.max_distance = 120.0
	add_child(_motor)


func _rig() -> void:
	super()
	for n in model.find_children("wheel_*", "", true, false):
		var tag := str(n.name).substr(6)             # "FL"
		wheels.append([n, (n as Node3D).transform.basis, tag.begins_with("F"), _local(n).origin.x])
	steer_node = model.find_child("steering_wheel", true, false)
	if steer_node:
		_steer_base = steer_node.transform.basis


func door_slide() -> float:
	return 0.6


func add_ramp(size: Vector3, at: Vector3, roll := 0.0) -> void:
	## A boarding ramp to a doorway: its own body, left out of the hull's sweep (it would catch kerbs).
	if _ramps == null:
		_ramps = StaticBody3D.new()
		_ramps.name = "Ramps"
		add_child(_ramps)
	var cs := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	cs.shape = box
	cs.position = at
	cs.rotation.z = roll
	_ramps.add_child(cs)


func _excluded() -> Array[RID]:
	var ex: Array[RID] = [get_rid()]
	for r in _riders:
		ex.append((r as PhysicsBody3D).get_rid())
	if pilot:
		ex.append(pilot.get_rid())
	for d in doors:
		ex.append((d as PhysicsBody3D).get_rid())
	var seat := get_node_or_null("PilotSeat")
	if seat:
		ex.append((seat as PhysicsBody3D).get_rid())
	if _ramps:
		ex.append(_ramps.get_rid())
	if _cabin:
		ex.append(_cabin.get_rid())
	return ex


# ------------------------------------------------------------------ driving
func _physics_process(delta: float) -> void:
	if pilot == null and absf(_speed) < 0.01 and _riders.is_empty() and _vy == 0.0:
		var near := false
		for p in get_tree().get_nodes_in_group("player"):
			if (p as Node3D).global_position.distance_squared_to(global_position) < 900.0:
				near = true
		if not near:
			if _motor.playing:
				_motor.stop()
			return
	var thr := 0.0
	var steer_in := 0.0
	var brake_in := false
	if pilot:
		# the keys or the left stick; or a controller's triggers (RT accelerate, LT brake and reverse)
		thr = clampf(Input.get_action_strength("move_forward") + Input.get_action_strength("accelerate")
			- Input.get_action_strength("move_back") - Input.get_action_strength("brake_reverse"), -1.0, 1.0)
		steer_in = Input.get_action_strength("move_right") - Input.get_action_strength("move_left")
		brake_in = Input.is_action_pressed("jump")
	# speed: drive, brake against the motion, reverse from a stop, coast
	if brake_in:
		_speed = move_toward(_speed, 0.0, brake * 1.5 * delta)
	elif thr > 0.05:
		_speed = move_toward(_speed, max_speed * thr, (accel if _speed >= 0.0 else brake) * delta)
	elif thr < -0.05:
		_speed = move_toward(_speed, -reverse_speed * -thr, (accel if _speed <= 0.0 else brake) * delta)
	else:
		_speed = move_toward(_speed, 0.0, coast * delta)
	_steer = move_toward(_steer, -steer_in * max_steer / (1.0 + absf(_speed) / 12.0), steer_rate * delta)
	var s := StationGeo.s_of(global_position)
	var up := StationGeo.up(s)
	var b := global_transform.basis.orthonormalized()
	_yaw_rate = _speed * tan(_steer) / wheelbase
	var turned := b.rotated(b.y, _yaw_rate * delta).orthonormalized()
	# a turn that swings a corner into something (a parked car, a wall) doesn't happen
	if absf(_yaw_rate) > 1e-5 and _depth(Transform3D(turned, global_position)) > _depth(Transform3D(b, global_position)) + 0.005:
		_yaw_rate = 0.0
	else:
		b = turned
	# along the ground's tangent, the hull swept a little above it
	var fwd := -b.z
	fwd = (fwd - up * fwd.dot(up)).normalized()
	var pos := global_position
	var motion := fwd * _speed * delta
	# no wading: stop at water deeper than WADE ahead of the front axle
	var ahead := pos + fwd * (wheelbase * 0.5 + 1.0) * signf(_speed)
	var wa := MapTerrain.water_at(fposmod(StationGeo.s_of(ahead), StationGeo.CIRC), ahead.x)
	if absf(_speed) > 0.01 and wa.x > -9000.0 and wa.x - MapTerrain.elevation(StationGeo.s_of(ahead), ahead.x) > WADE:
		motion = Vector3.ZERO
		_speed = 0.0
	if absf(ahead.x) > StationGeo.HALF_LEN - 15.0 and signf(ahead.x - pos.x) == signf(ahead.x):
		motion = Vector3.ZERO
		_speed = 0.0
	var before := pos
	pos = _sweep(Transform3D(b, pos), motion)
	# the ground under each wheel
	s = StationGeo.s_of(pos)
	up = StationGeo.up(s)
	var contacts := []
	var hsum := 0.0
	for w in wheels:
		var lp: Vector3 = _local(w[0]).origin
		var wp := pos + b * Vector3(lp.x, 0.0, lp.z)
		var g := _ground(wp, up)
		contacts.append(g)
		hsum += (g - pos).dot(up)
	if wheels.is_empty():
		var g0 := _ground(pos, up)
		contacts.append(g0)
		hsum = (g0 - pos).dot(up)
	# a wheel meeting ground more than a kerb above it has met a wall (a porch, a step, a plinth)
	for g in contacts:
		if (g - pos).dot(up) > STEP and pos != before:
			_impact(absf(_speed), (before - pos).normalized(), g)
			pos = before
			_speed = 0.0
			contacts.clear()
			hsum = 0.0
			for w in wheels:
				var lp2: Vector3 = _local(w[0]).origin
				var g2 := _ground(pos + b * Vector3(lp2.x, 0.0, lp2.z), up)
				contacts.append(g2)
				hsum += (g2 - pos).dot(up)
			break
	var target := hsum / maxf(1.0, contacts.size())
	# sit on the ground; over a drop, fall
	if target < -0.03:
		_vy -= 9.8 * delta
		pos += up * maxf(_vy * delta, target)
	else:
		_vy = 0.0
		pos += up * target
	# lean to the contacts (pitch and roll), always near the local up
	var n := up
	if contacts.size() == 4:
		var byname := {}
		for i in wheels.size():
			byname[str(wheels[i][0].name).substr(6)] = contacts[i]
		if byname.size() == 4:
			n = (byname["FR"] - byname["BL"]).cross(byname["FL"] - byname["BR"]).normalized()
			if n.dot(up) < 0.0:
				n = -n
			if n.dot(up) < 0.9:
				n = up
	b = Basis(Quaternion(b.y, b.y.slerp(n, clampf(delta * 8.0, 0.0, 1.0)).normalized())) * b
	global_transform = Transform3D(b.orthonormalized(), pos)
	_lv = Vector3(0.0, 0.0, -_speed)
	_animate_car(delta)
	_carry(delta)
	if pilot:
		pilot.global_transform = Transform3D(global_transform.basis, pilot_transform().origin)
		_update_hud(0.0)


func _sweep(from: Transform3D, motion: Vector3) -> Vector3:
	## The hull swept along motion (riders, doors, seat and ramps excepted), sliding along walls;
	## a head-on hit takes the speed off.  Returns where it ends up.
	var xf := from
	var ex := _excluded()
	for attempt in 3:
		if motion.length_squared() < 1e-10:
			break
		var params := PhysicsTestMotionParameters3D.new()
		params.from = xf
		params.motion = motion
		params.exclude_bodies = ex
		params.margin = 0.02
		var res := PhysicsTestMotionResult3D.new()
		if not PhysicsServer3D.body_test_motion(get_rid(), params, res):
			xf.origin += motion
			break
		var nrm := res.get_collision_normal()
		var along := motion.normalized()
		if nrm.dot(along) > 0.05:
			xf.origin += motion                      # already touching it, and moving away: free to go
			break
		xf.origin += res.get_travel()
		var head_on := -nrm.dot(along)
		_impact(absf(_speed) * head_on, nrm, res.get_collision_point())
		_speed *= clampf(1.0 - head_on, 0.0, 1.0)
		motion = res.get_remainder().slide(nrm)
	return xf.origin


func _depth(xf: Transform3D) -> float:
	## How far the hull at xf is pushed into something (0 if it's clear).
	var params := PhysicsTestMotionParameters3D.new()
	params.from = xf
	params.motion = Vector3.ZERO
	params.exclude_bodies = _excluded()
	params.margin = 0.001
	var res := PhysicsTestMotionResult3D.new()
	if PhysicsServer3D.body_test_motion(get_rid(), params, res):
		return res.get_collision_depth()
	return 0.0


func _ground(p: Vector3, up: Vector3) -> Vector3:
	## The ground under p: a ray down through the world (roads, decks, terrain tiles), else the map.
	var q := PhysicsRayQueryParameters3D.create(p + up * 1.0, p - up * 3.0)
	q.exclude = _excluded()
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	if not hit.is_empty():
		return hit.position
	var s := StationGeo.s_of(p)
	return StationGeo.point(s, p.x, MapTerrain.elevation(s, p.x))


func _animate_car(delta: float) -> void:
	_spin_a = fmod(_spin_a - _speed / wheel_r * delta, TAU)
	for w in wheels:
		var steer: float = _steer if w[2] else 0.0
		(w[0] as Node3D).transform.basis = w[1] * Basis(Vector3.UP, steer) * Basis(Vector3.RIGHT, _spin_a)
	if steer_node:
		steer_node.transform.basis = _steer_base * Basis(Vector3.BACK, -_steer * 4.0)
	var k := clampf(absf(_speed) / maxf(max_speed, 1.0), 0.0, 1.0)
	if pilot == null and k < 0.01:
		if _motor.playing:
			_motor.stop()
		return
	if not _motor.playing:
		_motor.play(randf() * 2.0)
	_motor.pitch_scale = 0.6 + 0.9 * k
	_motor.volume_db = linear_to_db(0.25 + 0.75 * k) - 6.0


func _update_hud(_h: float) -> void:
	if _hud:
		_hud.text = "SPEED %3d km/h\n" % roundi(absf(_speed) * 3.6) + Controls.hint(
			"W/S drive / brake / reverse   A/D steer   Space handbrake   E leave seat",
			"%s drive   %s brake / reverse   %s steer   %s handbrake   %s leave seat" % [Controls.button("RT"),
				Controls.button("LT"), Controls.button("LS"), Controls.button(JOY_BUTTON_A), Controls.button(JOY_BUTTON_X)])
