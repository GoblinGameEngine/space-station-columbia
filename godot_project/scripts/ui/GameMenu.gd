extends CanvasLayer

## The game menu is the player's handheld: a NYNEX Communicator, a portrait mid-90s PDA (the Apple
## Newton MessagePad's and Palm Pilot's upright form) running "The System".  The System keeps
## Windows CE 1.0's way of working -- a desktop of icons, a taskbar whose System button opens a flat
## (non-cascading) menu, full-screen apps with tabs -- and wears the Macintosh System 6 look: Chicago
## type, pinstriped title bars with a close box, rounded push buttons, the grey dither desktop.
##   Station Map (Station, Nearby) · Inventory (Weapons, Items) · Quests (Active, Completed)
##   NPC AI (Setup, Voice, Try it) · Control Panel (Sound, Display, Controls) · Help (Contents, About)
##   System menu: the apps, New Game..., Suspend (back to the game).
## The screen is a 240 x 320 dot-matrix LCD in 4 shades of black on green (ui/pda/lcd.gdshader), the
## green backlight on at night.  It is drawn at a whole number of screen pixels per LCD pixel (2 on
## the Steam Deck), and its type is pixel type drawn at its own size -- ChicagoFLF 12 for the
## system, Pixel Operator 16 for text -- so every letter lands on whole pixels: crisp at any size.
## Below the screen, four hardware keys open the apps (as the Palm Pilot's did) and the power key
## puts the device away.

const SCREEN := Vector2i(240, 320)
const TASKBAR_H := 20
const TITLE_H := 19
const SYS_SIZE := 12                    # ChicagoFLF: crisp at 12
const TEXT_SIZE := 16                   # Pixel Operator: crisp at 16
# the case round the screen, in screen pixels at 800 px of display height
const CASE_TOP := 58.0                  # the forehead: NYNEX, the speaker, the power key
const CASE_BOTTOM := 56.0               # the chin: the bell and COMMUNICATOR
const CASE_SIDE := 26.0
const BEZEL := 9.0                      # the well round the glass
const STRIP := 44.0                     # the soft keys' glass under the screen
const SHADOW := 24.0
const W := Color(1, 1, 1)
const L := Color(0.667, 0.667, 0.667)
const D := Color(0.333, 0.333, 0.333)
const K := Color(0, 0, 0)
const PDA := "res://ui/pda/"

var _is_open := false
var _theme: Theme
var _font: FontFile                     # Pixel Operator 16: text
var _bold: FontFile                     # ChicagoFLF 12: titles, menus, buttons, tabs
var _case_font: Font                    # the case's printing (smooth type, drawn at screen size)
var _case_bold: Font
var _px := 2.0                          # screen pixels per LCD pixel
var _k := 1.0                           # the case's scale

var _dim: ColorRect
var _device: Control
var _hw_keys: Array = []
var _screen_rect: TextureRect
var _vp: SubViewport
var _lcd: ShaderMaterial
var _desk: Control
var _desk_icons := {}
var _taskbar: Control
var _task_btn: Button
var _clock: Label
var _start_menu: Control
var _apps := {}                        # name -> app window Control
var _current := ""
var _msgbox: Control
var _last_click := {}                  # icon -> msec of its last click (double-tap opens)
var _map_station: Control
var _map_nearby: TextureRect
var _map_here: Label
var _map_tex: Texture2D
var _map_overview: Texture2D
var _towns := {}                       # settlement -> Vector2(s, x) centre
var _quest_active: VBoxContainer
var _quest_done: VBoxContainer
var _weapons: VBoxContainer
var _items: VBoxContainer
var _ai_status: Label
var _ai_key_edit: LineEdit
var _ai_clip_row: Control
var _ai_usage: Label
var _ai_say: LineEdit
var _ai_log: VBoxContainer
var _ai_history: Array = []
# a controller in the Communicator: the stylus (an arrow pointer on the LCD) the sticks move
var _stylus: TextureRect
var _stylus_at := Vector2(120, 150)
var _pad_tap := false                  # the tap under way came from a controller's A
var _scroll_t := 0.0
const STYLUS_SPEED := 190.0            # LCD pixels a second at full stick

const APPS := [
	["map", "Station Map", "icon_map.png"],
	["inventory", "Inventory", "icon_inventory.png"],
	["quests", "Quests", "icon_quests.png"],
	["ai", "NPC AI", "icon_ai.png"],
	["summon", "Summon Aerostat", "icon_summon.png"],
	["nav", "Navigation", "icon_nav.png"],
	["control", "Control Panel", "icon_control.png"],
	["help", "Help", "icon_help.png"],
]


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 10
	_build_theme()
	_build_device()
	_build_system()
	_set_visible(false)
	QuestManager.quest_started.connect(func(_id): _refresh_quests())
	QuestManager.quest_updated.connect(func(_id): _refresh_quests())
	QuestManager.quest_completed.connect(func(_id): _refresh_quests())
	QuestManager.quest_turned_in.connect(func(_id): _refresh_quests())
	QuestManager.tracked_quest_changed.connect(func(_id): _refresh_quests())
	Inventory.changed.connect(_refresh_inventory)
	WeaponManager.loadout_changed.connect(_refresh_inventory)
	WeaponManager.weapon_equipped.connect(func(_id): _refresh_inventory())
	NpcAI.key_changed.connect(_refresh_ai)
	get_viewport().size_changed.connect(_layout)


func _unhandled_input(event: InputEvent) -> void:
	# (not over the loading screen)
	if event.is_action_pressed("toggle_menu") and not StationGeo.loading:
		set_open(not _is_open)


func _input(event: InputEvent) -> void:
	## Typing goes to the text box that has the focus on The System's screen (the screen is its own
	## viewport, which only hears what it's handed).  Esc there just leaves the box.
	## A controller works the screen through the stylus (_pad_input).
	if not _is_open:
		return
	if event is InputEventJoypadButton:
		_pad_input(event)
		return
	if not event is InputEventKey:
		return
	var f := _vp.gui_get_focus_owner()
	if f is LineEdit:
		if event.pressed and event.physical_keycode == KEY_ESCAPE:
			f.release_focus()
		else:
			_vp.push_input(event)
		get_viewport().set_input_as_handled()


func set_open(open: bool) -> void:
	_is_open = open
	_set_visible(open)
	get_tree().paused = open
	if open:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		_layout()
		if Controls.using_pad:
			_set_stylus(Vector2(SCREEN) * 0.5)
		_refresh_quests()
		_refresh_inventory()
		_refresh_map()
		_refresh_ai()
		_update_backlight()
		_update_clock()
	else:
		_start_menu.visible = false
		var player := get_tree().get_first_node_in_group("player")
		if player and player.has_method("recapture_mouse"):
			player.recapture_mouse()
		else:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _set_visible(v: bool) -> void:
	# the full-screen dimmer MUST be hidden when closed, or it eats mouse motion (mouse-look)
	_dim.visible = v
	_device.visible = v
	_vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS if v else SubViewport.UPDATE_DISABLED


func _process(delta: float) -> void:
	if not _is_open:
		return
	_move_stylus(delta)
	_update_clock()
	_update_backlight()
	if _current == "map":
		_map_station.queue_redraw()
	if _current == "summon":
		_refresh_ride()
	if _current == "nav" and _nav_map:
		if _nav_map.follow:
			var p := _player_sx()
			_nav_map.view = Vector2(p.x, p.y)
		_nav_map.queue_redraw()


# ------------------------------------------------------------------ a controller
func _move_stylus(delta: float) -> void:
	## The left stick moves the stylus, the right stick scrolls where it points.
	_stylus.visible = Controls.using_pad
	# one pointer at a time: the stylus with a controller, the system's with a mouse
	var want := Input.MOUSE_MODE_HIDDEN if Controls.using_pad else Input.MOUSE_MODE_VISIBLE
	if Input.mouse_mode != want:
		Input.mouse_mode = want
	if not Controls.using_pad:
		return
	var v := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	if v.length() > 0.0:
		v = v.normalized() * pow(minf(v.length(), 1.0), 1.6)          # fine near the middle, quick at the rim
		_set_stylus(_stylus_at + v * STYLUS_SPEED * delta)
	var sc := Input.get_axis("look_up", "look_down")
	_scroll_t -= delta
	if absf(sc) > 0.3 and _scroll_t <= 0.0:
		_scroll_t = lerpf(0.18, 0.05, absf(sc))
		for pressed in [true, false]:
			var w := InputEventMouseButton.new()
			w.button_index = MOUSE_BUTTON_WHEEL_DOWN if sc > 0.0 else MOUSE_BUTTON_WHEEL_UP
			w.pressed = pressed
			w.position = _stylus_at.floor()
			w.global_position = w.position
			_vp.push_input(w, true)


func _set_stylus(at: Vector2) -> void:
	var p := at.clamp(Vector2.ZERO, Vector2(SCREEN) - Vector2.ONE)
	if p.floor() != _stylus_at.floor():
		var m := InputEventMouseMotion.new()
		m.position = p.floor()
		m.global_position = m.position
		m.relative = p.floor() - _stylus_at.floor()
		m.button_mask = MOUSE_BUTTON_MASK_LEFT if Input.is_joy_button_pressed(0, JOY_BUTTON_A) else 0
		_vp.push_input(m, true)
	_stylus_at = p
	_stylus.position = p.floor()
	_stylus.move_to_front()


func _pad_input(e: InputEventJoypadButton) -> void:
	## A taps (hold and move to drag), B goes back, LB / RB change tabs, Y the System menu, the D-pad
	## nudges the stylus; Menu (toggle_menu) is left to put the device away.
	if e.button_index == JOY_BUTTON_START:
		return
	get_viewport().set_input_as_handled()
	match e.button_index:
		JOY_BUTTON_A:
			_pad_tap = true
			var b := InputEventMouseButton.new()
			b.button_index = MOUSE_BUTTON_LEFT
			b.pressed = e.pressed
			b.button_mask = MOUSE_BUTTON_MASK_LEFT if e.pressed else 0
			b.position = _stylus_at.floor()
			b.global_position = b.position
			_vp.push_input(b, true)
			_pad_tap = false
			if not e.pressed and _vp.gui_get_focus_owner() is LineEdit:
				_show_keyboard()
		JOY_BUTTON_B:
			if e.pressed:
				_back()
		JOY_BUTTON_Y:
			if e.pressed:
				_start_menu.visible = not _start_menu.visible
		JOY_BUTTON_LEFT_SHOULDER, JOY_BUTTON_RIGHT_SHOULDER:
			if e.pressed and _current != "":
				var tabs := _apps[_current].get_child(2) as TabContainer
				if tabs:
					var step := 1 if e.button_index == JOY_BUTTON_RIGHT_SHOULDER else -1
					tabs.current_tab = posmod(tabs.current_tab + step, tabs.get_tab_count())
		JOY_BUTTON_DPAD_UP, JOY_BUTTON_DPAD_DOWN, JOY_BUTTON_DPAD_LEFT, JOY_BUTTON_DPAD_RIGHT:
			if e.pressed:
				var d := {JOY_BUTTON_DPAD_UP: Vector2.UP, JOY_BUTTON_DPAD_DOWN: Vector2.DOWN,
					JOY_BUTTON_DPAD_LEFT: Vector2.LEFT, JOY_BUTTON_DPAD_RIGHT: Vector2.RIGHT}
				_set_stylus(_stylus_at + d[e.button_index] * 6.0)


func _back() -> void:
	## B: the alert, then the System menu, then the app, then the device itself
	var f := _vp.gui_get_focus_owner()
	if f is LineEdit:
		f.release_focus()
	elif _msgbox.visible:
		_msgbox.visible = false
	elif _start_menu.visible:
		_start_menu.visible = false
	elif _current != "":
		_close_app()
	else:
		set_open(false)


