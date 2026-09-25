extends CanvasLayer

## The game menu is the player's handheld: a NYNEX Communicator, a portrait mid-90s PDA (the Apple
## Newton MessagePad's and Palm Pilot's upright form) running "The System" -- an operating system in
## the manner of Windows CE 1.0 (1996): a desktop of icons, a taskbar with a Start button and a clock,
## a Start menu that doesn't cascade (CE 1.0's didn't), and full-screen apps whose title bar carries
## [?] [OK] [X].  The menu's options are the apps; their sub-menus are the apps' tabs:
##   Station Map (Station, Nearby) · Inventory (Weapons, Items) · Quests (Active, Completed)
##   Control Panel (Sound, Display, Controls) · Help (Contents, About)
##   Start menu: the apps, New Game..., Suspend (back to the game).
## The screen is a 240 x 320 dot-matrix STN LCD, 4 shades of black on green (ui/pda/lcd.gdshader),
## with the green electroluminescent backlight on at night.  The System draws in 4 greys into a
## SubViewport; the LCD shader turns them green.  Below the screen, four hardware buttons open the
## apps (as the Palm Pilot's did) and the power button puts the device away.

const SCREEN := Vector2i(240, 320)
const BODY := Vector2(288, 478)        # the device, in screen pixels
const SCREEN_AT := Vector2(24, 50)
const TASKBAR_H := 18
const TITLE_H := 15
const W := Color(1, 1, 1)
const L := Color(0.667, 0.667, 0.667)
const D := Color(0.333, 0.333, 0.333)
const K := Color(0, 0, 0)
const PDA := "res://ui/pda/"

var _is_open := false
var _theme: Theme
var _font: FontFile
var _bold: FontFile

var _dim: ColorRect
var _device: Control
var _screen_rect: TextureRect
var _vp: SubViewport
var _lcd: ShaderMaterial
var _desk: Control
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

