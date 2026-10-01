extends AnimatableBody3D
class_name TramHull

## A tram section's collision body (TramSection builds it): vehicles that run into it (their
## knock(), see RemakeGroundVehicle._shove_others) and shots (take_hit) damage the section's modules.

var section: TramSection


func knock(by: Node, v_by: Vector3, m_by: float) -> void:
	if section and by is Node3D:
		section.knock_from(by, v_by, m_by)


func take_hit(amount: float, at: Vector3, _by: Node = null) -> void:
	if section:
		section.hit_at(section.global_transform.affine_inverse() * at, amount)
