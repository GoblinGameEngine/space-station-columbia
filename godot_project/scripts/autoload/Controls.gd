extends Node

## Controllers: a gamepad, or the built-in controls of a handheld -- the Steam Deck (through Steam
## Input), the ROG Ally, the Legion Go and the like all present themselves as a standard (Xbox-layout)
## gamepad.  At start this adds the controller's bindings to the game's actions beside the keyboard
## and mouse ones (the keyboard map in project.godot is untouched), keeps track of which the player
## used last (the on-screen hints follow it), and names buttons as the pad itself labels them.
##
##   On foot                              In a car / pod / van           In an aerostat
##   L stick   move       R stick look    L stick  steer (and throttle)  L stick  thrust, turn
##   A         jump / swim up             RT / LT  accelerate / brake,   RT / A   climb
##   B         swim down                           reverse               LT / B   descend
##   X         use, talk, board           A        handbrake             X        leave the seat
##   RT        attack / fire              X        leave the seat        R stick  look round
##   LB / RB   previous / next weapon     R stick  look round
##   D-pad     weapons 1-3
##   L3        sprint (stays on until you stop)
##   Menu      the Communicator
## In the Communicator: the L stick (or D-pad) moves the stylus, A taps, B goes back, LB / RB change
## tabs, the R stick scrolls, Y opens the System menu, Menu puts it away (GameMenu.gd).

signal device_changed(using_pad: bool)

const STICK_DEADZONE := 0.2
const TRIGGER_DEADZONE := 0.1

var using_pad := false
var pad_style := "xbox"               # "xbox" or "playstation": how its buttons are labelled

# [action, [joypad buttons], [[axis, direction]]]
const PAD := [
	["move_forward", [], [[JOY_AXIS_LEFT_Y, -1.0]]],
	["move_back", [], [[JOY_AXIS_LEFT_Y, 1.0]]],
	["move_left", [], [[JOY_AXIS_LEFT_X, -1.0]]],
	["move_right", [], [[JOY_AXIS_LEFT_X, 1.0]]],
	["look_left", [], [[JOY_AXIS_RIGHT_X, -1.0]]],
	["look_right", [], [[JOY_AXIS_RIGHT_X, 1.0]]],
	["look_up", [], [[JOY_AXIS_RIGHT_Y, -1.0]]],
	["look_down", [], [[JOY_AXIS_RIGHT_Y, 1.0]]],
	["jump", [JOY_BUTTON_A], []],
	["swim_down", [JOY_BUTTON_B], []],
	["interact", [JOY_BUTTON_X], []],
	["shoot", [], [[JOY_AXIS_TRIGGER_RIGHT, 1.0]]],
	["next_weapon", [JOY_BUTTON_RIGHT_SHOULDER], []],
	["prev_weapon", [JOY_BUTTON_LEFT_SHOULDER], []],
	["weapon_slot_1", [JOY_BUTTON_DPAD_LEFT], []],
	["weapon_slot_2", [JOY_BUTTON_DPAD_UP], []],
	["weapon_slot_3", [JOY_BUTTON_DPAD_RIGHT], []],
	["sprint", [JOY_BUTTON_LEFT_STICK], []],
	["toggle_menu", [JOY_BUTTON_START], []],
	# driving and flying (the triggers); pads only -- the keyboard drives with move_forward / move_back
	["accelerate", [], [[JOY_AXIS_TRIGGER_RIGHT, 1.0]]],
	["brake_reverse", [], [[JOY_AXIS_TRIGGER_LEFT, 1.0]]],
]

