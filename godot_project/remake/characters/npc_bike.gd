extends Node3D
class_name NpcBike

## A bicycle someone rides (remake/vehicles/bicycle.glb; rig in remake/blender/vehicles/bicycle.py):
## the wheels spin, the cranks turn (geared: half the wheel's rate), the pedals stay level, the bars
## steer about the head tube by the turn rate, the bike leans into turns, the kickstand folds up. For
## its rider it gives the pose targets in the rider's frame (NpcAnimator.ride): hips on the saddle,
## ankles over the pedals, wrists on the grips. The rider's root goes at rider_frame() (the bike as
## it leans), so those targets are the bike's own rig points.
##
##   var bike := NpcBike.make(); add_child(bike)
##   bike.update(delta, speed, yaw_rate);  animator.ride = bike.rider_pose()

const MODEL := "res://remake/vehicles/bicycle.glb"
const WHEEL_R := 0.34
const WHEELBASE := 1.10
const GEAR := 2.2                    # wheel turns per crank turn
static var _scene: PackedScene

var model: Node3D
var _wheels := {}                    # name -> [node, base basis]
var _steer: Node3D
var _steer_base := Basis()
var _cranks: Node3D
var _crank_base := Basis()
var _pedals := {}                    # "L"/"R" -> [node, base basis]
var _kick: Node3D
var _kick_base := Basis()
var _seat: Node3D
var _grips := {}
var spin := 0.0
var crank := 0.0
var steer := 0.0
var lean := 0.0
var parked := true


static func make() -> NpcBike:
	if _scene == null:
		_scene = load(MODEL)
	var b := NpcBike.new()
	b.name = "Bike"
	b.model = _scene.instantiate()
	b.add_child(b.model)
	b._find()
	return b


func _find() -> void:
	for nm in ["wheel_F", "wheel_B"]:
		var n := model.find_child(nm, true, false) as Node3D
		if n:
			_wheels[nm] = [n, n.transform.basis]
	_steer = model.find_child("steer", true, false) as Node3D
	if _steer:
		_steer_base = _steer.transform.basis
	_cranks = model.find_child("cranks", true, false) as Node3D
	if _cranks:
		_crank_base = _cranks.transform.basis
	for side in ["L", "R"]:
		var p := model.find_child("pedal_" + side, true, false) as Node3D
		if p:
			_pedals[side] = [p, p.transform.basis]
		_grips[side] = model.find_child("grip_" + side, true, false)
	_kick = model.find_child("kickstand", true, false) as Node3D
	if _kick:
		_kick_base = _kick.transform.basis
	_seat = model.find_child("seat_rider", true, false) as Node3D


func update(delta: float, speed: float, yaw_rate: float) -> void:
	spin = fmod(spin - speed / WHEEL_R * delta, TAU)
	crank = fmod(crank - speed / WHEEL_R / GEAR * delta, TAU)
	var want_steer := atan(yaw_rate * WHEELBASE / maxf(absf(speed), 0.5)) if absf(speed) > 0.05 else 0.0
	steer = lerpf(steer, clampf(want_steer, -0.6, 0.6), clampf(delta * 6.0, 0.0, 1.0))
	var want_lean := clampf(-atan(speed * yaw_rate / 9.8), -0.45, 0.45)
	lean = lerpf(lean, want_lean, clampf(delta * 3.0, 0.0, 1.0))
	parked = absf(speed) < 0.05
	for nm in _wheels:
		(_wheels[nm][0] as Node3D).transform.basis = (_wheels[nm][1] as Basis) * Basis(Vector3.RIGHT, spin)
	if _steer:
		_steer.transform.basis = _steer_base * Basis(Vector3.UP, steer)           # Blender local Z (the head tube) = Godot local Y
	if _cranks:
		_cranks.transform.basis = _crank_base * Basis(Vector3.RIGHT, crank)
		for side in _pedals:
			(_pedals[side][0] as Node3D).transform.basis = (_pedals[side][1] as Basis) * Basis(Vector3.RIGHT, -crank)
	if _kick:
		_kick.transform.basis = _kick_base * Basis(Vector3.RIGHT, 0.0 if parked else -1.4)
	model.transform.basis = Basis(Vector3.FORWARD, lean)


func _local(n: Node3D) -> Vector3:
	return model.global_transform.affine_inverse() * n.global_transform.origin


func rider_frame() -> Transform3D:
	## Where the rider's root goes: the bike as it leans.
	return model.global_transform


func rider_pose(leaning := 0.28) -> Dictionary:
	## Targets in the rider's frame (rider_frame()).
	var out := {"pitch": leaning, "grip": 0.85, "w": 1.0, "pole": Vector3(0.7, -0.5, 0.2)}
	if _seat:
		out["hips"] = _local(_seat) + Vector3(0, 0.08, 0.02)
	for side in ["L", "R"]:
		if _pedals.has(side):
			out["foot" + side] = _local(_pedals[side][0]) + Vector3(0, 0.07, 0.05)
		if _grips.get(side):
			out["hand" + side] = _local(_grips[side])
	return out
