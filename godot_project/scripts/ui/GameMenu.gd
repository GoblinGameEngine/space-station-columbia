extends CanvasLayer

## The game menu is the player's handheld: a NYNEX Communicator, a portrait mid-90s PDA (the Apple
## Newton MessagePad's and Palm Pilot's upright form) running "The System", which works and looks like
## the Macintosh's System 6 / 7 (the user, 2026-10-02: "Make the whole interface more Macintosh-like"):
##   - the menu bar along the top: the System menu (the logo: About, the apps), then the menus, and
##     the clock at the right. Menus drop down from it and may hold submenus (hierarchical, System 7's).
##     On the desktop: File (New Game, Load Game), Edit (Summon <kind> > every vehicle of it, Summon
##     Tram..., Dismiss Current Vehicle), System (Respawn, Exit Game). In an app: File (Close), View (its pages),
##     Help;
##   - the desktop: the grey dither, the apps' icons (double-tap opens);
##   - the apps: windows with a pinstriped title bar and a close box, their pages chosen from View:
##     Station Map (Station, Nearby) · Inventory (Weapons, Items) · Quests (Active, Completed) ·
##     NPC AI (Setup, Voice, Try it) · Navigation (Map, Travel, Law) · Control Panel (Sound, Display,
##     Controls) · Help (Contents, About);
##   - alerts: double-framed boxes with rounded buttons.
## The screen is a 240 x 320 dot-matrix LCD in 4 shades of black on green (ui/pda/lcd.gdshader), the
## green backlight on at night.  It is drawn at a whole number of screen pixels per LCD pixel (2 on
## the Steam Deck), and its type is pixel type drawn at its own size -- ChicagoFLF 12 for the
## system, Pixel Operator 16 for text -- so every letter lands on whole pixels: crisp at any size.
## The case has two controls: the power key (puts the device away) and a scroll wheel on its right side.

const SCREEN := Vector2i(240, 320)
const MENU_H := 20                      # the menu bar
const ROW_H := 16                       # a menu item
const TITLE_H := 19
const SYS_SIZE := 12                    # ChicagoFLF: crisp at 12
const TEXT_SIZE := 16                   # Pixel Operator: crisp at 16
# the case round the screen, in screen pixels at 800 px of display height
const CASE_TOP := 58.0                  # the forehead: NYNEX, the speaker, the power key
const CASE_BOTTOM := 56.0               # the chin: the bell and COMMUNICATOR
const CASE_SIDE := 26.0
const BEZEL := 9.0                      # the well round the glass
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
var _power: Button
var _wheel: CaseWheel
var _screen_rect: TextureRect
var _vp: SubViewport
var _lcd: ShaderMaterial
var _desk: Control
var _desk_icons := {}
var _clock: Label
var _bar: Control                      # the menu bar
var _bar_titles: HBoxContainer
var _menu_layer: Control               # the open menus (and a catcher: a tap off them closes them)
var _menus: Array = []                 # the bar's menus: [{title, logo, items}]
var _menu_stack: Array = []            # the open menu and its open submenus: [{node, rows, items}]
var _open_title := -1
var _apps := {}                        # name -> app window Control
var _pages := {}                       # name -> its TabContainer (the pages, chosen from View)
var _app_titles := {}                  # name -> its MacTitle
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
var _pointer_at := Vector2(120, 150)   # where the pointer last was on the LCD (the scroll wheel scrolls there)
var _pad_tap := false                  # the tap under way came from a controller's A
var _scroll_t := 0.0
const STYLUS_SPEED := 190.0            # LCD pixels a second at full stick

const APPS := [
	["map", "Station Map", "icon_map.png"],
	["inventory", "Inventory", "icon_inventory.png"],
	["quests", "Quests", "icon_quests.png"],
	["ai", "NPC AI", "icon_ai.png"],
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
		_close_menus()
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
	_pointer_at = p
	_stylus.position = p.floor()
	_stylus.move_to_front()


func _pad_input(e: InputEventJoypadButton) -> void:
	## A taps (hold and move to drag), B goes back, LB / RB change pages, Y the menu bar, the D-pad
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
				if _open_title >= 0:
					_close_menus()
				else:
					_open_menu(mini(1, _menus.size() - 1))
		JOY_BUTTON_LEFT_SHOULDER, JOY_BUTTON_RIGHT_SHOULDER:
			if e.pressed and _current != "":
				var tabs: TabContainer = _pages[_current]
				var step := 1 if e.button_index == JOY_BUTTON_RIGHT_SHOULDER else -1
				_show_page(posmod(tabs.current_tab + step, tabs.get_tab_count()))
		JOY_BUTTON_DPAD_UP, JOY_BUTTON_DPAD_DOWN, JOY_BUTTON_DPAD_LEFT, JOY_BUTTON_DPAD_RIGHT:
			if e.pressed:
				var d := {JOY_BUTTON_DPAD_UP: Vector2.UP, JOY_BUTTON_DPAD_DOWN: Vector2.DOWN,
					JOY_BUTTON_DPAD_LEFT: Vector2.LEFT, JOY_BUTTON_DPAD_RIGHT: Vector2.RIGHT}
				_set_stylus(_stylus_at + d[e.button_index] * 6.0)


func _back() -> void:
	## B: the alert, then the open menus, then the app, then the device itself
	var f := _vp.gui_get_focus_owner()
	if f is LineEdit:
		f.release_focus()
	elif _msgbox.visible:
		_msgbox.visible = false
	elif _open_title >= 0:
		_close_menus()
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
	## What's printed on the case: NYNEX centred on the forehead; the Bell bell and COMMUNICATOR
	## centred on the chin (tools/pda_case.py); POWER under the power key.
	var font: Font
	var k := 1.0
	var nynex: Texture2D
	var bell: Texture2D
	var word: Texture2D
	var forehead := Rect2()
	var chin := Rect2()
	var power := Rect2()
	const SILVER := Color(0.8, 0.81, 0.83)

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


class CaseWheel extends Control:
	## The scroll wheel on the case's right side: a ridged rubber wheel standing a little proud of the
	## case in its slot. Rolled (dragged up or down), turned with a mouse wheel, or tapped above or
	## below its middle, it scrolls the screen where the pointer is -- one notch at a time.
	signal notch(down: bool)
	var k := 1.0
	var phase := 0.0
	var _drag := false
	var _acc := 0.0

	func _draw() -> void:
		var r := Rect2(Vector2.ZERO, size)
		draw_rect(r.grow(1.0 * k), Color(0.04, 0.045, 0.05))                 # the slot
		var pitch := 4.0 * k
		var n := int(size.y / pitch) + 2
		for i in n:
			var y := fposmod(phase + i * pitch, size.y + pitch) - pitch * 0.5
			if y < 0.0 or y > size.y:
				continue
			var t := y / size.y                                                # round the wheel: lit on top, dark below
			var lit := sin(t * PI) * (1.15 - 0.5 * t)
			draw_rect(Rect2(0, y, size.x, maxf(1.0, pitch * 0.5 * sin(t * PI))), Color(0.07, 0.075, 0.08).lerp(Color(0.36, 0.37, 0.39), lit))
		for i in int(size.y):
			var t := (i + 0.5) / size.y                                       # its curve: the ends fall away into shadow
			draw_rect(Rect2(0, i, size.x, 1), Color(0, 0, 0, 0.75 * pow(absf(t - 0.42) * 2.0, 2.2)))

	func _step(down: bool) -> void:
		phase += (1.0 if down else -1.0) * 2.0 * k
		queue_redraw()
		notch.emit(down)

	func _gui_input(e: InputEvent) -> void:
		if e is InputEventMouseButton:
			if e.button_index == MOUSE_BUTTON_WHEEL_DOWN and e.pressed:
				_step(true)
			elif e.button_index == MOUSE_BUTTON_WHEEL_UP and e.pressed:
				_step(false)
			elif e.button_index == MOUSE_BUTTON_LEFT:
				if e.pressed:
					_drag = true
					_acc = 0.0
				else:
					if _drag and absf(_acc) < 2.0:                             # a tap: one notch, toward the side tapped
						_step(e.position.y > size.y * 0.5)
					_drag = false
			accept_event()
		elif e is InputEventMouseMotion and _drag:
			_acc += e.relative.y
			while absf(_acc) >= 7.0 * k:                                       # a notch every few pixels rolled
				_step(_acc < 0.0)                                               # (rolled up -- the thumb pushing the wheel up -- scrolls down)
				_acc -= signf(_acc) * 7.0 * k
			accept_event()


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
	# the two controls: the power key, and the scroll wheel down the right side
	_power = _power_key()
	body.add_child(_power)
	_wheel = CaseWheel.new()
	_wheel.notch.connect(_wheel_notch)
	body.add_child(_wheel)
	_layout()


func _wheel_notch(down: bool) -> void:
	## A notch of the case's wheel: a mouse wheel's notch on the screen, where the pointer is (over an
	## open menu, the menu).
	var at := _pointer_at
	if not _menu_stack.is_empty():
		var m: Control = _menu_stack[-1].node
		at = m.position + m.size * 0.5
	for pressed in [true, false]:
		var w := InputEventMouseButton.new()
		w.button_index = MOUSE_BUTTON_WHEEL_DOWN if down else MOUSE_BUTTON_WHEEL_UP
		w.pressed = pressed
		w.position = at.floor()
		w.global_position = w.position
		_vp.push_input(w, true)


func _mipmapped(path: String) -> ImageTexture:
	## the case's printing is drawn much smaller than its artwork: smooth it down
	var img := (load(path) as Texture2D).get_image()
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)


