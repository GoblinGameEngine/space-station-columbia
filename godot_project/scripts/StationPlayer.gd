extends CharacterBody3D
class_name StationPlayer

# Space-station variant of Player.gd -- same FPS controller shape
# (WASD, mouse look, jump, weapons via WeaponManager) but with radial
# gravity instead of fixed world-down, since the floor here is the
# inside of a ring (see scripts/world/StationGeo.gd and
# scripts/world/StationRingBuilder.gd). Forked from Player.gd rather
# than adding a gravity-mode flag to it -- the gravity/up-direction
# change touches nearly every line of the physics step, so branching it
# inline would be more confusing than a dedicated copy. No step-up/curb
# logic here (Player.gd's _try_step_up) -- this map's floor has no
# curbs or stairs, just ~3.75-degree seams between straight segments,
# comfortably inside CharacterBody3D's default floor_max_angle.
#
# NOT a spinning station -- RingBody never moves (see the file-level
# comment in StationGeo.gd for why: rotating it, and simulating
# centrifugal force from that rotation, went through several rounds of
# hard-to-fix bugs before this settled on a stationary ring with an
# artificial radial gravity gradient, StationGeo.gravity_at(),
# instead). "Down" is still radial, toward the ring wall -- that part
# is pure geometry, unrelated to whether anything is spinning -- but
# nothing here is being carried by a moving platform any more.
#
# Physics: each physics frame, "down" is computed fresh as the radial
# direction from the station's central axis through the player (the
# floor is further out along that direction; the ceiling/axis is the
# other way). up_direction is set to match every frame, and the body's
# whole basis is turned by the shortest rotation from its own current up
# to that true up (Quaternion(basis.y, up) * basis) -- not reconstructed
# from a fixed forward vector via Basis.looking_at(). That keeps forward (and any yaw/pitch already
# applied via mouse look) correctly glued to the floor as you WALK
# along its curve, the same "align to a changing surface normal, keep
# facing" technique used for walking on curved/spherical ground
# elsewhere -- looking_at(old_forward, up) alone let forward and up
# drift apart frame to frame instead. Velocity is decomposed into an
# "along up" component (gravity/jump accumulate here, exactly like
# Player.gd's velocity.y) and a fresh per-frame tangential component
# from WASD input, instead of Player.gd's world-axis velocity.x/.z.

# LIVE TUNING: `static var`, not `const` -- read fresh every physics/
# input frame, so these can be changed from a running game with no
# restart, e.g. `python3 tools/gcmd.py run "StationPlayer.WALK_SPEED = 6.0"`.
# See the matching comment in StationGeo.gd for the geometry/gravity
# side of tuning (radius, ceiling height, etc.), which needs a
# rebuild_ring() call instead since those are baked into the built mesh.
static var WALK_SPEED := 4.2
static var SPRINT_SPEED := 7.5  # held (not toggled) via the "sprint" action -- left shift, project.godot's [input]
static var JUMP_VELOCITY := 4.5
static var MOUSE_SENSITIVITY := 0.0025
static var PITCH_LIMIT := deg_to_rad(85)

# Swimming: neutrally buoyant, no current/flow force -- see WaterVolume.gd
# and this file's _physics_process() swim branch. "jump"/"swim_down" (Ctrl,
# project.godot's [input]) give vertical control in place of land's
# gravity+jump; letting go decays toward hovering in place rather than
# sinking or drifting.
static var SWIM_SPEED := 3.2
static var SWIM_VERTICAL_SPEED := 2.6

@export var faction_id: String = "player"

var spawn_transform: Transform3D
var _station: Node3D

@onready var head: Node3D = $Head
@onready var camera: Camera3D = $Head/Camera3D
@onready var muzzle_ray: RayCast3D = $Head/Camera3D/MuzzleRay
@onready var weapon_mount: Node3D = $Head/Camera3D/WeaponMount
@onready var health: Health = $Health

var _skip_next_mouse_delta := true
# a controller's right stick: turn / look speeds at full deflection (radians a second), scaled by
# Settings.stick_look_mult; L3 sprint stays on until the stick comes back (Controls.gd)
const STICK_YAW_SPEED := 3.2
const STICK_PITCH_SPEED := 2.3
var _sprint_latched := false

# Which WaterVolume(s) the player is currently overlapping -- an Array,
# not a bool, so two overlapping volumes (e.g. a future river/lake
# junction) don't prematurely end swim state when only one is exited.
var _water_volumes: Array[Area3D] = []