func _show_keyboard() -> void:
	## A text box tapped from a controller: the handheld's on-screen keyboard (Steam's on the Steam
	## Deck -- running under Steam; Windows' touch keyboard on the Ally, the Legion Go and the like).
	if DisplayServer.has_feature(DisplayServer.FEATURE_VIRTUAL_KEYBOARD):
		DisplayServer.virtual_keyboard_show((_vp.gui_get_focus_owner() as LineEdit).text)
	elif OS.get_name() == "Windows":
		var tabtip := "C:/Program Files/Common Files/microsoft shared/ink/TabTip.exe"
		if FileAccess.file_exists(tabtip):
			OS.create_process(tabtip, [])
	elif OS.get_environment("SteamAppId") != "" or OS.get_environment("SteamGameId") != "" or OS.get_environment("SteamDeck") != "":
		OS.shell_open("steam://open/keyboard")


# ------------------------------------------------------------------ look
func _pixel_font(path: String) -> FontFile:
	## A pixel font drawn at its own size: no smoothing, no hinting, whole-pixel positions.
	var f: FontFile = (load(path) as FontFile).duplicate()
	f.antialiasing = TextServer.FONT_ANTIALIASING_NONE
	f.hinting = TextServer.HINTING_NONE
	f.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_DISABLED
	f.generate_mipmaps = false
	return f


func _flat(c: Color, border := Color.TRANSPARENT, bw := 0, radius := 0, margin := 2) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = c
	s.border_color = border
	s.set_border_width_all(bw)
	s.set_corner_radius_all(radius)
	s.corner_detail = 3
	s.anti_aliasing = false
	s.set_content_margin_all(margin)
	return s


func _image(rows: Array) -> ImageTexture:
	## A little picture from rows of K / D / L / W / . (clear)
	var img := Image.create(rows[0].length(), rows.size(), false, Image.FORMAT_RGBA8)
	var pal := {"K": K, "D": D, "L": L, "W": W, ".": Color(0, 0, 0, 0)}
	for y in rows.size():
		for x in rows[y].length():
			img.set_pixel(x, y, pal[rows[y][x]])
	return ImageTexture.create_from_image(img)


func _checker() -> StyleBoxTexture:
	## The System 6 grey: a 50% dither
	var s := StyleBoxTexture.new()
	s.texture = _image(["LW", "WL"])
	s.axis_stretch_horizontal = StyleBoxTexture.AXIS_STRETCH_MODE_TILE
	s.axis_stretch_vertical = StyleBoxTexture.AXIS_STRETCH_MODE_TILE
	return s


func _build_theme() -> void:
	_font = _pixel_font(PDA + "PixelOperator.ttf")
	_bold = _pixel_font(PDA + "ChicagoFLF.ttf")
	_case_font = load(PDA + "DejaVuSans.ttf")
	_case_bold = load(PDA + "DejaVuSans-Bold.ttf")
	_theme = Theme.new()
	_theme.default_font = _font
	_theme.default_font_size = TEXT_SIZE
	for t in ["Button", "TabContainer", "TabBar", "OptionButton", "PopupMenu", "CheckBox"]:
		_theme.set_font("font", t, _bold)
		_theme.set_font_size("font_size", t, SYS_SIZE)
	for t in ["Label", "Button", "CheckBox", "TabContainer", "TabBar", "RichTextLabel", "LineEdit", "OptionButton", "PopupMenu"]:
		_theme.set_color("font_color", t, K)
	_theme.set_color("default_color", "RichTextLabel", K)
	# push buttons: rounded, black edged; pressed ones go black (System 6)
	for t in ["Button", "OptionButton"]:
		_theme.set_color("font_hover_color", t, K)
		_theme.set_color("font_focus_color", t, K)
		_theme.set_color("font_pressed_color", t, W)
		_theme.set_color("font_hover_pressed_color", t, W)
		_theme.set_color("font_disabled_color", t, L)
		_theme.set_stylebox("normal", t, _flat(W, K, 1, 5, 3))
		_theme.set_stylebox("hover", t, _flat(W, K, 1, 5, 3))
		_theme.set_stylebox("pressed", t, _flat(K, K, 1, 5, 3))
		_theme.set_stylebox("hover_pressed", t, _flat(K, K, 1, 5, 3))
		_theme.set_stylebox("disabled", t, _flat(W, L, 1, 5, 3))
		_theme.set_stylebox("focus", t, StyleBoxEmpty.new())
	_theme.set_icon("arrow", "OptionButton", _image(["KKKKKKK", ".KKKKK.", "..KKK..", "...K..."]))
	# tabs: folder tabs over a white panel
	var tab_on := _flat(W, K, 1, 0, 3)
	tab_on.border_width_bottom = 0
	tab_on.corner_radius_top_left = 3
	tab_on.corner_radius_top_right = 3
	var tab_off := _flat(L, K, 1, 0, 3)
	tab_off.corner_radius_top_left = 3
	tab_off.corner_radius_top_right = 3
	_theme.set_stylebox("tab_selected", "TabContainer", tab_on)
	_theme.set_stylebox("tab_unselected", "TabContainer", tab_off)
	_theme.set_stylebox("tab_hovered", "TabContainer", tab_off)
	_theme.set_stylebox("panel", "TabContainer", _flat(W, K, 1, 0, 4))
	_theme.set_color("font_selected_color", "TabContainer", K)
	_theme.set_color("font_unselected_color", "TabContainer", K)
	_theme.set_color("font_hovered_color", "TabContainer", K)
	_theme.set_constant("side_margin", "TabContainer", 0)
	_theme.set_stylebox("panel", "PanelContainer", _flat(W, K, 1, 0, 2))
	_theme.set_stylebox("panel", "ScrollContainer", StyleBoxEmpty.new())
	# scroll bars: the grey dither track, a white thumb, arrow boxes
	_theme.set_stylebox("scroll", "VScrollBar", _checker())
	_theme.set_stylebox("scroll_focus", "VScrollBar", _checker())
	for st in ["grabber", "grabber_highlight", "grabber_pressed"]:
		_theme.set_stylebox(st, "VScrollBar", _flat(W, K, 1, 0, 5))
	_theme.set_icon("decrement", "VScrollBar", _image(["KKKKKKKKKKK", "KWWWWWWWWWK", "KWWWWKWWWWK", "KWWWKKKWWWK",
		"KWWKKKKKWWK", "KWKKKKKKKWK", "KWWWKKKWWWK", "KWWWKKKWWWK", "KWWWWWWWWWK", "KKKKKKKKKKK"]))
	_theme.set_icon("increment", "VScrollBar", _image(["KKKKKKKKKKK", "KWWWWWWWWWK", "KWWWKKKWWWK", "KWWWKKKWWWK",
		"KWKKKKKKKWK", "KWWKKKKKWWK", "KWWWKKKWWWK", "KWWWWKWWWWK", "KWWWWWWWWWK", "KKKKKKKKKKK"]))
	for st in ["decrement_highlight", "decrement_pressed"]:
		_theme.set_icon(st, "VScrollBar", _theme.get_icon("decrement", "VScrollBar"))
	for st in ["increment_highlight", "increment_pressed"]:
		_theme.set_icon(st, "VScrollBar", _theme.get_icon("increment", "VScrollBar"))
	# sliders: a thin track and a white knob
	_theme.set_stylebox("slider", "HSlider", _flat(W, K, 1, 0, 1))
	_theme.set_stylebox("grabber_area", "HSlider", _flat(D))
	_theme.set_stylebox("grabber_area_highlight", "HSlider", _flat(D))
	var knob := _image(["KKKKKKKKK", "KWWWWWWWK", "KWWWWWWWK", "KWWWWWWWK", "KWKKKKKWK", "KWWWWWWWK", "KWKKKKKWK",
		"KWWWWWWWK", "KWWWWWWWK", "KWWWWWWWK", "KKKKKKKKK"])
	_theme.set_icon("grabber", "HSlider", knob)
	_theme.set_icon("grabber_highlight", "HSlider", knob)
	# text boxes
	_theme.set_stylebox("normal", "LineEdit", _flat(W, K, 1, 0, 3))
	_theme.set_stylebox("focus", "LineEdit", _flat(W, K, 2, 0, 3))
	_theme.set_stylebox("read_only", "LineEdit", _flat(W, L, 1, 0, 3))
	_theme.set_color("caret_color", "LineEdit", K)
	_theme.set_color("selection_color", "LineEdit", L)
	_theme.set_color("font_selected_color", "LineEdit", K)
	_theme.set_color("font_placeholder_color", "LineEdit", L)
	# menus (the OptionButton's list)
	_theme.set_stylebox("panel", "PopupMenu", _flat(W, K, 1, 0, 2))
	_theme.set_stylebox("hover", "PopupMenu", _flat(K))
	_theme.set_color("font_hover_color", "PopupMenu", W)
	var line := StyleBoxLine.new()
	line.color = K
	line.thickness = 1
	_theme.set_stylebox("separator", "HSeparator", line)
	_theme.set_constant("separation", "HSeparator", 5)


# ------------------------------------------------------------------ the device
class DeviceBody extends Control:
	## The NYNEX Communicator's case, after the Apple Newton MessagePad (ui/pda/case.gdshader draws
	## the plastic).  This draws the case and holds the printing layer.
	func _draw() -> void:
		var m := SHADOW
		draw_rect(Rect2(Vector2(-m, -m), size + Vector2(m, m) * 2.0), Color.WHITE)


class CasePrint extends Control:
	## What's printed on the case and its glass: NYNEX centred on the forehead; the Bell bell and
	## COMMUNICATOR centred on the chin (tools/pda_case.py); on the glass strip under the screen, the
	## soft keys -- the apps' pictures and names in the LCD's ink, as the Newton's were printed.
	var font: Font
	var k := 1.0
	var nynex: Texture2D
	var bell: Texture2D
	var word: Texture2D
	var forehead := Rect2()
	var chin := Rect2()
	var strip := Rect2()
	var power := Rect2()
	var keys: Array = []                  # [texture, label]
	const SILVER := Color(0.8, 0.81, 0.83)
	const INK := Color(0.07, 0.1, 0.06, 0.85)

	func _mark(tex: Texture2D, h: float, at: Vector2, c := SILVER) -> float:
		var w := h * tex.get_width() / tex.get_height()
		draw_texture_rect(tex, Rect2(at.round(), Vector2(w, h)), false, c)
		return w

	func _draw() -> void:
		var cap := 16.0 * k
		var nw := cap * nynex.get_width() / nynex.get_height()
		_mark(nynex, cap, forehead.get_center() - Vector2(nw, cap) * 0.5)
		var wh := 11.5 * k
		var ww := wh * word.get_width() / word.get_height()
		var bh := 17.0 * k
		var gap := 6.0 * k
		var x := chin.get_center().x - (bh + gap + ww) * 0.5
		var cy := chin.get_center().y
		_mark(bell, bh, Vector2(x, cy - bh * 0.5))
		_mark(word, wh, Vector2(x + bh + gap, cy - wh * 0.5))
		# the power key's name, under it
		var fs := maxi(10, int(10 * k))
		draw_string(font, Vector2(power.position.x - 20 * k, power.end.y + fs + 3 * k), "POWER", HORIZONTAL_ALIGNMENT_CENTER,
			power.size.x + 40 * k, fs, Color(0.62, 0.64, 0.67))
		# the soft keys
		var n := keys.size()
		var icon := minf(24.0 * k, strip.size.y * 0.55)
		var ls := maxi(10, int(11 * k))
		for i in n:
			var cx := strip.position.x + strip.size.x * (i + 0.5) / n
			var tex: Texture2D = keys[i][0]
			draw_texture_rect(tex, Rect2(Vector2(cx - icon * 0.5, strip.position.y + 4 * k).round(), Vector2(icon, icon)), false, INK)
			draw_string(font, Vector2(cx - 40 * k, strip.end.y - 5 * k).round(), keys[i][1], HORIZONTAL_ALIGNMENT_CENTER, 80 * k, ls, INK)