func _screen_input(event: InputEvent) -> void:
	## Taps and drags on the glass go to The System, in LCD pixels.
	if event is InputEventMouse:
		var ev: InputEventMouse = event.duplicate()
		ev.position = (event.position / _px).floor()
		_pointer_at = ev.position
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
	var case_h := (CASE_TOP + CASE_BOTTOM + 2.0 * BEZEL) * _k
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
	var well := lr.grow(BEZEL * _k)
	var forehead := Rect2(Vector2.ZERO, Vector2(body.x, well.position.y))
	var chin := Rect2(Vector2(0, well.end.y), Vector2(body.x, body.y - well.end.y))
	var power := Rect2(Vector2(well.position.x + 6 * _k, forehead.size.y * 0.5 - 8 * _k), Vector2(30, 11) * _k)
	_case_mat.set_shader_parameter("body_size", body)
	_case_mat.set_shader_parameter("radius", 24.0 * _k)
	_case_mat.set_shader_parameter("k", _k)
	_case_mat.set_shader_parameter("well", Vector4(well.position.x, well.position.y, well.size.x, well.size.y))
	_case_mat.set_shader_parameter("well_radius", 5.0 * _k)
	var gw := 7.0 * 6 * _k
	_case_mat.set_shader_parameter("grille", Vector4(well.end.x - gw - 4 * _k, forehead.size.y * 0.5 - 10.5 * _k, gw, 21.0 * _k))
	_case_mat.set_shader_parameter("silo", Vector4(5 * _k, well.position.y + 30 * _k, 7 * _k, well.size.y - 60 * _k))
	_device.queue_redraw()
	_print.size = body
	_print.k = _k
	_print.forehead = forehead
	_print.chin = chin
	_print.power = power
	_print.queue_redraw()
	_power.size = power.size.round()
	_power.position = power.position.floor()
	# the wheel: in the right side, level with the screen's upper middle, standing a little proud of the case
	_wheel.k = _k
	_wheel.size = Vector2(9.0, 70.0) * _k
	_wheel.position = Vector2(body.x - 6.0 * _k, well.position.y + well.size.y * 0.38 - 35.0 * _k).floor()
	_wheel.queue_redraw()
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


func _update_clock() -> void:
	var scene := get_tree().current_scene
	var sky: Node = scene.get("sky_system") if scene else null
	var t: float = sky.time_of_day if sky else 0.5
	var mins := int(t * 24.0 * 60.0)
	var h := (mins / 60) % 24
	_clock.text = "%d:%02d %s" % [12 if h % 12 == 0 else h % 12, mins % 60, "AM" if h < 12 else "PM"]


