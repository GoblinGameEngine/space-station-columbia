extends RemakeAirVehicle
class_name RemakeFleetCraft

## A fleet body that flies or floats (research/vehicles/aerostat/AEROSTATS.md): the aerostats, the spacecraft, the
## spoke elevator car, the EVA sled (they fly) and the boats (they float, and only drive on the water). Its body is
## the modular fleet body (FleetBodies) -- on a Steward keel, a hull, or none; it flies as every RemakeAirVehicle
## does, a player at its controls or an NPC through fly_input (VehiclePilot). The hull people stand in and the world
## bumps into is boxes: the gondola or cabin (its doorways open, a step or a stair up to each), spheres along an
## envelope, a cargo sling frame (it lands on it), a boat's sole, sides and ends. Local frame: x right, y up (0 = the
## keel's skids, a boat's waterline), -z the nose.

var vtype := ""
var info := {}
var body: VehicleBody
var _fc := FleetClosers.new()
var nose := -3.0
var tail := 3.0
var floor_y := 0.55
var roof_y := 2.9
var half_w := 1.2
var boat := false

# km/h, and how fast it climbs (m/s): by type
const SPEEDS := {"cargo_aerostat": [60.0, 3.0], "rescue_aerostat": [110.0, 5.0], "passenger_shuttle": [160.0, 6.0],
	"supply_freighter": [80.0, 3.0], "cargo_mule": [60.0, 4.0], "spoke_elevator_car": [36.0, 6.0], "eva_sled": [40.0, 4.0]}


func _init(t := "") -> void:
	if t == "":
		return
	vtype = t
	info = FleetBodies.of(t)
	boat = bool(info.get("boat", false))
	nose = -float(info.get("nose", 3.0))
	tail = -float(info.get("tail", -3.0))
	floor_y = float(info.get("floor", 0.55))
	roof_y = float(info.get("height", 2.9))
	half_w = float(info.get("half_w", 1.2))
	crash_physics = true
	if boat:                                          # (a boat: by its length, 15-40 km/h; it doesn't fly)
		var ln := tail - nose
		max_speed = clampf(10.0 + ln * 1.5, 15.0, 40.0) / 3.6
		water_speed_k = 1.0
		can_climb = false
		floats = true
		float_draft = 0.05
		climb_speed = 1.5
		accel = 1.5
		brake = 1.0
		turn_rate = clampf(1.2 - ln * 0.03, 0.15, 0.9)
	else:
		var sp: Array = SPEEDS.get(t, [80.0, 4.0])
		max_speed = float(sp[0]) / 3.6
		climb_speed = float(sp[1])
		var heavy := tail - nose > 15.0
		accel = 1.5 if heavy else 4.0
		brake = 2.5 if heavy else 6.0
		turn_rate = 0.2 if heavy else 0.5
	var crown := roof_y
	cabin_box = AABB(Vector3(-half_w, floor_y - 0.1, nose), Vector3(half_w * 2.0, crown - floor_y + 0.1, tail - nose))
	var st: Array = info.get("seat", []) if info.get("seat") != null else []
	stand_point = Vector3(0.6, st[1] - 0.4, st[2] + 0.5) if st.size() == 3 else Vector3(0.0, floor_y + 0.05, nose + 1.6)
	var A = info.get("aero", {})
	com_height = float(A.env[3]) * 0.5 if A is Dictionary and A.get("env") != null else (crown + floor_y) * 0.5


func _build_hull() -> void:
	var board := str(info.get("board", "none"))
	if board != "none" and ResourceLoader.exists(FleetBodies.board_path(board)):
		model = (load(FleetBodies.board_path(board)) as PackedScene).instantiate()
		FleetBodies.strip_board(model)
	else:
		model = Node3D.new()
	model.name = "Model"
	add_child(model)
	body = VehicleBody.make(VehicleBody.prepare(str(info.blueprint)))
	add_child(body)                                     # (beside the model: the base rig's door_* search stays off it)
	# the rig: the pilot's seat (the body's driver marker, or the registry's seat), the controls, the fans as engines
	var seat := body.get_node_or_null("seat_driver") as Node3D
	var seat_at := seat.position if seat else Vector3.ZERO
	if seat == null and info.get("seat") != null:
		var s: Array = info.seat
		seat_at = Vector3(float(s[0]), float(s[1]), float(s[2]))
		seat = model
	if seat:
		var n := Node3D.new()
		n.name = "seat_pilot"
		n.position = seat_at
		model.add_child(n)
	var mk := body.get_node_or_null("steering") as Node3D
	if mk:
		var n := Node3D.new()
		n.name = "steering_wheel"
		n.position = mk.position
		model.add_child(n)
	# the fans as the rig's engines: each fan's own mesh (role "engine": a node of its own) on a pivot at its middle, which
	# the flight rig tilts for thrust; without a mesh of its own, a bare pivot at its marker (sound only)
	var fan_meshes := body.get_children().filter(func(c): return c is MeshInstance3D and str(c.name).begins_with("fan_"))
	for m in fan_meshes:
		var mi := m as MeshInstance3D
		var e := Node3D.new()
		e.name = "engine_" + str(mi.name)
		e.position = mi.transform * mi.get_aabb().get_center()
		model.add_child(e)
		var xf := mi.transform
		body.remove_child(mi)
		e.add_child(mi)
		mi.transform = Transform3D(Basis(), -e.position) * xf
	if fan_meshes.is_empty():
		for m in body.get_children():
			if str(m.name).begins_with("fan_") and m is Node3D and not m is MeshInstance3D:
				var e := Node3D.new()
				e.name = "engine_" + str(m.name)
				e.position = (m as Node3D).position
				model.add_child(e)
	if boat:
		_boat_hull()
	elif info.get("standard", "").begins_with("PX"):
		_open_hull()                                    # (a recipe -- the EVA sled: its deck)
	else:
		_cabin_hull()
	_fc.build(self, body, body.plan.bp)


