extends RemakeAirVehicle
class_name RemakeFleetAerostat

## An aerostat of the fleet (research/vehicles/aerostat/AEROSTATS.md): the rescue and cargo aerostats. Its body is a
## modular fleet body (FleetBodies: the gondola's tube frame, both shells, doors and seats, and the envelope, fins,
## fans and struts as equipment tokens) on a Steward keel; it flies as every RemakeAirVehicle does. The hull is
## boxes for the gondola (its doorways open), spheres along the envelope, and the cargo aerostat's sling frame,
## which it lands on. Local frame: x right, y up (0 = the keel's skids), -z the nose.

var vtype := ""
var info := {}
var body: VehicleBody
var _fc := FleetClosers.new()
var nose := -3.0
var tail := 3.0
var floor_y := 0.55
var roof_y := 2.9
var half_w := 1.2


func _init(t := "") -> void:
	if t == "":
		return
	vtype = t
	info = FleetBodies.of(t)
	nose = -float(info.get("nose", 3.0))
	tail = -float(info.get("tail", -3.0))
	floor_y = float(info.get("floor", 0.55))
	roof_y = float(info.get("height", 2.9))
	half_w = float(info.get("half_w", 1.2))
	var heavy := t == "cargo_aerostat"
	max_speed = (60.0 if heavy else 110.0) / 3.6
	accel = 2.0 if heavy else 4.0
	brake = 3.0 if heavy else 6.0
	turn_rate = 0.25 if heavy else 0.5
	crash_physics = true
	cabin_box = AABB(Vector3(-half_w, floor_y - 0.1, nose), Vector3(half_w * 2.0, roof_y - floor_y + 0.1, tail - nose))
	stand_point = Vector3(0.0, floor_y + 0.05, nose + 1.6)
	com_height = float(info.get("aero", {}).get("env", [0, 0, 0, 3.0])[3]) * 0.5


func _build_hull() -> void:
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
	for mk in body.get_children():                      # (the fans, as the rig's engines: their sound and thrust)
		if str(mk.name).begins_with("fan_") and mk is Node3D and not mk is MeshInstance3D:
			var e := Node3D.new()
			e.name = "engine_" + str(mk.name)
			e.position = (mk as Node3D).position
			model.add_child(e)
	var bp: Dictionary = body.plan.bp
	var std: Dictionary = body.plan.std
	var crown := float(std.get("crown", roof_y))
	# the gondola: floor, roof, the end walls, the sides between the doorways (the doors are their own bodies)
	add_box(Vector3(half_w * 2.0, 0.12, tail - nose), Vector3(0, floor_y - 0.06, (nose + tail) * 0.5))
	add_box(Vector3(half_w * 2.0, 0.12, tail - nose), Vector3(0, crown - 0.06, (nose + tail) * 0.5))
	add_box(Vector3(half_w * 2.0, 0.42, tail - nose), Vector3(0, 0.30, (nose + tail) * 0.5))     # (the keel under the floor)
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
		for g in gaps:                                  # (a step up to each doorway: no one climbs a 0.55 m sill)
			add_box(Vector3(0.7, 0.05, g[1] - g[0]), Vector3(sx * (half_w + 0.3), floor_y * 0.5, (g[0] + g[1]) * 0.5), -sx * atan2(floor_y, 0.6))
	# the envelope: spheres along its axis (Blender (x, y, z) -> Godot (x, z, -y))
	var A: Dictionary = info.get("aero", {})
	if A.get("env") != null:
		var el := float(A.env[0])
		var er := float(A.env[1])
		var ey := float(A.env[2])
		var ez := float(A.env[3])
		var n := int(ceil(el / er))
		for k in n:
			var t := (k + 0.5) / n
			var r := er * (0.55 if t < 0.12 or t > 0.9 else (0.85 if t < 0.25 else 0.97))
			add_sphere(r, Vector3(0, ez, -(ey - el * 0.5 + el * t)))
	if A.get("sling") != null:                          # the cargo frame: its rails, ends and feet (it lands on them)
		var hw := float(A.sling[0])
		var y0 := float(A.sling[1])
		var y1 := float(A.sling[2])
		var sz := float(A.sling[3])
		for sx in [-1.0, 1.0]:
			add_box(Vector3(0.34, 0.42, y0 - y1), Vector3(sx * hw, sz - 0.21, -(y0 + y1) * 0.5))
		for y in [y0, y1]:
			add_box(Vector3(hw * 2.0 + 0.3, 0.42, 0.34), Vector3(0, sz - 0.21, -y))
	_fc.build(self, body, bp)


func _physics_process(delta: float) -> void:
	_fc.animate(delta)
	super(delta)


func _sweep_excluded() -> Array[RID]:
	return _fc.rids()


func take_seat(p: StationPlayer) -> void:
	super(p)
	if pilot:
		_fc.open("F" + str(info.get("driver", "L")), false)


func ground_offset() -> float:
	## How far below the local origin it stands on the ground (the cargo aerostat lands on its sling frame).
	return float(info.get("ground", 0.0))