# ------------------------------------------------------------------ The System
class MacTitle extends Control:
	## A System 6 title bar: pinstripes, the close box on the left, the title centred on a white band.
	signal close_pressed
	var title := ""
	var font: Font
	var font_size := 12
	var _down := false

	func _frame(r: Rect2, c: Color) -> void:
		draw_rect(Rect2(r.position, Vector2(r.size.x, 1)), c)
		draw_rect(Rect2(r.position + Vector2(0, r.size.y - 1), Vector2(r.size.x, 1)), c)
		draw_rect(Rect2(r.position, Vector2(1, r.size.y)), c)
		draw_rect(Rect2(r.position + Vector2(r.size.x - 1, 0), Vector2(1, r.size.y)), c)

	func close_box() -> Rect2:
		return Rect2(8, 4, 11, 11)

	func _draw() -> void:
		draw_rect(Rect2(Vector2.ZERO, size), Color.WHITE)
		for y in range(4, int(size.y) - 4, 2):
			draw_rect(Rect2(1, y, size.x - 2, 1), Color.BLACK)
		draw_rect(Rect2(0, size.y - 1, size.x, 1), Color.BLACK)
		var r := close_box()
		draw_rect(r.grow(1), Color.WHITE)
		_frame(r, Color.BLACK)
		if _down:
			draw_rect(r.grow(-2), Color.BLACK)
		var tw := font.get_string_size(title, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
		var tx := floorf((size.x - tw) * 0.5)
		draw_rect(Rect2(tx - 6, 1, tw + 12, size.y - 2), Color.WHITE)
		var base := floorf((size.y - font.get_height(font_size)) * 0.5) + font.get_ascent(font_size)
		draw_string(font, Vector2(tx, base), title, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color.BLACK)

	func _gui_input(e: InputEvent) -> void:
		if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT:
			var hit := close_box().grow(2).has_point(e.position)
			if e.pressed:
				_down = hit
			else:
				if hit and _down:
					close_pressed.emit()
				_down = false
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


class MenuBarView extends Control:
	## The menu bar: white, a black line under it.
	func _draw() -> void:
		draw_rect(Rect2(Vector2.ZERO, size), Color.WHITE)
		draw_rect(Rect2(0, size.y - 1, size.x, 1), Color.BLACK)


class MenuTitle extends Control:
	## A menu's title in the bar (its name, or the System menu's logo), inverted while its menu is open.
	signal tapped
	signal hovered
	var text := ""
	var logo: Texture2D
	var logo_open: Texture2D               # (the logo inverted)
	var font: Font
	var font_size := 12
	var open := false

	func _draw() -> void:
		var r := Rect2(0, 0, size.x, size.y - 1)
		if open:
			draw_rect(r, Color.BLACK)
		if logo:
			draw_texture(logo_open if open else logo, ((r.size - logo.get_size()) * 0.5).floor())
		else:
			var base := floorf((r.size.y - font.get_height(font_size)) * 0.5) + font.get_ascent(font_size)
			draw_string(font, Vector2(7, base), text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color.WHITE if open else Color.BLACK)

	func _gui_input(e: InputEvent) -> void:
		if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT and e.pressed:
			tapped.emit()
			accept_event()
		elif e is InputEventMouseMotion:
			hovered.emit()


class MenuRow extends Control:
	## An item of a menu: its name (grey when it can't be chosen), a check mark before it when it's the
	## one in force, a triangle after it when it opens a submenu; inverted under the pointer. A dotted
	## line between groups.
	signal chosen
	signal hovered
	var text := ""
	var font: Font
	var font_size := 12
	var sub := false
	var checked := false
	var disabled := false
	var sep := false
	var hot := false

	func _draw() -> void:
		if sep:
			for x in range(0, int(size.x), 2):
				draw_rect(Rect2(x, floorf(size.y * 0.5), 1, 1), Color.BLACK)
			return
		var ink := Color.BLACK
		if hot and not disabled:
			draw_rect(Rect2(Vector2.ZERO, size), Color.BLACK)
			ink = Color.WHITE
		elif disabled:
			ink = Color(0.667, 0.667, 0.667)
		var mid := floorf(size.y * 0.5)
		if checked:
			for q in [Vector2(0, 3), Vector2(1, 4), Vector2(2, 5), Vector2(3, 4), Vector2(4, 3), Vector2(5, 2), Vector2(6, 1), Vector2(7, 0)]:
				draw_rect(Rect2(Vector2(3, mid - 3) + q, Vector2(1, 2)), ink)
		var base := floorf((size.y - font.get_height(font_size)) * 0.5) + font.get_ascent(font_size)
		draw_string(font, Vector2(14, base), text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, ink)
		if sub:
			for i in 4:
				draw_rect(Rect2(size.x - 10 + i, mid - 3 + i, 1, 7 - 2 * i), ink)

	func _gui_input(e: InputEvent) -> void:
		if sep:
			return
		if e is InputEventMouseMotion:
			if not hot:
				hovered.emit()
		elif e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT:
			if not e.pressed:
				hovered.emit()
				chosen.emit()
			accept_event()


class ScreenCorners extends Control:
	## The Macintosh screen's rounded corners: a few black pixels at each.
	const R := 5
	func _draw() -> void:
		for y in R:
			for x in R:
				if pow(R - x - 0.5, 2.0) + pow(R - y - 0.5, 2.0) > R * R:
					for c in [Vector2(x, y), Vector2(size.x - 1 - x, y), Vector2(x, size.y - 1 - y), Vector2(size.x - 1 - x, size.y - 1 - y)]:
						draw_rect(Rect2(c, Vector2.ONE), Color.BLACK)


func _build_system() -> void:
	var root := Control.new()
	root.theme = _theme
	root.size = Vector2(SCREEN)
	_vp.add_child(root)
	# the desktop: the grey dither, the icons
	_desk = Panel.new()
	_desk.position = Vector2(0, MENU_H)
	_desk.size = Vector2(SCREEN.x, SCREEN.y - MENU_H)
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
	_app("map", "Station Map", _map_tabs(), "The station's map.  Station: the whole ring, north (the Marlowe end) up.  Nearby: the kilometre round you.")
	_app("inventory", "Inventory", _inventory_tabs(), "What you carry.  Weapons: tap Equip to arm one.")
	_app("quests", "Quests", _quest_tabs(), "Your tasks.  Tap Track to follow one on the map.")
	_app("ai", "NPC AI", _ai_tabs(), "The station's people talk through an AI service.  Setup: get a free Groq key and paste it in.  Voice: choose the model.  Try it: talk to someone.")
	_app("nav", "Navigation", _nav_tabs(), "The political map: whose law runs where (the dotted shades), town limits, roads, tram lines.  Drag to look round, + and - to zoom: the closer, the more is named.  Boxed T: a fast-travel tram stop -- tap it, or pick a town under Travel.  Law: the rules where you stand.")
	_app("control", "Control Panel", _control_tabs(), "Sound, Display and Controls settings.")
	_app("help", "Help", _help_tabs(), "The System Help.")
	for a in _apps.values():
		a.visible = false
		root.add_child(a)
	# the open menus, over everything but the bar (a tap off them closes them)
	_menu_layer = Control.new()
	_menu_layer.size = Vector2(SCREEN)
	_menu_layer.visible = false
	_menu_layer.gui_input.connect(func(e: InputEvent):
		if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
			_close_menus())
	root.add_child(_menu_layer)
	# the menu bar: the menus' titles, the clock at the right
	_bar = MenuBarView.new()
	_bar.size = Vector2(SCREEN.x, MENU_H)
	_bar.gui_input.connect(func(e: InputEvent):
		if e is InputEventMouseButton and e.pressed:
			_close_menus())
	_bar_titles = HBoxContainer.new()
	_bar_titles.add_theme_constant_override("separation", 0)
	_bar_titles.position = Vector2(6, 0)
	_bar_titles.size = Vector2(0, MENU_H)
	_bar.add_child(_bar_titles)
	_clock = Label.new()
	_clock.add_theme_font_override("font", _bold)
	_clock.add_theme_font_size_override("font_size", SYS_SIZE)
	_clock.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_clock.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_clock.position = Vector2(SCREEN.x - 76, 0)
	_clock.size = Vector2(68, MENU_H - 1)
	_clock.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_bar.add_child(_clock)
	root.add_child(_bar)
	_set_menus(_desktop_menus())
	_msgbox = Control.new()
	_msgbox.size = Vector2(SCREEN)
	_msgbox.visible = false
	root.add_child(_msgbox)
	var corners := ScreenCorners.new()
	corners.size = Vector2(SCREEN)
	corners.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(corners)
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
		_close_menus()
		_select_icon("")


func _select_icon(name: String) -> void:
	for k in _desk_icons:
		_desk_icons[k].selected = (k == name)
		_desk_icons[k].queue_redraw()


func _icon_tapped(name: String) -> void:
	## One tap selects, a double tap opens.
	_close_menus()
	var now := Time.get_ticks_msec()
	if _pad_tap or now - int(_last_click.get(name, -10000)) < 600:        # (a controller's tap opens at once)
		_last_click[name] = -10000
		_select_icon("")
		_open_app(name)
	else:
		_last_click[name] = now
		_select_icon(name)


# ------------------------------------------------------------------ the menu bar
## A menu is {title, logo, items}; an item is {text, do (a Callable)}, or {text, sub (items)} for a
## submenu, or {sep} for a dotted line; "checked" and "disabled" as they say.

func _item(text: String, do: Callable, extra := {}) -> Dictionary:
	var d := {"text": text, "do": do}
	d.merge(extra)
	return d


func _sub(text: String, items: Array) -> Dictionary:
	return {"text": text, "sub": items, "disabled": items.is_empty()}


func _sep() -> Dictionary:
	return {"sep": true}


func _logo_menu() -> Dictionary:
	## The System menu, under the logo (the Apple menu's place): About, and the apps.
	var items: Array = [_item("About The System...", _show_about), _sep()]
	for a in APPS:
		items.append(_item(a[1], _open_app.bind(a[0])))
	return {"title": "", "logo": true, "items": items}


func _desktop_menus() -> Array:
	## The game's menus (the user's: File > New Game, Load Game; Edit > Summon ...; System > Respawn, Exit Game).
	return [_logo_menu(),
		{"title": "File", "items": [_item("New Game...", _confirm_new_game), _item("Load Game...", _load_game)]},
		{"title": "Edit", "items": _edit_items()},
		{"title": "System", "items": [_item("Respawn", _respawn), _sep(), _item("Exit Game...", _confirm_exit)]}]


func _app_menus(name: String) -> Array:
	## An app's menus: File (Close), View (its pages, the one shown checked), Help.
	var tabs: TabContainer = _pages[name]
	var pages: Array = []
	for i in tabs.get_tab_count():
		pages.append(_item(tabs.get_tab_title(i), _show_page.bind(i), {"checked": i == tabs.current_tab}))
	var t: String = _app_titles[name].get_meta("app")
	return [_logo_menu(),
		{"title": "File", "items": [_item("Close", _close_app)]},
		{"title": "View", "items": pages},
		{"title": "Help", "items": [_item("%s Help" % t, func(): _show_message(t, str(_app_titles[name].get_meta("help"))))]}]


func _set_menus(spec: Array) -> void:
	_close_menus()
	_menus = spec
	for c in _bar_titles.get_children():
		_bar_titles.remove_child(c)
		c.queue_free()
	for i in spec.size():
		var m: Dictionary = spec[i]
		var t := MenuTitle.new()
		t.font = _bold
		t.font_size = SYS_SIZE
		if m.get("logo", false):
			t.logo = load(PDA + "system_logo.png")
			t.logo_open = _inverted(t.logo)
			t.custom_minimum_size = Vector2(28, MENU_H)
		else:
			t.text = str(m.title)
			t.custom_minimum_size = Vector2(ceilf(_bold.get_string_size(t.text, HORIZONTAL_ALIGNMENT_LEFT, -1, SYS_SIZE).x) + 14, MENU_H)
		t.tapped.connect(_title_tapped.bind(i))
		t.hovered.connect(_title_hovered.bind(i))
		_bar_titles.add_child(t)


func _inverted(tex: Texture2D) -> ImageTexture:
	var img := tex.get_image()
	img.convert(Image.FORMAT_RGBA8)
	for y in img.get_height():
		for x in img.get_width():
			var c := img.get_pixel(x, y)
			img.set_pixel(x, y, Color(1.0 - c.r, 1.0 - c.g, 1.0 - c.b, c.a))
	return ImageTexture.create_from_image(img)


func _title_tapped(i: int) -> void:
	if _open_title == i:
		_close_menus()
	else:
		_open_menu(i)


func _title_hovered(i: int) -> void:
	## With a menu open, moving along the bar opens the menu under the pointer (the Mac's way).
	if _open_title >= 0 and _open_title != i:
		_open_menu(i)


func _open_menu(i: int) -> void:
	_close_menus()
	if i < 0 or i >= _menus.size():
		return
	_open_title = i
	var t := _bar_titles.get_child(i) as MenuTitle
	t.open = true
	t.queue_redraw()
	_drop(_menus[i].items, Vector2(_bar_titles.position.x + t.position.x, MENU_H - 1), 0)


func _close_menus() -> void:
	for m in _menu_stack:
		(m.node as Node).queue_free()
	_menu_stack.clear()
	if _bar_titles and _open_title >= 0 and _open_title < _bar_titles.get_child_count():
		var t := _bar_titles.get_child(_open_title) as MenuTitle
		t.open = false
		t.queue_redraw()
	_open_title = -1
	if _menu_layer:
		_menu_layer.visible = false


func _drop(items: Array, at: Vector2, level: int) -> void:
	## A menu (level 0) or a submenu (1, 2 ...) at `at`: white, black edged, a shadow at its right and
	## foot. One too long for the screen scrolls (the wheel, the right stick, its scroll bar).
	while _menu_stack.size() > level:
		(_menu_stack.pop_back().node as Node).queue_free()
	var w := 0.0
	var h := 0.0
	var has_sub := false
	for it in items:
		if it.get("sep", false):
			h += 7
			continue
		w = maxf(w, _bold.get_string_size(str(it.text), HORIZONTAL_ALIGNMENT_LEFT, -1, SYS_SIZE).x)
		has_sub = has_sub or it.has("sub")
		h += ROW_H
	w = ceilf(w + 14 + (18 if has_sub else 10))
	var max_h := SCREEN.y - 4 - at.y
	if h > max_h and level > 0:                          # (a submenu moves up the screen before it scrolls)
		at.y = maxf(MENU_H, SCREEN.y - 4 - h)
		max_h = SCREEN.y - 4 - at.y
	var scroll := h > max_h
	var view_h := minf(h, max_h)
	var sb := 12.0 if scroll else 0.0
	var holder := Control.new()
	holder.size = Vector2(w + sb + 3, view_h + 3)
	holder.position = Vector2(clampf(at.x, 0.0, SCREEN.x - holder.size.x), at.y).floor()
	var shadow := ColorRect.new()
	shadow.color = K
	shadow.position = Vector2(1, 1)
	shadow.size = Vector2(w + sb + 2, view_h + 2)
	shadow.mouse_filter = Control.MOUSE_FILTER_IGNORE
	holder.add_child(shadow)
	var panel := Panel.new()
	panel.add_theme_stylebox_override("panel", _flat(W, K, 1, 0, 0))
	panel.size = Vector2(w + sb + 2, view_h + 2)
	holder.add_child(panel)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 0)
	var rows: Array = []
	for idx in items.size():
		var it: Dictionary = items[idx]
		var r := MenuRow.new()
		r.font = _bold
		r.font_size = SYS_SIZE
		r.sep = it.get("sep", false)
		r.text = str(it.get("text", ""))
		r.sub = it.has("sub")
		r.checked = it.get("checked", false)
		r.disabled = it.get("disabled", false)
		r.custom_minimum_size = Vector2(w, 7 if r.sep else ROW_H)
		r.hovered.connect(_row_hover.bind(level, idx))
		r.chosen.connect(_row_chosen.bind(level, idx))
		col.add_child(r)
		rows.append(r)
	if scroll:
		var sc := ScrollContainer.new()
		sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
		sc.position = Vector2(1, 1)
		sc.size = Vector2(w + sb, view_h)
		col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		sc.add_child(col)
		panel.add_child(sc)
	else:
		col.position = Vector2(1, 1)
		panel.add_child(col)
	_menu_layer.add_child(holder)
	_menu_layer.visible = true
	_menu_stack.append({"node": holder, "rows": rows, "items": items, "from": -1})


