extends RemakeGroundVehicle
class_name RemakeModularCar

## A road vehicle with a modular body (research/vehicles/FLEET_BODIES.md): its type's blueprint (FleetBodies) assembled
## in the game from the component library -- VehicleBody: the tube frame and its panels, inside and out -- on its
## board, whose pods hold the wheels and motors. Local frame: x right, y up (0 = where the tyres touch), -z the nose.
##
## Its closers are the blueprint's: hinged ("door", "hatch", "lid": a hinge point, an axis, a travel) or sliding
## ("slide": out from the side, then along it or up -- sliding doors, roll-up shutters), each eased open and shut
## with its own use zone and its own collision. Its lamps are the blueprint's light markers: projector headlamps (a
## cut-off that steps up on the kerb side: we drive on the right), tail, brake and reverse lamps, a cabin light, and
## a working vehicle's light bar or beacon. A crash bends its frame: the skin dents with it, and the panels strained
## past their fastenings' tolerance come off.


var vtype := ""
var info := {}                         # the registry's entry (FleetBodies)
var body: VehicleBody
var closers := {}                      # id -> {pivot, axis, deg, slide, t, open, kind, leaf (AnimatableBody3D)}
var _fc := FleetClosers.new()          # (the closers' workings, shared with the aerostats)
var lamps := {}                        # group -> [Light3D]
var nose := -2.3
var tail := 2.3
var floor_y := 0.55
var roof_y := 2.0
var half_w := 0.92
var _brake_t := 0.0
var _speed_prev := 0.0
var _flash := 0.0
var _clock: Node
static var _cutoff: ImageTexture
static var _boards := {}


func _init(t := "") -> void:
	if t != "":
		setup_type(t)


func setup_type(t: String) -> void:
	vtype = t
	info = FleetBodies.of(t)
	spec = str(info.get("phys", t))
	nose = -float(info.get("nose", 2.3))
	tail = -float(info.get("tail", -2.3))
	floor_y = float(info.get("floor", 0.55))
	roof_y = float(info.get("height", 2.0))
	half_w = float(info.get("half_w", 0.92))
	max_speed = 130.0 / 3.6
	reverse_speed = 5.0
	max_steer = 0.6
	var b := _board(str(info.get("board", "carrow_k28")))
	if not b.is_empty():
		wheel_r = float(b.wheel_r)
		track = float(b.track_m)
		wheelbase = float(b.wheelbase_m)
	cabin_box = AABB(Vector3(-half_w, floor_y, nose), Vector3(half_w * 2.0, roof_y - floor_y, tail - nose))
	var sx := -1.0 if str(info.get("driver", "L")) == "L" else 1.0
	stand_point = Vector3(sx * (half_w + 0.45), 0.05, nose * 0.25)
	seat_forward = 0.0
	hull_size = Vector3(half_w * 2.0, roof_y - CLEAR, tail - nose)


func _load_spec() -> void:
	## The type's mass, motor and drag (npc_vehicles.json) -- but the wheels are the board's: ride on their real radius,
	## or the tyres sink into the road (or float over it).
	super()
	var b := _board(str(info.get("board", "none")))
	if not b.is_empty():
		phys["wheel_r"] = float(b.wheel_r)


static func _board(id: String) -> Dictionary:
	if _boards.is_empty():
		var d = JSON.parse_string(FileAccess.get_file_as_string("res://remake/vehicles/chassis/platforms.json"))
		for b in d.boards:
			_boards[str(b.id)] = b
	return _boards.get(id, {})


