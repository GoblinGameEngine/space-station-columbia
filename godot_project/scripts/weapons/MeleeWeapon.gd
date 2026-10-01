extends WeaponBase

# Shared by Fists and Bat (see data/weapons.json for damage/range/cooldown
# per weapon id) -- a simple forward shape-check swing, deliberately basic
# per the "melee can be simple" brief.

func _perform() -> void:
	_swing_animation()
	if camera == null:
		return
	var range_m: float = float(data.get("range", 1.5))
	var from := camera.global_transform.origin
	var forward := -camera.global_transform.basis.z
	var space_state := camera.get_world_3d().direct_space_state

	var shape := SphereShape3D.new()
	shape.radius = 0.45
	var params := PhysicsShapeQueryParameters3D.new()
	params.shape = shape
	params.transform = Transform3D(Basis(), from + forward * range_m * 0.65)
	params.exclude = [user.get_rid()] if user and user is CollisionObject3D else []
	params.collision_mask = 0xFFFFFFFF

	var hits := space_state.intersect_shape(params, 4)
	for hit in hits:
		var collider = hit.collider
		if collider == user:
			continue
		if collider.has_method("take_hit"):
			collider.take_hit(float(data.get("damage", 10)), from + forward * range_m * 0.65, user)
			break
		if collider.get_node_or_null("Health") != null:
			CombatSystem.apply_damage(user, collider, float(data.get("damage", 10)))
			break

func _swing_animation() -> void:
	var tw := create_tween()
	var start_rot := rotation
	tw.tween_property(self, "rotation:x", start_rot.x - deg_to_rad(35), 0.06)
	tw.tween_property(self, "rotation:x", start_rot.x, 0.12)