func _soft_key(on_press: Callable) -> Button:
	## an invisible touch area over a printed soft key (it darkens a moment when pressed)
	var b := Button.new()
	b.focus_mode = Control.FOCUS_NONE
	b.flat = true
	for st in ["normal", "hover", "focus", "disabled"]:
		b.add_theme_stylebox_override(st, StyleBoxEmpty.new())
	var dn := StyleBoxFlat.new()
	dn.bg_color = Color(0, 0, 0, 0.18)
	dn.set_corner_radius_all(4)
	b.add_theme_stylebox_override("pressed", dn)
	b.add_theme_stylebox_override("hover_pressed", dn)
	b.pressed.connect(on_press)
	return b


func _power_key() -> Button:
	## the power key: a small dark rubber key set into the forehead
	var b := Button.new()
	b.focus_mode = Control.FOCUS_NONE
	var up := StyleBoxFlat.new()
	up.bg_color = Color(0.1, 0.105, 0.11)
	up.set_corner_radius_all(6)
	up.border_color = Color(0.05, 0.05, 0.055)
	up.set_border_width_all(1)
	up.border_width_bottom = 2
	var dn := up.duplicate()
	dn.bg_color = Color(0.07, 0.075, 0.08)
	dn.border_width_bottom = 1
	dn.border_width_top = 2
	for st in ["normal", "hover", "focus"]:
		b.add_theme_stylebox_override(st, up)
	b.add_theme_stylebox_override("pressed", dn)
	b.add_theme_stylebox_override("hover_pressed", dn)
	b.pressed.connect(func(): set_open(false))
	return b


var _print: CasePrint
var _case_mat: ShaderMaterial


func _build_device() -> void:
	_dim = ColorRect.new()
	_dim.color = Color(0, 0, 0, 0.55)
	_dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_dim)
	var body := DeviceBody.new()
	_case_mat = ShaderMaterial.new()
	_case_mat.shader = load(PDA + "case.gdshader")
	body.material = _case_mat
	body.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(body)
	_device = body
	_print = CasePrint.new()
	_print.font = _case_bold
	_print.nynex = _mipmapped(PDA + "case_nynex.png")
	_print.bell = _mipmapped(PDA + "case_bell.png")
	_print.word = _mipmapped(PDA + "case_communicator.png")
	for spec in [["icon_map.png", "MAP"], ["icon_inventory.png", "ITEMS"], ["icon_quests.png", "QUESTS"], ["icon_control.png", "SETUP"]]:
		_print.keys.append([_ink(PDA + spec[0]), spec[1]])
	_print.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	_print.mouse_filter = Control.MOUSE_FILTER_IGNORE
	body.add_child(_print)
	# the screen: The System renders into a 240 x 320 viewport; the LCD shader draws it, whole
	# screen pixels to each LCD pixel
	_vp = SubViewport.new()
	_vp.size = SCREEN
	_vp.transparent_bg = false
	_vp.handle_input_locally = true
	_vp.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	_vp.gui_embed_subwindows = true
	_vp.snap_2d_transforms_to_pixel = true
	_vp.snap_2d_vertices_to_pixel = true
	body.add_child(_vp)
	_screen_rect = TextureRect.new()
	_screen_rect.texture = _vp.get_texture()
	_screen_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_screen_rect.stretch_mode = TextureRect.STRETCH_SCALE
	_screen_rect.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_lcd = ShaderMaterial.new()
	_lcd.shader = load(PDA + "lcd.gdshader")
	_lcd.set_shader_parameter("screen_px", Vector2(SCREEN))
	_screen_rect.material = _lcd
	_screen_rect.mouse_filter = Control.MOUSE_FILTER_STOP
	_screen_rect.gui_input.connect(_screen_input)
	body.add_child(_screen_rect)
	# the soft keys printed under the screen, and the power key
	for app in ["map", "inventory", "quests", "control"]:
		var b := _soft_key(_open_app.bind(app))
		body.add_child(b)
		_hw_keys.append(b)
	var pw := _power_key()
	body.add_child(pw)
	_hw_keys.append(pw)
	_layout()


func _mipmapped(path: String) -> ImageTexture:
	## the case's printing is drawn much smaller than its artwork: smooth it down
	var img := (load(path) as Texture2D).get_image()
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)


func _ink(path: String) -> ImageTexture:
	## an icon as printing: its dark lines kept (as coverage), its white fill left out
	var img := (load(path) as Texture2D).get_image()
	img.convert(Image.FORMAT_RGBA8)
	for y in img.get_height():
		for x in img.get_width():
			var c := img.get_pixel(x, y)
			img.set_pixel(x, y, Color(1, 1, 1, c.a * clampf(1.4 - c.get_luminance() * 1.5, 0.0, 1.0)))
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)


func _screen_input(event: InputEvent) -> void:
	## Taps and drags on the glass go to The System, in LCD pixels.
	if event is InputEventMouse:
		var ev: InputEventMouse = event.duplicate()
		ev.position = (event.position / _px).floor()
		ev.global_position = ev.position
		_vp.push_input(ev, true)


func _layout() -> void:
	## Size the device to the display: the LCD at the largest whole number of screen pixels per LCD
	## pixel that fits, the case round it scaled smoothly.
	if _device == null:
		return
	var vs := get_viewport().get_visible_rect().size
	_k = clampf(vs.y / 800.0, 0.6, 3.0)
	var case_w := 2.0 * (CASE_SIDE + BEZEL) * _k
	var case_h := (CASE_TOP + CASE_BOTTOM + 2.0 * BEZEL + STRIP) * _k
	# the whole device on the display, its screen as big as that allows: a whole number of screen
	# pixels per LCD pixel when that's within 8% of it (perfectly sharp), else the exact size, the
	# LCD shader keeping each dot a solid block with a one-pixel soft edge
	var fit := minf((vs.y * 0.96 - case_h) / SCREEN.y, (vs.x * 0.95 - case_w) / SCREEN.x)
	_px = maxf(0.5, floorf(fit) if fit >= 1.0 and fit - floorf(fit) < 0.08 * fit else fit)
	var lcd := (Vector2(SCREEN) * _px).round()
	var body := (lcd + Vector2(case_w, case_h)).round()
	_device.size = body
	_device.scale = Vector2.ONE
	_device.position = ((vs - body) * 0.5).floor()
	_screen_rect.position = (Vector2(CASE_SIDE + BEZEL, CASE_TOP + BEZEL) * _k).floor()
	_screen_rect.size = lcd
	var lr := Rect2(_screen_rect.position, lcd)
	var well := Rect2(lr.position - Vector2(BEZEL, BEZEL) * _k, lr.size + Vector2(2.0 * BEZEL, 2.0 * BEZEL + STRIP) * _k)
	var strip := Rect2(Vector2(lr.position.x, lr.end.y + 4 * _k), Vector2(lr.size.x, (STRIP - 2.0) * _k))
	var forehead := Rect2(Vector2.ZERO, Vector2(body.x, well.position.y))
	var chin := Rect2(Vector2(0, well.end.y), Vector2(body.x, body.y - well.end.y))
	var power := Rect2(Vector2(well.position.x + 6 * _k, forehead.size.y * 0.5 - 8 * _k), Vector2(30, 11) * _k)
	_case_mat.set_shader_parameter("body_size", body)
	_case_mat.set_shader_parameter("radius", 24.0 * _k)
	_case_mat.set_shader_parameter("k", _k)
	_case_mat.set_shader_parameter("well", Vector4(well.position.x, well.position.y, well.size.x, well.size.y))
	_case_mat.set_shader_parameter("well_radius", 5.0 * _k)
	_case_mat.set_shader_parameter("strip", Vector4(strip.position.x, strip.position.y, strip.size.x, strip.size.y))
	var gw := 7.0 * 6 * _k
	_case_mat.set_shader_parameter("grille", Vector4(well.end.x - gw - 4 * _k, forehead.size.y * 0.5 - 10.5 * _k, gw, 21.0 * _k))
	_case_mat.set_shader_parameter("silo", Vector4(5 * _k, well.position.y + 30 * _k, 7 * _k, well.size.y - 60 * _k))
	_device.queue_redraw()
	_print.size = body
	_print.k = _k
	_print.forehead = forehead
	_print.chin = chin
	_print.strip = strip
	_print.power = power
	_print.queue_redraw()
	for i in 4:
		var b: Button = _hw_keys[i]
		b.size = Vector2(strip.size.x / 4.0 - 4 * _k, strip.size.y).round()
		b.position = Vector2(strip.position.x + strip.size.x * i / 4.0 + 2 * _k, strip.position.y).floor()
	var pw: Button = _hw_keys[4]
	pw.size = power.size.round()
	pw.position = power.position.floor()
	_lcd.set_shader_parameter("px_scale", float(_px))


func _update_backlight() -> void:
	## The backlight comes on at night (and fades in and out with dusk and dawn).
	var bl := 0.0
	var sky: Node = null
	var scene := get_tree().current_scene
	if scene:
		sky = scene.get("sky_system")
	if sky:
		var t: float = sky.time_of_day
		if t < DaySkySystem.DAWN_START or t > DaySkySystem.DUSK_END:
			bl = 1.0
		elif t < DaySkySystem.DAY_START:
			bl = 1.0 - (t - DaySkySystem.DAWN_START) / (DaySkySystem.DAY_START - DaySkySystem.DAWN_START)
		elif t > DaySkySystem.DAY_END:
			bl = (t - DaySkySystem.DAY_END) / (DaySkySystem.DUSK_END - DaySkySystem.DAY_END)
	_lcd.set_shader_parameter("backlight", clampf(bl, 0.0, 1.0))
	_case_mat.set_shader_parameter("backlight", clampf(bl, 0.0, 1.0))


func _update_clock() -> void:
	var scene := get_tree().current_scene
	var sky: Node = scene.get("sky_system") if scene else null
	var t: float = sky.time_of_day if sky else 0.5
	var mins := int(t * 24.0 * 60.0)
	var h := (mins / 60) % 24
	_clock.text = "%d:%02d %s" % [12 if h % 12 == 0 else h % 12, mins % 60, "AM" if h < 12 else "PM"]