func _build_hull() -> void:
	if str(info.get("board", "none")) == "none":
		model = Node3D.new()
	else:
		model = (load(FleetBodies.board_path(str(info.board))) as PackedScene).instantiate()
		FleetBodies.strip_board(model)
	model.name = "Model"
	add_child(model)
	body = VehicleBody.make(VehicleBody.prepare(str(info.blueprint)))
	add_child(body)                                     # (beside the model: the base rig's door_* search stays off it)
	for pair in [["seat_driver", "seat_pilot"], ["steering", "steering_wheel"]]:
		var mk := body.get_node_or_null(str(pair[0])) as Node3D
		if mk:
			var n := Node3D.new()
			n.name = str(pair[1])
			n.position = mk.position
			model.add_child(n)
	var bp: Dictionary = body.plan.bp
	var std: Dictionary = body.plan.std
	# the walls people walk round (they pass through the swept hull): the floor, the roof over the cabin, the front
	# to the cowl, the tail, and the sides between the door apertures; the closed doors are their own bodies
	var toe := -float(std.get("toe", -nose))
	var cab_tail := -float(std.get("tail", -tail))
	var belt := float(std.get("belt", 1.2))
	add_box(Vector3(half_w * 2.0, 0.1, tail - nose), Vector3(0, floor_y - 0.05, (nose + tail) * 0.5))
	add_box(Vector3(half_w * 2.0, 0.1, cab_tail - toe), Vector3(0, float(std.get("crown", roof_y)) - 0.05, (toe + cab_tail) * 0.5))
	add_box(Vector3(half_w * 2.0, belt - 0.3, toe - nose), Vector3(0, (belt + 0.3) * 0.5, (nose + toe) * 0.5))
	add_box(Vector3(half_w * 2.0, belt - 0.3, 0.1), Vector3(0, (belt + 0.3) * 0.5, cab_tail - 0.05))
	if tail > cab_tail + 0.2:                           # a cargo module: solid to people (its doors aside)
		add_box(Vector3(half_w * 2.0, roof_y - 0.6, tail - cab_tail), Vector3(0, (roof_y + 0.6) * 0.5, (cab_tail + tail) * 0.5))
	for sd in ["R", "L"]:
		var gaps: Array = []
		for d in bp.doors:
			if str(d.side) == sd and float(d.z) < cab_tail:
				gaps.append([float(d.z) - float(d.width) * 0.5, float(d.z) + float(d.width) * 0.5])
		gaps.sort_custom(func(a, b): return a[0] < b[0])
		var z := toe
		var sx := 1.0 if sd == "R" else -1.0
		for g in gaps + [[cab_tail, cab_tail]]:
			if g[0] > z + 0.02:
				add_box(Vector3(0.08, float(std.get("crown", roof_y)) - floor_y, g[0] - z),
					Vector3(sx * (half_w - 0.04), (float(std.get("crown", roof_y)) + floor_y) * 0.5, (z + g[0]) * 0.5))
			z = maxf(z, g[1])
	_build_closers(bp)


func _build_closers(bp: Dictionary) -> void:
	_fc.build(self, body, bp)
	closers = _fc.closers


func _closer_prompt(id: String) -> String:
	return _fc.prompt(id)


func _use_closer(id: String) -> String:
	return _fc.use(id)


func open_closer(id: String, on: bool) -> void:
	_fc.open(id, on)


func _animate_closers(delta: float) -> void:
	_fc.animate(delta)


func _excluded() -> Array[RID]:
	var ex := super()
	ex.append_array(_fc.rids())
	return ex


# ------------------------------------------------------------------ the driver
func _driver_door() -> String:
	return "F" + str(info.get("driver", "L"))


func take_seat(p: StationPlayer) -> void:
	super(p)
	if pilot:
		open_closer(_driver_door(), false)


func leave_seat() -> void:
	if pilot:
		open_closer(_driver_door(), true)
	super()


# ------------------------------------------------------------------ lamps
func _rig() -> void:
	super()
	_lights()