const APPS := [
	["map", "Station Map", "icon_map.png"],
	["inventory", "Inventory", "icon_inventory.png"],
	["quests", "Quests", "icon_quests.png"],
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
	get_viewport().size_changed.connect(_layout)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("toggle_menu"):
		set_open(not _is_open)


func set_open(open: bool) -> void:
	_is_open = open
	_set_visible(open)
	get_tree().paused = open
	if open:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		_layout()
		_refresh_quests()
		_refresh_inventory()
		_refresh_map()
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


func _process(_delta: float) -> void:
	if not _is_open:
		return
	_update_clock()
	_update_backlight()
	if _current == "map":
		_map_station.queue_redraw()


# ------------------------------------------------------------------ look
func _pixel_font(path: String) -> FontFile:
	var f: FontFile = load(path)
	f = f.duplicate()
	f.antialiasing = TextServer.FONT_ANTIALIASING_NONE
	f.hinting = TextServer.HINTING_NORMAL
	f.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_DISABLED
	return f


func _box(file: String, margin := 2) -> StyleBoxTexture:
	var s := StyleBoxTexture.new()
	s.texture = load(PDA + file)
	for side in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
		s.set_texture_margin(side, margin)
		s.set_content_margin(side, margin + 2)
	return s


func _flat(c: Color, border := Color.TRANSPARENT, bw := 0) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = c
	s.border_color = border
	s.set_border_width_all(bw)
	s.set_content_margin_all(2)
	return s


func _build_theme() -> void:
	_font = _pixel_font(PDA + "DejaVuSans.ttf")
	_bold = _pixel_font(PDA + "DejaVuSans-Bold.ttf")
	_theme = Theme.new()
	_theme.default_font = _font
	_theme.default_font_size = 10
	for t in ["Label", "Button", "CheckBox", "TabContainer", "TabBar", "RichTextLabel"]:
		_theme.set_color("font_color", t, K)
	_theme.set_color("default_color", "RichTextLabel", K)
	_theme.set_color("font_hover_color", "Button", K)
	_theme.set_color("font_pressed_color", "Button", K)
	_theme.set_color("font_focus_color", "Button", K)
	_theme.set_color("font_disabled_color", "Button", D)
	_theme.set_color("font_selected_color", "TabContainer", K)
	_theme.set_color("font_unselected_color", "TabContainer", K)
	_theme.set_color("font_hovered_color", "TabContainer", K)
	_theme.set_stylebox("normal", "Button", _box("btn_up.png"))
	_theme.set_stylebox("hover", "Button", _box("btn_up.png"))
	_theme.set_stylebox("pressed", "Button", _box("btn_down.png"))
	_theme.set_stylebox("disabled", "Button", _box("btn_down.png"))
	_theme.set_stylebox("focus", "Button", StyleBoxEmpty.new())
	var tab_on := _box("tab_on.png")
	tab_on.set_content_margin(SIDE_TOP, 2)
	tab_on.set_content_margin(SIDE_BOTTOM, 3)
	var tab_off := _box("tab_off.png")
	tab_off.set_content_margin(SIDE_TOP, 1)
	tab_off.set_content_margin(SIDE_BOTTOM, 1)
	tab_off.expand_margin_top = -2
	_theme.set_stylebox("tab_selected", "TabContainer", tab_on)
	_theme.set_stylebox("tab_unselected", "TabContainer", tab_off)
	_theme.set_stylebox("tab_hovered", "TabContainer", tab_off)
	_theme.set_stylebox("panel", "TabContainer", _box("raised_panel.png"))
	_theme.set_constant("side_margin", "TabContainer", 2)
	_theme.set_stylebox("panel", "PanelContainer", _box("raised_panel.png"))
	_theme.set_stylebox("panel", "ScrollContainer", _box("sunken.png"))
	_theme.set_stylebox("scroll", "VScrollBar", _flat(L))
	_theme.set_stylebox("grabber", "VScrollBar", _box("btn_up.png"))
	_theme.set_stylebox("grabber_highlight", "VScrollBar", _box("btn_up.png"))
	_theme.set_stylebox("grabber_pressed", "VScrollBar", _box("btn_down.png"))
	_theme.set_stylebox("slider", "HSlider", _box("sunken.png", 1))
	_theme.set_stylebox("grabber_area", "HSlider", _flat(D))
	_theme.set_stylebox("grabber_area_highlight", "HSlider", _flat(D))
	var knob := Image.create(7, 11, false, Image.FORMAT_RGBA8)
	knob.fill(L)
	for y in 11:
		knob.set_pixel(0, y, W)
		knob.set_pixel(6, y, K)
	for x in 7:
		knob.set_pixel(x, 0, W)
		knob.set_pixel(x, 10, K)
	var kt := ImageTexture.create_from_image(knob)
	_theme.set_icon("grabber", "HSlider", kt)
	_theme.set_icon("grabber_highlight", "HSlider", kt)
	_theme.set_stylebox("separator", "HSeparator", _flat(D))


# ------------------------------------------------------------------ the device
class DeviceBody extends Control:
	## The NYNEX Communicator's case: charcoal plastic, the screen's bezel, the NYNEX wordmark and
	## "Communicator" script, a speaker grille, and the silk-screened labels of the buttons below.
	var bold: Font
	var font: Font

	func _draw() -> void:
		var r := Rect2(Vector2.ZERO, size)
		var body := StyleBoxFlat.new()
		body.bg_color = Color(0.16, 0.17, 0.18)
		body.set_corner_radius_all(26)
		body.border_color = Color(0.3, 0.31, 0.33)
		body.set_border_width_all(2)
		body.shadow_color = Color(0, 0, 0, 0.6)
		body.shadow_size = 12
		draw_style_box(body, r)
		# a slightly lighter face plate round the screen
		var face := StyleBoxFlat.new()
		face.bg_color = Color(0.2, 0.21, 0.22)
		face.set_corner_radius_all(18)
		draw_style_box(face, Rect2(Vector2(10, 10), size - Vector2(20, 20)))
		# the bezel
		var bezel := StyleBoxFlat.new()
		bezel.bg_color = Color(0.07, 0.075, 0.08)
		bezel.set_corner_radius_all(6)
		draw_style_box(bezel, Rect2(SCREEN_AT - Vector2(8, 8), Vector2(SCREEN) + Vector2(16, 16)))
		# wordmarks and the speaker
		draw_string(bold, Vector2(26, 34), "NYNEX", HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color(0.86, 0.87, 0.89))
		draw_string(font, Vector2(size.x - 26 - 90, 34), "Communicator", HORIZONTAL_ALIGNMENT_RIGHT, 90, 11, Color(0.62, 0.64, 0.67))
		for i in 5:
			draw_rect(Rect2(Vector2(size.x * 0.5 - 22 + i * 10, 20), Vector2(6, 2)), Color(0.06, 0.06, 0.07))
		# under the screen: the labels of the four app keys, and the power key's
		var y := SCREEN_AT.y + SCREEN.y + 22
		for i in 4:
			var cx := 44.0 + i * 66.0
			draw_string(font, Vector2(cx - 30, y + 34), ["MAP", "ITEMS", "QUESTS", "SETUP"][i], HORIZONTAL_ALIGNMENT_CENTER, 60, 8,
				Color(0.55, 0.57, 0.6))
		draw_string(font, Vector2(size.x * 0.5 - 30, size.y - 10), "POWER", HORIZONTAL_ALIGNMENT_CENTER, 60, 7, Color(0.45, 0.47, 0.5))


func _hw_button(label: String, at: Vector2, sz: Vector2, on_press: Callable, round := true) -> Button:
	var b := Button.new()
	b.text = label
	b.position = at
	b.size = sz
	b.focus_mode = Control.FOCUS_NONE
	var up := StyleBoxFlat.new()
	up.bg_color = Color(0.27, 0.28, 0.3)
	up.set_corner_radius_all(int(sz.y * 0.5) if round else 4)
	up.border_color = Color(0.4, 0.41, 0.44)
	up.set_border_width_all(1)
	up.shadow_color = Color(0, 0, 0, 0.5)
	up.shadow_size = 2
	var dn := up.duplicate()
	dn.bg_color = Color(0.2, 0.21, 0.22)
	dn.shadow_size = 0
	b.add_theme_stylebox_override("normal", up)
	b.add_theme_stylebox_override("hover", up)
	b.add_theme_stylebox_override("pressed", dn)
	b.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	b.add_theme_color_override("font_color", Color(0.75, 0.77, 0.8))
	b.add_theme_color_override("font_hover_color", Color(0.9, 0.9, 0.92))
	b.add_theme_font_override("font", _bold)
	b.add_theme_font_size_override("font_size", 9)
	b.pressed.connect(on_press)
	return b


func _build_device() -> void:
	_dim = ColorRect.new()
	_dim.color = Color(0, 0, 0, 0.55)
	_dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_dim)
	var body := DeviceBody.new()
	body.bold = _bold
	body.font = _font
	body.size = BODY
	body.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(body)
	_device = body
	# the screen: The System renders into a 240 x 320 viewport; the LCD shader draws it
	_vp = SubViewport.new()
	_vp.size = SCREEN
	_vp.transparent_bg = false
	_vp.handle_input_locally = true
	_vp.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	_vp.gui_embed_subwindows = true
	body.add_child(_vp)
	_screen_rect = TextureRect.new()
	_screen_rect.texture = _vp.get_texture()
	_screen_rect.position = SCREEN_AT
	_screen_rect.size = Vector2(SCREEN)
	_screen_rect.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_lcd = ShaderMaterial.new()
	_lcd.shader = load(PDA + "lcd.gdshader")
	_lcd.set_shader_parameter("screen_px", Vector2(SCREEN))
	_screen_rect.material = _lcd
	_screen_rect.mouse_filter = Control.MOUSE_FILTER_STOP
	_screen_rect.gui_input.connect(_screen_input)
	body.add_child(_screen_rect)
	# the hardware buttons: four app keys (as the Palm Pilot's) and the power key
	var y := SCREEN_AT.y + SCREEN.y + 22
	for i in 4:
		var app: String = ["map", "inventory", "quests", "control"][i]
		body.add_child(_hw_button("", Vector2(26 + i * 66, y), Vector2(36, 22), _open_app.bind(app)))
	body.add_child(_hw_button("", Vector2(BODY.x * 0.5 - 12, BODY.y - 32), Vector2(24, 10), func(): set_open(false), false))
	_layout()


