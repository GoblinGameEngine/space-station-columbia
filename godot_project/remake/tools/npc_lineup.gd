extends SceneTree

## Lineup: a row of generated people under a daylight sun, rendered with the game's own outline
## pass and saved as a PNG -- the main visual check for the character generator.
##   ../godot/godot4 --path . --script res://remake/tools/npc_lineup.gd -- out.png [seed] [count] [first] [pop] [view]
## view: front (default), side, back, three (3/4), face (close-up of the first four)
## Opens a window briefly; needs the real renderer (not --headless).

var out := "/tmp/npc_lineup.png"
var frames := 0


func _init() -> void:
	var a := OS.get_cmdline_user_args()
	out = a[0] if a.size() > 0 else out
	var seed := int(a[1]) if a.size() > 1 else 1
	var count := int(a[2]) if a.size() > 2 else 10
	var first := int(a[3]) if a.size() > 3 else 1000
	var pop: String = a[4] if a.size() > 4 else ""
	var view: String = a[5] if a.size() > 5 else "front"
	if view == "face":
		count = mini(count, 4)
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
	var spacing := 0.75 if view != "face" else 0.5
	var labels := []
	var tallest := 0.0
	for i in count:
		var pid := "B%d:%d" % [first + i, i % 3]
		var v := db.person(seed, pid, ["L0", "L1"], pop)
		var npc := NpcCharacter.create(v, pid)
		npc.position = Vector3((i - (count - 1) / 2.0) * spacing, 0, 0)
		npc.rotation_degrees.y = {"front": 0.0, "side": -90.0, "back": 180.0, "three": -35.0, "face": -15.0}.get(view, 0.0)
		world.add_child(npc)
		if OS.get_environment("NPC_DEBUG") != "":
			(npc.body_mesh.mesh.surface_get_material(0) as ShaderMaterial).set_shader_parameter("debug_view", int(OS.get_environment("NPC_DEBUG")))
		tallest = maxf(tallest, float(npc.params.height))
		labels.append("%s %s %d %s %.2fm" % [pid, v.sex[0], v.age, v.occupation, v.height])
	var cam := Camera3D.new()
	world.add_child(cam)
	var width := count * spacing
	cam.fov = 30
	if view == "face":
		cam.look_at_from_position(Vector3(0, 1.45, -2.3), Vector3(0, 1.35, 0))
	else:
		# the figures face -Z, so the camera stands at -Z looking back at them
		var dist := maxf(width * 0.5 / tan(deg_to_rad(cam.fov * 0.5 * 16.0 / 9.0)) * 1.05, tallest * 2.2)
		cam.look_at_from_position(Vector3(0, tallest * 0.55, -dist), Vector3(0, tallest * 0.48, 0))
	cam.current = true
	ScreenOutline.attach_to_camera(cam)
	print("\n".join(labels))


func _process(_d: float) -> bool:
	frames += 1
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
