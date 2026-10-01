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
## Driving is physical (research/physics/vehicle_dynamics.md): a rigid body of the vehicle type's mass
## (npc_vehicles.json "phys": mass, motor power and torque, gear, drive, drag), under the station's
## gravity, carried on a spring-damper at each wheel (a ray to the ground, plus the surface's ISO 8608
## bumps), gripping by its tyres (a simplified Pacejka curve within the friction circle, the surface's
## mu and rolling resistance), driven by an electric motor (peak torque up to its base speed, then
## peak power), slowed by drag. Collisions are the physics engine's, mass against mass; their
## delta-V makes the crash sound and the damage (RCAR thresholds). On top, for play (GTA's balance,
## not a simulator's): extra grip, yaw stability, anti-roll, traction control, a handbrake that lets
## the back step out, a little air control, and it rights itself when left on its roof.

@export var wheelbase := 2.6
@export var track := 1.6
@export var wheel_r := 0.36
@export var max_steer := 0.6         # rad at walking pace
@export var steer_rate := 1.6        # rad/s
@export var coast := 0.8             # m/s^2 rolling to a stop
@export var motor_sound := "res://remake/audio/car_motor.wav"
@export var spec := "city_car"       # the vehicle type (npc_vehicles.json) whose mass, motor and drag it has
@export var ride_hz := 1.4           # the suspension's natural frequency (cars 1.2-1.6, trucks ~2)
@export var ride_damping := 0.38     # damping ratio
@export var travel := 0.16           # m of bump travel from the resting ride height
@export var self_balance := false    # two wheels: it holds itself up (a rider balancing) until a hard crash

const CLEAR := 0.5                   # the hull's box starts this far above the ground (kerbs and slopes pass under it)
const RAMP_LAYER := 1 << 4           # the boarding ramps: only people collide with it (StationPlayer's mask)
const HULL_LAYER := 1 << 8           # the swept hull's own layer: vehicles see it, people don't (they're inside it)
const WADE := 0.45
const STEP := 0.4                    # (old kinematic drive) the most a wheel climbs in one go
const GRIP := 1.15                   # play: a little more grip than real tyres
const RAY_UP := 0.45                 # the suspension ray starts this far above the hub
const PED_LAYER := 1 << 9            # people's bodies (vehicles collide with them)
static var _specs := {}

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
var blocked_by := ""                 # what last stopped it (remake/tools/drive_test.gd reads it)
var phys := {}                       # mass_kg, power_kw, torque_nm, gear, wheel_r, top_kmh, drive, cda
var damage := 0.0                    # 0..1: structural damage (RCAR thresholds, energy-scaled)
var surface := "street"              # under the front wheels
var drowned := false                 # the water reached the tops of its wheels: it's dead (disabled)
var immersion := 0.0                 # m of water over the bottom of its wheels
var _comp: Array = []                # each wheel's last suspension compression
var _grounded := 0
var _v_prev := Vector3.ZERO
var _f_sum := Vector3.ZERO           # the forces this vehicle applied itself last tick (for delta-V)
var _flip_t := 0.0
var _handbrake := false
var drive_input := {}                # {throttle -1..1, steer -1..1, handbrake}: overrides the pilot's controls


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
	collision_mask = 1 | HULL_LAYER | PED_LAYER
	_load_spec()
	mass = float(phys.mass_kg)
	gravity_scale = 0.0                                # the station's gravity, applied by hand
	center_of_mass_mode = RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
	center_of_mass = Vector3(0, CLEAR * 0.6, 0)        # low, for play (a GTA car keeps its feet)
	contact_monitor = true
	max_contacts_reported = 6
	continuous_cd = true
	can_sleep = true
	linear_damp_mode = RigidBody3D.DAMP_MODE_REPLACE
	linear_damp = 0.0
	angular_damp_mode = RigidBody3D.DAMP_MODE_REPLACE
	angular_damp = 0.3
	freeze = false
	for ch in find_children("*", "PhysicsBody3D", true, false):
		add_collision_exception_with(ch)               # its own doors, seat, cabin walls and ramps
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
		_ramps.collision_layer = RAMP_LAYER            # people step on it; cars pass over it
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
func take_seat(p: StationPlayer) -> void:
	super(p)
	if pilot:
		mass = float(phys.get("mass_kg", 1500)) + 80.0   # the driver's weight
		sleeping = false


func leave_seat() -> void:
	super()
	mass = float(phys.get("mass_kg", 1500))


