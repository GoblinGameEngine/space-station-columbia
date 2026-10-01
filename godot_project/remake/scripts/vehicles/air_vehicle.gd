extends RigidBody3D
class_name RemakeAirVehicle

## A flyable air vehicle -- the template every vehicle of this kind follows.  A subclass gives the
## model (MODEL, a .glb from remake/blender/vehicles) and its hull (_build_hull); everything else
## comes from the model's rig, found by name:
##   engine_<name>         tilting thrust units (rotate about local X; + tilt = thrust forward)
##   engine_<name>/rotor_* their rotors (spin about local Y)
##   door_<side><n>        sliding door leaves: a side's leaves open and close together (E, like any
##                         door in a building -- in flight too); they slide along local Z,
##                         <n> odd toward -Z (the nose), even toward +Z
##   seat_pilot            where the pilot sits (E on it: take the controls; E again: stand up)
##   exit_<side>           outside each doorway
##
## Controls (the player's own actions, so every vehicle flies the same):
##   move_forward / move_back   thrust forward / back (the engines tilt)
##   move_left / move_right     turn (the two sides' engines tilt opposite ways) -- no sideslip
##   jump / swim_down           climb / descend
##   interact                   leave the pilot's seat
## It always stands upright to the station's central axis, like everything else on the floor: each
## tick its up is re-levelled to the local up, so flying round the ring it stays level with the
## floor below.  Altitude is capped at ceiling_h.  With no pilot it holds where it is (lift
## carries its weight).  Flight is kinematic: the hull is
## swept against the world each tick (bodies inside the cabin excepted), sliding along what it hits.
## Anyone standing in the cabin is carried: the vehicle sets their carrier_velocity each tick.
##
## Collisions (research/physics/vehicle_physics.md): a hit whose speed into the surface reaches
## CRASH_KMH (10 km/h, the RCAR bumper test) plays the crash sound, louder and deeper the harder
## it is -- for every vehicle.  With crash_physics on (the aerostat) a crash also bounces it off,
## sets it swinging under its balloon and yawing, costs the pilot control for a moment, and past
## DAMAGE_KMH (15 km/h, the RCAR structural test) damages it by the energy above that; at no hull
## left it is disabled: the fans stop and it sinks to the ground.  A touchdown on the casters at up
## to GEAR_MS (10 ft/s, 14 CFR 23.473) is a landing, not a crash.

@export var max_speed := 15.0        # m/s forward
@export var reverse_speed := 5.0
@export var accel := 2.5             # m/s^2 toward the commanded speed
@export var brake := 3.5             # m/s^2 when there's no thrust command
@export var climb_speed := 5.0
@export var climb_accel := 2.5
@export var turn_rate := 0.6         # rad/s
@export var turn_accel := 1.2
@export var side_damp := 3.0         # m/s^2: sideslip bleeds off
@export var max_tilt := 0.6          # rad, engine tilt at full command
@export var tilt_rate := 1.2         # rad/s
@export var ceiling_h := 350.0       # m above the floor: the highest it will fly
@export var cabin_box := AABB(Vector3(-1.2, 0.0, -1.8), Vector3(2.4, 2.5, 3.6))   # local: who's aboard
@export var seat_eye := 0.72         # m from seat_pilot up to the pilot's eye node origin
@export var seat_forward := 0.0      # m the pilot's eye sits ahead of seat_pilot (toward the nose)
@export var stand_point := Vector3.ZERO   # local: where the pilot stands on leaving the seat

var model: Node3D
var pilot: StationPlayer
var engines: Array = []              # [Node3D engine, Node3D rotor or null, side +1 left / -1 right]
var doors: Array = []                # RemakeSlideDoor
var seat_pilot: Node3D
var _lv := Vector3.ZERO              # velocity in the vehicle's own frame (x right, y up, -z forward)
var _yaw_rate := 0.0
var _spin := 0.0
var _riders: Array = []
var _hud: Label
var _engine_sounds: Array = []
var _seat_local := Vector3.ZERO