# Vehicles (remake/scripts/vehicles/air_vehicle.gd). Seated: the vehicle
# places the body each tick, the mouse turns only the head, E stands up.
# Standing in a cabin: the vehicle sets carrier_velocity (its own motion at
# this point) every tick, added on top of walking, and sheltered (a cabin
# keeps a cloud's "water" out).
var carrier_velocity := Vector3.ZERO
var sheltered := false
var _vehicle: Node = null
var _last_carrier := Vector3.ZERO
const SEATED_YAW_LIMIT := 1.9

func sit_in(vehicle: Node) -> void:
	_vehicle = vehicle
	$CollisionShape3D.disabled = true
	weapon_mount.visible = false            # hands on the controls
	velocity = Vector3.ZERO
	carrier_velocity = Vector3.ZERO
	head.rotation.y = 0.0

func stand_up(at: Vector3, basis_: Basis) -> void:
	## Off a seat: on our feet on whatever floor is under `at` (the ground, a deck, a cabin floor),
	## found with a ray -- our origin is at the eyes, the feet are _feet_depth() below it. (Callers
	## passed ground points, or guesses at the eye height; a ground point put the body underground.)
	_vehicle = null
	var up := StationGeo.up(StationGeo.s_of(at))
	var q := PhysicsRayQueryParameters3D.create(at + up * 0.6, at - up * 2.5, collision_mask)   # (from just above: not onto a cabin roof)
	q.exclude = [get_rid()]
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	var feet: Vector3 = hit.position if not hit.is_empty() else at
	if hit.is_empty():
		var s := StationGeo.s_of(at)
		var g := StationGeo.point(s, at.x, MapTerrain.elevation(s, at.x))
		if (at - g).dot(up) < 0.0:
			feet = g                                 # never under the ground
	global_transform = Transform3D(basis_, feet + up * (_feet_depth() + 0.03))
	$CollisionShape3D.disabled = false
	weapon_mount.visible = true
	head.rotation.y = 0.0
	velocity = Vector3.ZERO

func _feet_depth() -> float:
	## From our origin down to the bottom of the capsule.
	var cs := $CollisionShape3D as CollisionShape3D
	var h := 1.8
	if cs.shape is CapsuleShape3D:
		h = (cs.shape as CapsuleShape3D).height
	return -cs.position.y + h * 0.5

func is_seated() -> bool:
	return _vehicle != null

func is_swimming() -> bool:
	if _water_volumes.is_empty() or sheltered or _vehicle != null:
		return false
	# in a volume that really holds this spot (a cloud only above its flat base: its spheres reach far
	# below what's drawn)
	for v in _water_volumes:
		if is_instance_valid(v) and (not v.has_method("holds") or v.holds(global_position)):
			return true
	return false

## WaterVolume.gd's own contract -- called via has_method(), not a typed
## signal connection, so any body (not just this class) can opt in.
func enter_water(volume: Area3D) -> void:
	if not _water_volumes.has(volume):
		_water_volumes.append(volume)

func exit_water(volume: Area3D) -> void:
	_water_volumes.erase(volume)

func get_faction() -> String:
	return faction_id

func recapture_mouse() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	_skip_next_mouse_delta = true

const FLOOR_MAX_DEG := 55.0
const FLOOR_SNAP := 0.5


