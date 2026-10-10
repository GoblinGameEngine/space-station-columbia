extends VehicleBody3D
class_name NpcCarBody

## An NPC vehicle's body (NpcTraffic): a box of its type's size and mass.
##
## Near the player it DRIVES (the user, 2026-10-09: "Their cars need to use driving physics and follow the roads and
## obey the road signs"): a VehicleBody3D -- the engine's raycast vehicle, native: a spring-damper at each of its four
## wheels, tyre friction within the friction circle (the road's grip), engine force, brakes -- under the station's
## gravity and the air's drag. Its driver (RoadDriver: the signs, signals, junctions, the car ahead, by Ohio's rules and
## their own traits) decides how hard to accelerate or brake; the chauffeur here turns that into engine force and
## brake, and steers its front axle onto the route in the driver's lane (Stanley's controller: passing, pulling over).
## Where the car really is along its route is read back from where the physics put it (NpcTraffic._drive). (The first
## cut did the tyres in GDScript, as RemakeGroundVehicle does for the one car the player drives: 0.12 ms a car a tick,
## and 29 of them at a rush hour sent the frame rate into a spiral.)
##
## Farther off, nobody sees it: it is frozen (kinematic) and placed along the route (the fake that keeps 100 cars a
## frame cheap). Parked, it is frozen too. Hit hard by something moving while frozen, it lets go to the physics with
## its share of the momentum -- a 1-D collision along the line between the two, by their masses (restitution 0.2:
## cars crumple, they don't bounce) -- and from then on it's a wreck, until it's left behind. A driven car hit hard
## (a change of speed its own forces don't explain) is a wreck too: the driver brakes and stays put.

const RESTITUTION := 0.2
const KNOCK_MS := 1.0                # closing speed (m/s) that's more than a nudge
const SHRUG_MS := 1.5                # its own change of speed (m/s) below which it carries on driving
const CLEAR := 0.32                  # its box starts this far above the ground: kerbs and humps pass under it
const GRIP := 1.1                   # the tyres' friction (VehicleWheel3D.wheel_friction_slip)
const RIDE := 0.1                    # m: the springs' static compression (a 1.6 Hz ride)
const TRAVEL := 0.18
const REST := 0.22                   # m: the wheel's attachment above its hub at rest
const ENGINE_SIGN := -1.0            # (VehicleBody3D drives along +z; these cars' noses are -z)
const MAX_STEER := 0.68              # rad (~39 degrees at the wheel)
const STEER_RATE := 2.2              # rad/s
const CRASH_DV := 3.0                # m/s in a tick, along the ground: a jolt this big ends the drive

var traffic: Node
var entry_id := ""
var v_now := Vector3.ZERO            # its velocity while driven (frozen: the route's)
var crashed := false

# driving (set by NpcTraffic)
var driving := false                 # true: the physics drives it (else frozen and placed)
var sim: RoadDriver                  # its driver
var phys := {}                       # the type's mass_kg, power_kw, torque_nm, gear, top_kmh, drive, cda
var half_wb := 1.25                  # half the wheelbase
var half_tr := 0.75                  # half the track
var wheel_r := 0.34
var want_acc := 0.0                  # m/s^2: the driver's last decision
var hard_stop := false               # the driver wants it stood still now (an obstacle right ahead)
var speed := 0.0                     # m/s along its nose (the wheels' spin)
var _steer_to := 0.0
var _steer_t := 0.0
var _v_prev := Vector3.ZERO


func _ready() -> void:
	freeze_mode = RigidBody3D.FREEZE_MODE_KINEMATIC
	freeze = true
	gravity_scale = 0.0
	can_sleep = true
	contact_monitor = true
	max_contacts_reported = 4
	var pm := PhysicsMaterial.new()
	pm.friction = 0.7
	pm.bounce = 0.1
	physics_material_override = pm
	linear_damp_mode = RigidBody3D.DAMP_MODE_REPLACE
	linear_damp = 0.0
	angular_damp_mode = RigidBody3D.DAMP_MODE_REPLACE
	angular_damp = 0.5
	# the wheels: the engine's raycast suspension (per unit of the body's mass: 4 x stiffness x RIDE = g)
	var drive := str(phys.get("drive", "RWD"))
	for c: Vector2 in [Vector2(-half_tr, -half_wb), Vector2(half_tr, -half_wb), Vector2(-half_tr, half_wb), Vector2(half_tr, half_wb)]:
		var front := c.y < 0.0
		var w := VehicleWheel3D.new()
		w.position = Vector3(c.x, wheel_r + REST, c.y)
		w.wheel_radius = wheel_r
		w.wheel_rest_length = REST + RIDE
		w.suspension_travel = TRAVEL
		w.suspension_stiffness = 9.81 / (4.0 * RIDE)
		w.damping_compression = 1.9
		w.damping_relaxation = 2.4
		w.suspension_max_force = mass * 9.81 * 2.0
		w.wheel_friction_slip = GRIP
		w.wheel_roll_influence = 0.05
		w.use_as_steering = front
		w.use_as_traction = drive == "AWD" or (drive == "FWD") == front
		add_child(w)
		_wheels.append(w)