const CRASH_KMH := 10.0              # the crash sound from here up (RCAR bumper test speed)
const DAMAGE_KMH := 15.0             # structural damage from here up (RCAR structural test speed)
const WRECK_KMH := 60.0              # one hit this hard wrecks it (damage goes with the energy, v^2)
const GEAR_MS := 3.05                # a touchdown this fast on the casters is only a landing
const RESTITUTION := 0.35            # the rebound: most of the energy goes into the hull and fabric
const PENDULUM_W := 1.8              # rad/s: the cabin swinging under the balloon, sqrt(g / 3 m)
const SWING_DAMP := 0.25             # its damping ratio
@export var crash_physics := false
@export var floats := false          # it rides on water (the aerostat's gondola is a hull); else water is no floor
@export var float_draft := 0.3       # m it sits in the water at rest
const SPLASH_DOWN_MS := 3.05         # a touchdown on water up to this sink rate (as on the casters) ...
const SPLASH_FWD_MS := 8.0           # ... and this forward speed is a landing; faster is a crash: disabled
var afloat := false
var swamped := false                 # the water came over the engines: disabled
var _engine_h := INF                 # m above the origin: the top of the lowest engine (water past it swamps them)
@export var com_height := 1.5        # m above the local origin: the centre of mass
var hull := 100.0                    # % left
var disabled := false
var _stun := 0.0                     # s the pilot has lost control for
var _wob := Vector3.ZERO             # the crash swing: a rotation vector (world), applied over the level attitude
var _wob_w := Vector3.ZERO
var _last_crash := -1000
var _crash_sound: AudioStreamPlayer3D


func _ready() -> void:
	# a rigid body: the air vehicles stay frozen and are moved by their own flight code (as an
	# AnimatableBody would be); ground vehicles unfreeze and drive by forces (RemakeGroundVehicle)
	freeze_mode = RigidBody3D.FREEZE_MODE_KINEMATIC
	freeze = true
	process_physics_priority = -10                     # before the players it carries
	_build_hull()
	_rig()
	_ranges()
	# the engines' sound: one looped emitter at each engine, pitched and loudened with the rotors
	var snd: AudioStreamWAV = load("res://remake/audio/aerostat_engine.wav")
	snd.loop_mode = AudioStreamWAV.LOOP_FORWARD
	snd.loop_end = snd.data.size() / 2
	for e in engines:
		var p := AudioStreamPlayer3D.new()
		p.name = "engine_sound"
		p.stream = snd
		p.unit_size = 6.0
		p.max_distance = 400.0
		p.volume_db = -80.0
		(e[0] as Node3D).add_child(p)
		_engine_sounds.append(p)


func _build_hull() -> void:
	pass


func load_model(path: String) -> void:
	model = (load(path) as PackedScene).instantiate()
	model.name = "Model"
	add_child(model)


const DETAIL_R := 150.0               # interior, doors and rotors draw within this
const BODY_R := 1000.0               # the cabin, fans and rigging within this; the balloon everywhere


func _ranges() -> void:
	## Draw distances: the insides only near, the hull further, the envelope from anywhere.
	for m in find_children("*", "GeometryInstance3D", true, false):
		var gi := m as GeometryInstance3D
		var nm := str(gi.name)
		if nm == "balloon":
			continue
		var fine := nm.begins_with("interior") or nm.begins_with("door_") or nm.begins_with("rotor_") or nm.ends_with("glass")
		gi.visibility_range_end = DETAIL_R if fine else BODY_R
		gi.visibility_range_end_margin = gi.visibility_range_end * 0.1