func _ready() -> void:
	_station = get_tree().get_first_node_in_group("space_station")
	spawn_transform = global_transform
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	WeaponManager.register_player(self, weapon_mount, camera, muzzle_ray)

	WeaponManager.add_weapon("fists")
	WeaponManager.add_weapon("bat")
	WeaponManager.add_weapon("pistol")
	WeaponManager.equip("pistol")

	health.died.connect(_on_died)
	# hillsides: walkable up to FLOOR_MAX_DEG (the terrain's 2 m triangles vary round a hill's
	# average slope, and at the default 45 degrees the steeper ones read as wall -- the player
	# dropped off them every few frames and bobbed); held to the ground over crests and dips;
	# the same speed up a hill as down it
	floor_max_angle = deg_to_rad(FLOOR_MAX_DEG)
	floor_snap_length = FLOOR_SNAP
	floor_constant_speed = true

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		if _skip_next_mouse_delta:
			_skip_next_mouse_delta = false
		else:
			var sens := MOUSE_SENSITIVITY * Settings.mouse_sensitivity_mult
			# NOT rotate_y() -- confirmed live that Node3D.rotate_y() turns
			# around the PARENT's Y axis, not this node's own current local
			# Y (easy to miss in Player.gd, where those are always the same
			# axis since that body never reorients -- not true here, where
			# local "up" constantly changes to track the ring's curve).
			# Rotating around the wrong axis was corrupting yaw AND bleeding
			# into the "up" component WASD reads from transform.basis,
			# which is what made forward input read as a jump instead of a
			# walk. Rotating explicitly around the body's own current up
			# (already expressed in the same space as global_transform)
			# fixes both.
			if _vehicle:
				# seated: look round the cabin without turning the body in the seat
				head.rotation.y = clamp(head.rotation.y - event.relative.x * sens, -SEATED_YAW_LIMIT, SEATED_YAW_LIMIT)
				head.rotation.x = clamp(head.rotation.x - event.relative.y * sens, -PITCH_LIMIT, PITCH_LIMIT)
			else:
				global_transform.basis = global_transform.basis.rotated(global_transform.basis.y, -event.relative.x * sens)
				head.rotate_x(-event.relative.y * sens)
				head.rotation.x = clamp(head.rotation.x, -PITCH_LIMIT, PITCH_LIMIT)

	if event.is_action_pressed("shoot") and _vehicle == null:
		if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
			WeaponManager.try_use_equipped()
		else:
			recapture_mouse()

	if event.is_action_pressed("next_weapon"):
		WeaponManager.cycle(1)
	if event.is_action_pressed("prev_weapon"):
		WeaponManager.cycle(-1)
	for i in range(1, 4):
		if event.is_action_pressed("weapon_slot_%d" % i) and i - 1 < WeaponManager.owned.size():
			WeaponManager.equip(WeaponManager.owned[i - 1])

	if event.is_action_pressed("interact"):
		if _vehicle:
			_vehicle.leave_seat()
		else:
			_try_interact()

const INTERACT_RANGE := 3.5

func _try_interact() -> void:
	if DialogBox.is_open():
		return
	# along the aim: solid things, and the use-only zones (RemakeInteractZone: a vehicle's doorway,
	# its steering wheel); areas that aren't for using (water, cloud) are looked through
	var from := camera.global_position
	var to := from - camera.global_transform.basis.z * (INTERACT_RANGE + 0.5)
	var q := PhysicsRayQueryParameters3D.create(from, to, muzzle_ray.collision_mask | RemakeInteractZone.LAYER)
	q.collide_with_areas = true               # (not from inside: standing in a doorway, you use what you look at past it)
	# a doorway gives way to anything usable seen through it (the steering wheel, the far door)
	var ex: Array[RID] = [get_rid()]
	var fallback: Object = null
	for attempt in 8:
		q.exclude = ex
		var hit := get_world_3d().direct_space_state.intersect_ray(q)
		if hit.is_empty():
			break
		var target: Object = hit.collider
		if target is Area3D and not target.has_method("interact"):
			ex.append((target as Area3D).get_rid())
			continue
		if target == null or not target.has_method("interact") or from.distance_to(hit.position) > INTERACT_RANGE:
			break
		if target is RemakeInteractZone and (target as RemakeInteractZone).gives_way:
			if fallback == null:
				fallback = target
			ex.append((target as Area3D).get_rid())
			continue
		target.interact(self)
		return
	if fallback:
		fallback.interact(self)

## Radial vector from the station's central axis to the player, with
## the axis-direction component projected out (so this is purely the
## "how far out, which way" part). Returns Vector3.ZERO if we somehow
## have no station reference (e.g. running this scene standalone).
func _radial_vector() -> Vector3:
	if _station == null:
		return Vector3.ZERO
	var rel := global_position - _station.global_position
	var axis: Vector3 = StationGeo.AXIS
	return rel - axis * rel.dot(axis)

func _process(delta: float) -> void:
	# looking round with a controller's right stick (the mouse's equivalent is in _unhandled_input)
	var v := Controls.look_vector()
	if v == Vector2.ZERO:
		return
	var k := Settings.stick_look_mult * delta
	if _vehicle:
		head.rotation.y = clamp(head.rotation.y - v.x * STICK_YAW_SPEED * k, -SEATED_YAW_LIMIT, SEATED_YAW_LIMIT)
	else:
		global_transform.basis = global_transform.basis.rotated(global_transform.basis.y.normalized(), -v.x * STICK_YAW_SPEED * k)
	head.rotation.x = clamp(head.rotation.x - v.y * STICK_PITCH_SPEED * k, -PITCH_LIMIT, PITCH_LIMIT)