func _cabin_hull() -> void:
	## A gondola or cabin on a keel: floor, keel, roof, end walls, the sides between the doorways; a step (or, standing
	## high on a frame, a stair) up to each doorway; the envelope as spheres; the sling frame's rails.
	var bp: Dictionary = body.plan.bp
	var std: Dictionary = body.plan.std
	var crown := float(std.get("crown", roof_y))
	var ground := float(info.get("ground", 0.0))
	add_box(Vector3(half_w * 2.0, 0.12, tail - nose), Vector3(0, floor_y - 0.06, (nose + tail) * 0.5))
	add_box(Vector3(half_w * 2.0, 0.12, tail - nose), Vector3(0, crown - 0.06, (nose + tail) * 0.5))
	add_box(Vector3(half_w * 1.4, 0.42, tail - nose), Vector3(0, 0.30, (nose + tail) * 0.5))     # (the keel under the floor)
	for z in [nose + 0.05, tail - 0.05]:
		add_box(Vector3(half_w * 2.0, crown - floor_y, 0.1), Vector3(0, (crown + floor_y) * 0.5, z))
	for sd in ["R", "L"]:
		var gaps: Array = []
		for d in bp.doors:
			if str(d.side) == sd:
				gaps.append([float(d.z) - float(d.width) * 0.5, float(d.z) + float(d.width) * 0.5])
		gaps.sort_custom(func(a, b): return a[0] < b[0])
		var z := nose
		var sx := 1.0 if sd == "R" else -1.0
		for g in gaps + [[tail, tail]]:
			if g[0] > z + 0.02:
				add_box(Vector3(0.08, crown - floor_y, g[0] - z), Vector3(sx * (half_w - 0.06), (crown + floor_y) * 0.5, (z + g[0]) * 0.5))
			z = maxf(z, g[1])
		for g in gaps:
			var wz: float = g[1] - g[0]
			var zc: float = (g[0] + g[1]) * 0.5
			if ground < -0.5:                           # (high over its frame: the boarding stair, out to the frame's rail)
				var A: Dictionary = info.get("aero", {})
				if sd == "R" and A.get("sling") != null:
					var x1 := float(A.sling[0]) - 0.1
					var y1 := float(A.sling[3])
					var run := x1 - half_w
					var rise := floor_y - y1
					var ln := sqrt(run * run + rise * rise)
					add_box(Vector3(ln, 0.06, wz + 0.1), Vector3((half_w + x1) * 0.5, (floor_y + y1) * 0.5 - 0.05, zc), -atan2(rise, run))
			else:                                       # (a step up: no one climbs a 0.55 m sill)
				add_box(Vector3(0.7, 0.05, wz), Vector3(sx * (half_w + 0.3), floor_y * 0.5, zc), -sx * atan2(floor_y, 0.6))
	var A2 = info.get("aero", {})
	if A2 is Dictionary and A2.get("env") != null:     # the envelope: spheres along its axis (Blender (x, y, z) -> Godot (x, z, -y))
		var el := float(A2.env[0])
		var er := float(A2.env[1])
		var ey := float(A2.env[2])
		var ez := float(A2.env[3])
		var n := int(ceil(el / er))
		for k in n:
			var t := (k + 0.5) / n
			var r := er * (0.55 if t < 0.12 or t > 0.9 else (0.85 if t < 0.25 else 0.97))
			add_sphere(r, Vector3(0, ez, -(ey - el * 0.5 + el * t)))
	if A2 is Dictionary and A2.get("sling") != null:   # the cargo frame: its rails and ends (it lands on them)
		var hw := float(A2.sling[0])
		var y0 := float(A2.sling[1])
		var y1 := float(A2.sling[2])
		var sz := float(A2.sling[3])
		for sx in [-1.0, 1.0]:
			add_box(Vector3(0.34, 0.42, y0 - y1), Vector3(sx * hw, sz - 0.21, -(y0 + y1) * 0.5))
		for y in [y0, y1]:
			add_box(Vector3(hw * 2.0 + 0.3, 0.42, 0.34), Vector3(0, sz - 0.21, -y))
	if vtype == "passenger_shuttle":                    # (its wings and fin: a slab each)
		add_box(Vector3(18.0, 0.3, 9.0), Vector3(0, 1.0, 4.5))
		add_box(Vector3(0.3, 5.0, 4.0), Vector3(0, crown + 2.5, 12.0))