func _rig() -> void:
	for n in model.find_children("engine_*", "", true, false):
		var rotor: Node3D = null
		for c in n.get_children():
			if str(c.name).begins_with("rotor_"):
				rotor = c
		engines.append([n, rotor, 1.0 if _local(n).origin.x < 0.0 else -1.0])
	seat_pilot = model.find_child("seat_pilot", true, false)
	if seat_pilot:
		_seat_local = _local(seat_pilot).origin
	var by_side := {}
	for n in model.find_children("door_*", "", true, false):
		if not n is MeshInstance3D:
			continue
		var tag := str(n.name).substr(5)                 # "R1"
		var d := RemakeSlideDoor.new()
		d.name = "DoorBody_" + tag
		d.sync_to_physics = false                      # else the physics state overwrites the placement below
		add_child(d)
		d.transform = _local(n)
		n.get_parent().remove_child(n)
		d.add_child(n)
		(n as Node3D).transform = Transform3D.IDENTITY
		var ab: AABB = (n as MeshInstance3D).get_aabb()
		var cs := CollisionShape3D.new()
		var box := BoxShape3D.new()
		box.size = ab.size.max(Vector3(0.06, 0.06, 0.06))
		cs.shape = box
		cs.position = ab.get_center()
		d.add_child(cs)
		var odd := int(tag.substr(1)) % 2 == 1
		d.setup(Vector3(0, 0, -1.0 if odd else 1.0) * door_slide())
		doors.append(d)
		if not by_side.has(tag[0]):
			by_side[tag[0]] = []
		by_side[tag[0]].append(d)
	for side in by_side:
		for d in by_side[side]:
			for o in by_side[side]:
				if o != d:
					d.partners.append(o)
	# each doorway: aim the use key anywhere in it -- the doors open or shut, from inside or out --
	# to work that side's doors (not only at a leaf, which slides out of reach when open)
	for side in by_side:
		var box := AABB()
		for i in by_side[side].size():
			var d: RemakeSlideDoor = by_side[side][i]
			var leaf := d.get_child(0) as MeshInstance3D
			var bb: AABB = d.transform * leaf.get_aabb()
			box = bb if i == 0 else box.merge(bb)
		var leaves: Array = by_side[side]
		var z := RemakeInteractZone.make(self, "Doorway_" + str(side), Transform3D(Basis(), box.get_center()),
			box.size + Vector3(0.8, 0.0, 0.0),
			func(by: Node) -> String: return (leaves[0] as RemakeSlideDoor).interact(by),
			func() -> String: return (leaves[0] as RemakeSlideDoor).interact_prompt())
		z.gives_way = true
	# the controls: the steering wheel (or, with none, the panel ahead of the pilot's seat) takes the
	# seat as well as the seat itself does
	var wheel := model.find_child("steering_wheel", true, false) as Node3D
	var at := Transform3D(Basis(), _local(wheel).origin) if wheel else Transform3D(Basis(), _seat_local + Vector3(0, 0.6, -0.6))
	if wheel or seat_pilot:
		RemakeInteractZone.make(self, "Controls", at, Vector3(0.55, 0.45, 0.35), _controls_used, _controls_prompt)
	if seat_pilot:
		var seat := RemakeVehicleSeat.new()
		seat.name = "PilotSeat"
		seat.vehicle = self
		add_child(seat)
		seat.position = _local(seat_pilot).origin + Vector3(0, 0.2, 0)
		var cs := CollisionShape3D.new()
		var box := BoxShape3D.new()
		box.size = Vector3(0.5, 0.5, 0.5)
		cs.shape = box
		seat.add_child(cs)


func _controls_used(by: Node) -> String:
	if by is StationPlayer and pilot == null:
		take_seat(by)
		return "seated"
	return ""


func _controls_prompt() -> String:
	return ("Drive" if self is RemakeGroundVehicle else "Take the controls") if pilot == null else ""


func _local(n: Node3D) -> Transform3D:
	## A rig node's transform in the vehicle's own frame.
	return global_transform.affine_inverse() * n.global_transform


func door_slide() -> float:
	return 0.6


func add_box(size: Vector3, at: Vector3, roll := 0.0) -> void:
	## A box of the hull; roll (about local Z) tilts it, e.g. into a boarding ramp.
	var cs := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	cs.shape = box
	cs.position = at
	cs.rotation.z = roll
	add_child(cs)


func add_sphere(r: float, at: Vector3) -> void:
	var cs := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = r
	cs.shape = sph
	cs.position = at
	add_child(cs)


