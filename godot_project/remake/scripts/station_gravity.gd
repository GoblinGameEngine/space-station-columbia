extends Area3D
class_name StationGravity

## The station's spin gravity for everything the physics engine moves by itself (wrecks, ragdolls,
## knocked-down signs): away from the axis (world x), at the floor's strength. An area around the
## player whose gravity points away from a point on the axis level with them (a point gravity of
## negative strength, constant with distance) -- near the player that is the radial direction.
## (Vehicles the code drives apply their own: gravity_scale 0.)

const SIZE := 500.0
var player: Node3D
var _shape: CollisionShape3D


func _ready() -> void:
	name = "StationGravity"
	gravity_space_override = Area3D.SPACE_OVERRIDE_REPLACE
	gravity_point = true
	gravity_point_unit_distance = 0.0                # the same strength at any distance
	gravity_point_center = Vector3.ZERO
	gravity = -StationGeo.TARGET_G                    # negative: away from the centre point
	monitoring = false
	monitorable = false
	collision_layer = 0
	collision_mask = 0xFFFFF                          # it acts on whatever is in it
	_shape = CollisionShape3D.new()
	var b := BoxShape3D.new()
	b.size = Vector3.ONE * SIZE
	_shape.shape = b
	add_child(_shape)


func _physics_process(_delta: float) -> void:
	if player == null:
		return
	var p := player.global_position
	global_position = Vector3(p.x, 0.0, 0.0)          # the point gravity's centre, on the axis
	_shape.position = Vector3(0.0, p.y, p.z)