func _row_hover(level: int, idx: int) -> void:
	## The pointer on an item: it lights; a submenu's item opens its submenu beside it.
	if level >= _menu_stack.size():
		return
	var m: Dictionary = _menu_stack[level]
	for j in m.rows.size():
		var r: MenuRow = m.rows[j]
		if r.hot != (j == idx):
			r.hot = (j == idx)
			r.queue_redraw()
	var it: Dictionary = m.items[idx]
	if it.has("sub") and not it.get("disabled", false):
		if _menu_stack.size() > level + 1 and int(_menu_stack[level + 1].get("opened_by", -1)) == idx:
			return
		var row: Control = m.rows[idx]
		var hold: Control = m.node
		_drop(it.sub, Vector2(hold.position.x + hold.size.x - 6, row.get_global_rect().position.y - 1), level + 1)
		_menu_stack[-1]["opened_by"] = idx
	else:
		while _menu_stack.size() > level + 1:
			(_menu_stack.pop_back().node as Node).queue_free()


func _row_chosen(level: int, idx: int) -> void:
	if level >= _menu_stack.size():
		return
	var it: Dictionary = _menu_stack[level].items[idx]
	if it.get("disabled", false) or it.get("sep", false) or it.has("sub"):
		return
	_close_menus()
	(it.do as Callable).call()


# ------------------------------------------------------------------ the windows
func _dotted() -> StyleBoxTexture:
	## the grey (dotted) line System 6 menus separate groups with
	var s := StyleBoxTexture.new()
	s.texture = _image(["KW"])
	s.axis_stretch_horizontal = StyleBoxTexture.AXIS_STRETCH_MODE_TILE
	s.content_margin_top = 1
	return s


func _app(name: String, title: String, tabs: TabContainer, help: String) -> void:
	## An app's window, under the menu bar: a System 6 title bar (the close box, the title and the page
	## shown), a black frame, then its pages -- chosen from the View menu, not tabs.
	var w := Control.new()
	w.position = Vector2(0, MENU_H)
	w.size = Vector2(SCREEN.x, SCREEN.y - MENU_H)
	var bg := Panel.new()
	bg.size = w.size
	bg.add_theme_stylebox_override("panel", _flat(W, K, 1))
	w.add_child(bg)
	var bar := MacTitle.new()
	bar.title = title
	bar.font = _bold
	bar.font_size = SYS_SIZE
	bar.size = Vector2(SCREEN.x, TITLE_H)
	bar.close_pressed.connect(_close_app)
	bar.set_meta("app", title)
	bar.set_meta("help", help)
	w.add_child(bar)
	tabs.tabs_visible = false
	tabs.position = Vector2(4, TITLE_H + 3)
	tabs.size = Vector2(SCREEN.x - 8, SCREEN.y - MENU_H - TITLE_H - 7)
	w.add_child(tabs)
	_apps[name] = w
	_pages[name] = tabs
	_app_titles[name] = bar


func _open_app(name: String) -> void:
	if not _is_open:
		return
	_close_menus()
	for k in _apps:
		_apps[k].visible = (k == name)
	_current = name
	_show_page(_pages[name].current_tab)
	if name == "map":
		_refresh_map()
	if name == "ai":
		_refresh_ai()
	if name == "nav":
		_refresh_nav()


func _show_page(i: int) -> void:
	## A page of the open app (View, or LB / RB): the title bar names it, View checks it.
	if _current == "":
		return
	var tabs: TabContainer = _pages[_current]
	tabs.current_tab = i
	var bar: MacTitle = _app_titles[_current]
	var t: String = bar.get_meta("app")
	bar.title = t if tabs.get_tab_count() < 2 else "%s: %s" % [t, tabs.get_tab_title(i)]
	bar.queue_redraw()
	_set_menus(_app_menus(_current))


func _close_app() -> void:
	if _current != "":
		_apps[_current].visible = false
	_current = ""
	_set_menus(_desktop_menus())