func add_cylinder(r: float, h: float, at: Vector3) -> void:
	var cs := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = r
	cyl.height = h
	cs.shape = cyl
	cs.position = at
	add_child(cs)


# ------------------------------------------------------------------ the pilot
func take_seat(p: StationPlayer) -> void:
	if pilot or p == null:
		return
	pilot = p
	p.sit_in(self)
	_show_hud(true)


func leave_seat() -> void:
	if pilot == null:
		return
	var p := pilot
	pilot = null
	p.stand_up(global_transform * stand_point, global_transform.basis)
	_show_hud(false)


func pilot_transform() -> Transform3D:
	## Where the seated pilot's body goes: on the seat, facing the nose.
	return global_transform * Transform3D(Basis(), _seat_local + Vector3(0, seat_eye, -seat_forward))


# ------------------------------------------------------------------ flight
func _physics_process(delta: float) -> void:
	# parked and still, with nobody near: nothing to do (dozens of these stand about the map)
	if pilot == null and _lv.length_squared() < 1e-6 and absf(_yaw_rate) < 1e-5 and _spin == 0.0 and _riders.is_empty() \
			and _wob_w.length_squared() < 1e-8 and _wob.length_squared() < 1e-8 and not disabled:
		var near := false
		for p in get_tree().get_nodes_in_group("player"):
			if (p as Node3D).global_position.distance_squared_to(global_position) < 900.0:
				near = true
		if not near:
			return
	var fwd_in := 0.0
	var turn_in := 0.0
	var lift_in := 0.0
	_stun = maxf(0.0, _stun - delta)
	if pilot and _stun <= 0.0 and not disabled:
		fwd_in = Input.get_action_strength("move_forward") - Input.get_action_strength("move_back")
		turn_in = Input.get_action_strength("move_right") - Input.get_action_strength("move_left")
		lift_in = clampf(Input.get_action_strength("jump") + Input.get_action_strength("accelerate")
			- Input.get_action_strength("swim_down") - Input.get_action_strength("brake_reverse"), -1.0, 1.0)
	# stay level with the local floor: the vehicle's up follows the station's
	var up := StationGeo.up(StationGeo.s_of(global_position))
	var b := global_transform.basis.orthonormalized()
	b = _unswung(b)
	b = Basis(Quaternion(b.y, up)) * b
	_yaw_rate = move_toward(_yaw_rate, -turn_in * turn_rate, turn_accel * delta)
	b = b.rotated(up, _yaw_rate * delta).orthonormalized()
	# the commanded speeds, in the vehicle's frame
	var fit := 0.4 + 0.6 * hull / 100.0            # a damaged hull flies slower
	var target_f := fwd_in * (max_speed if fwd_in > 0.0 else reverse_speed) * fit
	var vf := -_lv.z
	vf = move_toward(vf, target_f, (accel if absf(fwd_in) > 0.05 else brake) * delta)
	_lv.z = -vf
	var target_up := lift_in * climb_speed
	if disabled:
		target_up = -2.0                           # the fans are dead: it sinks, the balloon slowing it
	_lv.y = move_toward(_lv.y, target_up, climb_accel * delta)
	_lv.x = move_toward(_lv.x, 0.0, side_damp * delta)
	var h := StationGeo.h_of(global_position)
	if floats:
		_on_water(h, lift_in, delta)
	if h >= ceiling_h and _lv.y > 0.0:
		_lv.y = 0.0
	if h > ceiling_h + 1.0:
		_lv.y = minf(_lv.y, -1.0)                      # somehow above it: sink back
	var vel := b * _lv
	# the ends of the station
	var x_room := StationGeo.HALF_LEN - 12.0
	if absf(global_position.x) > x_room and signf(vel.x) == signf(global_position.x):
		_lv -= b.inverse() * Vector3(vel.x, 0, 0)
		vel.x = 0.0
	_move(Transform3D(_swung(b, delta), global_position), vel * delta)
	_animate(fwd_in, turn_in, lift_in, delta)
	_carry(delta)
	if pilot:
		pilot.global_transform = Transform3D(global_transform.basis, pilot_transform().origin)
		_update_hud(h - MapTerrain.elevation(StationGeo.s_of(global_position), global_position.x))