# what each button is called on the pad in hand
const NAMES := {
	"xbox": {JOY_BUTTON_A: "A", JOY_BUTTON_B: "B", JOY_BUTTON_X: "X", JOY_BUTTON_Y: "Y", JOY_BUTTON_START: "Menu",
		JOY_BUTTON_BACK: "View", JOY_BUTTON_LEFT_SHOULDER: "LB", JOY_BUTTON_RIGHT_SHOULDER: "RB",
		JOY_BUTTON_LEFT_STICK: "L3", JOY_BUTTON_RIGHT_STICK: "R3", JOY_BUTTON_DPAD_UP: "D-pad up",
		JOY_BUTTON_DPAD_DOWN: "D-pad down", JOY_BUTTON_DPAD_LEFT: "D-pad left", JOY_BUTTON_DPAD_RIGHT: "D-pad right",
		"LT": "LT", "RT": "RT", "LS": "L stick", "RS": "R stick"},
	"playstation": {JOY_BUTTON_A: "Cross", JOY_BUTTON_B: "Circle", JOY_BUTTON_X: "Square", JOY_BUTTON_Y: "Triangle",
		JOY_BUTTON_START: "Options", JOY_BUTTON_BACK: "Share", JOY_BUTTON_LEFT_SHOULDER: "L1",
		JOY_BUTTON_RIGHT_SHOULDER: "R1", JOY_BUTTON_LEFT_STICK: "L3", JOY_BUTTON_RIGHT_STICK: "R3",
		JOY_BUTTON_DPAD_UP: "D-pad up", JOY_BUTTON_DPAD_DOWN: "D-pad down", JOY_BUTTON_DPAD_LEFT: "D-pad left",
		JOY_BUTTON_DPAD_RIGHT: "D-pad right", "LT": "L2", "RT": "R2", "LS": "L stick", "RS": "R stick"},
}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for spec in PAD:
		var action: String = spec[0]
		if not InputMap.has_action(action):
			InputMap.add_action(action, STICK_DEADZONE)
		elif action.begins_with("move_") or action.begins_with("look_"):
			InputMap.action_set_deadzone(action, STICK_DEADZONE)
		for b in spec[1]:
			var e := InputEventJoypadButton.new()
			e.button_index = b
			e.device = -1
			InputMap.action_add_event(action, e)
		for ax in spec[2]:
			var m := InputEventJoypadMotion.new()
			m.axis = ax[0]
			m.axis_value = ax[1]
			m.device = -1
			InputMap.action_add_event(action, m)
		if action in ["shoot", "accelerate", "brake_reverse"]:
			InputMap.action_set_deadzone(action, TRIGGER_DEADZONE)
	Input.joy_connection_changed.connect(func(_d, _c): _read_style())
	_read_style()


func _read_style() -> void:
	pad_style = "xbox"
	for d in Input.get_connected_joypads():
		var n := Input.get_joy_name(d).to_lower()
		if "ps4" in n or "ps5" in n or "dualsense" in n or "dualshock" in n or "sony" in n or "playstation" in n:
			pad_style = "playstation"


func _input(event: InputEvent) -> void:
	# which the player is using now: a real stick push or button press counts, stick noise doesn't;
	# a key or a click brings the keyboard back (not mouse motion: the game recentres the pointer, and
	# a handheld's trackpad drifts)
	var pad := false
	var kbm := false
	if event is InputEventJoypadButton and event.pressed:
		pad = true
	elif event is InputEventJoypadMotion and absf(event.axis_value) > 0.5:
		pad = true
	elif event is InputEventKey and event.pressed:
		kbm = true
	elif event is InputEventMouseButton and event.pressed:
		kbm = true
	if pad and not using_pad:
		using_pad = true
		device_changed.emit(true)
	elif kbm and using_pad:
		using_pad = false
		device_changed.emit(false)


func button(b: Variant) -> String:
	## A pad control's name as printed on the pad in hand (b: a JOY_BUTTON_*, or "LT"/"RT"/"LS"/"RS")
	return NAMES[pad_style].get(b, str(b))


func hint(keyboard: String, pad: String) -> String:
	## Whichever of two prompts suits what the player is holding
	return pad if using_pad else keyboard


func look_vector() -> Vector2:
	## The right stick, shaped for aiming: a gentle middle and full speed at the rim (radians a second
	## per unit is the caller's); y down is looking down unless inverted.
	var v := Input.get_vector("look_left", "look_right", "look_up", "look_down")
	var l := v.length()
	if l < 0.001:
		return Vector2.ZERO
	v = v / l * pow(l, 1.8)
	if Settings.invert_look_y:
		v.y = -v.y
	return v
