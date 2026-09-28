extends Area3D
class_name WaterVolume

# Generic swim-trigger volume for any water body (today: the lake;
# future: river/pond zones once built). Built as an Area3D with
# per-segment BoxShape3D children -- matching StationRingBuilder.
# _add_collision_segments()'s own per-segment convex-box convention,
# since one box spanning many ring segments would float off the real
# floor the same way a naive multi-segment quad would (see
# StreetBuilder.gd's header comment for the general problem).
#
# Purely a trigger: enter/exit notifications only, never a physics
# force. Explicitly no flow/current here -- "I don't want the water to
# flow, just make it so the play character can swim in it." Whatever
# body enters just gets told via enter_water()/exit_water() (if it
# implements them) and decides its own swim physics; see
# StationPlayer.gd for the player's side of that contract.

## a cloud's volume: its puffs are spheres, but the cloud is drawn cut flat at its base (its parent's
## local y = 0) -- it only holds what's above that
var flat_base := false


func holds(p: Vector3) -> bool:
	if not flat_base:
		return true
	return ((get_parent() as Node3D).global_transform.affine_inverse() * p).y >= 0.0


func _ready() -> void:
	monitorable = false
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)

func _on_body_entered(body: Node3D) -> void:
	if body.has_method("enter_water"):
		body.enter_water(self)

func _on_body_exited(body: Node3D) -> void:
	if body.has_method("exit_water"):
		body.exit_water(self)