func _physics_process(delta: float) -> void:
	if _vehicle:
		return                      # the vehicle places us on the seat
	var radial := _radial_vector()
	var radial_len := radial.length()
	var degenerate := radial_len < 0.001
	if degenerate:
		# Degenerate (on/near the axis) -- fall back to ordinary world-down
		# rather than dividing by ~zero; shouldn't happen once spawned on
		# the floor, but keeps this from producing NaNs if it ever does.
		radial = Vector3.DOWN
		radial_len = 1.0
	var radial_dir := radial / radial_len
	var up := -radial_dir
	up_direction = up

	# Stand along the true up every tick: turn the body from wherever its own up now points, not by
	# the change since last tick -- that way nothing can leave it tilted (the old incremental turn
	# skipped changes below Vector3's epsilon yet still recorded them as done, so a slow drift --
	# floating in a cloud -- piled up an unrecoverable lean).
	var body_up := global_transform.basis.y.normalized()
	if body_up.angle_to(up) > 1e-6:
		global_transform.basis = Basis(Quaternion(body_up, up)) * global_transform.basis
	global_transform.basis = global_transform.basis.orthonormalized()

	var up_speed := (velocity - _last_carrier).dot(up)
	var swimming := is_swimming()
	if swimming:
		# Neutrally buoyant -- no gravity pull, and explicitly no current/
		# flow force applied here or anywhere in WaterVolume.gd ("I don't
		# want the water to flow, just make it so the play character can
		# swim in it"). Vertical control replaces jump/gravity: hold jump
		# to rise, swim_down to sink, let go to coast toward a hover
		# instead of falling.
		if Input.is_action_pressed("jump"):
			up_speed = move_toward(up_speed, SWIM_VERTICAL_SPEED, SWIM_VERTICAL_SPEED * 6.0 * delta)
		elif Input.is_action_pressed("swim_down"):
			up_speed = move_toward(up_speed, -SWIM_VERTICAL_SPEED, SWIM_VERTICAL_SPEED * 6.0 * delta)
		else:
			up_speed = move_toward(up_speed, 0.0, SWIM_VERTICAL_SPEED * 3.0 * delta)
	else:
		if not is_on_floor():
			# Stepped radial gradient (0G at the axis, TARGET_G at the wall)
			# instead of a flat pull or omega^2*radial_len -- see
			# StationGeo.gravity_at(). Using radial_len here (not just
			# whatever gravity_at() was for the floor you took off from)
			# means a jump/fall that drifts toward the axis genuinely gets
			# lighter as it goes, same as it would get lighter walking
			# inward through the bands on foot.
			up_speed -= StationGeo.gravity_at(radial_len) * delta
		else:
			up_speed = minf(up_speed, 0.0)       # grounded: no speed left over from the slope to carry off a crest

		if Input.is_action_just_pressed("jump") and is_on_floor():
			up_speed = JUMP_VELOCITY

	var input_dir := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var move_dir := (transform.basis * Vector3(input_dir.x, 0, input_dir.y))
	if move_dir.length_squared() > 0.0001:
		# full speed on the keys; a stick walks as far over as it's pushed
		move_dir = move_dir.normalized() * minf(input_dir.length(), 1.0)

	# sprint: held (Shift), or clicked in on a stick (L3) until the player stops
	if Controls.using_pad and Input.is_action_just_pressed("sprint"):
		_sprint_latched = not _sprint_latched
	if input_dir.length() < 0.2:
		_sprint_latched = false
	var sprinting := _sprint_latched or (Input.is_action_pressed("sprint") and not Controls.using_pad)
	var speed := SWIM_SPEED if swimming else (SPRINT_SPEED if sprinting else WALK_SPEED)
	velocity = up * up_speed + move_dir * speed + carrier_velocity
	# a cabin carries us itself (carrier_velocity); the engine's own platform velocity would double it
	platform_floor_layers = 0 if carrier_velocity != Vector3.ZERO else 0xFFFFFFFF
	_last_carrier = carrier_velocity
	move_and_slide()

func _on_died(_attacker: Node) -> void:
	print("StationPlayer died -- respawning.")
	respawn()


func respawn() -> void:
	## Back to where you started (the Communicator's System > Respawn, or a death), out of any vehicle, healed.
	if _vehicle:
		_vehicle.leave_seat()
	carrier_velocity = Vector3.ZERO
	sheltered = false
	global_transform = spawn_transform
	velocity = Vector3.ZERO
	_water_volumes.clear()  # a mid-swim death would otherwise respawn the player still "swimming" on dry land
	health.heal(health.max_health)