# ------------------------------------------------------------------ The System
class MacTitle extends Control:
	## A System 6 title bar: pinstripes, the close box on the left, the title centred on a white
	## band, and (in the zoom box's place) a help box.
	signal close_pressed
	signal help_pressed
	var title := ""
	var font: Font
	var font_size := 12
	var _down := ""

	func _frame(r: Rect2, c: Color) -> void:
		draw_rect(Rect2(r.position, Vector2(r.size.x, 1)), c)
		draw_rect(Rect2(r.position + Vector2(0, r.size.y - 1), Vector2(r.size.x, 1)), c)
		draw_rect(Rect2(r.position, Vector2(1, r.size.y)), c)
		draw_rect(Rect2(r.position + Vector2(r.size.x - 1, 0), Vector2(1, r.size.y)), c)

	func close_box() -> Rect2:
		return Rect2(8, 4, 11, 11)

	func help_box() -> Rect2:
		return Rect2(size.x - 19, 4, 11, 11)

	func _draw() -> void:
		draw_rect(Rect2(Vector2.ZERO, size), Color.WHITE)
		for y in range(4, int(size.y) - 4, 2):
			draw_rect(Rect2(1, y, size.x - 2, 1), Color.BLACK)
		draw_rect(Rect2(0, size.y - 1, size.x, 1), Color.BLACK)
		for spec in [[close_box(), "close"], [help_box(), "help"]]:
			var r: Rect2 = spec[0]
			draw_rect(r.grow(1), Color.WHITE)
			_frame(r, Color.BLACK)
			if _down == spec[1]:
				draw_rect(r.grow(-2), Color.BLACK)
		# the help box's "?"
		var h := help_box().position + Vector2(3, 2)
		for p in [Vector2(1, 0), Vector2(2, 0), Vector2(3, 0), Vector2(0, 1), Vector2(4, 1), Vector2(4, 2), Vector2(3, 3),
				Vector2(2, 4), Vector2(2, 6)]:
			draw_rect(Rect2(h + p, Vector2.ONE), Color.WHITE if _down == "help" else Color.BLACK)
		var tw := font.get_string_size(title, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
		var tx := floorf((size.x - tw) * 0.5)
		draw_rect(Rect2(tx - 6, 1, tw + 12, size.y - 2), Color.WHITE)
		var base := floorf((size.y - font.get_height(font_size)) * 0.5) + font.get_ascent(font_size)
		draw_string(font, Vector2(tx, base), title, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color.BLACK)

	func _gui_input(e: InputEvent) -> void:
		if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT:
			var hit := ""
			if close_box().grow(2).has_point(e.position):
				hit = "close"
			elif help_box().grow(2).has_point(e.position):
				hit = "help"
			if e.pressed:
				_down = hit
			else:
				if hit != "" and hit == _down:
					if hit == "close":
						close_pressed.emit()
					else:
						help_pressed.emit()
				_down = ""
			queue_redraw()
			accept_event()


class DeskIcon extends Control:
	## A desktop icon: the picture, and its name on a white label under it; the label goes black
	## when the icon is selected (the Finder's way).
	signal activated
	var tex: Texture2D
	var text := ""
	var font: Font
	var font_size := 16
	var selected := false

	func _draw() -> void:
		var ix := floorf((size.x - tex.get_width()) * 0.5)
		draw_texture(tex, Vector2(ix, 0))
		if selected:
			draw_rect(Rect2(ix, 0, tex.get_width(), tex.get_height()), Color(0, 0, 0, 0.5))
		var lines := text.split("\n")
		var y := float(tex.get_height() + 2)
		for line in lines:
			var tw := font.get_string_size(line, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
			var tx := floorf((size.x - tw) * 0.5)
			var hgt := font.get_height(font_size)
			draw_rect(Rect2(tx - 2, y, tw + 4, hgt), Color.BLACK if selected else Color.WHITE)
			draw_string(font, Vector2(tx, y + font.get_ascent(font_size)), line, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size,
				Color.WHITE if selected else Color.BLACK)
			y += hgt

	func _gui_input(e: InputEvent) -> void:
		if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT and e.pressed:
			activated.emit()
			accept_event()


func _build_system() -> void:
	var root := Control.new()
	root.theme = _theme
	root.size = Vector2(SCREEN)
	_vp.add_child(root)
	# the desktop: the grey dither, the icons
	_desk = Panel.new()
	_desk.size = Vector2(SCREEN.x, SCREEN.y - TASKBAR_H)
	_desk.add_theme_stylebox_override("panel", _checker())
	_desk.gui_input.connect(_desk_input)
	for i in APPS.size():
		var ic := DeskIcon.new()
		ic.tex = load(PDA + APPS[i][2])
		ic.text = String(APPS[i][1]).replace(" ", "\n") if String(APPS[i][1]).length() > 10 else APPS[i][1]
		ic.font = _font
		ic.font_size = TEXT_SIZE
		ic.position = Vector2(4 + (i % 3) * 78, 10 + (i / 3) * 84)
		ic.size = Vector2(76, 72)
		ic.activated.connect(_icon_tapped.bind(APPS[i][0]))
		_desk.add_child(ic)
		_desk_icons[APPS[i][0]] = ic
	root.add_child(_desk)
	# the apps
	_apps["map"] = _app("Station Map", _map_tabs(), "The station's map.  Station: the whole ring, north (the Marlowe end) up.  Nearby: the kilometre round you.")
	_apps["inventory"] = _app("Inventory", _inventory_tabs(), "What you carry.  Weapons: tap Equip to arm one.")
	_apps["quests"] = _app("Quests", _quest_tabs(), "Your tasks.  Tap Track to follow one on the map.")
	_apps["ai"] = _app("NPC AI", _ai_tabs(), "The station's people talk through an AI service.  Setup: get a free Groq key and paste it in.  Voice: choose the model.  Try it: talk to someone.")
	_apps["summon"] = _app("Summon Aerostat", _summon_tabs(), "Call an aerostat to you.  Tap Request: the nearest free one (the red one) comes down and lands near you.  Deliver Station Wagon: a car set down in front of you.  Drag the map to look round, + and - to zoom, Center to follow yourself again.")
	_apps["nav"] = _app("Navigation", _nav_tabs(), "The political map: whose law runs where (the dotted shades), town limits, roads, tram lines.  Drag to look round, + and - to zoom: the closer, the more is named.  Boxed T: a fast-travel tram stop -- tap it, or pick a town under Travel.  Law: the rules where you stand.")
	_apps["control"] = _app("Control Panel", _control_tabs(), "Sound, Display and Controls settings.")
	_apps["help"] = _app("Help", _help_tabs(), "The System Help.")
	for a in _apps.values():
		a.visible = false
		root.add_child(a)
	# the taskbar
	_taskbar = PanelContainer.new()
	_taskbar.position = Vector2(0, SCREEN.y - TASKBAR_H)
	_taskbar.size = Vector2(SCREEN.x, TASKBAR_H)
	var tb := _flat(W, K, 0, 0, 1)
	tb.border_width_top = 1
	_taskbar.add_theme_stylebox_override("panel", tb)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 3)
	_taskbar.add_child(row)
	var sysb := Button.new()
	sysb.text = "System"
	sysb.icon = load(PDA + "system_logo.png")
	sysb.add_theme_constant_override("h_separation", 3)
	for st in ["normal", "hover", "pressed", "hover_pressed"]:
		var sb: StyleBoxFlat = _theme.get_stylebox(st, "Button").duplicate()
		sb.content_margin_top = 0
		sb.content_margin_bottom = 0
		sysb.add_theme_stylebox_override(st, sb)
	sysb.pressed.connect(func(): _start_menu.visible = not _start_menu.visible)
	row.add_child(sysb)
	_task_btn = Button.new()
	_task_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_task_btn.clip_text = true
	_task_btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
	_task_btn.visible = false
	for st in ["normal", "hover", "pressed", "hover_pressed"]:
		var sb: StyleBoxFlat = _theme.get_stylebox(st, "Button").duplicate()
		sb.content_margin_top = 0
		sb.content_margin_bottom = 0
		_task_btn.add_theme_stylebox_override(st, sb)
	_task_btn.pressed.connect(func(): if _current != "": _apps[_current].visible = not _apps[_current].visible)
	row.add_child(_task_btn)
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	spacer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.add_child(spacer)
	_task_btn.visibility_changed.connect(func(): spacer.visible = not _task_btn.visible)
	_clock = Label.new()
	_clock.add_theme_font_override("font", _bold)
	_clock.add_theme_font_size_override("font_size", SYS_SIZE)
	_clock.custom_minimum_size = Vector2(56, 0)
	_clock.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_clock.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	row.add_child(_clock)
	root.add_child(_taskbar)
	_start_menu = _build_start_menu()
	root.add_child(_start_menu)
	_msgbox = Control.new()
	_msgbox.size = Vector2(SCREEN)
	_msgbox.visible = false
	root.add_child(_msgbox)
	# the stylus: System 6's arrow, shown while a controller is in use
	_stylus = TextureRect.new()
	_stylus.texture = _image(["K..........", "KK.........", "KWK........", "KWWK.......", "KWWWK......", "KWWWWK.....",
		"KWWWWWK....", "KWWWWWWK...", "KWWWWWWWK..", "KWWWWWWWWK.", "KWWWWWKKKKK", "KWWKWWK....", "KWK.KWWK...",
		"KK..KWWK...", "K....KWWK..", ".....KWWK..", "......KK..."])
	_stylus.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_stylus.visible = false
	root.add_child(_stylus)


func _desk_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed:
		_start_menu.visible = false
		_select_icon("")


func _select_icon(name: String) -> void:
	for k in _desk_icons:
		_desk_icons[k].selected = (k == name)
		_desk_icons[k].queue_redraw()


func _icon_tapped(name: String) -> void:
	## One tap selects, a double tap opens.
	_start_menu.visible = false
	var now := Time.get_ticks_msec()
	if _pad_tap or now - int(_last_click.get(name, -10000)) < 600:        # (a controller's tap opens at once)
		_last_click[name] = -10000
		_select_icon("")
		_open_app(name)
	else:
		_last_click[name] = now
		_select_icon(name)


func _build_start_menu() -> Control:
	## The System menu (CE 1.0's Start menu: one flat list, no cascading), drawn as a System 6 menu:
	## white, black edged, a drop shadow, the highlighted item inverted; the OS's name down the left.
	var holder := Control.new()
	holder.visible = false
	var shadow := ColorRect.new()
	shadow.color = K
	holder.add_child(shadow)
	var m := PanelContainer.new()
	m.add_theme_stylebox_override("panel", _flat(W, K, 1, 0, 1))
	holder.add_child(m)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 0)
	m.add_child(row)
	var banner := ColorRect.new()
	banner.color = K
	banner.custom_minimum_size = Vector2(20, 0)
	var bl := Label.new()
	bl.text = "The System"
	bl.add_theme_font_override("font", _bold)
	bl.add_theme_font_size_override("font_size", SYS_SIZE)
	bl.add_theme_color_override("font_color", W)
	bl.rotation = -PI * 0.5
	banner.add_child(bl)
	var logo := TextureRect.new()
	logo.texture = load(PDA + "system_logo.png")
	var logo_bg := ColorRect.new()
	logo_bg.color = W
	logo_bg.size = Vector2(18, 18)
	logo.position = Vector2(1, 1)
	logo_bg.add_child(logo)
	banner.add_child(logo_bg)
	banner.resized.connect(func():
		logo_bg.position = Vector2(1, banner.size.y - 19)
		bl.position = Vector2(3, banner.size.y - 24))
	row.add_child(banner)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 0)
	row.add_child(col)
	var entries := []
	for a in APPS:
		entries.append([a[1], _open_app.bind(a[0])])
	entries.append([])
	entries.append(["New Game...", _confirm_new_game])
	entries.append(["Suspend", func(): set_open(false)])
	for e in entries:
		if e.is_empty():
			var sep := HSeparator.new()
			sep.add_theme_stylebox_override("separator", _dotted())
			col.add_child(sep)
			continue
		var b := Button.new()
		b.text = e[0]
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.custom_minimum_size = Vector2(124, 18)
		b.add_theme_stylebox_override("normal", _flat(Color.TRANSPARENT, Color.TRANSPARENT, 0, 0, 4))
		b.add_theme_stylebox_override("hover", _flat(K, K, 0, 0, 4))
		b.add_theme_stylebox_override("pressed", _flat(K, K, 0, 0, 4))
		b.add_theme_stylebox_override("hover_pressed", _flat(K, K, 0, 0, 4))
		b.add_theme_color_override("font_hover_color", W)
		b.pressed.connect(func():
			_start_menu.visible = false
			e[1].call())
		col.add_child(b)
	var place := func():
		m.reset_size()
		m.position = Vector2(0, SCREEN.y - TASKBAR_H - m.size.y - 1)
		shadow.position = m.position + Vector2(1, 1)
		shadow.size = m.size
		holder.size = Vector2(SCREEN)
	m.resized.connect(place)
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	place.call()
	return holder


func _dotted() -> StyleBoxTexture:
	## the grey (dotted) line System 6 menus separate groups with
	var s := StyleBoxTexture.new()
	s.texture = _image(["KW"])
	s.axis_stretch_horizontal = StyleBoxTexture.AXIS_STRETCH_MODE_TILE
	s.content_margin_top = 1
	return s


func _app(title: String, tabs: TabContainer, help: String) -> Control:
	## A full-screen app window (CE's apps didn't overlap): a System 6 title bar -- close box, title,
	## help box -- a black frame, then the app's tabs.
	var w := Control.new()
	w.size = Vector2(SCREEN.x, SCREEN.y - TASKBAR_H)
	var bg := Panel.new()
	bg.size = w.size
	bg.add_theme_stylebox_override("panel", _flat(W, K, 1))
	w.add_child(bg)
	var bar := MacTitle.new()
	bar.title = title
	bar.font = _bold
	bar.font_size = SYS_SIZE
	bar.position = Vector2.ZERO
	bar.size = Vector2(SCREEN.x, TITLE_H)
	bar.close_pressed.connect(_close_app)
	bar.help_pressed.connect(func(): _show_message(title, help))
	w.add_child(bar)
	tabs.position = Vector2(4, TITLE_H + 3)
	tabs.size = Vector2(SCREEN.x - 8, SCREEN.y - TASKBAR_H - TITLE_H - 7)
	w.add_child(tabs)
	return w