func _screen_input(event: InputEvent) -> void:
	## Taps and drags on the glass go to The System (the screen rect is in LCD pixels already).
	if event is InputEventMouse:
		var ev: InputEventMouse = event.duplicate()
		ev.position = event.position
		ev.global_position = event.position
		_vp.push_input(ev, true)


func _layout() -> void:
	if _device == null:
		return
	var vs := get_viewport().get_visible_rect().size
	var k := minf(vs.y * 0.95 / BODY.y, vs.x * 0.9 / BODY.x)
	_device.scale = Vector2(k, k)
	_device.position = (vs - BODY * k) * 0.5


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
func _build_system() -> void:
	var root := Control.new()
	root.theme = _theme
	root.size = Vector2(SCREEN)
	_vp.add_child(root)
	# the desktop
	_desk = Control.new()
	_desk.size = Vector2(SCREEN.x, SCREEN.y - TASKBAR_H)
	var bg := ColorRect.new()
	bg.color = W
	bg.size = _desk.size
	bg.mouse_filter = Control.MOUSE_FILTER_PASS
	bg.gui_input.connect(func(e): if e is InputEventMouseButton and e.pressed: _start_menu.visible = false)
	_desk.add_child(bg)
	for i in APPS.size():
		_desk.add_child(_desk_icon(APPS[i], Vector2(8 + (i % 3) * 76, 8 + (i / 3) * 58)))
	root.add_child(_desk)
	# the apps
	_apps["map"] = _app("Station Map", _map_tabs(), "The station's map.  Station: the whole ring, north (the Marlowe end) up.  Nearby: the kilometre round you.")
	_apps["inventory"] = _app("Inventory", _inventory_tabs(), "What you carry.  Weapons: tap Equip to arm one.")
	_apps["quests"] = _app("Quests", _quest_tabs(), "Your tasks.  Tap Track to follow one on the map.")
	_apps["control"] = _app("Control Panel", _control_tabs(), "Sound, Display and Controls settings.")
	_apps["help"] = _app("Help", _help_tabs(), "The System Help.")
	for a in _apps.values():
		a.visible = false
		root.add_child(a)
	# the taskbar
	_taskbar = PanelContainer.new()
	_taskbar.position = Vector2(0, SCREEN.y - TASKBAR_H)
	_taskbar.size = Vector2(SCREEN.x, TASKBAR_H)
	_taskbar.add_theme_stylebox_override("panel", _box("raised_panel.png", 1))
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 2)
	_taskbar.add_child(row)
	var start := Button.new()
	start.text = "Start"
	start.icon = load(PDA + "start_logo.png")
	start.add_theme_font_override("font", _bold)
	start.add_theme_font_size_override("font_size", 9)
	start.add_theme_constant_override("h_separation", 2)
	start.custom_minimum_size = Vector2(46, 14)
	start.pressed.connect(func(): _start_menu.visible = not _start_menu.visible)
	row.add_child(start)
	_task_btn = Button.new()
	_task_btn.add_theme_font_size_override("font_size", 9)
	_task_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_task_btn.clip_text = true
	_task_btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
	_task_btn.visible = false
	_task_btn.pressed.connect(func(): if _current != "": _apps[_current].visible = not _apps[_current].visible)
	row.add_child(_task_btn)
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(spacer)
	var tray := PanelContainer.new()
	tray.add_theme_stylebox_override("panel", _box("sunken.png", 1))
	_clock = Label.new()
	_clock.add_theme_font_size_override("font_size", 9)
	_clock.custom_minimum_size = Vector2(44, 0)
	_clock.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tray.add_child(_clock)
	row.add_child(tray)
	root.add_child(_taskbar)
	_start_menu = _build_start_menu()
	root.add_child(_start_menu)
	_msgbox = Control.new()
	_msgbox.size = Vector2(SCREEN)
	_msgbox.visible = false
	root.add_child(_msgbox)