func _show_message(title: String, text: String, buttons := [["OK", Callable()]], extra: Control = null) -> void:
	## A System 6 alert: a double-framed box in the middle of the screen, the logo, the message (and
	## any control it asks with) and rounded buttons (the first, the default, ringed).
	_close_menus()
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
	if extra:
		tv.add_child(extra)
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
	outer.position = ((Vector2(SCREEN) - outer.size) * 0.5).floor()
	_msgbox.visible = true


func _show_about() -> void:
	_show_message("About The System", "NYNEX Communicator\nThe System, version 2.0\n240 x 320, 4-level display.  Backlight: automatic.")


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


func _load_game() -> void:
	## (There's no saving yet: nothing to load.)
	_show_message("Load Game", "There are no saved games.")


func _respawn() -> void:
	## Back to where you started, out of any vehicle.
	var pl := get_tree().get_first_node_in_group("player") as StationPlayer
	if pl == null:
		return
	set_open(false)
	pl.respawn()


func _confirm_exit() -> void:
	_show_message("Exit Game", "Leave Space Station Columbia?", [["Exit", func(): get_tree().quit()], ["Cancel", Callable()]])


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
		_map_overview = load(PDA + "map_overview.png")      # (tools/pda_detail_map.py; the detail is PdaMapTiles)
		_map_tex = _map_overview
	if _towns.is_empty() and FileAccess.file_exists("res://remake/placement.json"):
		var acc := {}
		for e in Placement.entries():
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
		_map_nearby.queue_redraw()                          # (the window is drawn in _draw_nearby_marker)
	_map_station.queue_redraw()


func _draw_station_map() -> void:
	var sz := _map_station.size
	if _map_tex:
		var h := floorf(sz.x * StationGeo.LENGTH / StationGeo.CIRC)
		_map_station.draw_texture_rect(_map_overview, Rect2(0, 0, sz.x, h), false)
		_map_station.draw_rect(Rect2(0, 0, sz.x, h), K, false)
		var p := _player_sx()
		var u := Vector2(fposmod(p.x, StationGeo.CIRC) / StationGeo.CIRC * sz.x,
			(p.y + StationGeo.HALF_LEN) / StationGeo.LENGTH * h).floor()
		var blink := int(Time.get_ticks_msec() / 400) % 2 == 0
		_map_station.draw_rect(Rect2(u - Vector2(3, 3), Vector2(7, 7)), K if blink else W)
		_map_station.draw_string(_font, Vector2(2, h + 14), "N (Marlowe) up   E ->", HORIZONTAL_ALIGNMENT_LEFT, -1, TEXT_SIZE, K)


func _draw_nearby_marker() -> void:
	var c := (_map_nearby.size * 0.5).floor()
	var p := _player_sx()
	# Nearby: a 0.9 km x 1 km window of the map round the player, north up (1 LCD pixel = one 4 m map pixel)
	var mpp := PdaMapTiles.M
	PdaMapTiles.draw(_map_nearby, Rect2(Vector2.ZERO, _map_nearby.size), p.x - _map_nearby.size.x * 0.5 * mpp,
		p.y - _map_nearby.size.y * 0.5 * mpp, mpp)
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
var _nav_where: OptionButton
var _ft_groups: Array = []           # [{name, dests: [{name, s, x, face, what}]}] (fast travel: _fast_travel_groups)
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
	tv.add_child(_label("Fast travel to:", true))
	_nav_where = OptionButton.new()
	_nav_where.item_selected.connect(_fill_fast_travel)
	tv.add_child(_nav_where)
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
	if _ft_groups.is_empty():
		_ft_groups = _fast_travel_groups()
		_nav_where.clear()
		for g in _ft_groups:
			_nav_where.add_item(str(g.name))
	# (the town you're nearest, each time the PDA opens)
	var here_i := 0
	var hd2 := INF
	var p0 := _player_sx()
	for i in _ft_groups.size():
		var c = _ft_groups[i].get("centre")
		if c is Vector2:
			var d := Vector2(StationGeo.wrap_ds((c as Vector2).x - p0.x), (c as Vector2).y - p0.y).length()
			if d < hd2:
				hd2 = d
				here_i = i
	if not _ft_groups.is_empty():
		_nav_where.select(here_i)
		_fill_fast_travel(here_i)
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


# ------------------------------------------------------------------ fast travel (the Navigator's Travel page)
## The user, 2026-10-09: "fast travel locations to points of interest in each city and significant places on the map"
## (the player's alone: NPCs never use it). Each town's civic and public places (its town hall, courthouse, library,
## hospital, schools, churches, post office, station, cinema, lighthouse ...), its squares, beaches and fields, and its
## tram stop; and the map's landmarks -- the summits, the islands, the falls, the ponds. You arrive outside, facing it;
## the clock moves on by the trip.
const FT_PLACES := [["town_hall", "Town Hall", 1], ["courthouse", "Courthouse", 1], ["admin_center", "Administration Centre", 1],
	["police_fire", "Police and Fire", 1], ["hospital", "Hospital", 1], ["library", "Library", 1], ["post_office", "Post Office", 1],
	["college", "College", 1], ["college_extension", "College Extension", 1], ["school", "School", 2], ["church", "Church", 2],
	["community_hall", "Community Hall", 1], ["movie_theater", "Cinema", 1], ["hotel", "Hotel", 1], ["transit_station", "Station", 1],
	["transit_depot", "Transit Depot", 1], ["lighthouse", "Lighthouse", 1], ["grocery", "Grocery", 1], ["diner", "Diner", 1],
	["bar", "Bar", 1], ["bank", "Bank", 1], ["charge_stop", "Charge Stop", 1], ["grain_elevator", "Grain Elevator", 1],
	["farm", "Farm", 1]]
const FT_WORKS := ["remelting_works", "rolling_mill", "tube_works", "foundry", "machine_shop", "motor_works", "cell_works",
	"tyre_works", "glass_works", "gauge_works", "electronics_works", "coachworks", "paint_works", "textile_mill", "sawmill",
	"food_plant", "printing_plant", "factory", "distribution_centre", "truck_terminal", "warehouse"]
const FT_AREAS := {"square": "Town Square", "plaza": "Plaza", "beach": "Beach", "sportsfield": "Sports Field", "green": "Village Green",
	"campus": "Campus", "boat_ramp": "Boat Ramp"}


func _fast_travel_groups() -> Array:
	var units := NpcPlaces.units()
	var by_town := {}                                    # settlement -> [units]
	for uid in units:
		var u: Dictionary = units[uid]
		var t := str(u.get("settlement", ""))
		if t == "":
			continue
		if not by_town.has(t):
			by_town[t] = []
		(by_town[t] as Array).append(u)
	var info := {}
	if FileAccess.file_exists("res://remake/law/settlements.json"):
		for st in JSON.parse_string(FileAccess.get_file_as_string("res://remake/law/settlements.json")).settlements:
			info[str(st.name)] = st
	var trams := {}
	for dd in _nav_dests():
		if dd.own:
			trams[str(dd.name)] = dd
	var areas: Array = MapTerrain.data().get("areas", [])
	var groups: Array = []
	for t in by_town:
		var us: Array = by_town[t]
		var st: Dictionary = info.get(t, {})
		var c := Vector2.INF
		if st.get("centre") != null:
			c = Vector2(float(st.centre[0]), float(st.centre[1]))
		else:                                            # (the middle of its places)
			var acc := Vector2.ZERO
			var s0 := float(us[0].door[0])
			for u in us:
				acc += Vector2(StationGeo.wrap_ds(float(u.door[0]) - s0), float(u.door[1]))
			acc /= us.size()
			c = Vector2(fposmod(s0 + acc.x, StationGeo.CIRC), acc.y)
		var dests: Array = []
		if trams.has(t):
			var td: Dictionary = trams[t]
			var right := Vector2(-(td.dir as Vector2).y, (td.dir as Vector2).x)
			dests.append({"name": "Tram stop: " + str(td.stop), "s": float(td.s) + right.x * 7.5, "x": float(td.x) + right.y * 7.5,
				"face": -right})
		for pt in FT_PLACES:
			var of: Array = us.filter(func(u): return str(u.type) == str(pt[0]))
			of.sort_custom(func(a, b): return _sx_dist(a.door, c) < _sx_dist(b.door, c))
			for k in mini(int(pt[2]), of.size()):
				dests.append(_door_dest(of[k], str(pt[1]) + ("" if k == 0 else " %d" % (k + 1))))
		var works: Array = us.filter(func(u): return FT_WORKS.has(str(u.type)))
		if not works.is_empty():
			works.sort_custom(func(a, b): return _sx_dist(a.door, c) > _sx_dist(b.door, c))
			dests.append(_door_dest(works[0], "Works District"))      # (the industry out at the town's edge)
		var seen := {}
		for a in areas:
			if str(a.get("town", "")) != t or not FT_AREAS.has(str(a.kind)) or seen.has(str(a.kind)):
				continue
			seen[str(a.kind)] = true
			var poly: Array = a.poly
			var m := Vector2.ZERO
			for q in poly:
				m += Vector2(StationGeo.wrap_ds(float(q[0]) - float(poly[0][0])), float(q[1]))
			m /= poly.size()
			dests.append({"name": str(FT_AREAS[str(a.kind)]), "s": fposmod(float(poly[0][0]) + m.x, StationGeo.CIRC), "x": m.y,
				"face": Vector2.ZERO})
		groups.append({"name": t, "centre": c, "pop": int(st.get("pop", us.size())), "dests": dests})
	groups.sort_custom(func(a, b): return int(a.pop) > int(b.pop))
	groups.append({"name": "Landmarks", "dests": _landmark_dests()})
	return groups