func _on_water(h: float, lift_in: float, delta: float) -> void:
	## The rivers, lake and seas as a floor it floats on. Settling onto the water gently is a landing
	## (it taxis, slowly); hitting it hard is a crash that disables it; pushed down (the fans driving
	## it under) until the water is over its engines, it is swamped and disabled. Disabled, it still
	## floats: the balloon and the gondola's hull hold it up.
	var p := global_position
	var wa := MapTerrain.water_at(StationGeo.s_of(p), p.x)
	var d := wa.x - h if wa.x > -9000.0 else -1.0       # m of the hull under the surface
	var was := afloat
	afloat = d > 0.0
	if not afloat:
		return
	if not was:
		var sink := -_lv.y
		var fwd := Vector2(_lv.x, _lv.z).length()
		if sink > SPLASH_DOWN_MS or fwd > SPLASH_FWD_MS:
			_impact(maxf(sink, fwd), StationGeo.up(StationGeo.s_of(p)), p)
			if not disabled:
				hull = minf(hull, 10.0)
				disabled = true
				_on_disabled()
	if _engine_h == INF:
		var inv := global_transform.affine_inverse()
		for e in engines:                              # the lowest engine's top: past it, they're all under
			var top := -INF
			for mi in (e[0] as Node3D).find_children("*", "MeshInstance3D", true, false):
				top = maxf(top, ((inv * (mi as MeshInstance3D).global_transform) * (mi as MeshInstance3D).get_aabb()).end.y)
			if top > -INF:
				_engine_h = minf(_engine_h, top)
		if _engine_h == INF:
			_engine_h = 1.5
	# where it settles: its draft, deeper as the fans push it down
	var settle := float_draft + maxf(0.0, -lift_in) * (_engine_h + 0.4) * (0.0 if disabled else 1.0)
	if lift_in <= 0.0 or disabled:
		_lv.y = move_toward(_lv.y, clampf((d - settle) * 1.5, -0.2, 2.0), climb_accel * 2.0 * delta)
	# taxiing: the hull ploughs the water
	_lv.z = move_toward(_lv.z, clampf(_lv.z, -max_speed * 0.35, reverse_speed * 0.5), accel * 2.0 * delta)
	if d > _engine_h and not swamped:
		swamped = true
		if not disabled:
			disabled = true
			_on_disabled()


func _move(from: Transform3D, motion: Vector3) -> void:
	## Sweep the hull along motion (riders excepted), sliding along whatever it meets.
	var exclude: Array[RID] = []
	for r in _riders:
		exclude.append((r as PhysicsBody3D).get_rid())
	if pilot:
		exclude.append(pilot.get_rid())
	for d in doors:
		exclude.append((d as PhysicsBody3D).get_rid())
	var seat := get_node_or_null("PilotSeat")
	if seat:
		exclude.append((seat as PhysicsBody3D).get_rid())
	var xf := from
	var hit_v := 0.0
	var hit_n := Vector3.ZERO
	var hit_at := Vector3.ZERO
	for attempt in 3:
		if motion.length_squared() < 1e-10:
			break
		var params := PhysicsTestMotionParameters3D.new()
		params.from = xf
		params.motion = motion
		params.exclude_bodies = exclude
		params.margin = 0.02
		var res := PhysicsTestMotionResult3D.new()
		if not PhysicsServer3D.body_test_motion(get_rid(), params, res):
			xf.origin += motion
			break
		xf.origin += res.get_travel()
		var n := res.get_collision_normal()
		motion = res.get_remainder().slide(n)
		# lose the velocity into the surface (a landing stops the descent)
		var lv_n := xf.basis.inverse() * n
		var into := _lv.dot(lv_n)
		if into < 0.0:
			_lv -= lv_n * into
			if -into > hit_v:
				hit_v = -into
				hit_n = n
				hit_at = res.get_collision_point()
	global_transform = xf
	if hit_v > 0.0:
		# a touchdown on the casters (the floor below, ground under it) at up to GEAR_MS is a landing
		var up := StationGeo.up(StationGeo.s_of(xf.origin))
		var gear := hit_n.dot(up) > 0.8 and (hit_at - xf.origin).dot(up) < com_height * 0.5
		if not (gear and hit_v <= GEAR_MS):
			_impact(hit_v, hit_n, hit_at)