func _desk_icon(app: Array, at: Vector2) -> Control:
	var b := Button.new()
	b.flat = true
	b.position = at
	b.size = Vector2(70, 52)
	b.icon = load(PDA + app[2])
	b.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
	b.vertical_icon_alignment = VERTICAL_ALIGNMENT_TOP
	b.text = app[1]
	b.add_theme_font_size_override("font_size", 9)
	b.add_theme_stylebox_override("normal", StyleBoxEmpty.new())
	b.add_theme_stylebox_override("hover", StyleBoxEmpty.new())
	b.add_theme_stylebox_override("pressed", _flat(D))
	b.add_theme_stylebox_override("focus", _flat(Color.TRANSPARENT, K, 1))
	b.add_theme_color_override("font_pressed_color", W)
	# CE opens a desktop icon on a double tap; one tap selects it
	b.pressed.connect(func():
		var now := Time.get_ticks_msec()
		if now - int(_last_click.get(app[0], -10000)) < 600:
			_open_app(app[0])
			_last_click[app[0]] = -10000
		else:
			_last_click[app[0]] = now
			b.grab_focus())
	return b


func _build_start_menu() -> Control:
	## CE 1.0's Start menu: one flat list (no cascading submenus), the OS name down its left edge.
	var m := PanelContainer.new()
	m.visible = false
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 0)
	m.add_child(row)
	var banner := ColorRect.new()
	banner.color = D
	banner.custom_minimum_size = Vector2(16, 0)
	var bl := Label.new()
	bl.text = "The System"
	bl.add_theme_font_override("font", _bold)
	bl.add_theme_font_size_override("font_size", 10)
	bl.add_theme_color_override("font_color", W)
	bl.rotation = -PI * 0.5
	bl.position = Vector2(2, 150)
	banner.add_child(bl)
	row.add_child(banner)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 0)
	row.add_child(col)
	var entries := []
	for a in APPS:
		entries.append([a[1], a[2], _open_app.bind(a[0])])
	entries.append([])
	entries.append(["New Game...", "", _confirm_new_game])
	entries.append(["Suspend", "", func(): set_open(false)])
	for e in entries:
		if e.is_empty():
			col.add_child(HSeparator.new())
			continue
		var b := Button.new()
		b.text = e[0]
		if e[1] != "":
			var img: Image = (load(PDA + e[1]) as Texture2D).get_image()
			img.resize(16, 16, Image.INTERPOLATE_NEAREST)
			b.icon = ImageTexture.create_from_image(img)
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.custom_minimum_size = Vector2(118, 18)
		b.add_theme_stylebox_override("normal", StyleBoxEmpty.new())
		b.add_theme_stylebox_override("hover", _flat(K))
		b.add_theme_stylebox_override("pressed", _flat(K))
		b.add_theme_color_override("font_hover_color", W)
		b.add_theme_color_override("font_pressed_color", W)
		b.pressed.connect(func():
			_start_menu.visible = false
			e[2].call())
		col.add_child(b)
	m.reset_size()
	m.position = Vector2(0, SCREEN.y - TASKBAR_H - m.size.y)
	m.resized.connect(func(): m.position = Vector2(0, SCREEN.y - TASKBAR_H - m.size.y))
	return m


