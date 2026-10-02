extends RemakeGroundVehicle
class_name RemakeWagon

## The Carrow station wagon (research/vehicles/wagon/WAGON.md): an SW180 body assembled in the game from the
## component library (VehicleBody: the tube frame and its panels, inside and out) on a Carrow Keel K-28 board,
## whose pods hold the wheels and motors. Local frame: x right, y up (0 = where the tyres touch), -z the nose.
##
## Its closers swing on their hinges (the blueprint's "closers": hinge point, axis, travel): four doors, the
## tailgate and the frunk lid, each eased open and shut, each with its own use zone. Its lamps are the
## blueprint's light markers: projector headlamps (a cut-off that steps up on the kerb side: we drive on the
## right), tail, brake and reverse lamps, a cabin light. A crash bends its frame: the skin dents with it, and
## the panels strained past their fastenings' tolerance come off (as the tram's do).

const BLUEPRINT := "res://remake/vehicles/wagon/carrow_wagon.blueprint.json"
const BOARD := "res://remake/vehicles/chassis/carrow_k28.glb"
const FLOOR := 0.55
const ROOF := 2.06
const HALF_W := 0.93
const NOSE := -2.28
const TAIL := 2.36
const DOOR_UP := 0.55                  # s: a door's swing (by hand); the tailgate and lid run slower
const LID_UP := 0.9
const LID_DOWN := 0.7

var body: VehicleBody
var closers := {}                      # id -> {pivot, axis, deg, t, open, kind, leaf (AnimatableBody3D)}
var lamps := {}                        # group -> [Light3D]
var _brake_t := 0.0
var _speed_prev := 0.0
var _clock: Node
static var _cutoff: ImageTexture


func _init() -> void:
	spec = "station_wagon"
	max_speed = 130.0 / 3.6
	reverse_speed = 5.0
	wheelbase = 2.8
	track = 1.56
	wheel_r = 0.32
	max_steer = 0.6
	cabin_box = AABB(Vector3(-0.85, FLOOR, -1.15), Vector3(1.7, 1.45, 3.45))
	stand_point = Vector3(-1.4, 0.05, -0.31)              # the driver gets out on the left (we drive on the right)
	seat_forward = 0.0
	hull_size = Vector3(HALF_W * 2.0, ROOF - CLEAR, TAIL - NOSE)


func _build_hull() -> void:
	# the board: only its pods, wheels and motors show (through the arches); the deck is under the floor
	model = (load(BOARD) as PackedScene).instantiate()
	model.name = "Model"
	add_child(model)
	for n in model.find_children("*", "Node3D", true, false):
		var nm := str(n.name)
		if nm.begins_with("mount_") or nm.begins_with("rib_") or nm.begins_with("bulkhead_") or nm.begins_with("keel") \
				or nm == "gunwale" or nm == "controller":
			n.queue_free()
	body = VehicleBody.make(VehicleBody.prepare(BLUEPRINT))
	add_child(body)                                     # (beside the model: the base rig's door_* search stays off it)
	# the rig points the base classes look for: the driver's seat and the steering wheel
	for pair in [["seat_driver", "seat_pilot"], ["steering", "steering_wheel"]]:
		var mk := body.get_node_or_null(str(pair[0])) as Node3D
		if mk:
			var n := Node3D.new()
			n.name = str(pair[1])
			n.position = mk.position
			model.add_child(n)
	# the walls people walk round (they pass through the swept hull): the floor, the roof, the nose and the
	# tail, and the sides between the door apertures; the closed doors are their own bodies
	var bp: Dictionary = body.plan.bp
	add_box(Vector3(HALF_W * 2.0, 0.1, TAIL - NOSE), Vector3(0, FLOOR - 0.05, (NOSE + TAIL) * 0.5))
	add_box(Vector3(HALF_W * 2.0, 0.1, TAIL - NOSE - 1.2), Vector3(0, ROOF - 0.05, (NOSE + 1.2 + TAIL) * 0.5))
	add_box(Vector3(HALF_W * 2.0, 0.55, -0.92 - NOSE), Vector3(0, 0.78, (NOSE - 0.92) * 0.5))       # the nose to the cowl
	add_box(Vector3(HALF_W * 2.0, 0.6, 0.1), Vector3(0, 1.35, 2.31))                                 # the tail panel
	var gaps: Array = []
	for d in bp.doors:
		if str(d.side) == "R":
			gaps.append([float(d.z) - float(d.width) * 0.5, float(d.z) + float(d.width) * 0.5])
	gaps.sort_custom(func(a, b): return a[0] < b[0])
	var z := -0.92
	var spans: Array = []
	for g in gaps:
		if g[0] > z + 0.02:
			spans.append([z, g[0]])
		z = g[1]
	spans.append([z, TAIL - 0.06])
	for sx in [-1.0, 1.0]:
		for sp in spans:
			add_box(Vector3(0.08, ROOF - FLOOR, sp[1] - sp[0]), Vector3(sx * (HALF_W - 0.04), (FLOOR + ROOF) * 0.5, (sp[0] + sp[1]) * 0.5))
	_build_closers(bp)


