extends RemakeAirVehicle
class_name RemakeAerostat

## The aerostat (remake/blender/vehicles/aerostat.py): a cabin under a lift balloon, four
## tilting ducted fans.  Flies as every RemakeAirVehicle does; this gives its model and hull.
## Local frame (glTF): x right, y up (0 = the casters' contact), -z the nose.  4.6 m long: the
## front seats sit wholly ahead of the doorways; the cockpit floor and chin are clear acrylic.

const MODEL := "res://remake/vehicles/aerostat.glb"
const FLOOR := 0.35
const H := 2.45


const DOOR_Z := 0.15                 # the doorways' centre (the model's DOOR_Y, negated)
const HALF_L := 2.3


func _init() -> void:
	stand_point = Vector3(0.45, FLOOR + 1.45, -0.35)     # in the aisle just behind the front seats
	cabin_box = AABB(Vector3(-1.2, 0.0, -HALF_L), Vector3(2.4, 2.5, HALF_L * 2.0))
	seat_forward = 0.2
	max_speed = 150.0 / 3.6              # 150 km/h
	accel = 5.0
	brake = 7.0
	crash_physics = true


func _build_hull() -> void:
	load_model(MODEL)
	# floor and belly (the acrylic ahead of the doorways is as solid underfoot as the mat)
	add_box(Vector3(2.0, 0.1, 4.3), Vector3(0, FLOOR - 0.05, 0))
	add_box(Vector3(1.9, 0.26, 4.0), Vector3(0, 0.15, 0))
	# walls, leaving each side's doorway (z DOOR_Z +- 0.65) to the door leaves
	var wall_h := H - 0.15 - FLOOR
	var yc := FLOOR + wall_h * 0.5
	for sx in [-1.0, 1.0]:
		add_box(Vector3(0.1, wall_h, 1.6), Vector3(sx * 1.13, yc, -1.3))
		add_box(Vector3(0.1, wall_h, 1.3), Vector3(sx * 1.13, yc, 1.45))
	add_box(Vector3(1.8, wall_h, 0.1), Vector3(0, yc, -2.15))
	add_box(Vector3(1.8, wall_h, 0.1), Vector3(0, yc, 2.15))
	add_box(Vector3(2.2, 0.12, 4.5), Vector3(0, H - 0.1, 0))
	# boarding ramps up to each doorway (the model's step; the player can't climb a 35 cm sill)
	for sx in [-1.0, 1.0]:
		add_box(Vector3(0.72, 0.05, 1.0), Vector3(sx * 1.45, FLOOR * 0.5, DOOR_Z), -sx * atan2(FLOOR, 0.6))
	# furniture: the dash (legroom under it), the two front seats, the rear bench
	add_box(Vector3(2.0, 0.3, 0.45), Vector3(0, 0.97, -1.95))
	for sx in [-0.5, 0.5]:
		add_box(Vector3(0.56, 0.55, 0.52), Vector3(sx, FLOOR + 0.27, -1.05))
	add_box(Vector3(1.7, 0.52, 0.46), Vector3(0, FLOOR + 0.26, 1.75))
	# the fans (as upright cylinders) and the balloon
	for sx in [-1.0, 1.0]:
		for sz in [-1.0, 1.0]:
			add_cylinder(0.62, 0.46, Vector3(sx * 1.8, 0.39, sz * 1.75))
	add_sphere(2.4, Vector3(0, H + 0.62 + 2.4, 0))


func door_slide() -> float:
	return 0.62