func _app(title: String, tabs: TabContainer, help: String) -> Control:
	## A full-screen app (CE 1.0's apps weren't overlapping windows): a title bar with [?] [OK] [X],
	## then its tabs.
	var w := Control.new()
	w.size = Vector2(SCREEN.x, SCREEN.y - TASKBAR_H)
	var bg := ColorRect.new()
	bg.color = W
	bg.size = w.size
	w.add_child(bg)
	var bar := ColorRect.new()
	bar.color = K
	bar.size = Vector2(SCREEN.x, TITLE_H)
	w.add_child(bar)
	var t := Label.new()
	t.text = title
	t.position = Vector2(3, 0)
	t.add_theme_font_override("font", _bold)
	t.add_theme_font_size_override("font_size", 10)
	t.add_theme_color_override("font_color", W)
	bar.add_child(t)
	var bx := SCREEN.x - 1
	for spec in [["X", 14, _close_app], ["OK", 20, _close_app], ["?", 14, _show_message.bind(title, help)]]:
		var b := Button.new()
		b.text = spec[0]
		b.add_theme_font_override("font", _bold)
		b.add_theme_font_size_override("font_size", 8)
		b.add_theme_stylebox_override("normal", _box("btn_up.png", 1))
		b.add_theme_stylebox_override("hover", _box("btn_up.png", 1))
		b.add_theme_stylebox_override("pressed", _box("btn_down.png", 1))
		for st in ["normal", "hover", "pressed"]:
			var sb: StyleBoxTexture = b.get_theme_stylebox(st)
			sb.set_content_margin_all(1)
		var bw := maxf(spec[1], b.get_combined_minimum_size().x)
		bx -= bw + 1
		b.position = Vector2(bx, 1)
		b.size = Vector2(bw, TITLE_H - 2)
		b.pressed.connect(spec[2])
		bar.add_child(b)
	tabs.position = Vector2(2, TITLE_H + 2)
	tabs.size = Vector2(SCREEN.x - 4, SCREEN.y - TASKBAR_H - TITLE_H - 4)
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