func knock(by: Node, v_by: Vector3, m_by: float) -> void:
	## Hit by another moving body: it's already dynamic, the physics engine shares the momentum.
	sleeping = false


func _load_spec() -> void:
	if _specs.is_empty():
		var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://remake/characters/npc_vehicles.json"))
		for k in d.vehicles:
			_specs[k] = d.vehicles[k].get("phys", {})
	phys = (_specs.get(spec, {}) as Dictionary).duplicate()
	if phys.is_empty():
		phys = {"mass_kg": 1500, "power_kw": 120, "torque_nm": 300, "gear": 10.0, "wheel_r": wheel_r, "top_kmh": 160, "drive": "RWD", "cda": 0.6}


func _physics_process(delta: float) -> void:
	var b := global_transform.basis
	var s := StationGeo.s_of(global_position)
	var up := StationGeo.up(s)
	var v := linear_velocity
	# parked, still and nobody about: let it sleep
	if pilot == null and _riders.is_empty() and v.length_squared() < 0.01 and _grounded == wheels.size() and wheels.size() > 0:
		var near := false
		for p in get_tree().get_nodes_in_group("player"):
			if (p as Node3D).global_position.distance_squared_to(global_position) < 900.0:
				near = true
		if not near:
			if _motor.playing:
				_motor.stop()
			sleeping = true
			return
	# what this tick's collisions did: the velocity change the vehicle's own forces don't explain
	var dv := (v - _v_prev) - _f_sum / mass * delta
	_f_sum = Vector3.ZERO
	if dv.length() > 2.0 and _v_prev.length() > 1.0:
		_hit(dv)
	_v_prev = v
	_shove_others()
	# the controls
	var thr := 0.0
	var steer_in := 0.0
	_handbrake = false
	if not drive_input.is_empty() and not disabled:   # a tool or an AI at the wheel
		thr = float(drive_input.get("throttle", 0.0))
		steer_in = float(drive_input.get("steer", 0.0))
		_handbrake = bool(drive_input.get("handbrake", false))
	elif pilot and not disabled:
		thr = clampf(Input.get_action_strength("move_forward") + Input.get_action_strength("accelerate")
			- Input.get_action_strength("move_back") - Input.get_action_strength("brake_reverse"), -1.0, 1.0)
		steer_in = Input.get_action_strength("move_right") - Input.get_action_strength("move_left")
		_handbrake = Input.is_action_pressed("jump")
	if absf(thr) > 0.02 or absf(steer_in) > 0.02:
		sleeping = false                               # a sleeping body ignores forces
	var fwd := -b.z
	var vf := v.dot(fwd)
	_speed = vf
	_steer = move_toward(_steer, -steer_in * max_steer / (1.0 + absf(vf) / 12.0), steer_rate * delta)
	# the station's gravity
	var g_here := StationGeo.gravity_at(Vector2(global_position.y, global_position.z).length())
	_apply(-up * g_here * mass, Vector3.ZERO)
	# wheels: suspension, then tyres
	var n_w := maxi(1, wheels.size())
	var m_corner := mass / n_w
	var k := m_corner * pow(TAU * ride_hz, 2.0)
	var c := 2.0 * ride_damping * sqrt(k * m_corner)
	var x0 := m_corner * 9.81 / k                      # the static compression
	var r: float = float(phys.get("wheel_r", wheel_r))
	var drive: String = phys.get("drive", "RWD")
	var driven := 0
	for w in wheels:
		if drive == "AWD" or (drive == "FWD" and w[2]) or (drive == "RWD" and not w[2]):
			driven += 1
	var top := float(phys.get("top_kmh", 160.0)) / 3.6
	var p_max := float(phys.get("power_kw", 100.0)) * 1000.0 * (1.0 - 0.6 * damage)
	var f_max := float(phys.get("torque_nm", 300.0)) * float(phys.get("gear", 10.0)) / r
	var f_motor := 0.0
	if absf(thr) > 0.02:
		var forward_cmd := thr > 0.0
		var reversing := not forward_cmd and vf < 0.5
		if forward_cmd and vf > -0.5 or reversing:
			f_motor = thr * minf(f_max, p_max / maxf(absf(vf), 0.5))
			if (forward_cmd and vf > top) or (reversing and vf < -reverse_speed):
				f_motor = 0.0
	var braking := (thr > 0.02 and vf < -0.5) or (thr < -0.02 and vf > 0.5)
	if _comp.size() != wheels.size():
		_comp.resize(wheels.size())
		_comp.fill(x0)
	_grounded = 0
	var front_surface := ""
	for i in wheels.size():
		var w: Array = wheels[i]
		var hub: Vector3 = global_transform * Vector3(w[3], _local(w[0]).origin.y, _local(w[0]).origin.z)
		var from := hub + b.y * RAY_UP
		var q := PhysicsRayQueryParameters3D.create(from, from - b.y * (RAY_UP + r + travel + x0 + 0.3), 1)
		q.exclude = _excluded()
		var hit := get_world_3d().direct_space_state.intersect_ray(q)
		var gp: Vector3
		var gn: Vector3 = up
		if hit.is_empty():
			var ps := StationGeo.s_of(hub)
			gp = StationGeo.point(ps, hub.x, MapTerrain.elevation(ps, hub.x))
			if (from - gp).dot(b.y) > RAY_UP + r + travel + x0 + 0.3:
				_comp[i] = 0.0
				continue
		else:
			gp = hit.position
			gn = hit.normal
		var flat := Vector2(StationGeo.s_of(gp), gp.x)
		var surf := RoadSurface.at(flat) if i % 2 == 0 or front_surface == "" else front_surface
		if w[2] and front_surface == "":
			front_surface = surf
		var sp := RoadSurface.props(surf)
		var dist := (from - gp).dot(b.y) - RoadSurface.bump(flat, surf)
		var comp := clampf(RAY_UP + r + x0 - dist, 0.0, x0 + travel + 0.2)
		if comp <= 0.0:
			_comp[i] = 0.0
			continue
		_grounded += 1
		var dcomp := (comp - float(_comp[i])) / delta
		_comp[i] = comp
		var fz := maxf(0.0, k * comp + c * dcomp)
		if comp > x0 + travel:                         # the bump stop
			fz += k * 8.0 * (comp - x0 - travel)
		var contact := gp
		_apply(gn * fz, contact - global_position)
		# the tyre, in the contact plane
		var steer: float = _steer if w[2] else 0.0
		var wf := (-b.z).rotated(b.y, steer)
		wf = (wf - gn * wf.dot(gn)).normalized()
		var ws := gn.cross(wf).normalized()
		var vc := v + angular_velocity.cross(contact - (global_transform * center_of_mass))
		var vl := vc.dot(wf)
		var vs := vc.dot(ws)
		var mu: float = float(sp[0]) * GRIP * (1.0 - 0.3 * damage) * (0.6 if immersion > 0.05 else 1.0)   # a wet, soft bed
		var lat_mu := mu * (0.35 if _handbrake and not w[2] else 1.0)
		var alpha := atan2(vs, maxf(absf(vl), 1.5))
		var fy := -lat_mu * fz * sin(1.4 * atan(9.0 * alpha))
		if absf(vl) < 1.5:                             # at a crawl: no sideways creep
			fy = clampf(-vs * m_corner * 6.0, -lat_mu * fz, lat_mu * fz)
		var fx := 0.0
		if (drive == "AWD" or (drive == "FWD" and w[2]) or (drive == "RWD" and not w[2])) and driven > 0:
			fx += f_motor / driven
		fx -= float(sp[1]) * fz * signf(vl)            # rolling resistance
		if braking or (_handbrake and not w[2]):
			fx = -signf(vl) * mu * fz * 0.9 if absf(vl) > 0.3 else -vl * m_corner * 4.0
		elif absf(thr) < 0.02 and absf(vl) < 0.3 and pilot != null:
			fx = -vl * m_corner * 4.0                  # holding still
		# traction control and the friction circle
		var lim := mu * fz
		fx = clampf(fx, -lim, lim)
		var tot := Vector2(fx, fy)
		if tot.length() > lim:
			tot = tot.normalized() * lim
		_apply(wf * tot.x + ws * tot.y, contact - global_position)
	if front_surface != "":
		surface = front_surface
	# drag
	_apply(-v * v.length() * 0.5 * 1.2 * float(phys.get("cda", 0.6)), Vector3.ZERO)
	_water(v, up, r, delta)
	# play: stability, anti-roll, air control, righting itself
	var wv := angular_velocity
	if _grounded > 0:
		if absf(steer_in) < 0.1 and not _handbrake:
			apply_torque(-b.y * wv.dot(b.y) * mass * 0.8)
		apply_torque(-fwd * wv.dot(fwd) * mass * 1.5)
	else:
		apply_torque(-b.y * steer_in * mass * 0.6 + b.x * thr * mass * 0.4)
	if self_balance and not disabled:
		var lean_target := up.rotated(fwd, clampf(-vf * _yaw_rate / 9.81, -0.5, 0.5))
		var err := b.y.cross(lean_target)
		apply_torque((err * 30.0 - wv * 4.0) * mass)
	if b.y.dot(up) < 0.3 and v.length() < 2.0:
		_flip_t += delta
		if _flip_t > 2.0:
			_flip_t = 0.0
			var lev := Basis(Quaternion(b.y, up)) * b
			global_transform = Transform3D(lev.orthonormalized(), global_position + up * 1.2)
			linear_velocity = Vector3.ZERO
			angular_velocity = Vector3.ZERO
	else:
		_flip_t = 0.0
	# the old readouts and riders
	_yaw_rate = wv.dot(b.y)
	_lv = b.inverse() * v
	_animate_car(delta)
	_carry(delta)
	if pilot:
		pilot.global_transform = Transform3D(global_transform.basis, pilot_transform().origin)
		_update_hud(0.0)