var _wheels: Array[VehicleWheel3D] = []


func start_driving(v0: float) -> void:
	## From frozen and placed to the physics, rolling at v0 along its nose (no faster than the bend ahead allows).
	if driving:
		return
	if sim != null:
		v0 = minf(v0, sim.bend_speed(sim.t, 30.0))
		sim.v = v0
	driving = true
	freeze = false
	sleeping = false
	can_sleep = false
	linear_velocity = -global_transform.basis.z * v0
	angular_velocity = Vector3.ZERO
	_v_prev = linear_velocity
	steering = 0.0
	_settle = 0.5                                        # (its first ticks on its own wheels aren't a crash)


func stop_driving() -> void:
	## Back to frozen (far from the player, or parked again).
	if not driving:
		return
	driving = false
	if not crashed:
		freeze = true
	can_sleep = true
	engine_force = 0.0
	brake = 0.0
	linear_velocity = Vector3.ZERO
	angular_velocity = Vector3.ZERO


func knock(by: Node, v_by: Vector3, m_by: float) -> void:
	if crashed or not (by is Node3D) or driving:
		return                                       # (driven: the physics engine has the collision itself)
	var n := (global_position - (by as Node3D).global_position)
	n = n.normalized() if n.length() > 0.01 else Vector3.FORWARD
	var u1 := v_by.dot(n)
	var u2 := v_now.dot(n)
	if u1 - u2 < KNOCK_MS:
		return
	var m1 := m_by
	var m2 := mass
	var u2p := (m1 * u1 + m2 * u2 + m1 * RESTITUTION * (u1 - u2)) / (m1 + m2)
	var u1p := (m1 * u1 + m2 * u2 - m2 * RESTITUTION * (u1 - u2)) / (m1 + m2)
	if absf(u2p - u2) < SHRUG_MS:
		return                                       # a truck nudging a parked car: it drives on (and pushes it)
	crashed = true
	freeze = false
	linear_velocity = v_now + n * (u2p - u2)
	# an off-centre hit sets it turning
	var up := global_transform.basis.y
	angular_velocity = up * (n.cross(global_transform.basis.z).dot(up)) * (u2p - u2) * 0.25
	if by is RigidBody3D:
		(by as RigidBody3D).linear_velocity = v_by + n * (u1p - u1)
	if traffic and traffic.has_method("on_crash"):
		traffic.on_crash(entry_id)


func interact(by: Node = null) -> String:
	## Parked: get in and drive it (the user, 2026-10-09: "the ability to enter parked cars and drive them"). The traffic
	## hands it over as the full drivable body of its type (NpcTraffic.take_over); a car on the move, or a wreck, isn't
	## anyone's to take.
	if driving or sim != null or crashed or not (by is StationPlayer) or traffic == null:
		return ""
	return traffic.take_over(entry_id, by)


func interact_prompt() -> String:
	return "Get in" if not driving and sim == null and not crashed else ""


func _physics_process(delta: float) -> void:
	if freeze or sleeping:
		return
	var up := StationGeo.up(StationGeo.s_of(global_position))
	apply_central_force(-up * StationGeo.gravity_at(Vector2(global_position.y, global_position.z).length()) * mass)
	var v := linear_velocity
	# a jolt along the ground that its tyres can't make (they brake at ~8 m/s^2: 0.13 m/s a tick): hit, or it hit
	# something -- the drive is over
	var dv := v - _v_prev
	dv -= up * dv.dot(up)
	_v_prev = v
	_settle = maxf(0.0, _settle - delta)
	var was_v := _v_prev_speed
	_v_prev_speed = v.length()
	# (a bump in a queue at a crawl -- into the car ahead, a stood car -- isn't a crash: it was going under BUMP_MS)
	if driving and not crashed and dv.length() > CRASH_DV and _settle <= 0.0 and was_v > BUMP_MS:
		crashed = true
		var what: Array = []
		for o in get_colliding_bodies():
			what.append(str((o as Node).name))
		print("NpcCarBody: %s crashed (a %.1f m/s jolt at %.1f m/s) into %s" % [entry_id, dv.length(), v.length(), str(what)])
		for o in get_colliding_bodies():
			if o is StaticBody3D:
				var owner_n: Node = o
				while owner_n.get_parent() != null and not (owner_n.get_parent() is Window) and str(owner_n.name).begins_with("@"):
					owner_n = owner_n.get_parent()
				var gp := global_position
				TrafficReports.file("crash_static", Vector2(StationGeo.s_of(gp), gp.x), "driven into %s at %.0f km/h" % [
					str(owner_n.get_path()).get_file(), was_v * 3.6], entry_id)
				break
		if traffic and traffic.has_method("on_crash"):
			traffic.on_crash(entry_id)
	if not driving and not crashed:
		return
	Prof.begin("carbody.drive")
	_chauffeur(delta, v)
	Prof.end("carbody.drive")