func _animate(fwd_in: float, turn_in: float, lift_in: float, delta: float) -> void:
	var powered := (pilot != null or _flying_self()) and not disabled
	_spin = move_toward(_spin, (10.0 + 30.0 * clampf(absf(fwd_in) + absf(turn_in) + absf(lift_in), 0.0, 1.0)) if powered else 0.0, 12.0 * delta)
	for e in engines:
		var eng: Node3D = e[0]
		var tilt := clampf(fwd_in * max_tilt + turn_in * max_tilt * 0.6 * e[2], -max_tilt, max_tilt)
		# + tilt leans the duct's top toward the nose, which is -X rotation in Godot's frame
		eng.rotation.x = move_toward(eng.rotation.x, -tilt, tilt_rate * delta)
		if e[1]:
			(e[1] as Node3D).rotate_object_local(Vector3.UP, _spin * delta)
	for p in _engine_sounds:
		var sp := p as AudioStreamPlayer3D
		if _spin < 0.5:
			if sp.playing:
				sp.stop()
			continue
		if not sp.playing:
			sp.play(randf() * 3.0)
		var k := clampf(_spin / 40.0, 0.0, 1.0)
		sp.pitch_scale = 0.55 + 0.75 * k
		sp.volume_db = linear_to_db(0.15 + 0.85 * k) - 4.0


# ------------------------------------------------------------------ crashes
func _impact(speed: float, normal: Vector3, at: Vector3) -> void:
	## Something was hit at speed m/s into its surface.
	var kmh := speed * 3.6
	if kmh < CRASH_KMH:
		return
	var now := Time.get_ticks_msec()
	if now - _last_crash < 350:                     # one crash, not one per tick of the scrape
		return
	_last_crash = now
	if _crash_sound == null:
		_crash_sound = AudioStreamPlayer3D.new()
		_crash_sound.name = "crash_sound"
		_crash_sound.stream = load("res://remake/audio/crash.wav")
		_crash_sound.unit_size = 10.0
		_crash_sound.max_distance = 300.0
		add_child(_crash_sound)
	_crash_sound.global_position = at
	var k := clampf((kmh - CRASH_KMH) / (WRECK_KMH - CRASH_KMH), 0.0, 1.0)
	_crash_sound.volume_db = linear_to_db(0.35 + 0.65 * k) + 3.0
	_crash_sound.pitch_scale = lerpf(1.15, 0.75, k) * randf_range(0.95, 1.05)
	_crash_sound.play()
	if crash_physics:
		_crash(speed, normal, at)


func _crash(speed: float, normal: Vector3, at: Vector3) -> void:
	## The aerostat's response to a crash (the velocity into the surface is already gone).
	var kmh := speed * 3.6
	var b := global_transform.basis
	# rebound
	_lv += b.inverse() * normal * speed * RESTITUTION
	# the off-centre hit's angular impulse: omega ~ (r x n) v (1 + e) / k^2, k ~ 2 m, and
	# much of it soaked up by the air the balloon has to push aside
	var com := global_position + b.y * com_height
	var w := (at - com).cross(normal) * speed * (1.0 + RESTITUTION) / 4.0 * 0.25
	var up := b.y
	_yaw_rate += w.dot(up)
	_wob_w += w - up * w.dot(up)
	# the pilot loses it for a moment, the longer the harder
	_stun = maxf(_stun, clampf((kmh - CRASH_KMH) / 12.0, 0.3, 3.0))
	if kmh > DAMAGE_KMH:
		var d := 100.0 * (kmh * kmh - DAMAGE_KMH * DAMAGE_KMH) / (WRECK_KMH * WRECK_KMH - DAMAGE_KMH * DAMAGE_KMH)
		hull = maxf(0.0, hull - d)
		if hull <= 0.0 and not disabled:
			disabled = true
			_on_disabled()


