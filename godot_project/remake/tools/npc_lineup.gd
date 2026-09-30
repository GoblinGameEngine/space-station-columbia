extends SceneTree

## Lineup: a row of generated people under a daylight sun, rendered with the game's own outline
## pass and saved as a PNG -- the main visual check for the character generator.
##   ../godot/godot4 --path . --script res://remake/tools/npc_lineup.gd -- out.png [seed] [count] [first] [pop] [view]
## view: front (default), side, back, three (3/4), face (close-up of the first four), faceside (the same in profile),
##       walk (one person -- `first` -- at `count` phases of the walk cycle, side on; NPC_MOOD=sad...),
##       hands (one person's hands close up, at grips 0, 0.3, 0.6, 1 -- count ignored),
##       stances (one person in each idle stance, three-quarter view),
##       clip (one person -- `first` -- playing the clip named by NPC_CLIP, a figure per moment
##             of it, `count` moments from start to end; NPC_CLIP_VIEW sets the yaw, default -30),
##       anim (one person -- `first` -- walking past in real time; every frame saved as out_NN.png
##             for tools/charref/onion.py to composite: the animator's light table)
## Opens a window briefly; needs the real renderer (not --headless).

var out := "/tmp/npc_lineup.png"
var frames := 0
var walkers: Array = []
var anim_npc: NpcCharacter
var anim_an: NpcAnimator
var anim_frames := 0


func _init() -> void:
	var a := OS.get_cmdline_user_args()
	out = a[0] if a.size() > 0 else out
	var seed := int(a[1]) if a.size() > 1 else 1
	var count := int(a[2]) if a.size() > 2 else 10
	var first := int(a[3]) if a.size() > 3 else 1000
	var pop: String = a[4] if a.size() > 4 else ""
	var view: String = a[5] if a.size() > 5 else "front"
	if view == "face" or view == "faceside":
		count = mini(count, 4)
	if view == "hands":
		count = 4
	if view == "stances":
		count = NpcAnimator.STANCES.size()
	if view == "anim":
		count = 1
	var clip_id := OS.get_environment("NPC_CLIP")
	root.size = Vector2i(1920, 1080)
	for n in ["Hud", "GameMenu", "DialogBox"]:
		var node := root.get_node_or_null(n)
		if node:
			node.queue_free()
	var world := Node3D.new()
	root.add_child(world)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("#9fc4d8")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.5, 0.5, 0.55)
	env.ambient_light_energy = 1.2
	var we := WorldEnvironment.new()
	we.environment = env
	world.add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, -35, 0)
	sun.shadow_enabled = true
	sun.light_energy = 1.7             # the game's full daylight (DaySkySystem), the toon shader's reference
	world.add_child(sun)
	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(60, 20)
	ground.mesh = pm
	var gm := StandardMaterial3D.new()
	gm.albedo_color = Color("#8f9a76")
	ground.material_override = gm
	world.add_child(ground)
	var db := NpcTraits.shared()
	var spacing := 0.75 if not view in ["face", "faceside"] else 0.5
	var labels := []
	var tallest := 0.0
	for i in count:
		var pid := "B%d:%d" % [first + i, i % 3] if not view in ["walk", "hands", "walkfront", "stances", "anim", "clip"] else "B%d:0" % first
		var v := db.person(seed, pid, ["L0", "L1"], pop)
		var npc := NpcCharacter.create(v, pid, seed)
		npc.position = Vector3((i - (count - 1) / 2.0) * spacing, 0, 0)
		npc.rotation_degrees.y = {"front": 0.0, "side": -90.0, "back": 180.0, "three": -35.0, "face": -15.0, "faceside": -75.0, "walk": -90.0, "walkfront": 0.0, "stances": -30.0}.get(view, 0.0)
		world.add_child(npc)
		if view == "anim":
			anim_npc = npc
			anim_an = NpcAnimator.attach(npc)
			anim_an.speed = 1.3
			npc.position = Vector3(1.2, 0, 0)
			npc.rotation_degrees.y = 90.0
		if view == "clip":
			npc.position.x = -npc.position.x         # +x is screen left: time runs left to right
			npc.rotation_degrees.y = float(OS.get_environment("NPC_CLIP_VIEW")) if OS.get_environment("NPC_CLIP_VIEW") != "" else -30.0
			var ca := NpcAnimator.attach(npc)
			ca.manual = true
			walkers.append([ca, -1.0, float(i) / maxf(count - 1, 1)])
			ca.set_meta("clip", clip_id)
		if view == "stances":
			var sa := NpcAnimator.attach(npc)
			sa.manual = true
			sa._stance_pose = NpcAnimator.STANCES.keys()[i]
			walkers.append([sa, 0.0, 0.0])
		if view == "hands":
			npc.position = Vector3((i - 1.5) * 0.35, 0, 0)
			npc.rotation_degrees.y = -90.0
			var ha := NpcAnimator.attach(npc)
			ha.manual = true
			ha.grip = [0.0, 0.3, 0.6, 1.0][i]
			walkers.append([ha, 0.0, 0.0])
		if view == "walk" or view == "walkfront":
			npc.position.x = (i - (count - 1) / 2.0) * 0.6
			var an := NpcAnimator.attach(npc)
			an.manual = true
			an.speed = 1.25
			if OS.get_environment("NPC_MOOD") != "":
				an.set_mood(OS.get_environment("NPC_MOOD"))
			walkers.append([an, float(i) / count, 1.0])
		if OS.get_environment("NPC_DEBUG") != "":
			(npc.body_mesh.mesh.surface_get_material(0) as ShaderMaterial).set_shader_parameter("debug_view", int(OS.get_environment("NPC_DEBUG")))
		tallest = maxf(tallest, float(npc.params.height))
		labels.append("%s %s %d %s %.2fm" % [pid, v.sex[0], v.age, v.occupation, v.height])
	var cam := Camera3D.new()
	world.add_child(cam)
	var width := count * spacing
	cam.fov = 30
	if view == "anim":
		cam.look_at_from_position(Vector3(-0.9, tallest * 0.55, -7.0), Vector3(-0.9, tallest * 0.5, 0))
	elif view == "hands":
		var hy: float = tallest * 0.46
		cam.look_at_from_position(Vector3(0, hy + 0.1, 1.1), Vector3(0, hy, 0))
	elif view == "face" or view == "faceside":
		cam.look_at_from_position(Vector3(0, 1.45, -2.3), Vector3(0, 1.35, 0))
	else:
		# the figures face -Z, so the camera stands at -Z looking back at them
		var dist := maxf(width * 0.5 / tan(deg_to_rad(cam.fov * 0.5 * 16.0 / 9.0)) * 1.05, tallest * 2.2)
		cam.look_at_from_position(Vector3(0, tallest * 0.55, -dist), Vector3(0, tallest * 0.48, 0))
	cam.current = true
	ScreenOutline.attach_to_camera(cam)
	print("\n".join(labels))


