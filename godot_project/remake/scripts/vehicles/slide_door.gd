extends AnimatableBody3D
class_name RemakeSlideDoor

## A vehicle's sliding door leaf (RemakeAirVehicle builds these from the model's door_* nodes).
## E opens or closes it with its partners, like any door in a building -- in flight too.

const SLIDE_TIME := 0.8

var slide := Vector3.ZERO            # local offset when open
var is_open := false
var partners: Array = []
var _closed := Vector3.ZERO
var _tween: Tween
var _snd: AudioStreamPlayer3D


func setup(p_slide: Vector3) -> void:
	slide = p_slide
	_closed = position
	sync_to_physics = false
	add_to_group("remake_door")
	collision_mask = 0               # (a door is moved, it never needs to find what it touches: with a mask
	                                 # every leaf paired with the walls and floor round it -- thousands of pairs)


## Called by the player's interact ray.
func interact(_by: Node = null) -> String:
	var target := not is_open
	_slide(target)
	for p in partners:
		p._slide(target)
	return "open" if target else "closed"


func interact_prompt() -> String:
	return "Close door" if is_open else "Open door"


func _slide(to_open: bool) -> void:
	is_open = to_open
	if _snd == null:
		_snd = AudioStreamPlayer3D.new()
		_snd.stream = load("res://remake/audio/door_slide.wav")
		_snd.unit_size = 3.0
		_snd.max_distance = 40.0
		add_child(_snd)
	_snd.pitch_scale = 1.0 if to_open else 0.92
	_snd.play()
	if _tween:
		_tween.kill()
	_tween = create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_tween.tween_property(self, "position", _closed + (slide if to_open else Vector3.ZERO), SLIDE_TIME)