func _open_app(name: String) -> void:
	if not _is_open:
		return
	_start_menu.visible = false
	for k in _apps:
		_apps[k].visible = (k == name)
	_current = name
	for a in APPS:
		if a[0] == name:
			_task_btn.text = a[1]
	_task_btn.visible = true
	if name == "map":
		_refresh_map()
	if name == "ai":
		_refresh_ai()
	if name == "summon":
		_ride_follow = true
		_refresh_ride()
	if name == "nav":
		_refresh_nav()


func _close_app() -> void:
	if _current != "":
		_apps[_current].visible = false
	_current = ""
	_task_btn.visible = false


func _show_message(title: String, text: String, buttons := [["OK", Callable()]]) -> void:
	## A System 6 alert: a double-framed box in the middle of the screen, the logo, the message and
	## rounded buttons (the first, the default, ringed).
	for c in _msgbox.get_children():
		c.queue_free()
	var shade := Control.new()
	shade.size = Vector2(SCREEN)
	shade.mouse_filter = Control.MOUSE_FILTER_STOP
	_msgbox.add_child(shade)
	var outer := PanelContainer.new()
	outer.add_theme_stylebox_override("panel", _flat(W, K, 1, 0, 2))
	var inner := PanelContainer.new()
	inner.add_theme_stylebox_override("panel", _flat(W, K, 2, 0, 6))
	outer.add_child(inner)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	inner.add_child(v)
	var head := HBoxContainer.new()
	head.add_theme_constant_override("separation", 6)
	var ic := TextureRect.new()
	ic.texture = load(PDA + "system_logo_32.png")
	ic.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	head.add_child(ic)
	var tv := VBoxContainer.new()
	var tl := Label.new()
	tl.text = title
	tl.add_theme_font_override("font", _bold)
	tl.add_theme_font_size_override("font_size", SYS_SIZE)
	tv.add_child(tl)
	var msg := Label.new()
	msg.text = text
	msg.autowrap_mode = TextServer.AUTOWRAP_WORD
	msg.custom_minimum_size = Vector2(150, 0)
	tv.add_child(msg)
	head.add_child(tv)
	v.add_child(head)
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_END
	row.add_theme_constant_override("separation", 8)
	v.add_child(row)
	for i in buttons.size():
		var spec: Array = buttons[i]
		var b := Button.new()
		b.text = spec[0]
		b.custom_minimum_size = Vector2(52, 18)
		b.pressed.connect(func():
			_msgbox.visible = false
			if spec[1].is_valid():
				spec[1].call())
		if i == 0:
			# the default button's heavy ring
			var ring := PanelContainer.new()
			ring.add_theme_stylebox_override("panel", _flat(Color.TRANSPARENT, K, 2, 7, 2))
			ring.add_child(b)
			row.add_child(ring)
		else:
			row.add_child(b)
	_msgbox.add_child(outer)
	outer.reset_size()
	outer.position = ((Vector2(SCREEN) - Vector2(0, TASKBAR_H) - outer.size) * 0.5).floor()
	_msgbox.visible = true


func _confirm_new_game() -> void:
	_show_message("New Game", "Start a new game?  Everything you have done will be lost.",
		[["Yes", _on_new_game], ["No", Callable()]])


func _on_new_game() -> void:
	QuestManager.active.clear()
	QuestManager.completed.clear()
	QuestManager.turned_in.clear()
	QuestManager.tracked_quest_id = ""
	Inventory.stacks.clear()
	WeaponManager.owned.clear()
	WeaponManager.equipped_index = -1
	set_open(false)
	get_tree().reload_current_scene()


func _tab_page(tabs: TabContainer, title: String, scroll := true) -> VBoxContainer:
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 3)
	if scroll:
		var s := ScrollContainer.new()
		s.name = title
		s.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
		v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		s.add_child(v)
		tabs.add_child(s)
	else:
		v.name = title
		tabs.add_child(v)
	return v


func _label(text: String, bold := false, wrap := true) -> Label:
	var l := Label.new()
	l.text = text
	if bold:
		l.add_theme_font_override("font", _bold)
		l.add_theme_font_size_override("font_size", SYS_SIZE)
	if wrap:
		l.autowrap_mode = TextServer.AUTOWRAP_WORD
		l.custom_minimum_size = Vector2(200, 0)
		l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return l


func _button(text: String, on_press: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(0, 18)
	b.pressed.connect(on_press)
	return b


# ------------------------------------------------------------------ Station Map
func _map_tabs() -> TabContainer:
	var tabs := TabContainer.new()
	var st := _tab_page(tabs, "Station", false)
	_map_station = Control.new()
	_map_station.custom_minimum_size = Vector2(222, 128)
	_map_station.draw.connect(_draw_station_map)
	st.add_child(_map_station)
	_map_here = _label("")
	st.add_child(_map_here)
	var nb := _tab_page(tabs, "Nearby", false)
	_map_nearby = TextureRect.new()
	_map_nearby.custom_minimum_size = Vector2(222, 236)
	_map_nearby.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_map_nearby.stretch_mode = TextureRect.STRETCH_SCALE
	_map_nearby.draw.connect(_draw_nearby_marker)
	nb.add_child(_map_nearby)
	return tabs


func _player_sx() -> Vector3:
	## (s, x, heading on the map in radians: 0 = east, +pi/2 = south) of the player
	var p := get_tree().get_first_node_in_group("player") as Node3D
	if p == null:
		return Vector3.ZERO
	var s := StationGeo.s_of(p.global_position)
	var cam := p.get_viewport().get_camera_3d()
	var f := -(cam.global_transform.basis.z if cam else p.global_transform.basis.z)
	return Vector3(s, p.global_position.x, atan2(f.x, f.dot(StationGeo.forward(s))))


func _refresh_map() -> void:
	if _map_tex == null:
		_map_tex = load(PDA + "map_detail.png")              # 4 m / px, 4 levels (tools: see ui/pda)
		_map_overview = load(PDA + "map_overview.png")
	if _towns.is_empty() and FileAccess.file_exists("res://remake/placement.json"):
		var acc := {}
		for e in JSON.parse_string(FileAccess.get_file_as_string("res://remake/placement.json")).structures:
			if e.settlement == null:
				continue
			if not acc.has(e.settlement):
				acc[e.settlement] = [Vector2.ZERO, 0, e.s]
			var a: Array = acc[e.settlement]
			a[0] += Vector2(StationGeo.wrap_ds(e.s - a[2]), e.x)
			a[1] += 1
		for k in acc:
			var a: Array = acc[k]
			_towns[k] = Vector2(fposmod(a[2] + a[0].x / a[1], StationGeo.CIRC), a[0].y / a[1])
	var p := _player_sx()
	var near := ""
	var nd := INF
	for k in _towns:
		var d := Vector2(StationGeo.wrap_ds(_towns[k].x - p.x), _towns[k].y - p.y).length()
		if d < nd:
			nd = d
			near = k
	var dirs := "north" if p.y < 0 else "south"
	_map_here.text = "You are %.1f km round the ring, %.1f km %s of the middle.  Nearest town: %s (%.1f km)." % [
		p.x / 1000.0, absf(p.y) / 1000.0, dirs, near, nd / 1000.0]
	if _map_tex:
		# Nearby: a 0.9 km x 1 km window of the map round the player, north up
		var ppm: float = _map_tex.get_width() / StationGeo.FARSIDE_W
		var wm := 888.0                                     # 1 LCD pixel = one 4 m map pixel
		var hm := wm * 236.0 / 222.0
		var at := AtlasTexture.new()
		at.atlas = _map_tex
		var cx := fposmod(p.x, StationGeo.CIRC) * ppm
		var cy := (p.y + StationGeo.FARSIDE_H * 0.5) * ppm
		at.region = Rect2(cx - wm * ppm * 0.5, cy - hm * ppm * 0.5, wm * ppm, hm * ppm)
		_map_nearby.texture = at
		_map_nearby.queue_redraw()
	_map_station.queue_redraw()


func _draw_station_map() -> void:
	var sz := _map_station.size
	if _map_tex:
		var h := floorf(sz.x * StationGeo.FARSIDE_H / StationGeo.FARSIDE_W)
		_map_station.draw_texture_rect(_map_overview, Rect2(0, 0, sz.x, h), false)
		_map_station.draw_rect(Rect2(0, 0, sz.x, h), K, false)
		var p := _player_sx()
		var u := Vector2(fposmod(p.x, StationGeo.CIRC) / StationGeo.FARSIDE_W * sz.x,
			(p.y + StationGeo.FARSIDE_H * 0.5) / StationGeo.FARSIDE_H * h).floor()
		var blink := int(Time.get_ticks_msec() / 400) % 2 == 0
		_map_station.draw_rect(Rect2(u - Vector2(3, 3), Vector2(7, 7)), K if blink else W)
		_map_station.draw_string(_font, Vector2(2, h + 14), "N (Marlowe) up   E ->", HORIZONTAL_ALIGNMENT_LEFT, -1, TEXT_SIZE, K)


func _draw_nearby_marker() -> void:
	var c := (_map_nearby.size * 0.5).floor()
	var p := _player_sx()
	var d := Vector2(cos(p.z), sin(p.z))
	var side := Vector2(-d.y, d.x)
	_map_nearby.draw_colored_polygon(PackedVector2Array([c + d * 8, c - d * 5 + side * 5, c - d * 2, c - d * 5 - side * 5]), K)
	_map_nearby.draw_rect(Rect2(Vector2.ZERO, _map_nearby.size), K, false)
	_map_nearby.draw_rect(Rect2(2, 2, 12, 15), W)
	_map_nearby.draw_string(_bold, Vector2(4, 14), "N", HORIZONTAL_ALIGNMENT_LEFT, -1, SYS_SIZE, K)


# ------------------------------------------------------------------ Navigation
## The political map (NavMap), fast travel by tram to the two largest tiers of towns (research/law/
## 03_settlements.md), and the law where you stand (research/law/02_cities.md).
var _nav_map: NavMap
var _nav_list: VBoxContainer
var _nav_law: Label
var _nav_status: Label


func _nav_tabs() -> TabContainer:
	var tabs := TabContainer.new()
	var pg := _tab_page(tabs, "Map", false)
	_nav_map = NavMap.new()
	_nav_map.font = _font
	_nav_map.bold = _bold
	_nav_map.custom_minimum_size = Vector2(222, 196)
	_nav_map.travel_requested.connect(_nav_confirm)
	pg.add_child(_nav_map)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 3)
	var c := _button("Center", func(): _nav_map.follow = true)
	c.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(c)
	var zin := _button("+", func(): _nav_map.zoom(-1))
	zin.custom_minimum_size = Vector2(30, 18)
	row.add_child(zin)
	var zout := _button("-", func(): _nav_map.zoom(1))
	zout.custom_minimum_size = Vector2(30, 18)
	row.add_child(zout)
	pg.add_child(row)
	var tv := _tab_page(tabs, "Travel")
	tv.add_child(_label("Ride the tram to:", true))
	_nav_list = VBoxContainer.new()
	_nav_list.add_theme_constant_override("separation", 3)
	tv.add_child(_nav_list)
	var lw := _tab_page(tabs, "Law")
	_nav_law = _label("")
	lw.add_child(_nav_law)
	return tabs


