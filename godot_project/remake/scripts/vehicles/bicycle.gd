extends RemakeGroundVehicle
class_name RemakeBicycle

## A bicycle the player rides (remake/vehicles/bicycle.glb; rig in remake/blender/vehicles/bicycle.py).
## It drives like the station's other ground vehicles (RemakeGroundVehicle: kinematic on the curved
## floor, kerbs climbed, walls stop it) at a cyclist's pace, with the bicycle's own animation: the
## wheels spin, the bars steer about the head tube, the cranks turn with the pedals kept level, it
## leans into turns, and the kickstand folds when it moves. No motor: it's pedal-powered.
##   E (interact) on the bike: ride;  W/S pedal / brake;  A/D steer;  Space brake;  E get off.
## The player rides it in person: their body (a generated character, the same for the whole game)
## sits on the saddle with feet on the pedals and hands on the grips (NpcAnimator.ride, as NPC
## cyclists do), and the view is from that body's eyes, so looking down you see yourself pedal.

const MODEL := "res://remake/vehicles/bicycle.glb"
const GEAR := 2.2

var _cranks: Node3D
var _crank_base := Basis()
var _pedals: Array = []          # [node, base basis]
var _kick: Node3D
var _kick_base := Basis()
var _crank_a := 0.0
var _lean := 0.0
var _rider: NpcCharacter
var _rider_an: NpcAnimator
var _seat_n: Node3D
var _grips := {}


func _init() -> void:
	max_speed = 25.0 / 3.6
	reverse_speed = 0.8               # walking it backwards
	accel = 1.3
	brake = 4.0
	coast = 0.25
	wheelbase = 1.10
	track = 0.0
	wheel_r = 0.34
	max_steer = 0.55
	steer_rate = 2.2
	hull_size = Vector3(0.45, 0.8, 1.6)
	stand_point = Vector3(0.75, 0.0, 0.1)     # beside it, on the right
	cabin_box = AABB(Vector3(-0.3, 0.0, -0.9), Vector3(0.6, 1.4, 1.8))
	seat_eye = 0.78
	seat_forward = 0.12


func _build_hull() -> void:
	load_model(MODEL)


func _rig() -> void:
	super()
	_cranks = model.find_child("cranks", true, false) as Node3D
	if _cranks:
		_crank_base = _cranks.transform.basis
	for side in ["L", "R"]:
		var p := model.find_child("pedal_" + side, true, false) as Node3D
		if p:
			_pedals.append([p, p.transform.basis])
	_kick = model.find_child("kickstand", true, false) as Node3D
	if _kick:
		_kick_base = _kick.transform.basis
	_seat_n = model.find_child("seat_rider", true, false) as Node3D
	for side in ["L", "R"]:
		_grips[side] = model.find_child("grip_" + side, true, false)
	steer_node = model.find_child("steer", true, false) as Node3D
	if steer_node:
		_steer_base = steer_node.transform.basis
	# aim at any part of the bike to ride it
	RemakeInteractZone.make(self, "Ride", Transform3D(Basis(), Vector3(0, 0.6, 0)), Vector3(0.6, 1.2, 1.8), _controls_used, _controls_prompt)


func _ranges() -> void:
	for m in find_children("*", "GeometryInstance3D", true, false):
		(m as GeometryInstance3D).visibility_range_end = 160.0


func _controls_prompt() -> String:
	return "Ride" if pilot == null else ""


func _animate_car(delta: float) -> void:
	_spin_a = fmod(_spin_a - _speed / wheel_r * delta, TAU)
	_crank_a = fmod(_crank_a - _speed / wheel_r / GEAR * delta, TAU)
	for w in wheels:
		(w[0] as Node3D).transform.basis = (w[1] as Basis) * Basis(Vector3.RIGHT, _spin_a)
	if steer_node:
		steer_node.transform.basis = _steer_base * Basis(Vector3.UP, _steer)
	if _cranks:
		_cranks.transform.basis = _crank_base * Basis(Vector3.RIGHT, _crank_a)
		for p in _pedals:
			(p[0] as Node3D).transform.basis = (p[1] as Basis) * Basis(Vector3.RIGHT, -_crank_a)
	if _kick:
		_kick.transform.basis = _kick_base * Basis(Vector3.RIGHT, 0.0 if absf(_speed) < 0.05 and pilot == null else -1.4)
	_lean = lerpf(_lean, clampf(-atan(_speed * _yaw_rate / 9.8), -0.45, 0.45), clampf(delta * 3.0, 0.0, 1.0))
	model.transform.basis = Basis(Vector3.FORWARD, _lean)
	if _rider_an:
		_rider_an.ride = _rider_pose()


# ------------------------------------------------------------------ the player in person
func take_seat(p: StationPlayer) -> void:
	super(p)
	if pilot == null or _rider:
		return
	var seed := 1
	var life := NpcLife.shared() if FileAccess.file_exists(NpcLife.PATH) else null
	if life:
		seed = life.seed
	var v := NpcTraits.shared().person(seed, "player", ["L0", "L1"], "", {"age": 30})
	_rider = NpcCharacter.from_prepared(NpcCharacter.prepare(v, "player", seed, "work"))
	_rider.name = "Rider"
	model.add_child(_rider)                      # leans with the bike
	_rider_an = NpcAnimator.attach(_rider)
	_rider_an.ambient = false
	_rider_an.ride = _rider_pose()


func leave_seat() -> void:
	super()
	if pilot == null and _rider:
		_rider.queue_free()
		_rider = null
		_rider_an = null


func _rider_pose() -> Dictionary:
	## The same targets an NPC cyclist gets (NpcBike.rider_pose), in the leaning model's frame.
	var inv := model.global_transform.affine_inverse()
	var out := {"pitch": 0.28, "grip": 0.85, "w": 1.0, "pole": Vector3(0.7, -0.5, 0.2)}
	if _seat_n:
		out["hips"] = inv * _seat_n.global_position + Vector3(0, 0.08, 0.02)
	for k in _pedals.size():
		var side := "L" if str((_pedals[k][0] as Node).name).ends_with("L") else "R"
		out["foot" + side] = inv * (_pedals[k][0] as Node3D).global_position + Vector3(0, 0.07, 0.05)
	for side in _grips:
		if _grips[side]:
			out["hand" + side] = inv * (_grips[side] as Node3D).global_position
	return out


func pilot_transform() -> Transform3D:
	## The view from the rider's own eyes: the player's body is placed so its camera sits at the
	## generated body's head, a little forward of its centre (inside the head nothing is drawn).
	if _rider == null or pilot == null:
		return super()
	var sk := _rider.find_child("Skeleton*", true, false) as Skeleton3D
	if sk == null:
		return super()
	var hi := sk.find_bone("Head")
	if hi < 0:
		return super()
	var b := global_transform.basis
	var hx := sk.global_transform * sk.get_bone_global_pose(hi)
	var eye := hx * Vector3(0, 0.12, -0.2)             # just in front of the face (characters face -Z)
	var off := pilot.global_transform.affine_inverse() * pilot.camera.global_position
	return Transform3D(b, eye - b * off)


func _update_hud(_h: float) -> void:
	if _hud:
		_hud.text = "SPEED %3d km/h\n" % roundi(absf(_speed) * 3.6) + Controls.hint(
			"W pedal   S brake   A/D steer   Space brake   E get off",
			"%s pedal   %s brake   %s steer   %s get off" % [Controls.button("RT"), Controls.button("LT"), Controls.button("LS"), Controls.button(JOY_BUTTON_X)])
