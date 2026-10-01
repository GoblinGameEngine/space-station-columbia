extends RigidBody3D
class_name NpcCarBody

## An NPC vehicle's body (NpcTraffic): a box of its type's size and mass. Driven, it is frozen
## (kinematic) and placed by its RoadDriver; hit hard by something moving, it lets go to the physics
## with its share of the momentum -- a 1-D collision along the line between the two, by their masses
## (restitution 0.2: cars crumple, they don't bounce) -- and from then on it's a wreck the physics
## moves under the station's gravity, until it's left behind.

const RESTITUTION := 0.2
const KNOCK_MS := 1.0                # closing speed (m/s) that's more than a nudge
const SHRUG_MS := 1.5                # its own change of speed (m/s) below which it carries on driving

var traffic: Node
var entry_id := ""
var v_now := Vector3.ZERO            # its velocity while driven
var crashed := false


func _ready() -> void:
	freeze_mode = RigidBody3D.FREEZE_MODE_KINEMATIC
	freeze = true
	gravity_scale = 0.0
	can_sleep = true
	var pm := PhysicsMaterial.new()
	pm.friction = 0.7
	pm.bounce = 0.1
	physics_material_override = pm


func knock(by: Node, v_by: Vector3, m_by: float) -> void:
	if crashed or not (by is Node3D):
		return
	var n := (global_position - (by as Node3D).global_position)
	n = n.normalized() if n.length() > 0.01 else Vector3.FORWARD
	var u1 := v_by.dot(n)
	var u2 := v_now.dot(n)
	if u1 - u2 < KNOCK_MS:
		return
	var m1 := m_by
	var m2 := mass
	var u2p := (m1 * u1 + m2 * u2 + m1 * RESTITUTION * (u1 - u2)) / (m1 + m2)
	var u1p := (m1 * u1 + m2 * u2 - m2 * RESTITUTION * (u1 - u2)) / (m1 + m2)
	if absf(u2p - u2) < SHRUG_MS:
		return                                       # a truck nudging a parked car: it drives on (and pushes it)
	crashed = true
	freeze = false
	linear_velocity = v_now + n * (u2p - u2)
	# an off-centre hit sets it turning
	var up := global_transform.basis.y
	angular_velocity = up * (n.cross(global_transform.basis.z).dot(up)) * (u2p - u2) * 0.25
	if by is RigidBody3D:
		(by as RigidBody3D).linear_velocity = v_by + n * (u1p - u1)
	if traffic and traffic.has_method("on_crash"):
		traffic.on_crash(entry_id)


func _physics_process(_delta: float) -> void:
	if freeze or sleeping:
		return
	var s := StationGeo.s_of(global_position)
	apply_central_force(-StationGeo.up(s) * StationGeo.gravity_at(Vector2(global_position.y, global_position.z).length()) * mass)