func _nav_dests() -> Array:
	## The fast-travel stops: each town of the two largest tiers, at its tram stop nearest its middle
	## (the user: "Make sure the fast travel destinations are at tram stops").
	var out := []
	if not FileAccess.file_exists("res://remake/law/settlements.json"):
		return out
	var sets: Array = JSON.parse_string(FileAccess.get_file_as_string("res://remake/law/settlements.json")).settlements
	for st in sets:
		if not st.fast_travel or not st.get("centre"):
			continue
		var c := Vector2(float(st.centre[0]), float(st.centre[1]))
		var best := {}
		var bd := INF
		for l in TransitNet.lines():
			if str(l.kind) != "tram":
				continue
			for sp in l.stops:
				var p := TransitNet.point_at(l, float(sp.d))
				var d := Vector2(StationGeo.wrap_ds(p.x - c.x), p.y - c.y).length() * (1.0 if str(sp.town) == str(st.name) else 3.0)
				if d < bd:
					bd = d
					var q := TransitNet.point_at(l, float(sp.d) + 1.0)
					best = {"name": st.name, "tier": st.tier, "s": fposmod(p.x, StationGeo.CIRC), "x": p.y, "stop": str(sp.name), "line": str(l.name),
						"dir": Vector2(StationGeo.wrap_ds(q.x - p.x), q.y - p.y).normalized(), "own": str(sp.town) == str(st.name)}
		if not best.is_empty():
			out.append(best)
	return out


func _refresh_nav() -> void:
	if _nav_map == null:
		return
	if _nav_map.dests.is_empty():
		_nav_map.dests = _nav_dests()
		for c in _nav_list.get_children():
			c.queue_free()
		for dd in _nav_map.dests:
			var b := _button("%s -- %s%s" % [dd.name, dd.stop, "" if dd.own else " (nearest)"], _nav_confirm.bind(dd))
			b.alignment = HORIZONTAL_ALIGNMENT_LEFT
			_nav_list.add_child(b)
	_nav_map.follow = true
	# the law where you stand: the nearest settlement, and the city whose ordinances it follows
	var p := _player_sx()
	var law := {}
	if FileAccess.file_exists("res://remake/law/ordinances.json"):
		law = JSON.parse_string(FileAccess.get_file_as_string("res://remake/law/ordinances.json"))
	var sets: Array = JSON.parse_string(FileAccess.get_file_as_string("res://remake/law/settlements.json")).settlements if FileAccess.file_exists("res://remake/law/settlements.json") else []
	var here := {}
	var hd := INF
	for st in sets:
		if not st.get("centre"):
			continue
		var d := Vector2(StationGeo.wrap_ds(float(st.centre[0]) - p.x), float(st.centre[1]) - p.y).length()
		if d < hd:
			hd = d
			here = st
	var txt := "Out in the country."
	if not here.is_empty():
		var city := {}
		for c in law.get("cities", []):
			if c.id == here.governed_by:
				city = c
		if not city.is_empty():
			var pk: Dictionary = city.parking
			txt = "%s (%s, %.1f km)\nLaw of %s: %s.\n\nSpeed: %d km/h in town, %d near schools, %d in alleys.\nDowntown parking: %s, %d-hour limit.\nResidential: at most %d hours in one place.\nTransit: %s.\nSidewalks: the owner keeps them (ORC 729.01)." % [
				here.name, here.tier, hd / 1000.0, city.name, city.code, int(city.speed.residential_kmh), int(city.speed.school_kmh), int(city.speed.alley_kmh),
				pk.downtown.hours, int(pk.downtown.limit_h), int(pk.residential.max_hours), city.transit.authority]
	_nav_law.text = txt


func _nav_confirm(dd: Dictionary) -> void:
	var p := _player_sx()
	var km := Vector2(StationGeo.wrap_ds(float(dd.s) - p.x), float(dd.x) - p.y).length() / 1000.0
	var mins := int(round(4.0 + km * 3.2))
	_show_message("Travel", "Take the tram to %s?\n%s, the %s.\nAbout %d minutes." % [dd.name, dd.stop, dd.line, mins],
		[["Travel", _nav_travel.bind(dd, mins)], ["Cancel", Callable()]])


func _nav_travel(dd: Dictionary, mins: int) -> void:
	## Off at the stop: on the kerbside, by the stop, facing the street; the clock moves on by the ride.
	var pl := get_tree().get_first_node_in_group("player") as StationPlayer
	if pl == null:
		return
	if pl.is_seated() and pl._vehicle and pl._vehicle.has_method("leave_seat"):
		pl._vehicle.leave_seat()
	set_open(false)
	var dir: Vector2 = dd.dir
	var right := Vector2(-dir.y, dir.x)
	var at := Vector2(float(dd.s), float(dd.x)) + right * 7.5
	var s := fposmod(at.x, StationGeo.CIRC)
	var face := -right                                   # looking back at the street
	var yaw := atan2(-face.y, face.x)
	pl.stand_up(StationGeo.point(s, at.y, MapTerrain.elevation(s, at.y) + 1.0), StationGeo.basis(s, yaw))
	var sky := get_tree().current_scene.get_node_or_null("DaySkySystem")
	if sky:
		sky.time_of_day = fposmod(float(sky.time_of_day) + mins / 1440.0, 1.0)
	var hud := get_tree().root.get_node_or_null("Hud")
	if hud and hud.has_method("toast"):
		hud.toast("%s: %s" % [dd.name, dd.stop])


# ------------------------------------------------------------------ Summon Aerostat
## A ride-hailing app: a local map (north up, dragged to look round, zoomed with + and -) with you
## and your aerostat on it, live; a status line; Request / Cancel.  The aerostat flies itself
## (remake/scripts/vehicles/summoned_aerostat.gd) and keeps flying while the Communicator is open.
const RIDE_ZOOMS := [1.0, 2.0, 4.0, 8.0]           # metres per LCD pixel
var _ride_map: Control
var _ride_status: Label
var _ride_btn: Button
var _ride_view := Vector2.ZERO                     # (s, x) at the map's centre
var _ride_follow := true                           # keep the player centred (until the map is dragged)
var _ride_zoom_i := 1
var _ride_msg := ""                                # the last request's answer, while nothing is coming


func _summon_tabs() -> TabContainer:
	var tabs := TabContainer.new()
	var pg := _tab_page(tabs, "Ride", false)
	_ride_map = Control.new()
	_ride_map.custom_minimum_size = Vector2(222, 146)
	_ride_map.clip_contents = true
	_ride_map.mouse_filter = Control.MOUSE_FILTER_STOP
	_ride_map.draw.connect(_draw_ride_map)
	_ride_map.gui_input.connect(_ride_map_input)
	pg.add_child(_ride_map)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 3)
	var c := _button("Center", func(): _ride_follow = true)
	c.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(c)
	var zin := _button("+", func(): _ride_zoom(-1))
	zin.custom_minimum_size = Vector2(30, 18)
	row.add_child(zin)
	var zout := _button("-", func(): _ride_zoom(1))
	zout.custom_minimum_size = Vector2(30, 18)
	row.add_child(zout)
	pg.add_child(row)
	_ride_status = _label("")
	_ride_status.custom_minimum_size = Vector2(200, 36)
	pg.add_child(_ride_status)
	_ride_btn = _button("Request Aerostat", _ride_request)
	_ride_btn.custom_minimum_size = Vector2(0, 22)
	pg.add_child(_ride_btn)
	var wb := _button("Deliver Station Wagon", _wagon_request)
	wb.custom_minimum_size = Vector2(0, 22)
	pg.add_child(wb)
	return tabs


func _wagon_request() -> void:
	## A Carrow station wagon set down a few metres in front of you, facing the way you look (look down the
	## road first). One at a time: asking again takes the last one away.
	var p := get_tree().get_first_node_in_group("player") as Node3D
	if p == null:
		return
	for w in get_tree().get_nodes_in_group("delivered_wagon"):
		(w as Node).queue_free()
	var up := StationGeo.up(StationGeo.s_of(p.global_position))
	var cam := p.get_viewport().get_camera_3d()
	var fwd := -(cam.global_transform.basis.z if cam else p.global_transform.basis.z)
	fwd = (fwd - up * fwd.dot(up)).normalized()
	var at := p.global_position + fwd * 5.5 - fwd.cross(up) * 1.4      # (ahead, a little to the left: its door by you)
	var q := PhysicsRayQueryParameters3D.create(at + up * 4.0, at - up * 8.0, 1)
	if p is CollisionObject3D:
		q.exclude = [(p as CollisionObject3D).get_rid()]
	var hit := p.get_world_3d().direct_space_state.intersect_ray(q)
	if not hit.is_empty():
		at = hit.position
	var w := RemakeWagon.new()
	w.name = "DeliveredWagon"
	w.add_to_group("delivered_wagon")
	get_tree().current_scene.add_child(w)
	w.global_transform = Transform3D(Basis(fwd.cross(up), up, -fwd).orthonormalized(), at + up * 0.15)
	_ride_msg = "A station wagon is waiting ahead of you, facing the way you look.  Use its doors, or its steering wheel to drive."
	_refresh_ride()


func _ride() -> RemakeSummonedAerostat:
	for a in get_tree().get_nodes_in_group("summoned_aerostat"):
		if not (a as Node).is_queued_for_deletion():
			return a
	return null


func _ride_request() -> void:
	var a := _ride()
	if a and a.phase != "parked" and not a.disabled:
		a.queue_free()                                 # Cancel
		a.remove_from_group("summoned_aerostat")
		_ride_msg = "Ride cancelled."
	else:
		var r := RemakeSummonedAerostat.summon(get_tree())
		_ride_msg = r.message
	_ride_follow = true
	_refresh_ride()


func _ride_zoom(step: int) -> void:
	_ride_zoom_i = clampi(_ride_zoom_i + step, 0, RIDE_ZOOMS.size() - 1)
	_ride_map.queue_redraw()


func _ride_map_input(e: InputEvent) -> void:
	## Drag to look round, the wheel (or a controller's right stick) to zoom.
	if e is InputEventMouseMotion and (e.button_mask & MOUSE_BUTTON_MASK_LEFT):
		_ride_follow = false
		_ride_view -= e.relative * RIDE_ZOOMS[_ride_zoom_i]
		_ride_view.x = fposmod(_ride_view.x, StationGeo.CIRC)
		_ride_view.y = clampf(_ride_view.y, -StationGeo.HALF_LEN, StationGeo.HALF_LEN)
		_ride_map.queue_redraw()
	elif e is InputEventMouseButton and e.pressed and e.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
		_ride_zoom(-1 if e.button_index == MOUSE_BUTTON_WHEEL_UP else 1)
		_ride_map.accept_event()


func _refresh_ride() -> void:
	if _ride_map == null:
		return
	if _map_tex == null:
		_map_tex = load(PDA + "map_detail.png")
		_map_overview = load(PDA + "map_overview.png")
	var p := _player_sx()
	if _ride_follow:
		_ride_view = Vector2(p.x, p.y)
	var a := _ride()
	var t := ""
	if a == null:
		t = (_ride_msg + "\n" if _ride_msg != "" else "") + "Tap Request and an aerostat will come to you."
		_ride_btn.text = "Request Aerostat"
	else:
		var st := a.status()
		if st.disabled:
			t = "Your aerostat is disabled."
			_ride_btn.text = "Request Another"
		elif st.phase == "dive":
			t = "Your aerostat is on its way: %d m away, %d m up.  Arriving in %s." % [st.dist, st.alt, _mmss(st.eta)]
			_ride_btn.text = "Cancel Ride"
		elif st.phase == "let_down":
			t = "Arriving now: landing %d m from you.  %s." % [st.dist, _mmss(st.eta)]
			_ride_btn.text = "Cancel Ride"
		elif a.pilot:
			t = "Enjoy your flight."
			_ride_btn.text = "Request Another"
		else:
			t = "Your aerostat is here, %d m away (the red one).  Step aboard." % st.dist
			_ride_btn.text = "Request Another"
	if _ride_status.text != t:
		_ride_status.text = t
	_ride_map.queue_redraw()


func _mmss(sec: float) -> String:
	var n := maxi(0, ceili(sec))
	return "%d:%02d" % [n / 60, n % 60]


func _ride_to_map(s: float, x: float) -> Vector2:
	## A place (s, x) on the ride map, in its pixels.
	var m: float = RIDE_ZOOMS[_ride_zoom_i]
	return (_ride_map.size * 0.5 + Vector2(StationGeo.wrap_ds(s - _ride_view.x), x - _ride_view.y) / m).floor()