func _sx_dist(door: Array, c: Vector2) -> float:
	return Vector2(StationGeo.wrap_ds(float(door[0]) - c.x), float(door[1]) - c.y).length()


func _door_dest(u: Dictionary, label: String) -> Dictionary:
	## Outside a place: 4 m out from its door, away from its building, looking at it.
	var door := Vector2(float(u.door[0]), float(u.door[1]))
	var out := Vector2.ZERO
	var bi := Placement.index(str(u.get("building", "")))
	if bi >= 0:
		out = Vector2(StationGeo.wrap_ds(door.x - Placement.s(bi)), door.y - Placement.x(bi)).normalized()
	var at := door + out * 4.0
	return {"name": label, "s": fposmod(at.x, StationGeo.CIRC), "x": at.y, "face": -out}


func _landmark_dests() -> Array:
	var d := MapTerrain.data()
	var out: Array = []
	for m in d.get("summits", []):
		out.append({"name": "%s (%d m)" % [m.name, roundi(float(m.h))], "s": float(m.s), "x": float(m.x), "face": Vector2.ZERO})
	for f in d.get("falls", []):
		var lip := Vector2(float(f.lip[0]), float(f.lip[1]))
		var foot := Vector2(float(f.foot[0]), float(f.foot[1]))
		var away := Vector2(StationGeo.wrap_ds(foot.x - lip.x), foot.y - lip.y).normalized()
		var at := foot + away * 25.0                    # (down the run from its foot, looking up at it)
		out.append({"name": str(f.name), "s": fposmod(at.x, StationGeo.CIRC), "x": at.y, "face": -away})
	for i in d.get("islands", []):
		out.append({"name": str(i.name), "s": float(i.s), "x": float(i.x), "face": Vector2.ZERO, "land": true})
	for p in d.get("ponds", []):
		var a := float(p.a) + 8.0                       # (on its shore, looking across it)
		var dir := Vector2.from_angle(float(p.get("rot", 0.0)))
		out.append({"name": str(p.name), "s": fposmod(float(p.s) - dir.x * a, StationGeo.CIRC), "x": float(p.x) - dir.y * a, "face": dir})
	out.sort_custom(func(a, b): return str(a.name) < str(b.name))
	return out


func _fill_fast_travel(i: int) -> void:
	for c in _nav_list.get_children():
		c.queue_free()
	if i < 0 or i >= _ft_groups.size():
		return
	for dd in _ft_groups[i].dests:
		var b := _button(str(dd.name), _ft_confirm.bind(dd, str(_ft_groups[i].name)))
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		_nav_list.add_child(b)


func _ft_confirm(dd: Dictionary, where: String) -> void:
	var p := _player_sx()
	var km := Vector2(StationGeo.wrap_ds(float(dd.s) - p.x), float(dd.x) - p.y).length() / 1000.0
	var mins := int(round(4.0 + km * 3.2))
	var title := str(dd.name) if where == "Landmarks" else "%s, %s" % [dd.name, where]
	_show_message("Fast Travel", "Travel to %s?\nAbout %d minutes." % [title, mins],
		[["Travel", _fast_travel.bind(dd, mins, title)], ["Cancel", Callable()]])


func _fast_travel(dd: Dictionary, mins: int, title: String) -> void:
	## There, on foot (out of any vehicle first), on the ground -- on land, for an island -- facing the place; the clock
	## moves on by the trip.
	var pl := get_tree().get_first_node_in_group("player") as StationPlayer
	if pl == null:
		return
	if pl.is_seated() and pl._vehicle and pl._vehicle.has_method("leave_seat"):
		pl._vehicle.leave_seat()
	set_open(false)
	var s := float(dd.s)
	var x := float(dd.x)
	if MapTerrain.water_at(s, x).x > -9000.0:          # (in the water: the nearest dry ground round it)
		var found := false
		for r in [10.0, 25.0, 50.0, 100.0, 200.0, 400.0, 800.0]:
			for k in 16:
				var a := TAU * k / 16.0
				if MapTerrain.water_at(s + cos(a) * r, x + sin(a) * r).x < -9000.0:
					s += cos(a) * r
					x += sin(a) * r
					found = true
					break
			if found:
				break
	s = fposmod(s, StationGeo.CIRC)
	var face: Vector2 = dd.get("face", Vector2.ZERO)
	var yaw := atan2(-face.y, face.x) if face.length() > 0.1 else 0.0
	pl.carrier_velocity = Vector3.ZERO
	pl.sheltered = false
	pl.stand_up(StationGeo.point(s, x, MapTerrain.elevation(s, x) + 1.0), StationGeo.basis(s, yaw))
	var sky := get_tree().current_scene.get_node_or_null("DaySkySystem")
	if sky:
		sky.time_of_day = fposmod(float(sky.time_of_day) + mins / 1440.0, 1.0)
	_tell(title)


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
	_tell("%s: %s" % [dd.name, dd.stop])


