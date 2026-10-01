extends SceneTree

## Riding poses: people on bicycles (side on, at several crank angles), a seated rider and a
## standing strap-hanger (transit), rendered with the game's outline pass.
##   ../godot/godot4 --path . --script res://remake/tools/npc_ride_test.gd -- out.png [first_pid] [close]
## Opens a window briefly (the real renderer).

var out := "/tmp/npc_ride.png"
var frames := 0
var items: Array = []        # [npc, animator, bike or null, ride dict or null]


func _init() -> void:
	var a := OS.get_cmdline_user_args()
	out = a[0] if a.size() > 0 else out
	var first := int(a[1]) if a.size() > 1 else 2000
	root.size = Vector2i(1920, 1080)
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
	sun.light_energy = 1.7
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
	for i in 4:
		var pid := "B%d:0" % (first + i)
		var v := db.person(1, pid, ["L0", "L1"], "", {"age": [16, 30, 45, 66][i]})
		var npc := NpcCharacter.create(v, pid, 1)
		world.add_child(npc)
		var an := NpcAnimator.attach(npc)
		an.manual = true
		var bike := NpcBike.make()
		world.add_child(bike)
		bike.position = Vector3((i - 2.0) * 1.9 + 0.9, 0, 0)
		bike.rotation_degrees.y = -90.0
		bike.crank = i * PI / 2.0
		items.append([npc, an, bike, null])
	# a seated rider (a bench seat 0.45 m high) and a strap-hanger
	for j in 2:
		var pid2 := "B%d:1" % (first + 10 + j)
		var v2 := db.person(1, pid2, ["L0", "L1"], "", {"age": 40})
		var npc2 := NpcCharacter.create(v2, pid2, 1)
		world.add_child(npc2)
		npc2.position = Vector3(-6.2 - j * 1.2, 0, 0)
		npc2.rotation_degrees.y = -90.0
		var an2 := NpcAnimator.attach(npc2)
		an2.manual = true
		var ride: Dictionary
		if j == 0:
			var seat := MeshInstance3D.new()
			var bm := BoxMesh.new()
			bm.size = Vector3(0.5, 0.06, 0.45)
			seat.mesh = bm
			seat.position = npc2.position + Vector3(0, 0.42, 0)
			world.add_child(seat)
			ride = NpcRide.seated(npc2, 0.45)
		else:
			ride = NpcRide.strap(npc2, Vector3(0.18, 1.95, -0.05))
		items.append([npc2, an2, null, ride])
	var cam := Camera3D.new()
	world.add_child(cam)
	cam.fov = 30
	if a.size() > 2 and a[2] == "close":
		cam.look_at_from_position(Vector3(-2.0, 1.2, -4.2), Vector3(-1.9, 0.75, 0))
	else:
		cam.look_at_from_position(Vector3(-1.6, 0.95, -15.0), Vector3(-1.6, 0.85, 0))
	cam.current = true
	ScreenOutline.attach_to_camera(cam)


func _process(_d: float) -> bool:
	frames += 1
	for it in items:
		var npc: NpcCharacter = it[0]
		var an: NpcAnimator = it[1]
		if it[2]:
			var bike: NpcBike = it[2]
			bike.update(0.0, 0.0, 0.0)
			npc.global_transform = bike.rider_frame()
			an.ride = bike.rider_pose()
		else:
			an.ride = it[3]
		an.pose(0.0, 0.0, frames / 24.0, 1.0 / 24.0)
	for n in ["Hud", "GameMenu", "DialogBox"]:
		var node := root.get_node_or_null(n)
		if node and node is CanvasItem:
			(node as CanvasItem).visible = false
		elif node:
			for c in node.get_children():
				if c is CanvasItem:
					c.visible = false
	if frames == 30:
		root.get_texture().get_image().save_png(out)
		print("saved ", out)
		quit()
	return false