static func cutoff() -> ImageTexture:
	## The low beam's projector mask (we drive on the right): dark above a flat cut on the left (the oncoming
	## side), the cut stepping up 15 degrees on the right (the kerb side); a hot spot just below and right of
	## the middle.
	if _cutoff:
		return _cutoff
	var n := 128
	var img := Image.create(n, n, false, Image.FORMAT_L8)
	for py in n:
		for px in n:
			var x := (px - n * 0.5) / (n * 0.5)
			var y := (n * 0.5 - py) / (n * 0.5)
			var cut := -0.04 + (maxf(0.0, x) * tan(deg_to_rad(15.0)) if x > 0.0 else 0.0)
			var v := 0.0
			if y < cut:
				var r := Vector2(x - 0.12, (y + 0.12) * 1.8).length()
				v = clampf(0.35 + 0.65 * exp(-r * r * 6.0), 0.0, 1.0) * smoothstep(0.0, 0.03, cut - y)
				v *= clampf(1.0 - Vector2(x, y).length() * 0.6, 0.0, 1.0)
			img.set_pixel(px, py, Color(v, v, v))
	_cutoff = ImageTexture.create_from_image(img)
	return _cutoff


func _lights() -> void:
	for mk in body.get_children():
		var n := str(mk.name)
		if not n.begins_with("light_"):
			continue
		var l: Light3D
		var group := ""
		if n.begins_with("light_head"):
			var sp := SpotLight3D.new()
			sp.spot_range = 45.0
			sp.spot_angle = 28.0
			sp.spot_attenuation = 0.6
			sp.light_color = Color(1.0, 0.96, 0.88)
			sp.light_projector = cutoff()
			sp.rotation.x = deg_to_rad(-1.5)
			l = sp
			group = "head"
		elif n.begins_with("light_tail") or n == "light_brake_high":
			var om := OmniLight3D.new()
			om.omni_range = 3.0
			om.light_color = Color(1.0, 0.12, 0.08)
			l = om
			group = "tail"
		elif n.begins_with("light_reverse"):
			var rv := SpotLight3D.new()
			rv.spot_range = 8.0
			rv.spot_angle = 50.0
			l = rv
			group = "reverse"
		elif n == "light_cabin" or n == "light_frunk":
			var om2 := OmniLight3D.new()
			om2.omni_range = 2.2 if n == "light_cabin" else 1.2
			om2.light_color = Color(1.0, 0.92, 0.78)
			l = om2
			group = "cabin" if n == "light_cabin" else "frunk"
		elif n == "light_bar" or n == "light_beacon":
			var om3 := OmniLight3D.new()
			om3.omni_range = 9.0
			om3.light_color = Color(1.0, 0.55, 0.1) if n == "light_beacon" else Color(1.0, 0.1, 0.1)
			l = om3
			group = "warning"
		else:
			continue
		l.shadow_enabled = false
		l.visible = false
		(mk as Node3D).add_child(l)
		if not lamps.has(group):
			lamps[group] = []
		lamps[group].append(l)


func _night() -> float:
	if _clock == null:
		_clock = get_tree().current_scene.get_node_or_null("DaySkySystem")
	var h := (float(_clock.time_of_day) if _clock else 0.4) * 24.0
	if h < 5.0 or h > 20.5:
		return 1.0
	if h < 7.0:
		return 1.0 - (h - 5.0) / 2.0
	if h > 18.5:
		return (h - 18.5) / 2.0
	return 0.0