# ------------------------------------------------------------------ Summon (the Edit menu)
## Call a vehicle to you from Edit > Summon <kind> > <vehicle>: it is set down a few metres in front of you, to the
## left, facing the way you look (an aerostat flies in and lands near you). Summon Tram... asks how many sections.
## Dismiss Current Vehicle sends away the one you're in (or beside, or summoned); summoning another dismisses the last
## (one at a time). Every type of the fleet (FleetBodies) is in a kind; any the kinds don't name go under Summon Other,
## so none is ever missing.
const HAND_BUILT := ["aerostat", "pod", "van", "bicycle"]
const SUMMON_KINDS := [
	["Summon Aerostat", ["aerostat", "personal_aerostat", "summoned_aerostat", "cargo_aerostat", "rescue_aerostat"]],
	["Summon Boat", ["rowboat_dinghy", "canoe_kayak", "fishing_skiff", "pedal_boat", "personal_watercraft", "rescue_board", "sailboat",
		"pontoon_boat", "cabin_cruiser", "lobster_boat", "coast_guard_boat", "workboat_tug", "trawler", "ferry", "barge", "travel_lift"]],
	["Summon Passenger Car", ["city_car", "minivan", "station_wagon", "sedan", "luxury_sedan", "company_car", "police_car", "taxi", "fire_chief_car",
		"unmarked_car", "crossover_suv", "full_size_suv", "police_suv", "sports_car", "convertible", "limousine", "hearse", "pickup_truck",
		"public_works_pickup", "tow_truck", "utility_bucket_truck", "brush_truck", "lifeguard_truck", "hi_rail_truck", "delivery_van",
		"parcel_van", "service_van", "paratransit_van", "ambulance", "hotel_shuttle", "food_truck", "ice_cream_truck", "mail_truck",
		"armored_truck"]],
	["Summon HGV", ["box_truck", "refrigerated_truck", "garbage_truck", "recycling_truck", "dump_truck", "fire_engine", "ladder_truck",
		"street_sweeper", "milk_tanker", "semi_truck", "yard_tug", "grain_truck", "cement_mixer", "mobile_crane", "motorhome", "transit_bus",
		"school_bus", "sightseeing_trolley", "tram_maintenance_car", "excavator"]],
	["tram", []],
	["Summon Farm Vehicle", ["utility_tractor", "row_crop_tractor", "backhoe_loader", "combine_harvester", "crop_sprayer", "grain_cart",
		"hay_wagon", "manure_spreader", "hay_baler", "planter_drill", "plough_disc", "farm_pickup_flatbed"]],
	["Summon Small Vehicle", ["bicycle", "golf_cart", "utility_cart", "hydroponics_harvest_cart", "utv", "parks_mower", "riding_mower", "atv",
		"go_kart", "bumper_car", "mobility_scooter", "power_wheelchair", "skid_steer", "forklift", "kiddie_train", "motorcycle",
		"scooter_moped", "child_bicycle", "cargo_bike", "adult_tricycle", "kick_scooter", "skateboard", "surrey_bike", "manual_wheelchair",
		"rollator", "baby_stroller", "child_wagon", "shopping_cart", "hand_truck", "pallet_jack", "wheelbarrow", "luggage_cart",
		"housekeeping_cart", "hospital_gurney", "food_cart"]],
	# (kinds the user's list didn't name, so no vehicle is left out)
	["Summon Train", ["passenger_train", "freight_locomotive", "boxcar", "covered_hopper", "tank_car", "flatcar", "reefer_car"]],
	["Summon Trailer", ["utility_trailer", "boat_trailer", "camper_trailer", "livestock_trailer", "semi_trailer_dry", "semi_trailer_reefer",
		"low_loader"]],
	["Summon Spacecraft", ["passenger_shuttle", "supply_freighter", "eva_sled", "cargo_mule", "spoke_elevator_car"]],
]
const VEHICLE_NAMES := {"aerostat": "Personal aerostat", "pod": "City car (pod)", "van": "Minivan"}
var _tram_n := TransitVehicle.MIN_SECTIONS


func _vname(vt: String) -> String:
	if VEHICLE_NAMES.has(vt):
		return VEHICLE_NAMES[vt]
	var words := vt.split("_")
	for i in words.size():
		if words[i] in ["suv", "atv", "utv", "eva", "pwc"]:
			words[i] = words[i].to_upper()
	var t := " ".join(words)
	return t.substr(0, 1).to_upper() + t.substr(1)


func _edit_items() -> Array:
	var reg := FleetBodies.types()
	var seen := {}
	var out: Array = []
	for kind in SUMMON_KINDS:
		if kind[0] == "tram":
			out.append(_item("Summon Tram...", _ask_tram))
			continue
		var ts: Array = []
		for t in kind[1]:
			seen[t] = true
			if HAND_BUILT.has(t) or reg.has(t):
				ts.append(t)
		out.append(_sub(kind[0], _vehicle_items(ts)))
	var rest: Array = []
	for t in reg:
		if not seen.has(t):
			rest.append(t)
	if not rest.is_empty():
		out.append(_sub("Summon Other", _vehicle_items(rest)))
	out.append(_sep())
	out.append(_item("Dismiss Current Vehicle", _dismiss_current))
	return out


func _current_vehicle() -> Node3D:
	## The vehicle you're in (at the controls, or standing aboard), else the nearest one beside you (within 10 m: a parked
	## car, a map aerostat, a traffic car stood at the kerb), else the one you summoned.
	var p := get_tree().get_first_node_in_group("player") as StationPlayer
	if p == null:
		return null
	if p.is_seated():
		return p._vehicle as Node3D
	# (every vehicle, not a shape query: in a town the query's results were all buildings and road before any car)
	var best: Node3D = null
	var bd := 10.0
	var sc := get_tree().current_scene
	var cands: Array = sc.find_children("*", "RemakeAirVehicle", true, false)
	var tr = sc.find_child("NpcTraffic", false, false)
	if tr != null:
		for id in tr.live:
			var e: Dictionary = tr.live[id]
			if e.sim == null:                           # (parked or a wreck; not one someone's driving)
				cands.append(e.node)
	for n in cands:
		if not is_instance_valid(n) or (n as Node3D).is_queued_for_deletion() or not (n as Node3D).is_visible_in_tree():
			continue
		var riders = n.get("_riders")
		if riders is Array and (riders as Array).has(p):
			return n as Node3D                          # (aboard it)
		var d := (n as Node3D).global_position.distance_to(p.global_position)
		if d < bd:
			bd = d
			best = n as Node3D
	if best:
		return best
	for v in get_tree().get_nodes_in_group("delivered_wagon") + get_tree().get_nodes_in_group("summoned_aerostat"):
		if not (v as Node).is_queued_for_deletion():
			return v as Node3D
	return null


func _dismiss_current() -> void:
	## Edit > Dismiss Current Vehicle (the user, 2026-10-09): gone, whichever it is -- you out of it first. A parked one
	## (the map's, or the traffic's) is gone for good: it isn't put back when you come by again.
	set_open(false)
	var v := _current_vehicle()
	if v == null:
		_tell("No vehicle to dismiss.")
		return
	var p := get_tree().get_first_node_in_group("player") as StationPlayer
	if v.get("pilot") != null and v.has_method("leave_seat"):
		v.leave_seat()
	var riders = v.get("_riders")
	if p and riders is Array and (riders as Array).has(p):
		var up := StationGeo.up(StationGeo.s_of(v.global_position))
		var side := v.global_transform.basis.x
		side = (side - up * side.dot(up)).normalized()
		var r := maxf(2.5, float(v.get("half_w")) + 1.5 if v.get("half_w") != null else 2.5)
		p.carrier_velocity = Vector3.ZERO
		p.sheltered = false
		p.stand_up(v.global_position + side * r + up * 1.0, p.global_transform.basis)
	var what := "vehicle"
	if v is NpcCarBody:
		var tr := v.get_parent()
		what = _vname(str(tr.live[(v as NpcCarBody).entry_id].v.type)).to_lower() if tr.live.has((v as NpcCarBody).entry_id) else what
		tr.forget((v as NpcCarBody).entry_id)
	else:
		if v.get("vtype") != null and str(v.get("vtype")) != "":
			what = _vname(str(v.get("vtype"))).to_lower()
		v.remove_from_group("delivered_wagon")
		v.remove_from_group("summoned_aerostat")
		v.remove_from_group("taken_vehicle")
		if not (v.get_parent() is VehicleStreamer and (v.get_parent() as VehicleStreamer).forget(v)):
			v.queue_free()
	_tell("Dismissed the %s." % what)


func _vehicle_items(ts: Array) -> Array:
	var names := ts.duplicate()
	names.sort_custom(func(x, y): return _vname(x) < _vname(y))
	var items: Array = []
	for t in names:
		items.append(_item(_vname(t), _summon_now.bind(t)))
	return items


func _tell(text: String) -> void:
	var hud := get_tree().root.get_node_or_null("Hud")
	if hud and hud.has_method("show_notification"):
		hud.show_notification(text)


func _dismiss(say: bool) -> void:
	## Send the summoned vehicle away (getting you out of it first, if you're aboard).
	var gone := false
	for v in get_tree().get_nodes_in_group("delivered_wagon") + get_tree().get_nodes_in_group("summoned_aerostat"):
		if (v as Node).is_queued_for_deletion():
			continue
		if v.get("pilot") != null and v.has_method("leave_seat"):
			v.leave_seat()
		v.remove_from_group("delivered_wagon")
		v.remove_from_group("summoned_aerostat")
		(v as Node).queue_free()
		gone = true
	if say:
		set_open(false)
		_tell("Dismissed." if gone else "Nothing to dismiss.")


