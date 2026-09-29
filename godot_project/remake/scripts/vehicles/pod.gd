extends RemakeGroundVehicle
class_name RemakePod

## The pod (remake/blender/vehicles/groundcar.py "pod"): a small electric people-mover, sliding double
## doors each side, the driver on the left at a yoke.  Local frame (glTF): x right, y up (0 = where
## the tyres touch), -z the nose.  3.95 m long, 1.9 m wide.

const MODEL := "res://remake/vehicles/pod.glb"
const FLOOR := 0.42
const H := 2.35
const DOOR_Z := 0.12                  # the doorways' centre (the model's DOOR_Y, negated)
const DOOR_HW := 0.62


func _init() -> void:
	max_speed = 75.0 / 3.6               # 75 km/h
	reverse_speed = 4.0
	accel = 3.0
	brake = 6.0
	wheelbase = 2.62
	track = 1.6
	wheel_r = 0.36
	stand_point = Vector3(0.0, FLOOR + 1.45, 0.1)
	cabin_box = AABB(Vector3(-0.95, 0.0, -1.9), Vector3(1.9, H, 3.8))
	seat_forward = 0.05
	hull_size = Vector3(1.85, 1.95, 3.9)


func _build_hull() -> void:
	load_model(MODEL)
	add_box(Vector3(1.75, 0.12, 3.6), Vector3(0, FLOOR - 0.06, 0.0))
	var wall_h := H - 0.12 - FLOOR
	var yc := FLOOR + wall_h * 0.5
	var z0 := DOOR_Z - DOOR_HW
	var z1 := DOOR_Z + DOOR_HW
	for sx in [-1.0, 1.0]:
		add_box(Vector3(0.1, wall_h, z0 + 1.55), Vector3(sx * 0.86, yc, (z0 - 1.55) * 0.5))
		add_box(Vector3(0.1, wall_h, 1.88 - z1), Vector3(sx * 0.86, yc, (z1 + 1.88) * 0.5))
	add_box(Vector3(1.8, wall_h, 0.1), Vector3(0, yc, -1.55))        # behind the windscreen, clear of the dash
	add_box(Vector3(1.8, wall_h, 0.1), Vector3(0, yc, 1.88))
	add_box(Vector3(1.85, 0.1, 3.8), Vector3(0, H - 0.08, 0))
	add_box(Vector3(1.7, 0.35, 0.3), Vector3(0, 1.0, -1.4))          # the dash
	for sx in [-0.42, 0.42]:
		add_box(Vector3(0.52, 0.5, 0.5), Vector3(sx, FLOOR + 0.25, -0.72))
		add_box(Vector3(0.56, 0.5, 0.5), Vector3(sx * 0.95, FLOOR + 0.25, 1.25))
	for sx in [-1.0, 1.0]:
		add_ramp(Vector3(0.8, 0.05, 1.1), Vector3(sx * 1.2, FLOOR * 0.5, DOOR_Z), -sx * atan2(FLOOR, 0.72))


func door_slide() -> float:
	return 0.68                        # a leaf (DOOR_HW wide) clear of the doorway, with 6 cm to spare