func _draw_ride_map() -> void:
	var sz := _ride_map.size
	var m: float = RIDE_ZOOMS[_ride_zoom_i]
	_ride_map.draw_rect(Rect2(Vector2.ZERO, sz), W)
	if _map_tex:
		# the map image (4 m / px) under the window, in up to two pieces across the ring's seam
		var ppm: float = _map_tex.get_width() / StationGeo.FARSIDE_W
		var tw := float(_map_tex.get_width())
		var src := Rect2(fposmod(_ride_view.x - sz.x * 0.5 * m, StationGeo.CIRC) * ppm,
			(_ride_view.y - sz.y * 0.5 * m + StationGeo.FARSIDE_H * 0.5) * ppm, sz.x * m * ppm, sz.y * m * ppm)
		var first := minf(src.size.x, tw - src.position.x)
		_ride_map.draw_texture_rect_region(_map_tex, Rect2(0, 0, sz.x * first / src.size.x, sz.y),
			Rect2(src.position, Vector2(first, src.size.y)))
		if first < src.size.x:
			var dx := sz.x * first / src.size.x
			_ride_map.draw_texture_rect_region(_map_tex, Rect2(dx, 0, sz.x - dx, sz.y),
				Rect2(0, src.position.y, src.size.x - first, src.size.y))
	var p := _player_sx()
	var a := _ride()
	if a and not a.is_queued_for_deletion():
		var ap := a.global_position
		var au := _ride_to_map(StationGeo.s_of(ap), ap.x)
		if a.phase != "parked":
			# the route to where it will land, dotted, and the landing mark
			var pu := _ride_to_map(StationGeo.s_of(a.pad), a.pad.x)
			var n := int(au.distance_to(pu) / 4.0)
			for i in n:
				var q := au.lerp(pu, float(i) / maxf(1, n)).floor()
				_ride_map.draw_rect(Rect2(q, Vector2(2, 2)), K)
			_ride_map.draw_line(pu + Vector2(-4, -4), pu + Vector2(5, 5), K, 2.0)
			_ride_map.draw_line(pu + Vector2(-4, 5), pu + Vector2(5, -4), K, 2.0)
		var inside := Rect2(Vector2(6, 6), sz - Vector2(12, 12))
		if inside.has_point(au):
			# a balloon over its cabin; blinking while it flies
			var on := a.phase == "parked" or int(Time.get_ticks_msec() / 300) % 2 == 0
			_ride_map.draw_circle(au + Vector2(0, -3), 5.0, K)
			_ride_map.draw_circle(au + Vector2(0, -3), 3.0, W if on else D)
			_ride_map.draw_rect(Rect2(au + Vector2(-2, 3), Vector2(5, 3)), K)
		else:
			# off the map: an arrow at the edge pointing its way
			var c := sz * 0.5
			var d := (au - c).normalized()
			var e := c + d * minf(absf((sz.x * 0.5 - 8) / d.x) if absf(d.x) > 1e-3 else 1e9,
				absf((sz.y * 0.5 - 8) / d.y) if absf(d.y) > 1e-3 else 1e9)
			var sd := Vector2(-d.y, d.x)
			_ride_map.draw_colored_polygon(PackedVector2Array([e + d * 6, e - d * 4 + sd * 5, e - d * 4 - sd * 5]), K)
	# you
	var c2 := _ride_to_map(p.x, p.y)
	var d2 := Vector2(cos(p.z), sin(p.z))
	var side := Vector2(-d2.y, d2.x)
	_ride_map.draw_colored_polygon(PackedVector2Array([c2 + d2 * 8, c2 - d2 * 5 + side * 5, c2 - d2 * 2, c2 - d2 * 5 - side * 5]), K)
	_ride_map.draw_polyline(PackedVector2Array([c2 + d2 * 9, c2 - d2 * 6 + side * 6, c2 - d2 * 2, c2 - d2 * 6 - side * 6, c2 + d2 * 9]), W, 1.0)
	# the frame, north, the scale
	_ride_map.draw_rect(Rect2(Vector2.ZERO, sz), K, false)
	_ride_map.draw_rect(Rect2(2, 2, 12, 15), W)
	_ride_map.draw_string(_bold, Vector2(4, 14), "N", HORIZONTAL_ALIGNMENT_LEFT, -1, SYS_SIZE, K)
	var bar_m := 50.0 * m
	var bw := bar_m / m
	_ride_map.draw_rect(Rect2(3, sz.y - 18, bw + 36, 15), W)
	_ride_map.draw_rect(Rect2(5, sz.y - 7, bw, 2), K)
	_ride_map.draw_string(_font, Vector2(bw + 8, sz.y - 5), "%d m" % bar_m, HORIZONTAL_ALIGNMENT_LEFT, -1, TEXT_SIZE, K)


# ------------------------------------------------------------------ Inventory
func _inventory_tabs() -> TabContainer:
	var tabs := TabContainer.new()
	_weapons = _tab_page(tabs, "Weapons")
	_items = _tab_page(tabs, "Items")
	return tabs


func _refresh_inventory() -> void:
	if _weapons == null:
		return
	for c in _weapons.get_children():
		c.queue_free()
	if WeaponManager.owned.is_empty():
		_weapons.add_child(_label("No weapons."))
	for weapon_id in WeaponManager.owned:
		var def: Dictionary = WeaponManager.definitions.get(weapon_id, {})
		var row := HBoxContainer.new()
		var lbl := _label(def.get("name", weapon_id), false, false)
		lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(lbl)
		var btn := Button.new()
		var equipped := WeaponManager.is_equipped(weapon_id)
		btn.text = "Equipped" if equipped else "Equip"
		btn.disabled = equipped
		btn.pressed.connect(WeaponManager.equip.bind(weapon_id))
		row.add_child(btn)
		_weapons.add_child(row)
	for c in _items.get_children():
		c.queue_free()
	var stacks := Inventory.all_stacks()
	if stacks.is_empty():
		_items.add_child(_label("Nothing yet."))
	for item_id in stacks.keys():
		var def := Inventory.get_definition(item_id)
		_items.add_child(_label("%s  x%d" % [def.get("name", item_id), stacks[item_id]]))


# ------------------------------------------------------------------ Quests
func _quest_tabs() -> TabContainer:
	var tabs := TabContainer.new()
	_quest_active = _tab_page(tabs, "Active")
	_quest_done = _tab_page(tabs, "Completed")
	return tabs


func _refresh_quests() -> void:
	if _quest_active == null:
		return
	for c in _quest_active.get_children():
		c.queue_free()
	for c in _quest_done.get_children():
		c.queue_free()
	var active_ids := QuestManager.get_active_quests()
	if active_ids.is_empty():
		_quest_active.add_child(_label("No active quests."))
	for quest_id in active_ids:
		var head := HBoxContainer.new()
		var title := _label(QuestManager.get_quest_title(quest_id), true, false)
		title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		head.add_child(title)
		var tb := Button.new()
		var tracked: bool = QuestManager.tracked_quest_id == quest_id
		tb.text = "Tracked" if tracked else "Track"
		tb.disabled = tracked
		tb.pressed.connect(QuestManager.set_tracked_quest.bind(quest_id))
		head.add_child(tb)
		_quest_active.add_child(head)
		_quest_active.add_child(_label(QuestManager.get_quest_description(quest_id)))
		for obj in QuestManager.get_objectives(quest_id):
			_quest_active.add_child(_label("- %s: %d / %d" % [_objective_label(obj), obj.progress, obj.count]))
		_quest_active.add_child(HSeparator.new())
	var done := QuestManager.get_completed_quests()
	if done.is_empty():
		_quest_done.add_child(_label("None yet."))
	for quest_id in done:
		_quest_done.add_child(_label("- " + QuestManager.get_quest_title(quest_id)))


func _objective_label(obj: Dictionary) -> String:
	match obj.type:
		"fetch":
			return "Collect %s" % obj.target
		"kill":
			return "Defeat %s" % obj.target
		"quest":
			return "Complete '%s'" % QuestManager.get_quest_title(obj.target)
		_:
			return String(obj.type)


# ------------------------------------------------------------------ NPC AI
const TRY_PERSONA := "You are Marge Pruett, 58, who runs the Main Street Diner in Harrow Falls, a small town " + \
	"on Space Station Columbia -- an O'Neill cylinder whose inside is American countryside, with towns, farms, " + \
	"rivers and two seas.  You are warm, nosy and practical, proud of your pie, and you've never left the " + \
	"station.  Speak as Marge, in one to three short sentences of plain speech.  Never mention being an AI."


func _ai_tabs() -> TabContainer:
	var tabs := TabContainer.new()
	# Setup: three steps, as few taps as can be
	var su := _tab_page(tabs, "Setup")
	su.add_child(_label("The station's people talk through Groq, a free AI service.  Setup takes a minute:"))
	su.add_child(_label("1. Get a free key", true))
	su.add_child(_label("Sign in at console.groq.com/keys, press Create API Key, then Copy."))
	var r1 := HBoxContainer.new()
	r1.add_child(_button("Open Groq", func(): OS.shell_open(NpcAI.info().key_url)))
	su.add_child(r1)
	su.add_child(_label("2. Paste it here", true))
	_ai_clip_row = HBoxContainer.new()
	_ai_key_edit = LineEdit.new()
	_ai_key_edit.placeholder_text = "gsk_..."
	_ai_key_edit.secret = true
	_ai_key_edit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_ai_key_edit.text_submitted.connect(func(t): _ai_use_key(t))
	var r2 := HBoxContainer.new()
	r2.add_child(_ai_key_edit)
	r2.add_child(_button("Paste", func(): _ai_use_key(DisplayServer.clipboard_get())))
	su.add_child(r2)
	su.add_child(_label("3. That's it", true))
	_ai_status = _label("")
	su.add_child(_ai_status)
	var r3 := HBoxContainer.new()
	r3.add_theme_constant_override("separation", 6)
	r3.add_child(_button("Test again", _ai_test))
	r3.add_child(_button("Remove key", _ai_remove_key))
	su.add_child(r3)
	su.add_child(HSeparator.new())
	su.add_child(_label(NpcAI.info().free))
	# Voice: the model
	var vo := _tab_page(tabs, "Voice")
	vo.add_child(_label("Model", true))
	var models: Array = NpcAI.info().models
	var group := ButtonGroup.new()
	for m in models:
		var cb := CheckBox.new()
		cb.button_group = group
		cb.text = m[1]
		cb.button_pressed = m[0] == NpcAI.model
		cb.toggled.connect(func(on): if on: NpcAI.set_model(m[0]))
		vo.add_child(cb)
		vo.add_child(_label("    " + m[2]))
	vo.add_child(HSeparator.new())
	_ai_usage = _label("")
	vo.add_child(_ai_usage)
	# Try it: talk to someone
	var tr := _tab_page(tabs, "Try it")
	tr.add_child(_label("Marge Pruett, Main Street Diner, Harrow Falls.", true))
	var r4 := HBoxContainer.new()
	_ai_say = LineEdit.new()
	_ai_say.placeholder_text = "Say something..."
	_ai_say.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_ai_say.text_submitted.connect(func(_t): _ai_talk())
	r4.add_child(_ai_say)
	r4.add_child(_button("Say", _ai_talk))
	tr.add_child(r4)
	_ai_log = VBoxContainer.new()
	_ai_log.add_theme_constant_override("separation", 3)
	tr.add_child(_ai_log)
	_style_checkboxes(vo)
	return tabs