func _apply(f: Vector3, at: Vector3) -> void:
	apply_force(f, at)
	_f_sum += f


func _water(v: Vector3, up: Vector3, r: float, delta: float) -> void:
	## The rivers, lake and seas. Wading slows it (the water's drag on what's under the surface, and
	## a soft bed); once the water is up to the tops of its wheels it is drowned -- dead, like a real
	## EV whose motors and pack are under -- unless it is built for the water (phys.amphibious:
	## boats, submersibles, amphibians). A drowned vehicle sinks and stays.
	var p := global_position
	var s := StationGeo.s_of(p)
	var wa := MapTerrain.water_at(s, p.x)
	var was := immersion
	immersion = maxf(0.0, wa.x - StationGeo.h_of(p)) if wa.x > -9000.0 else 0.0
	if immersion <= 0.0:
		return
	if was <= 0.0 and -v.dot(up) > 3.0:
		_impact(-v.dot(up), up, p)                     # the splash of going in hard
	var amphibious := bool(phys.get("amphibious", false))
	# the drag of the water on the submerged frontal area: Cd ~1 over the width, to the waterline
	var deep := minf(immersion, float(phys.get("height_m", 1.5)))
	var vh := v - up * v.dot(up)
	_apply(-vh * vh.length() * 0.5 * 1000.0 * float(phys.get("width_m", 1.8)) * deep, Vector3.ZERO)
	if amphibious:
		return
	if immersion >= 2.0 * r and not drowned:
		drowned = true
		disabled = true
		_handbrake = false
		if _motor.playing:
			_motor.stop()
	if drowned:
		linear_velocity = linear_velocity.move_toward(Vector3.ZERO, 3.0 * delta)


