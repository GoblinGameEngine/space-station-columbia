extends AnimatableBody3D
class_name RemakeDoor

## A hinged door leaf from a remake building .glb. Built by building_loader.gd from a
## node named  door_<id>[_L|_R]__<p|n>[__locked]  whose origin sits on the hinge axis.
## <p|n> is the sign of rotation about the up axis that swings it open (from the plan).
## Leaves of a double door share <id> and open together.

const OPEN_ANGLE := deg_to_rad(90.0)
const SWING_TIME := 0.7

var door_id := ""
var open_sign := 1.0
var locked := false
var is_open := false
var partners: Array[RemakeDoor] = []
var _closed_rot := 0.0
var _tween: Tween


func setup(id: String, sign: float, is_locked: bool) -> void:
	door_id = id
	open_sign = sign
	locked = is_locked
	_closed_rot = rotation.y
	add_to_group("remake_door")
	sync_to_physics = false
	collision_mask = 0               # (a door is moved, it never needs to find what it touches: with a mask
	                                 # every leaf paired with the walls and floor round it -- thousands of pairs)


## Called by the player's interact ray.
func interact(_by: Node = null) -> String:
	if locked:
		_rattle()
		return "locked"
	var target := not is_open
	_swing(target)
	for p in partners:
		p._swing(target)
	return "open" if target else "closed"


func interact_prompt() -> String:
	if locked:
		return "Locked"
	return "Close door" if is_open else "Open door"


func _swing(to_open: bool) -> void:
	is_open = to_open
	if _tween:
		_tween.kill()
	_tween = create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	var goal := _closed_rot + (open_sign * OPEN_ANGLE if to_open else 0.0)
	_tween.tween_property(self, "rotation:y", goal, SWING_TIME)


func _rattle() -> void:
	if _tween:
		_tween.kill()
	_tween = create_tween()
	for k in 3:
		_tween.tween_property(self, "rotation:y", _closed_rot + open_sign * 0.02, 0.05)
		_tween.tween_property(self, "rotation:y", _closed_rot, 0.05)