func _chauffeur(delta: float, v: Vector3) -> void:
	## The driver's decision as engine force and brake; the wheel turned for the route (20 times a second), eased.
	var b := global_transform.basis
	var vf := v.dot(-b.z)
	speed = vf
	var acc := want_acc if driving and not crashed else -8.0
	if driving and not crashed and sim != null:
		_steer_t -= delta
		if _steer_t <= 0.0:
			_steer_t = 0.05
			_steer_to = _pursuit(vf)
			_bend_t -= 1
			if _bend_t <= 0:
				_bend_t = 2                                # (10 times a second)
				_bend_v = sim.bend_speed(sim.t, 4.0 + vf * vf / 8.0)
		if vf > _bend_v:
			acc = minf(acc, -clampf((vf - _bend_v) * 3.0, 1.5, 8.0))     # (the bend ahead: slower, now)
	else:
		_steer_to = 0.0
	steering = move_toward(steering, _steer_to, STEER_RATE * delta)
	if absf(_steer_to) >= MAX_STEER and vf > 2.5:
		acc = minf(acc, -2.5)                          # (on full lock and still off the line: slower, as a driver would)
	var hold := crashed or hard_stop or (acc <= 0.3 and absf(vf) < 0.4)        # (no creeping up in a queue)
	var cda := float(phys.get("cda", 0.7))
	apply_central_force(-v * v.length() * 0.6 * cda)   # the air
	if hold:
		engine_force = 0.0
		brake = mass * 9.0 * delta / 4.0               # (the brake is an impulse a wheel a tick: VehicleWheel3D)
		# stood still: the parking brake -- frozen where it is till its driver goes again (wake). The engine's raycast
		# wheels let a braked car creep sideways down a camber or a hill, ~5 cm a second
		if absf(vf) < 0.15 and not crashed:
			_still += delta
			if _still > 0.6:
				freeze = true
				linear_velocity = Vector3.ZERO
				angular_velocity = Vector3.ZERO
		return
	_still = 0.0
	if acc > 0.0:
		var top := float(phys.get("top_kmh", 120.0)) / 3.6
		var r := wheel_r
		var f_max := float(phys.get("torque_nm", 300.0)) * float(phys.get("gear", 10.0)) / r
		var p_max := float(phys.get("power_kw", 100.0)) * 1000.0
		var f := mass * acc + 0.6 * cda * vf * absf(vf) + 0.012 * mass * 9.81
		f = clampf(f, 0.0, minf(f_max, p_max / maxf(absf(vf), 0.5))) if vf < top else 0.0
		var n := 0
		for w in _wheels:
			if w.use_as_traction:
				n += 1
		for w in _wheels:
			w.engine_force = ENGINE_SIGN * f / maxi(n, 1) if w.use_as_traction else 0.0
		brake = 0.0
	else:
		engine_force = 0.0
		for w in _wheels:
			w.engine_force = 0.0
		brake = mass * -acc * delta / 4.0


var _settle := 0.0
var _v_prev_speed := 0.0
const BUMP_MS := 2.5
var _still := 0.0
var _bend_t := 0
var _bend_v := INF


func wake() -> void:
	## Off the parking brake (NpcTraffic, once its driver wants to go).
	if driving and freeze and not crashed:
		freeze = false
		sleeping = false
		_still = 0.0
		_v_prev = Vector3.ZERO
		_settle = 0.3


func _pursuit(vf: float) -> float:
	## The wheel angle that keeps its front axle on the route, in the driver's lane (Stanley's controller: the heading
	## error, plus the cross-track error over the speed). (Pure pursuit, aiming at a point up the road, cut every
	## corner -- a van turning into 121th St climbed the car parked on it, 2026-10-09.)
	var b := global_transform.basis
	var fa := global_position - b.z * half_wb
	var at := Vector2(StationGeo.s_of(fa), fa.x)
	var t := sim.t + half_wb
	for k in 2:                                               # (the route's point abreast the front axle)
		var a0 := sim.pos_at(t)
		var d0 := sim.dir_at(t)
		t += clampf(Vector2(StationGeo.wrap_ds(at.x - a0.x), at.y - a0.y).dot(d0), -6.0, 6.0)
	var d := sim.dir_at(t)
	var right := Vector2(-d.y, d.x)
	var p := sim.pos_at(t) + right * sim.lat
	var rel := Vector2(StationGeo.wrap_ds(at.x - p.x), at.y - p.y)
	var e := rel.dot(right)                                   # m right of where it should be
	var f := -b.z
	var hd := Vector2(f.dot(StationGeo.forward(at.x)), f.x)
	var psi := -hd.angle_to(d)                                # + : the road turns left of its nose
	# ((s, x) is left-handed against the world's turn: +x is to the right of +s, so angle_to's sign flips)
	var st := psi + atan2(1.6 * e, absf(vf) + 1.5)              # (right of it: steer left)
	return clampf(st, -MAX_STEER, MAX_STEER)