func _hit(dv: Vector3) -> void:
	## A collision's delta-V: the crash sound from 10 km/h, damage from 15 (RCAR), energy-scaled.
	var kmh := dv.length() * 3.6
	_impact(dv.length(), -dv.normalized(), global_position)
	if kmh > DAMAGE_KMH:
		damage = clampf(damage + (kmh * kmh - DAMAGE_KMH * DAMAGE_KMH) / (WRECK_KMH * WRECK_KMH - DAMAGE_KMH * DAMAGE_KMH), 0.0, 1.0)
		if damage >= 1.0:
			disabled = true


func _shove_others() -> void:
	## Whatever it's touching that is held still by its own logic (a driven car, a person, a sign)
	## gets the hit: it lets go to the physics with its share of the momentum (Physics.knock).
	for o in get_colliding_bodies():
		if o is Node and (o as Node).has_method("knock"):
			o.knock(self, _v_prev, mass)


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
		if head_on > 0.3:
			var hit := res.get_collider()
			blocked_by = "hull: %s" % (str((hit as Node).get_path()) if hit is Node else str(res.get_collider_rid()))
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
	var q := PhysicsRayQueryParameters3D.create(p + up * 1.0, p - up * 3.0, 1)     # the world: not a parked van's boarding ramp
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
		var state := ""
		if drowned:
			state = "   DROWNED -- the water reached the tops of the wheels"
		elif disabled:
			state = "   WRECKED"
		elif immersion > 0.05:
			state = "   WADING %.1f m" % immersion
		_hud.text = "SPEED %3d km/h%s\n" % [roundi(absf(_speed) * 3.6), state] + Controls.hint(
			"W/S drive / brake / reverse   A/D steer   Space handbrake   E leave seat",
			"%s drive   %s brake / reverse   %s steer   %s handbrake   %s leave seat" % [Controls.button("RT"),
				Controls.button("LT"), Controls.button("LS"), Controls.button(JOY_BUTTON_A), Controls.button(JOY_BUTTON_X)])