func _set_lights(delta: float) -> void:
	var live := pilot != null or not drive_input.is_empty()
	var night := _night() if live else 0.0
	var dark := night > 0.05
	var decel := (absf(_speed_prev) - absf(_speed)) / maxf(delta, 1e-3)
	_speed_prev = _speed
	if live and decel > 2.0 and absf(_speed) > 0.3:
		_brake_t = 0.4
	_brake_t = maxf(0.0, _brake_t - delta)
	var braking := _brake_t > 0.0
	var reversing := live and _speed < -0.3
	for l in lamps.get("head", []):
		(l as Light3D).visible = dark
		(l as Light3D).light_energy = lerpf(0.6, 4.0, night)
		(l as Light3D).shadow_enabled = pilot != null
	for l in lamps.get("tail", []):
		(l as Light3D).visible = dark or braking
		(l as Light3D).light_energy = (2.0 if braking else 0.6) * maxf(night, 0.5)
	for l in lamps.get("reverse", []):
		(l as Light3D).visible = reversing
	var any_door := false
	for id in closers:
		if str(closers[id].kind) in ["door", "slide", "roll"] and float(closers[id].t) > 0.0:
			any_door = true
	for l in lamps.get("cabin", []):
		(l as Light3D).visible = any_door and night > 0.3
	var lid_open: bool = closers.has("frunk") and float(closers.frunk.t) > 0.0
	for l in lamps.get("frunk", []):
		(l as Light3D).visible = lid_open
	# a working vehicle's warning lamps: flashing while it's in use
	_flash = fmod(_flash + delta, 0.5)
	var on := live and _flash < 0.25
	for l in lamps.get("warning", []):
		(l as Light3D).visible = on
	var lm := body.lamp_mats
	for m in lm.get("lamp_head", []):
		(m as BaseMaterial3D).emission_energy_multiplier = lerpf(0.3, 3.5, night) if live else 0.0
	for m in lm.get("lamp_drl", []):
		(m as BaseMaterial3D).emission_energy_multiplier = 1.2 if live else 0.0
	for m in lm.get("lamp_tail", []):
		(m as BaseMaterial3D).emission_energy_multiplier = (1.6 if dark else 0.0) + (3.0 if braking else 0.0)
	for m in lm.get("lamp_brake", []):
		(m as BaseMaterial3D).emission_energy_multiplier = 4.0 if braking else 0.0
	for m in lm.get("lamp_reverse", []):
		(m as BaseMaterial3D).emission_energy_multiplier = 3.0 if reversing else 0.0
	for k in ["lamp_red", "lamp_blue"]:
		for m in lm.get(k, []):
			(m as BaseMaterial3D).emission_energy_multiplier = 5.0 if (on if k == "lamp_red" else (live and not on)) else 0.0
	for m in lm.get("lamp_amber", []):
		(m as BaseMaterial3D).emission_energy_multiplier = 3.0 if (on and lamps.has("warning")) else 0.0


# ------------------------------------------------------------------ the tick
func _physics_process(delta: float) -> void:
	_animate_closers(delta)
	super(delta)
	if not sleeping:
		_set_lights(delta)


# ------------------------------------------------------------------ crashes
const BEND_KMH := 8.0                  # below this a knock only rocks it
var _last_bend := -100000             # ms: one blow per collision (it reports on the next ticks too)


func _hit(dv: Vector3) -> void:
	super(dv)
	var kmh := dv.length() * 3.6
	var now := Time.get_ticks_msec()
	if kmh < BEND_KMH or now - _last_bend < 500:
		return
	_last_bend = now
	var dir := global_transform.basis.inverse() * dv.normalized()           # (local: the way the blow pushes the body in)
	var hb := AABB(Vector3(-half_w, CLEAR, nose), Vector3(half_w * 2.0, roof_y - CLEAR, tail - nose))
	var at := hb.get_center() - dir * 3.0
	at = Vector3(clampf(at.x, hb.position.x, hb.end.x), clampf(1.0, hb.position.y, hb.end.y), clampf(at.z, hb.position.z, hb.end.z))
	bend(at, dir, 0.5 * mass * dv.length_squared() * 0.5)        # (J: half the energy goes into the frame)


func bend(at: Vector3, dir: Vector3, energy: float) -> void:
	## A blow to the frame (local point and direction): it dents, the skin with it; parts strained past their
	## tolerance come off.
	for mid in body.impact(at, dir, energy):
		var m: Dictionary = body.plan.modules.get(mid, {})
		body.break_off(mid, "shatter" if str(m.get("breaks", "")) == "shatter" else str(m.get("breaks", "detach")), linear_velocity)
