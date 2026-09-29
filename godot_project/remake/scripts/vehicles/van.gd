extends RemakeGroundVehicle
class_name RemakeVan

## The van (remake/blender/vehicles/groundcar.py "van"): a retro-futurist minibus, mustard and
## woodgrain under a white roof, a sliding side door each side behind the front seats, three rows.
## Local frame (glTF): x right, y up (0 = where the tyres touch), -z the nose.  5.15 m long.

const MODEL := "res://remake/vehicles/van.glb"
const FLOOR := 0.55
const H := 2.42
const DOOR_Z := -0.72
const DOOR_HW := 0.55


func _init() -> void:
	max_speed = 100.0 / 3.6              # 100 km/h
	reverse_speed = 4.0
	accel = 3.0
	brake = 5.5
	wheelbase = 3.34
	track = 1.68
	wheel_r = 0.4
	max_steer = 0.55
	stand_point = Vector3(0.0, FLOOR + 1.45, -0.4)
	cabin_box = AABB(Vector3(-1.0, 0.0, -2.5), Vector3(2.0, H, 5.0))
	seat_forward = 0.05
	hull_size = Vector3(1.95, 2.0, 5.1)


func _build_hull() -> void:
	load_model(MODEL)
	add_box(Vector3(1.8, 0.12, 4.7), Vector3(0, FLOOR - 0.06, 0.1))
	var wall_h := H - 0.12 - FLOOR
	var yc := FLOOR + wall_h * 0.5
	var z0 := DOOR_Z - DOOR_HW
	var z1 := DOOR_Z + DOOR_HW
	for sx in [-1.0, 1.0]:
		add_box(Vector3(0.1, wall_h, z0 + 2.3), Vector3(sx * 0.92, yc, (z0 - 2.3) * 0.5))
		add_box(Vector3(0.1, wall_h, 2.45 - z1), Vector3(sx * 0.92, yc, (z1 + 2.45) * 0.5))
	add_box(Vector3(1.9, wall_h, 0.1), Vector3(0, yc, -2.2))
	add_box(Vector3(1.9, wall_h, 0.1), Vector3(0, yc, 2.45))
	add_box(Vector3(1.95, 0.1, 5.0), Vector3(0, H - 0.08, 0))
	add_box(Vector3(1.8, 0.4, 0.35), Vector3(0, 1.1, -2.05))
	for sx in [-0.48, 0.48]:
		add_box(Vector3(0.52, 0.5, 0.5), Vector3(sx, FLOOR + 0.25, -1.5))
	for z in [0.25, 1.55]:
		add_box(Vector3(1.6, 0.5, 0.5), Vector3(0, FLOOR + 0.25, z))
	for sx in [-1.0, 1.0]:
		add_ramp(Vector3(0.9, 0.05, 1.0), Vector3(sx * 1.3, FLOOR * 0.5, DOOR_Z), -sx * atan2(FLOOR, 0.82))


func door_slide() -> float:
	return 1.2                         # the whole leaf (2 x DOOR_HW) clear of the doorway, with 10 cm to spare
