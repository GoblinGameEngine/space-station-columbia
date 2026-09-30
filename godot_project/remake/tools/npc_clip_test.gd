extends SceneTree

## Every authored clip (npc_clips.json) played through on a spread of bodies -- small children to
## heavy elders -- at 24 fps, checking each bone's pose stays finite and the clip ends cleanly.
##   ../godot/godot4 --headless --path . --script res://remake/tools/npc_clip_test.gd -- [people]


func _init() -> void:
	var a := OS.get_cmdline_user_args()
	var people := int(a[0]) if a.size() > 0 else 12
	var db := NpcTraits.shared()
	var world := Node3D.new()
	root.add_child(world)
	var ids: Array = (NpcClips.data().clips as Dictionary).keys()
	var fails := 0
	var frames := 0
	for i in people:
		var pid := "B%d:%d" % [3000 + i, i % 3]
		var npc := NpcCharacter.create(db.person(7, pid, ["L0", "L1"], ""), pid, 7)
		world.add_child(npc)
		var an := NpcAnimator.attach(npc)
		an.manual = true
		an._ready()
		for id in ids:
			var length := an.play(id)
			if length <= 0.0:
				print("FAIL %s: no clip" % id)
				fails += 1
				continue
			var n := int(ceil((length + 1.0) * 24.0))
			for f in n:
				if f == n - 24:
					an.stop_clip()                   # loops end on request; one-shots have ended
				an.pose(0.0, 0.0, f / 24.0, 1.0 / 24.0)
				frames += 1
				for b in npc.skeleton.get_bone_count():
					var q := npc.skeleton.get_bone_pose_rotation(b)
					var p := npc.skeleton.get_bone_pose_position(b)
					if not (q.is_finite() and p.is_finite()):
						print("FAIL %s %s frame %d bone %s" % [id, pid, f, NpcBody.BONES[b]])
						fails += 1
						break
			if an.clip_playing() != "":
				print("FAIL %s %s: did not end" % [id, pid])
				fails += 1
		npc.free()
	print("clips: %d x %d people, %d frames; failures %d" % [ids.size(), people, frames, fails])
	quit(1 if fails > 0 else 0)