func _close_app() -> void:
	if _current != "":
		_apps[_current].visible = false
	_current = ""
	_task_btn.visible = false


func _show_message(title: String, text: String, buttons := [["OK", Callable()]]) -> void:
	## A CE message box: a small raised window in the middle of the screen.
	for c in _msgbox.get_children():
		c.queue_free()
	var shade := ColorRect.new()
	shade.color = Color(0, 0, 0, 0.0)
	shade.size = Vector2(SCREEN)
	_msgbox.add_child(shade)
	var p := PanelContainer.new()
	p.position = Vector2(20, 100)
	p.custom_minimum_size = Vector2(200, 0)
	var v := VBoxContainer.new()
	p.add_child(v)
	var bar := Label.new()
	bar.text = " " + title
	bar.add_theme_font_override("font", _bold)
	bar.add_theme_color_override("font_color", W)
	var barbg := _flat(K)
	bar.add_theme_stylebox_override("normal", barbg)
	v.add_child(bar)
	var msg := Label.new()
	msg.text = text
	msg.autowrap_mode = TextServer.AUTOWRAP_WORD
	msg.custom_minimum_size = Vector2(190, 0)
	v.add_child(msg)
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_child(row)
	for spec in buttons:
		var b := Button.new()
		b.text = spec[0]
		b.custom_minimum_size = Vector2(50, 16)
		b.pressed.connect(func():
			_msgbox.visible = false
			if spec[1].is_valid():
				spec[1].call())
		row.add_child(b)
	_msgbox.add_child(p)
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
	if wrap:
		l.autowrap_mode = TextServer.AUTOWRAP_WORD
		l.custom_minimum_size = Vector2(200, 0)
	return l