func _on_disabled() -> void:
	## Wrecked: the balloon slackens a little (the fans stop in _animate).
	var bal := find_child("balloon", true, false) as Node3D
	if bal:
		bal.scale = Vector3(1.0, 0.86, 1.0)


func _unswung(b: Basis) -> Basis:
	## The attitude without the crash swing.
	if _wob.length_squared() < 1e-12:
		return b
	return (Basis(_wob.normalized(), _wob.length()).inverse() * b).orthonormalized()


func _swung(level: Basis, delta: float) -> Basis:
	## Advance the swing (a damped pendulum: the cabin hangs under the balloon) and apply it.
	if _wob.length_squared() < 1e-10 and _wob_w.length_squared() < 1e-10:
		_wob = Vector3.ZERO
		_wob_w = Vector3.ZERO
		return level
	var up := level.y
	_wob_w += (-PENDULUM_W * PENDULUM_W * _wob - 2.0 * SWING_DAMP * PENDULUM_W * _wob_w) * delta
	_wob_w -= up * _wob_w.dot(up)
	_wob += _wob_w * delta
	_wob -= up * _wob.dot(up)
	if _wob.length() > 0.7:                          # never past 40 degrees
		_wob = _wob.normalized() * 0.7
		_wob_w -= _wob.normalized() * maxf(0.0, _wob_w.dot(_wob.normalized()))
	return (Basis(_wob.normalized(), _wob.length()) * level).orthonormalized() if _wob.length() > 1e-6 else level


func _flying_self() -> bool:
	## Under its own control (a summoned aerostat): the fans run with nobody at them.
	return false


func _carry(delta: float) -> void:
	## Everyone standing in the cabin moves with it.
	var w := global_transform.basis.y * _yaw_rate
	var vel := global_transform.basis * _lv
	var now: Array = []
	for p in get_tree().get_nodes_in_group("player"):
		if not p is StationPlayer or p == pilot:
			continue
		var lp: Vector3 = global_transform.affine_inverse() * (p as Node3D).global_position
		if cabin_box.has_point(lp):
			now.append(p)
			(p as StationPlayer).carrier_velocity = vel + w.cross((p as Node3D).global_position - global_position)
			(p as StationPlayer).sheltered = true
	for p in _riders:
		if not now.has(p) and is_instance_valid(p):
			(p as StationPlayer).carrier_velocity = Vector3.ZERO
			(p as StationPlayer).sheltered = false
	_riders = now


# ------------------------------------------------------------------ a readout while piloting
func _show_hud(on: bool) -> void:
	if on and _hud == null:
		var layer := CanvasLayer.new()
		layer.name = "FlightHud"
		add_child(layer)
		_hud = Label.new()
		_hud.position = Vector2(24, 140)
		_hud.add_theme_font_size_override("font_size", 18)
		_hud.add_theme_color_override("font_outline_color", Color.BLACK)
		_hud.add_theme_constant_override("outline_size", 4)
		layer.add_child(_hud)
	if _hud:
		_hud.get_parent().visible = on


func _update_hud(h: float) -> void:
	if _hud:
		var state := "   HULL %d%%" % roundi(hull) if crash_physics else ""
		if swamped:
			state = "   SWAMPED (engines under water) -- summon another from the Communicator"
		elif disabled:
			state = "   DISABLED -- summon another from the Communicator"
		elif afloat:
			state += "   AFLOAT"
		elif _stun > 0.0:
			state += "   !! CRASH"
		_hud.text = "SPEED %3d km/h   ALT %4.0f m (above ground)%s\n" % [roundi(-_lv.z * 3.6), h, state] + Controls.hint(
			"W/S thrust   A/D turn   Space/Ctrl climb/descend   E leave seat",
			"%s thrust and turn   %s / %s climb / descend   %s leave seat" % [Controls.button("LS"), Controls.button("RT"),
				Controls.button("LT"), Controls.button(JOY_BUTTON_X)])