func _build_closers(bp: Dictionary) -> void:
	for c in bp.closers:
		var pivot := Node3D.new()
		pivot.name = "Hinge_" + str(c.id)
		var h := Vector3(c.hinge[0], c.hinge[1], c.hinge[2])
		pivot.position = h
		body.add_child(pivot)
		var box := AABB()
		var first := true
		for mid in c.parts:
			var mi := body.get_node_or_null(str(mid)) as MeshInstance3D
			if mi == null:
				continue
			var xf := mi.transform
			body.remove_child(mi)
			pivot.add_child(mi)
			mi.transform = Transform3D(Basis(), -h) * xf
			var bb := mi.transform * mi.get_aabb()
			box = bb if first else box.merge(bb)
			first = false
		# the leaf's body: people bump it, it swings with the leaf (not synced: it follows its parent)
		var leaf := AnimatableBody3D.new()
		leaf.name = "Leaf_" + str(c.id)
		leaf.sync_to_physics = false
		leaf.collision_layer = 1
		leaf.collision_mask = 0
		var cs := CollisionShape3D.new()
		var sh := BoxShape3D.new()
		sh.size = box.size.max(Vector3.ONE * 0.06)
		cs.shape = sh
		cs.position = box.get_center()
		leaf.add_child(cs)
		pivot.add_child(leaf)
		var kind := str(c.kind)
		closers[str(c.id)] = {"pivot": pivot, "axis": Vector3(c.axis[0], c.axis[1], c.axis[2]).normalized(),
			"deg": float(c.open_deg), "t": 0.0, "open": false, "kind": kind, "leaf": leaf}
		# its use zone: outside the door, behind the tailgate, over the lid
		var at: Vector3
		var size: Vector3
		var mid_box := Transform3D(Basis(), h) * box
		if kind == "door":
			var sx := signf(h.x)
			at = Vector3(sx * (HALF_W + 0.1), 1.2, mid_box.get_center().z)
			size = Vector3(0.5, 1.3, mid_box.size.z)
		elif kind == "hatch":
			at = Vector3(0, 1.2, TAIL + 0.15)
			size = Vector3(1.4, 1.2, 0.4)
		else:
			at = Vector3(0, 1.1, mid_box.get_center().z)
			size = Vector3(1.4, 0.4, mid_box.size.z)
		var cid := str(c.id)
		var z := RemakeInteractZone.make(self, "Use_" + cid, Transform3D(Basis(), at), size,
			func(_by: Node) -> String: return _use_closer(cid),
			func() -> String: return _closer_prompt(cid))
		z.gives_way = true


func _closer_prompt(id: String) -> String:
	var c: Dictionary = closers[id]
	var what: String = {"door": "the door", "hatch": "the tailgate", "lid": "the frunk"}.get(str(c.kind), "it")
	return ("Close " if c.open else "Open ") + str(what)


func _use_closer(id: String) -> String:
	closers[id].open = not bool(closers[id].open)
	sleeping = false
	return "door"