func _process(_d: float) -> bool:
	if anim_npc:
		for n in ["Hud", "GameMenu", "DialogBox"]:
			var node := root.get_node_or_null(n)
			if node:
				for c in node.get_children():
					if c is CanvasItem:
						c.visible = false
		# fixed 24 fps steps, the NPC moving at its walking speed (-x: it faces -x after the turn)
		var dt := 1.0 / 24.0
		anim_an._process(dt)
		anim_npc.position.x -= anim_an.speed * dt
		anim_frames += 1
		if anim_frames > 30 and anim_frames <= 30 + 48:
			var img0 := root.get_texture().get_image()
			img0.save_png(out.get_basename() + "_%02d.png" % (anim_frames - 31))
		if anim_frames > 30 + 48:
			print("saved frames")
			quit()
		return false
	frames += 1
	for w in walkers:
		if float(w[1]) < 0.0:
			# a clip moment: played from its start in 24 fps steps to that fraction of its length
			if frames == 1:
				var ca := w[0] as NpcAnimator
				var length := ca.play(str(ca.get_meta("clip")))
				var n := int(round(float(w[2]) * length * 24.0))
				for f in maxi(n, 1):
					ca.pose(0.0, 0.0, f / 24.0, 1.0 / 24.0)
			continue
		(w[0] as NpcAnimator).pose(w[1], w[2], 0.0)
	for n in ["Hud", "GameMenu", "DialogBox"]:          # the game's autoloaded UI
		var node := root.get_node_or_null(n)
		if node and node is CanvasItem:
			(node as CanvasItem).visible = false
		elif node:
			for c in node.get_children():
				if c is CanvasItem:
					c.visible = false
	if frames == 8:
		var img := root.get_texture().get_image()
		img.save_png(out)
		print("saved ", out)
		quit()
	return false