func _style_checkboxes(parent: Control) -> void:
	## System 6 radio buttons: a round-ish box, filled when chosen
	var off := _image(["..KKKK..", ".K....K.", "K......K", "K......K", "K......K", "K......K", ".K....K.", "..KKKK.."])
	var on := _image(["..KKKK..", ".K....K.", "K.KKKK.K", "K.KKKK.K", "K.KKKK.K", "K.KKKK.K", ".K....K.", "..KKKK.."])
	for c in parent.get_children():
		if c is CheckBox:
			for n in ["radio_unchecked", "unchecked"]:
				c.add_theme_icon_override(n, off)
			for n in ["radio_checked", "checked"]:
				c.add_theme_icon_override(n, on)
			for st in ["normal", "hover", "pressed", "hover_pressed", "focus"]:
				c.add_theme_stylebox_override(st, StyleBoxEmpty.new())
			c.add_theme_color_override("font_pressed_color", K)
			c.add_theme_color_override("font_hover_pressed_color", K)
			c.add_theme_color_override("font_hover_color", K)


func _refresh_ai() -> void:
	if _ai_status == null:
		return
	if NpcAI.has_key():
		_ai_status.text = "Key %s is set%s.  NPCs can talk." % [NpcAI.masked_key(), " (from GROQ_API_KEY)" if NpcAI.key_from_env() else ""]
	else:
		_ai_status.text = "No key yet.  Paste one above."
		# a key already on the clipboard: offer it
		var clip := NpcAI.clean_key(DisplayServer.clipboard_get()) if DisplayServer.has_feature(DisplayServer.FEATURE_CLIPBOARD) else ""
		if NpcAI.looks_like_key(clip):
			_ai_status.text = "A Groq key is on the clipboard.  Press Paste to use it."
	_ai_usage.text = "Replies today: %d." % NpcAI.requests_today
	if NpcAI.last_latency_ms > 0:
		_ai_usage.text += "  The last took %.1f s." % (NpcAI.last_latency_ms / 1000.0)


func _ai_remove_key() -> void:
	NpcAI.clear_key()
	_ai_status.text = "Key removed."


func _ai_use_key(raw: String) -> void:
	var k := NpcAI.clean_key(raw)
	if k == "":
		_ai_status.text = "The clipboard is empty.  Copy the key on Groq's page first."
		return
	if not NpcAI.looks_like_key(k):
		_ai_status.text = "That doesn't look like a Groq key (they start gsk_).  Copy it again?"
		return
	NpcAI.set_key(k)
	_ai_key_edit.text = ""
	_ai_key_edit.release_focus()
	await _ai_test()


func _ai_test() -> void:
	_ai_status.text = "Checking the key with Groq..."
	var r: Dictionary = await NpcAI.test_connection()
	_ai_status.text = ("Key %s works.  %s  NPCs can talk." % [NpcAI.masked_key(), r.message]) if r.ok else r.message


func _ai_talk() -> void:
	var line := _ai_say.text.strip_edges()
	if line == "":
		line = "Hello!"
	_ai_say.text = ""
	_ai_log.add_child(_label("You: " + line))
	var wait := _label("Marge: ...")
	_ai_log.add_child(wait)
	_ai_history.append({"role": "user", "content": line})
	var msgs: Array = [{"role": "system", "content": TRY_PERSONA}]
	msgs.append_array(_ai_history.slice(-8))
	var r: Dictionary = await NpcAI.chat(msgs)
	if r.ok:
		wait.text = "Marge: " + r.text
		_ai_history.append({"role": "assistant", "content": r.text})
	else:
		wait.text = "(%s)" % r.error
		_ai_history.pop_back()
	_refresh_ai()


# ------------------------------------------------------------------ Control Panel
func _slider_row(parent: Control, text: String, lo: float, hi: float, value: float, on_change: Callable) -> void:
	parent.add_child(_label(text, false, false))
	var s := HSlider.new()
	s.min_value = lo
	s.max_value = hi
	s.step = 0.01
	s.value = value
	s.custom_minimum_size = Vector2(200, 14)
	s.value_changed.connect(on_change)
	parent.add_child(s)


func _control_tabs() -> TabContainer:
	var tabs := TabContainer.new()
	var snd := _tab_page(tabs, "Sound")
	_slider_row(snd, "Sound effects", 0.0, 1.0, Settings.sfx_volume, func(v): Settings.set_sfx_volume(v))
	_slider_row(snd, "Music", 0.0, 1.0, Settings.music_volume, func(v): Settings.set_music_volume(v))
	var disp := _tab_page(tabs, "Display")
	_slider_row(disp, "Brightness (gamma)", 0.5, 1.8, Settings.gamma, func(v): Settings.set_gamma(v))
	var readout := _label("")
	_slider_row(disp, "Draw distance", 0.4, 2.0, Settings.draw_distance_mult, func(v):
		readout.text = "Houses to %d m, trees to %d m." % [round(DistanceCulling.HOUSE_RANGE * v), round(DistanceCulling.TREE_RANGE * v)]
		Settings.set_draw_distance(v))
	readout.text = "Houses to %d m, trees to %d m." % [round(DistanceCulling.HOUSE_RANGE * Settings.draw_distance_mult),
		round(DistanceCulling.TREE_RANGE * Settings.draw_distance_mult)]
	disp.add_child(readout)
	var ctl := _tab_page(tabs, "Controls")
	_slider_row(ctl, "Mouse speed", 0.3, 3.0, Settings.mouse_sensitivity_mult, func(v): Settings.set_mouse_sensitivity(v))
	ctl.add_child(HSeparator.new())
	ctl.add_child(_label("Keys", true))
	var names := {"move_forward": "Forward", "move_back": "Back", "move_left": "Left", "move_right": "Right",
		"jump": "Jump", "shoot": "Attack / Fire", "next_weapon": "Next weapon", "prev_weapon": "Prev. weapon",
		"interact": "Use / Talk", "toggle_menu": "Communicator"}
	for action in names:
		var row := HBoxContainer.new()
		var a := _label(names[action], false, false)
		a.custom_minimum_size = Vector2(112, 0)
		row.add_child(a)
		row.add_child(_label(_format_binding(action), true, false))
		ctl.add_child(row)
	# a controller: gamepads, and handhelds' own controls (Steam Deck, ROG Ally, Legion Go)
	ctl.add_child(HSeparator.new())
	ctl.add_child(_label("Controller", true))
	_slider_row(ctl, "Stick look speed", 0.3, 2.5, Settings.stick_look_mult, func(v): Settings.set_stick_look(v))
	var inv := CheckBox.new()
	inv.text = "Invert look up / down"
	inv.button_pressed = Settings.invert_look_y
	inv.toggled.connect(func(on): Settings.set_invert_look_y(on))
	# System 6's checkbox: a square, crossed when on
	inv.add_theme_icon_override("unchecked", _image(["KKKKKKKKKK", "KWWWWWWWWK", "KWWWWWWWWK", "KWWWWWWWWK", "KWWWWWWWWK",
		"KWWWWWWWWK", "KWWWWWWWWK", "KWWWWWWWWK", "KWWWWWWWWK", "KKKKKKKKKK"]))
	inv.add_theme_icon_override("checked", _image(["KKKKKKKKKK", "KKWWWWWWKK", "KWKWWWWKWK", "KWWKWWKWWK", "KWWWKKWWWK",
		"KWWWKKWWWK", "KWWKWWKWWK", "KWKWWWWKWK", "KKWWWWWWKK", "KKKKKKKKKK"]))
	for st in ["normal", "hover", "pressed", "hover_pressed", "focus"]:
		inv.add_theme_stylebox_override(st, StyleBoxEmpty.new())
	for c in ["font_pressed_color", "font_hover_pressed_color", "font_hover_color"]:
		inv.add_theme_color_override(c, K)
	ctl.add_child(inv)
	_pad_rows = VBoxContainer.new()
	ctl.add_child(_pad_rows)
	_refresh_pad_rows()
	Controls.device_changed.connect(func(_p): _refresh_pad_rows())
	Input.joy_connection_changed.connect(func(_d, _c): _refresh_pad_rows())
	return tabs


var _pad_rows: VBoxContainer


func _refresh_pad_rows() -> void:
	## the controller's layout, its buttons named as the pad in hand labels them
	for c in _pad_rows.get_children():
		c.queue_free()
	var pads := Input.get_connected_joypads()
	_pad_rows.add_child(_label("Connected: %s" % (Input.get_joy_name(pads[0]) if not pads.is_empty() else "none")))
	var B := func(b): return Controls.button(b)
	for r in [["Move", B.call("LS")], ["Look", B.call("RS")], ["Jump / swim up", B.call(JOY_BUTTON_A)],
			["Swim down", B.call(JOY_BUTTON_B)], ["Use / Talk / Board", B.call(JOY_BUTTON_X)],
			["Attack / Fire", B.call("RT")], ["Weapons", "%s / %s" % [B.call(JOY_BUTTON_LEFT_SHOULDER), B.call(JOY_BUTTON_RIGHT_SHOULDER)]],
			["Sprint", B.call(JOY_BUTTON_LEFT_STICK)], ["Communicator", B.call(JOY_BUTTON_START)],
			["Drive / brake", "%s / %s" % [B.call("RT"), B.call("LT")]],
			["Climb / descend", "%s / %s" % [B.call("RT"), B.call("LT")]],
			["Stylus: tap / back", "%s / %s" % [B.call(JOY_BUTTON_A), B.call(JOY_BUTTON_B)]],
			["Stylus: tabs", "%s / %s" % [B.call(JOY_BUTTON_LEFT_SHOULDER), B.call(JOY_BUTTON_RIGHT_SHOULDER)]]]:
		var row := HBoxContainer.new()
		var a := _label(r[0], false, false)
		a.custom_minimum_size = Vector2(112, 0)
		row.add_child(a)
		row.add_child(_label(r[1], true, false))
		_pad_rows.add_child(row)


func _format_binding(action: String) -> String:
	if not InputMap.has_action(action):
		return "(none)"
	var events := InputMap.action_get_events(action)
	if events.is_empty():
		return "(unbound)"
	var e = events[0]
	if e is InputEventKey:
		return OS.get_keycode_string(e.physical_keycode if e.physical_keycode != 0 else e.keycode)
	if e is InputEventMouseButton:
		match e.button_index:
			MOUSE_BUTTON_LEFT: return "Mouse Left"
			MOUSE_BUTTON_RIGHT: return "Mouse Right"
			MOUSE_BUTTON_WHEEL_UP: return "Wheel Up"
			MOUSE_BUTTON_WHEEL_DOWN: return "Wheel Down"
			_: return "Mouse %d" % e.button_index
	return "?"


# ------------------------------------------------------------------ Help
func _help_tabs() -> TabContainer:
	var tabs := TabContainer.new()
	var c := _tab_page(tabs, "Contents")
	for line in [["Using The System", true],
			["Double-tap an icon on the desktop to open it, or tap System and choose it.  The keys under the screen open the Map, Items, Quests and Setup.", false],
			["In an app", true],
			["The tabs change pages.  The box at the top left closes the app; the ? box at the top right explains it.", false],
			["With a controller", true],
			["The left stick moves the stylus; A taps, B goes back, LB and RB change tabs, the right stick scrolls, Y opens the System menu.  On a Steam Deck the screen also takes your finger.", false],
			["Talking to people", true],
			["Open NPC AI and follow its three steps to give the station's people their voices.", false],
			["Getting a ride", true],
			["Open Summon Aerostat and tap Request: a red aerostat comes down and lands near you.  Fly gently -- it takes damage from 15 km/h, and a hard enough crash disables it.", false],
			["Putting it away", true],
			["Choose Suspend from the System menu, press the Power key, or press the Communicator key again.", false]]:
		c.add_child(_label(line[0], line[1]))
	var a := _tab_page(tabs, "About")
	var logo := TextureRect.new()
	logo.texture = load(PDA + "system_logo_32.png")
	logo.stretch_mode = TextureRect.STRETCH_KEEP_CENTERED
	a.add_child(logo)
	a.add_child(_label("NYNEX Communicator", true))
	a.add_child(_label("The System  version 1.1"))
	a.add_child(_label("240 x 320, 4-level display.  Backlight: automatic."))
	a.add_child(HSeparator.new())
	a.add_child(_label("Space Station Columbia", true))
	a.add_child(_label("Chicago FLF (public domain) and Pixel Operator (CC0) type."))
	return tabs