func open_closer(id: String, on: bool) -> void:
	if closers.has(id):
		closers[id].open = on
		sleeping = false


func _animate_closers(delta: float) -> void:
	for id in closers:
		var c: Dictionary = closers[id]
		var target := 1.0 if c.open else 0.0
		var t := float(c.t)
		if t == target:
			continue
		var dur := DOOR_UP if str(c.kind) == "door" else (LID_UP if c.open else LID_DOWN)
		t = move_toward(t, target, delta / dur)
		if absf(t - target) < 1e-4:
			t = target                                  # (exactly shut: the seal test's closed leaf)
		c.t = t
		var e := smoothstep(0.0, 1.0, t)
		(c.pivot as Node3D).transform.basis = Basis(c.axis, deg_to_rad(float(c.deg)) * e)


func _excluded() -> Array[RID]:
	var ex := super()
	for id in closers:
		ex.append((closers[id].leaf as PhysicsBody3D).get_rid())
	return ex


# ------------------------------------------------------------------ the driver
func take_seat(p: StationPlayer) -> void:
	super(p)
	if pilot:
		open_closer("FL", false)


func leave_seat() -> void:
	if pilot:
		open_closer("FL", true)
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
			var x := (px - n * 0.5) / (n * 0.5)                # -1 left .. 1 right (as the lamp looks)
			var y := (n * 0.5 - py) / (n * 0.5)                # -1 down .. 1 up
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
			sp.rotation.x = deg_to_rad(-1.5)                # (aimed a little down: the cut-off meets the road at ~30 m)
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
			rv.light_color = Color(1.0, 1.0, 1.0)
			l = rv
			group = "reverse"
		elif n == "light_cabin" or n == "light_frunk":
			var om2 := OmniLight3D.new()
			om2.omni_range = 2.2 if n == "light_cabin" else 1.2
			om2.light_color = Color(1.0, 0.92, 0.78)
			l = om2
			group = "cabin" if n == "light_cabin" else "frunk"
		else:
			continue                                      # (the indicators: their lenses only, for now)
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
	# braking: slowing harder than coasting (whatever the pedal) -- the lamps stay lit a moment after
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
		(l as Light3D).shadow_enabled = pilot != null           # (shadows only on the player's own car)
	for l in lamps.get("tail", []):
		(l as Light3D).visible = dark or braking
		(l as Light3D).light_energy = (2.0 if braking else 0.6) * maxf(night, 0.5)
	for l in lamps.get("reverse", []):
		(l as Light3D).visible = reversing
	var any_door := false
	for id in closers:
		if str(closers[id].kind) == "door" and float(closers[id].t) > 0.0:
			any_door = true
	for l in lamps.get("cabin", []):
		(l as Light3D).visible = any_door and night > 0.3
	var lid_open: bool = closers.has("frunk") and float(closers.frunk.t) > 0.0
	for l in lamps.get("frunk", []):
		(l as Light3D).visible = lid_open
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
	# the blow lands on the body where the hull meets what it hit: the side of the hull facing the impulse
	var dir := global_transform.basis.inverse() * dv.normalized()           # (local: the way the blow pushes the body in)
	var hb := AABB(Vector3(-HALF_W, CLEAR, NOSE), Vector3(HALF_W * 2.0, ROOF - CLEAR, TAIL - NOSE))
	var at := hb.get_center() - dir * 3.0
	at = Vector3(clampf(at.x, hb.position.x, hb.end.x), clampf(1.0, hb.position.y, hb.end.y), clampf(at.z, hb.position.z, hb.end.z))
	bend(at, dir, 0.5 * mass * dv.length_squared() * 0.5)        # (J: half the energy goes into the frame)


func bend(at: Vector3, dir: Vector3, energy: float) -> void:
	## A blow to the frame (local point and direction): it dents, the skin with it; parts strained past their
	## tolerance come off.
	for mid in body.impact(at, dir, energy):
		var m: Dictionary = body.plan.modules.get(mid, {})
		body.break_off(mid, "shatter" if str(m.get("breaks", "")) == "shatter" else str(m.get("breaks", "detach")), linear_velocity)