func _drop_point(length: float, half: float) -> Array:
	## Where a vehicle is set down: ahead of you and to the left (its door by you), on the ground.
	## [position, basis], or [] with no player.
	var p := get_tree().get_first_node_in_group("player") as Node3D
	if p == null:
		return []
	var up := StationGeo.up(StationGeo.s_of(p.global_position))
	var cam := p.get_viewport().get_camera_3d()
	var fwd := -(cam.global_transform.basis.z if cam else p.global_transform.basis.z)
	fwd = (fwd - up * fwd.dot(up)).normalized()
	var at := p.global_position + fwd * (3.2 + length * 0.5) - fwd.cross(up) * (0.7 + half)
	return [_ground(at, up, p), Basis(fwd.cross(up), up, -fwd).orthonormalized()]


func _ground(at: Vector3, up: Vector3, p: Node3D) -> Vector3:
	var q := PhysicsRayQueryParameters3D.create(at + up * 4.0, at - up * 8.0, 1)
	if p is CollisionObject3D:
		q.exclude = [(p as CollisionObject3D).get_rid()]
	var hit := p.get_world_3d().direct_space_state.intersect_ray(q)
	return hit.position if not hit.is_empty() else at


func _water_drop(length: float) -> Array:
	## The nearest water deep enough for a hull this long, round the player (out to 400 m), the waterline there and the
	## player's heading: [position, basis] or [].
	var p := get_tree().get_first_node_in_group("player") as Node3D
	if p == null:
		return []
	var s0 := StationGeo.s_of(p.global_position)
	var x0 := p.global_position.x
	for r in [12.0, 25.0, 50.0, 80.0, 120.0, 180.0, 260.0, 400.0]:
		for k in 24:
			var a := TAU * k / 24.0
			var s: float = s0 + cos(a) * r
			var x: float = x0 + sin(a) * r
			var wa := MapTerrain.water_at(s, x)
			if wa.x > -9000.0 and wa.y > 0.8 + length * 0.03:
				return [StationGeo.point(s, x, wa.x), StationGeo.basis(s, 0.0)]
	return []


func _summon_now(vt: String) -> void:
	_dismiss(false)
	set_open(false)
	if vt == "aerostat":
		var r := RemakeSummonedAerostat.summon(get_tree())
		_tell(str(r.message))
		return
	var info := FleetBodies.of(vt)
	var drop := _drop_point(float(info.get("nose", 2.3)) - float(info.get("tail", -2.3)), float(info.get("half_w", 0.95)))
	if drop.is_empty():
		return
	var w: Node3D
	if vt == "pod":
		w = RemakePod.new()
	elif vt == "van":
		w = RemakeVan.new()
	elif vt == "bicycle":
		w = RemakeBicycle.new()
	elif bool(info.get("air", false)) or bool(info.get("boat", false)):   # (it flies or floats: RemakeFleetCraft)
		w = RemakeFleetCraft.new(vt)
		if bool(info.get("boat", false)):              # (a boat: set on the nearest water, if there's any near)
			var wet := _water_drop(float(info.get("nose", 3.0)) - float(info.get("tail", -3.0)))
			if not wet.is_empty():
				drop = wet
				info = info.duplicate()
				info["ground"] = 0.0
	elif bool(info.get("prop", false)):                    # (a cart, a chair, a boat: just its body, set down)
		w = Node3D.new()
		w.set_meta("vtype", vt)
		w.add_child(VehicleBody.make(VehicleBody.prepare(str(info.blueprint))))
	else:
		w = RemakeModularCar.new(vt)
	w.name = "DeliveredVehicle"
	w.add_to_group("delivered_wagon")
	get_tree().current_scene.add_child(w)
	var up: Vector3 = (drop[1] as Basis).y
	w.global_transform = Transform3D(drop[1], drop[0] + up * (0.15 - float(info.get("ground", 0.0))))
	_tell("Your %s." % _vname(vt).to_lower())


func _ask_tram() -> void:
	## How many sections: from two (a front and a rear) to the most a tram on the lines has.
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 4)
	var n := _label("", true, false)
	n.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	n.custom_minimum_size = Vector2(84, 0)
	var upd := func(): n.text = "%d sections" % _tram_n
	var less := _button("<", func():
		_tram_n = maxi(TransitVehicle.MIN_SECTIONS, _tram_n - 1)
		upd.call())
	less.custom_minimum_size = Vector2(24, 18)
	var more := _button(">", func():
		_tram_n = mini(TransitVehicle.MAX_SECTIONS, _tram_n + 1)
		upd.call())
	more.custom_minimum_size = Vector2(24, 18)
	row.add_child(less)
	row.add_child(n)
	row.add_child(more)
	upd.call()
	_show_message("Summon Tram", "How many sections?  From %d to %d." % [TransitVehicle.MIN_SECTIONS, TransitVehicle.MAX_SECTIONS],
		[["Summon", func(): _summon_tram(_tram_n)], ["Cancel", Callable()]], row)


func _summon_tram(n: int) -> void:
	## A Carrow tram of n sections (front, mids, rear) with their joints, standing beside you.
	_dismiss(false)
	set_open(false)
	var kinds: Array = ["front"]
	for i in n - 2:
		kinds.append("mid")
	kinds.append("rear")
	var length := TransitVehicle.JOINT_GAP * (n - 1)
	for k in kinds:
		length += TramSection.length_front(k) + TramSection.length_back(k)
	var drop := _drop_point(length, 1.3)
	if drop.is_empty():
		return
	var p := get_tree().get_first_node_in_group("player") as Node3D
	var up: Vector3 = (drop[1] as Basis).y
	var tram := Node3D.new()
	tram.name = "SummonedTram"
	tram.set_meta("vtype", "tram")
	tram.add_to_group("delivered_wagon")
	get_tree().current_scene.add_child(tram)
	tram.global_transform = Transform3D(drop[1], drop[0])
	var secs: Array = []
	var z := -length * 0.5                                 # (the front's nose; -z is forward)
	for k in kinds:
		var sec := TramSection.new()
		tram.add_child(sec)
		sec.setup(k, null)
		z += TramSection.length_front(k)
		sec.position = Vector3(0, 0, z)
		sec.global_position = _ground(sec.global_position, up, p)   # (each on the ground under it)
		sec.sync_bodies()
		z += TramSection.length_back(k) + TransitVehicle.JOINT_GAP
		secs.append(sec)
	for i in secs.size() - 1:
		var j := TramJoint.new()
		tram.add_child(j)
		j.setup(secs[i], secs[i + 1])
		j.update()
	_tell("Your tram: %d sections." % n)


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
			["Double-tap an icon on the desktop to open it, or choose it from the menu under the logo at the top left.", false],
			["The menu bar", true],
			["Tap a menu's name to open it, then tap an item.  An item with a triangle opens a submenu.  File starts a new game, Edit summons vehicles, System respawns you or exits the game.", false],
			["In an app", true],
			["Its View menu changes pages.  The box at the top left of its window closes it, as does File > Close.  Help explains it.", false],
			["With a controller", true],
			["The left stick moves the stylus; A taps, B goes back, LB and RB change pages, the right stick scrolls, Y opens the menu bar.  On a Steam Deck the screen also takes your finger.", false],
			["The scroll wheel", true],
			["Roll the wheel on the right of the case, or tap above or below its middle, to scroll a page or a long menu.", false],
			["Talking to people", true],
			["Open NPC AI and follow its three steps to give the station's people their voices.", false],
			["Getting a ride", true],
			["Choose Edit > Summon and a kind of vehicle: it is set down in front of you.  Summon Tram... asks how many sections.  Edit > Dismiss Current Vehicle sends away the one you're in or beside (or the one you summoned).  An aerostat flies in and lands near you; fly gently -- it takes damage from 15 km/h.", false],
			["Putting it away", true],
			["Press the Power key, or the Communicator key again.", false]]:
		c.add_child(_label(line[0], line[1]))
	var a := _tab_page(tabs, "About")
	var logo := TextureRect.new()
	logo.texture = load(PDA + "system_logo_32.png")
	logo.stretch_mode = TextureRect.STRETCH_KEEP_CENTERED
	a.add_child(logo)
	a.add_child(_label("NYNEX Communicator", true))
	a.add_child(_label("The System  version 2.0"))
	a.add_child(_label("240 x 320, 4-level display.  Backlight: automatic."))
	a.add_child(HSeparator.new())
	a.add_child(_label("Space Station Columbia", true))
	a.add_child(_label("Chicago FLF (public domain) and Pixel Operator (CC0) type."))
	return tabs