# ------------------------------------------------------------------ Station Map
func _map_tabs() -> TabContainer:
	var tabs := TabContainer.new()
	var st := _tab_page(tabs, "Station", false)
	_map_station = Control.new()
	_map_station.custom_minimum_size = Vector2(228, 114)
	_map_station.draw.connect(_draw_station_map)
	st.add_child(_map_station)
	_map_here = _label("")
	st.add_child(_map_here)
	var nb := _tab_page(tabs, "Nearby", false)
	_map_nearby = TextureRect.new()
	_map_nearby.custom_minimum_size = Vector2(228, 250)
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
	_map_here.text = "You are %.1f km round the ring, %.1f km %s of the middle.\nNearest town: %s (%.1f km)." % [
		p.x / 1000.0, absf(p.y) / 1000.0, dirs, near, nd / 1000.0]
	if _map_tex:
		# Nearby: a 0.9 km x 1 km window of the map round the player, north up
		var ppm: float = _map_tex.get_width() / StationGeo.FARSIDE_W
		var wm := 912.0                                     # 1 LCD pixel = one 4 m map pixel
		var hm := wm * 250.0 / 228.0
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
		var h := sz.x * StationGeo.FARSIDE_H / StationGeo.FARSIDE_W
		_map_station.draw_texture_rect(_map_overview, Rect2(0, 0, sz.x, h), false)
		_map_station.draw_rect(Rect2(0, 0, sz.x, h), K, false)
		var p := _player_sx()
		var u := Vector2(fposmod(p.x, StationGeo.CIRC) / StationGeo.FARSIDE_W * sz.x,
			(p.y + StationGeo.FARSIDE_H * 0.5) / StationGeo.FARSIDE_H * h)
		var blink := int(Time.get_ticks_msec() / 400) % 2 == 0
		_map_station.draw_rect(Rect2(u - Vector2(3, 3), Vector2(7, 7)), K if blink else W)
		_map_station.draw_string(_font, Vector2(2, h + 11), "N (Marlowe) up   E ->", HORIZONTAL_ALIGNMENT_LEFT, -1, 9, K)


func _draw_nearby_marker() -> void:
	var c := _map_nearby.size * 0.5
	var p := _player_sx()
	var d := Vector2(cos(p.z), sin(p.z))
	var side := Vector2(-d.y, d.x)
	_map_nearby.draw_colored_polygon(PackedVector2Array([c + d * 8, c - d * 5 + side * 5, c - d * 2, c - d * 5 - side * 5]), K)
	_map_nearby.draw_rect(Rect2(Vector2.ZERO, _map_nearby.size), K, false)
	_map_nearby.draw_string(_font, Vector2(3, 10), "N", HORIZONTAL_ALIGNMENT_LEFT, -1, 10, K)


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
		"jump": "Jump", "shoot": "Attack / Fire", "next_weapon": "Next weapon", "prev_weapon": "Previous weapon",
		"interact": "Use / Talk", "toggle_menu": "Communicator"}
	for action in names:
		var row := HBoxContainer.new()
		var a := _label(names[action], false, false)
		a.custom_minimum_size = Vector2(110, 0)
		row.add_child(a)
		row.add_child(_label(_format_binding(action), true, false))
		ctl.add_child(row)
	return tabs


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
			["Double-tap an icon on the desktop to open it, or tap Start and choose it.  The keys under the screen open the Map, Items, Quests and Setup.", false],
			["In an app", true],
			["The tabs along the top change pages.  OK or X closes the app; ? explains it.", false],
			["Putting it away", true],
			["Choose Suspend from the Start menu, press the Power key, or press the Communicator key again.", false]]:
		c.add_child(_label(line[0], line[1]))
	var a := _tab_page(tabs, "About")
	a.add_child(_label("NYNEX Communicator", true))
	a.add_child(_label("The System  version 1.0"))
	a.add_child(_label("240 x 320, 4-level display.  Backlight: automatic."))
	a.add_child(HSeparator.new())
	a.add_child(_label("Space Station Columbia", true))
	return tabs