func _boat_hull() -> void:
	## A boat: its sole (the floor people stand on), its sides to the sheer and a rail's height, its ends; a wheelhouse's
	## roof and sides. The waterline is the origin.
	var H: Dictionary = info.get("hull", {})
	var sheer := float(H.get("sheer", 0.6))
	var draft := float(H.get("draft", 0.3))
	var t := float(H.get("t", 0.04))
	var sole := -draft + t + minf(0.35, draft * 0.6)
	if H.get("sole") != null:                           # (the cockpit's sole: fleet/boat_interiors.py)
		sole = float(H["sole"])
	var ln := tail - nose
	add_box(Vector3(half_w * 1.4, 0.1, ln * 0.8), Vector3(0, sole - 0.05, (nose + tail) * 0.5))
	add_box(Vector3(half_w * 0.9, sole + draft, ln * 0.85), Vector3(0, (sole - draft) * 0.5, (nose + tail) * 0.5))   # (the hull below it)
	for sx in [-1.0, 1.0]:
		add_box(Vector3(0.1, sheer - sole + 0.5, ln * 0.85), Vector3(sx * (half_w - t), (sheer + sole + 0.5) * 0.5, (nose + tail) * 0.5))
	for z in [nose + ln * 0.08, tail - 0.1]:
		add_box(Vector3(half_w * 1.6, sheer - sole + 0.3, 0.12), Vector3(0, (sheer + sole + 0.3) * 0.5, z))
	_hull_mask(H.get("waterline", []))
	var wh = H.get("wheelhouse")
	if wh != null:                                      # [y0, y1, half w, height]: its roof and sides (the back open)
		var zf := -float(wh[0])
		var zb := -float(wh[1])
		var hw := float(wh[2])
		var hh := float(wh[3])
		var wf := float(H["wh_floor"]) if H.get("wh_floor") != null else sheer + 0.05
		add_box(Vector3(hw * 2.0, 0.1, zb - zf), Vector3(0, wf - 0.05, (zf + zb) * 0.5))          # (its sole, over the deck)
		add_box(Vector3(hw * 2.0 + 0.2, 0.1, zb - zf + 0.2), Vector3(0, wf + hh + 0.05, (zf + zb) * 0.5))
		for sx in [-1.0, 1.0]:
			add_box(Vector3(0.08, hh, zb - zf), Vector3(sx * hw, wf + hh * 0.5, (zf + zb) * 0.5))
		add_box(Vector3(hw * 2.0, hh, 0.08), Vector3(0, wf + hh * 0.5, zf))


func _open_hull() -> void:
	## An open recipe (the EVA sled): its deck and the tower behind the seat.
	add_box(Vector3(half_w * 2.0, 0.3, tail - nose), Vector3(0, 0.55, (nose + tail) * 0.5))
	add_box(Vector3(half_w * 2.0, 1.5, 0.6), Vector3(0, 1.3, tail - 0.3))


func _physics_process(delta: float) -> void:
	_fc.animate(delta)
	super(delta)
	if body and (pilot or not fly_input.is_empty()):
		body.set_gauges(_lv.length() * 3.6, battery)


func _sweep_excluded() -> Array[RID]:
	return _fc.rids()


func take_seat(p: StationPlayer) -> void:
	super(p)
	if pilot:
		_fc.open("F" + str(info.get("driver", "L")), false)


func ground_offset() -> float:
	## How far below the local origin it stands on the ground (the cargo aerostat on its sling frame, a boat on its keel).
	return float(info.get("ground", 0.0))


func _hull_mask(wl: Array) -> void:
	## The water this hull displaces: an invisible fan over its waterline outline (both halves) that marks the stencil,
	## so the water isn't drawn inside the shell (MapWater.hull_masked).
	if wl.size() < 2:
		return
	var ring: Array = []
	for p in wl:
		ring.append(Vector3(float(p[0]), 0.0, float(p[1])))
	for i in range(wl.size() - 1, -1, -1):
		ring.append(Vector3(-float(wl[i][0]), 0.0, float(wl[i][1])))
	var c := Vector3.ZERO
	for p in ring:
		c += p
	c /= ring.size()
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in ring.size():
		st.add_vertex(c)
		st.add_vertex(ring[i])
		st.add_vertex(ring[(i + 1) % ring.size()])
	var mi := MeshInstance3D.new()
	mi.name = "HullWaterMask"
	mi.mesh = st.commit()
	mi.material_override = MapWater.hull_mask_material()
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)
