extends Node3D
class_name RemakeStation

## The remake's station: an O'Neill cylinder (StationGeo -- 500 m radius, 3 km long, central shaft
## 50 m) holding only the map's world (tools/map_preview.py -> remake/user_reference/map_current.png):
##   * the shell -- the two end walls (annuli from the shaft out past the floor) and the central
##     shaft, which the day/night sky system colours (DaySkySystem, surface 1 = the "ceiling");
##   * the map's terrain (MapTerrain / MapTerrainMesh, streamed round the player), its river and
##     lake (MapWater), the end-cap cliffs (CliffWalls);
##   * the map's structures (RemakeWorld: SETTLEMENTS, or everything), with full detail streamed
##     near the player (RemakeDetailStreamer).
## Nothing of the earlier procedural layout.  The player (StationPlayer, radial spin gravity via
## StationGeo.gravity_at) finds this node through the "space_station" group.

const STATION_PLAYER_SCENE := preload("res://scenes/StationPlayer.tscn")
const WALL_TILE := 6.0
const AEROSTAT_BALLOON_Y := 5.47        # the balloon centre above an aerostat's base (aerostat.py: H + 0.62 + BALLOON_R)

static var SETTLEMENTS: Array = []            # [] = the whole map
static var SPAWN_S := 2370.0                  # Harrow Falls, Main Street (the expanded map)
static var SPAWN_X := 783.0

var player: StationPlayer
var sun: DirectionalLight3D
var environment: Environment
var sky_system: DaySkySystem
var npcs: NpcPopulation
var shell_mesh: MeshInstance3D
var terrain: MapTerrainMesh
var world: Node3D
var streamer: RemakeDetailStreamer
var far_side: RemakeFarSide


func _ready() -> void:
	_t_mark = Time.get_ticks_msec()
	print("LOAD ready starts at %d ms after launch" % _t_mark)
	add_to_group("space_station")
	_show_splash()
	_setup_environment()
	_mark("environment")
	_build_shell()
	_mark("shell")
	_spawn_player()
	_mark("player")
	var detail := _neutral_detail("res://assets/textures/grass_tinted.png")
	var floor_mat := MapTerrainMesh.make_material(detail)      # land cover per pixel, the grain over it
	_mark("neutral detail texture")
	terrain = MapTerrainMesh.new()
	terrain.name = "Terrain"
	add_child(terrain)
	far_side = RemakeFarSide.new()
	far_side.name = "FarSide"
	add_child(far_side)
	far_side.setup(player, terrain, detail)
	terrain.setup(player, floor_mat)
	_mark("terrain setup")
	MapWater.build(self)
	_mark("water")
	MapWater.build_small(self)
	_mark("small water")
	var trees := MapTrees.new()
	trees.name = "Trees"
	add_child(trees)
	trees.setup()
	_mark("trees setup")
	var roads := MapRoads.new()
	roads.name = "Roads"
	add_child(roads)
	roads.setup(Vector2(StationGeo.s_of(player.global_position), player.global_position.x))
	_mark("roads setup")
	var furniture := RoadFurniture.new()
	furniture.name = "RoadFurniture"
	add_child(furniture)
	furniture.setup()
	_mark("road furniture setup")
	var walks := CoastalWalks.new()
	walks.name = "Walks"
	add_child(walks)
	walks.setup()
	_mark("walks setup")
	var bridges := GreatBridges.new()
	bridges.name = "GreatBridges"
	add_child(bridges)
	bridges.setup(player.global_position if player else Vector3.INF)
	_mark("great bridges")
	# (no CliffWalls bluff since the seas reach the caps: the mountains rise out of the water -- the user, 2026-10-06)
	var mountains := CapMountains.new()
	mountains.name = "CapMountains"
	add_child(mountains)
	mountains.setup(player)
	_mark("cap mountains setup")
	for c in get_children():
		if c.name.begins_with("map_water_") or c.name.begins_with("map_small_water_"):
			far_side.add_node(c)
	sky_system = DaySkySystem.new()
	sky_system.name = "DaySkySystem"
	add_child(sky_system)
	# the sun is always overhead where the player is (one directional light can't be, everywhere on
	# a cylinder: elsewhere it would shine up through the ground)
	sky_system.sun_frame = func() -> Basis: return StationGeo.basis(StationGeo.s_of(player.global_position))
	sky_system.setup(self, sun, shell_mesh, StationGeo.R - StationGeo.SHAFT_R, WALL_TILE, environment)
	_mark("sky")
	var clouds := RemakeClouds.new()
	clouds.name = "Clouds"
	add_child(clouds)
	clouds.setup(player.get_node("Head/Camera3D"), environment, sky_system)
	var rain := RemakeRain.new()
	rain.name = "Rain"
	add_child(rain)
	rain.setup(player.get_node("Head/Camera3D"), clouds)
	var water_amb := WaterAmbience.new()
	water_amb.name = "WaterAmbience"
	add_child(water_amb)
	water_amb.setup(player.get_node("Head/Camera3D"))
	_mark("clouds setup")
	world = Node3D.new()
	world.name = "World"
	add_child(world)
	streamer = RemakeDetailStreamer.new()
	streamer.name = "DetailStreamer"
	add_child(streamer)
	_place_structures()
	_mark("structures (first slice)")
	_place_aerostats()
	_mark("aerostats (first slice)")
	_place_ground_vehicles()
	_mark("ground vehicles (first slice)")
	_place_bicycles()
	_mark("bicycles")
	# the people: generated round the player as they go, never stored (remake/characters/)
	npcs = NpcPopulation.new()
	npcs.player = player
	add_child(npcs)
	_mark("people")
	transit = TransitSystem.new()
	transit.player = player
	add_child(transit)
	_mark("transit")
	traffic = NpcTraffic.new()
	traffic.player = player
	add_child(traffic)
	_mark("traffic")
	var grav := StationGravity.new()
	grav.player = player
	add_child(grav)
	var signs := SignPhysics.new()
	signs.name = "SignPhysics"
	signs.player = player
	signs.furniture = furniture
	add_child(signs)
	_watch_load()


var _t_mark := 0
var _aero_done := false


func _mark(label: String) -> void:
	## The load timeline: each startup step's cost (printed; see _watch_load for the rest).
	var now := Time.get_ticks_msec()
	print("LOAD %-24s %6d ms   (t=%d)" % [label, now - _t_mark, now])
	_t_mark = now


func _watch_load() -> void:
	## When each piece built over later frames is done, and the worst frame meanwhile.
	var t0 := Time.get_ticks_msec()
	var waiting := {
		"terrain (all tiers)": func() -> bool: return terrain._far_todo.is_empty() and not terrain.busy(),
		"trees": func() -> bool: return (get_node("Trees") as MapTrees).loaded(),
		"roads": func() -> bool: return not get_node("Roads").is_processing(),
		"walks": func() -> bool: return not get_node("Walks").is_processing(),
		"mountains": func() -> bool: return (get_node("CapMountains") as CapMountains).loaded(),
		"cloud skins": func() -> bool: return (get_node("Clouds") as RemakeClouds)._skin_task == -1,
		"structures": func() -> bool: return streamer.records.size() > 0,
		"aerostats": func() -> bool: return _aero_done,
		"ground vehicles": func() -> bool: return _cars_done,
	}
	var worst := 0.0
	var frames := 0
	var total := waiting.size()
	while not waiting.is_empty():
		if _splash:
			_splash_bar.value = 1.0 - waiting.size() / float(total)
			# the splash stays up until the world is all in (the builders work flat out meanwhile, the 3D
			# view off), or LOADING_MAX_MS at the most
			if Time.get_ticks_msec() - t0 > LOADING_MAX_MS:
				_hide_splash()
		await get_tree().process_frame
		frames += 1
		worst = maxf(worst, get_process_delta_time())
		for k in waiting.keys():
			if waiting[k].call():
				print("LOAD %-24s done at t=%d  (%d ms after ready)" % [k, Time.get_ticks_msec(), Time.get_ticks_msec() - t0])
				waiting.erase(k)
	_hide_splash()
	print("LOAD complete: %d frames, worst frame %.0f ms, t=%d" % [frames, worst * 1000.0, Time.get_ticks_msec()])


var _splash: CanvasLayer
const LOADING_MAX_MS := 90000
var _splash_bar: ProgressBar


func _show_splash() -> void:
	StationGeo.loading = true
	get_viewport().disable_3d = true            # nothing to see behind the splash: let the GPU rest
	## A placeholder splash (ui/pda/splash.png -- also the engine's boot splash) held over the start of
	## the load, with a progress bar.
	_splash = CanvasLayer.new()
	_splash.layer = 100
	var bg := ColorRect.new()
	bg.color = Color(0.0157, 0.0235, 0.047)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_splash.add_child(bg)
	var img := TextureRect.new()
	img.texture = load("res://ui/pda/splash.png")
	img.set_anchors_preset(Control.PRESET_FULL_RECT)
	img.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	img.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_splash.add_child(img)
	_splash_bar = ProgressBar.new()
	_splash_bar.max_value = 1.0
	_splash_bar.show_percentage = false
	_splash_bar.anchor_left = 0.3
	_splash_bar.anchor_right = 0.7
	_splash_bar.anchor_top = 0.9
	_splash_bar.anchor_bottom = 0.9
	_splash_bar.offset_bottom = 6
	var fill := StyleBoxFlat.new()
	fill.bg_color = Color(0.6, 0.72, 0.9)
	var back := StyleBoxFlat.new()
	back.bg_color = Color(0.12, 0.14, 0.2)
	_splash_bar.add_theme_stylebox_override("fill", fill)
	_splash_bar.add_theme_stylebox_override("background", back)
	_splash.add_child(_splash_bar)
	add_child(_splash)


func _hide_splash() -> void:
	StationGeo.loading = false
	get_viewport().disable_3d = false
	if _splash == null:
		return
	var s := _splash
	_splash = null
	var tw := create_tween()
	tw.set_pause_mode(Tween.TWEEN_PAUSE_PROCESS)       # finishes even if the Communicator pauses the game
	for c in s.get_children():
		tw.parallel().tween_property(c, "modulate:a", 0.0, 0.6)
	tw.tween_callback(s.queue_free)


func _place_ground_vehicles() -> void:
	## The pods and vans, parked where remake/tools/place_ground_vehicles.gd put them
	## (remake/groundcars.json): kerbside in every town, a van at every farm without an aerostat.
	## Records only; a VehicleStreamer builds the ones near the player.
	if not FileAccess.file_exists("res://remake/groundcars.json"):
		_cars_done = true
		return
	var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://remake/groundcars.json"))
	var root := VehicleStreamer.new()
	root.name = "GroundVehicles"
	root.player = player
	add_child(root)
	for a in d.groundcars:
		var s: float = a.s
		var x: float = a.x
		var mk := (func(): return RemakeVan.new()) if a.kind == "van" else ((func(): return RemakeWagon.new()) if a.kind == "wagon" else (func(): return RemakePod.new()))
		root.add(str(a.id), mk, Transform3D(StationGeo.basis(s, a.yaw), StationGeo.point(s, x, MapTerrain.elevation(s, x))))
	root.build_near(player.global_position)
	print("RemakeStation: %d ground vehicles parked (%d built near the player)" % [d.groundcars.size(), root.live_count()])
	_cars_done = true


var _cars_done := false
var transit: TransitSystem
var traffic: NpcTraffic


func _place_bicycles() -> void:
	## Bicycles leaning by the front doors of the homes where someone keeps one (NpcLife's residents:
	## about a third of people from 10 to 75 own a bike; one parked bike per such home, two homes in
	## three), along the facade beside the door. Every one can be ridden (RemakeBicycle).
	if not FileAccess.file_exists(NpcLife.PATH):
		return
	var life := NpcLife.shared()
	var st: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://remake/placement.json"))
	var by_id := {}
	for b in st.structures:
		by_id[b.id] = b
	var root := VehicleStreamer.new()
	root.name = "Bicycles"
	root.player = player
	root.near = 120.0
	root.far = 160.0
	add_child(root)
	var n := 0
	var t0 := Time.get_ticks_usec()
	for home in life.by_home:
		var owner := false
		for pid in life.by_home[home]:
			var P: Dictionary = life.person(pid)
			if int(P.age) >= 10 and int(P.age) <= 75 and NpcRng.for_trait(life.seed, pid, "owns_bike").rand() < 0.35:
				owner = true
				break
		if not owner or NpcRng.for_trait(life.seed, str(home), "bike_parked").rand() > 0.66:
			continue
		var b: Dictionary = by_id.get(str(home).split("/")[0], {})
		if b.is_empty():
			continue
		var door := NpcHouseholds.door(b)
		var yaw: float = b.yaw
		var front := Vector2(cos(yaw), -sin(yaw))
		var right := Vector2(sin(yaw), cos(yaw))
		var side := 1.0 if NpcRng.for_trait(life.seed, str(home), "bike_side").rand() < 0.5 else -1.0
		var p := door + right * side * 1.3 - front * 0.45
		# parallel to the facade, leaning on its kickstand
		var heading := atan2(-right.y * side, right.x * side)
		root.add("Bike_%s" % str(home).replace("/", "_"), func(): return RemakeBicycle.new(),
			Transform3D(StationGeo.basis(p.x, heading), StationGeo.point(p.x, p.y, MapTerrain.elevation(p.x, p.y))))
		n += 1
		if Time.get_ticks_usec() - t0 > 4000:
			await get_tree().process_frame
			t0 = Time.get_ticks_usec()
	root.build_near(player.global_position)
	print("RemakeStation: %d bicycles parked (%d built near the player)" % [n, root.live_count()])


func _place_aerostats() -> void:
	## The aerostats, where remake/tools/place_aerostats.gd parked them (remake/aerostats.json):
	## some in every town by its size, one at every other farmstead. Records; built within 700 m of
	## the player, and further off (across the ring, overhead) only their balloons, as impostors.
	var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://remake/aerostats.json"))
	var root := VehicleStreamer.new()
	root.name = "Aerostats"
	root.player = player
	root.near = 700.0
	root.far = 800.0
	root.slice = 20
	var bal := SphereMesh.new()
	bal.radius = 2.4
	bal.height = 4.8
	bal.radial_segments = 16
	bal.rings = 8
	var fab := StandardMaterial3D.new()
	fab.albedo_color = Color(0.93, 0.92, 0.88)
	fab.roughness = 0.8
	bal.material = fab
	root.impostor = bal
	root.impostor_lift = Vector3(0, AEROSTAT_BALLOON_Y, 0)
	add_child(root)
	for a in d.aerostats:
		var s: float = a.s
		var x: float = a.x
		root.add(str(a.id), func(): return RemakeAerostat.new(), Transform3D(StationGeo.basis(s, a.yaw), StationGeo.point(s, x, MapTerrain.elevation(s, x))))
	root.build_near(player.global_position)
	print("RemakeStation: %d aerostats parked (%d built near the player)" % [d.aerostats.size(), root.live_count()])
	_aero_done = true


func compass_bearing(at: Vector3, dir: Vector3) -> float:
	## The compass heading (degrees clockwise from north) of dir at a point on the floor, for the
	## HUD.  North is the Marlowe end cap (-x), south the Kessler end; east and west run round
	## the ring -- east is +s, to your right as you face north with the axis overhead.
	var east := StationGeo.forward(StationGeo.s_of(at))
	return rad_to_deg(atan2(dir.dot(east), dir.dot(Vector3.LEFT)))


static func _neutral_detail(path: String) -> ImageTexture:
	## A texture's grain without its colour: greyscale, scaled so its mean is 1 -- the vertex colour
	## is then the colour you see.
	var img: Image = (load(path) as Texture2D).get_image()
	img.decompress()
	img.convert(Image.FORMAT_RGB8)
	var total := 0.0
	var n := 0
	for y in range(0, img.get_height(), 4):
		for x in range(0, img.get_width(), 4):
			total += img.get_pixel(x, y).get_luminance()
			n += 1
	var mean := maxf(0.05, total / n)
	for y in img.get_height():
		for x in img.get_width():
			var l := clampf(img.get_pixel(x, y).get_luminance() / mean, 0.0, 1.0)
			img.set_pixel(x, y, Color(l, l, l))
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)


func _place_structures() -> void:
	## Not awaited: the structures fill in a building per frame while the game runs.
	var info: Dictionary = await RemakeWorld.build(world, SETTLEMENTS)
	streamer.setup(player, info.records)
	# the far side draws them flat (RemakeFarSide): every merged district mesh and ordinary
	# building, the trees and roads -- not the landmarks
	var landmarks := {}
	for r in info.records:
		if r.landmark:
			landmarks[r.root] = true
	far_side.add_children_of(world, func(n: Node) -> bool: return landmarks.has(n))
	while not (get_node("Trees") as MapTrees).loaded() or get_node("Roads").is_processing() or get_node("Walks").is_processing():
		await get_tree().process_frame
	far_side.add_children_of(get_node("Trees"))
	far_side.add_children_of(get_node("Roads"))
	far_side.add_children_of(get_node("Walks"), func(n: Node) -> bool: return n is StaticBody3D)
	info.erase("records")
	print("RemakeStation: placed ", info)


func _setup_environment() -> void:
	environment = Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.01, 0.01, 0.02)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.5, 0.5, 0.55)
	environment.ambient_light_energy = 1.2
	var world_env := WorldEnvironment.new()
	world_env.environment = environment
	add_child(world_env)
	sun = DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-35, 40, 0)
	sun.light_energy = 1.3
	sun.light_color = Color(1.0, 0.98, 0.92)
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS   # 4 splits drew every caster twice more
	add_child(sun)


func _build_shell() -> void:
	## End walls (surface 0) and the central shaft with the caps' sky discs (surface 1, the sky system's "ceiling").
	## The caps (the user, 2026-10-05: "a mountain range running up 1.5 km, then sky blue filling the centre ... like a
	## curved canyon"; 2026-10-06: "start below the water ... a moving cloud texture ... the clouds will circle the
	## axis"): the mountains (CapMountains) rise from under the seas and recede to the cap proper, pushed out by
	## CapMountains.DEPTH, where a rock backing ring hides behind them; the sky disc fills the centre round the shaft
	## (cap_sky.gdshader: the sky's colour, clouds circling the axis). The wall the seas end at stays as collision only.
	var n := 256
	var walls := SurfaceTool.new()
	walls.begin(Mesh.PRIMITIVE_TRIANGLES)
	var shaft := SurfaceTool.new()
	shaft.begin(Mesh.PRIMITIVE_TRIANGLES)
	var sky := SurfaceTool.new()
	sky.begin(Mesh.PRIMITIVE_TRIANGLES)
	var strip := SurfaceTool.new()                     # (collision only: the wall the seas end at, behind the rock)
	strip.begin(Mesh.PRIMITIVE_TRIANGLES)
	var r_in := StationGeo.SHAFT_R
	var r_out := StationGeo.R + 30.0                   # past the floor, under the terrain's lowest point
	var x_cap := StationGeo.HALF_LEN + CapMountains.DEPTH
	var r_sky := StationGeo.R - 1300.0                 # (under the lowest saddle of the crest: the disc's rim is hidden)
	var rings := [[StationGeo.HALF_LEN, StationGeo.R - 146.0, r_out, strip],   # the wall the seas end at (not drawn)
		[x_cap, r_sky - 20.0, StationGeo.R + 60.0, walls],                      # the backing behind the mountains
		[x_cap, r_in, r_sky, sky]]                                              # the sky
	for end in [-1.0, 1.0]:
		for ring in rings:
			var x: float = end * float(ring[0])
			var ra: float = ring[1]
			var rb: float = ring[2]
			var stl: SurfaceTool = ring[3]
			for i in n:
				var a0 := TAU * i / n
				var a1 := TAU * (i + 1) / n
				var q := [Vector3(x, ra * cos(a0), ra * sin(a0)), Vector3(x, rb * cos(a0), rb * sin(a0)),
					Vector3(x, rb * cos(a1), rb * sin(a1)), Vector3(x, ra * cos(a1), ra * sin(a1))]
				var order := [0, 1, 2, 0, 2, 3] if end > 0.0 else [0, 2, 1, 0, 3, 2]
				for k in order:
					var v: Vector3 = q[k]
					stl.set_normal(Vector3(-end, 0, 0))
					stl.set_uv(Vector2(v.y / WALL_TILE, v.z / WALL_TILE))
					stl.add_vertex(v)
	var wall_mat := StandardMaterial3D.new()          # (only the backing ring behind the mountains now: dark rock)
	wall_mat.albedo_color = Color(0.32, 0.29, 0.26)
	wall_mat.roughness = 1.0
	walls.set_material(wall_mat)
	for i in n:
		var a0 := TAU * i / n
		var a1 := TAU * (i + 1) / n
		var q := [Vector3(-x_cap, r_in * cos(a0), r_in * sin(a0)), Vector3(x_cap, r_in * cos(a0), r_in * sin(a0)),
			Vector3(x_cap, r_in * cos(a1), r_in * sin(a1)), Vector3(-x_cap, r_in * cos(a1), r_in * sin(a1))]
		for k in [0, 2, 1, 0, 3, 2]:
			var v: Vector3 = q[k]
			shaft.set_normal(Vector3(0, v.y, v.z).normalized())       # facing out, toward the floor
			shaft.set_uv(Vector2(v.x / WALL_TILE, TAU * r_in * (i + (1 if k in [1, 2] else 0)) / n / WALL_TILE))
			shaft.add_vertex(v)
	shaft.set_material(StandardMaterial3D.new())
	var sky_mat := ShaderMaterial.new()                # (moving clouds round the axis, in the sky's colour)
	sky_mat.shader = load("res://remake/shaders/cap_sky.gdshader")
	sky.set_material(sky_mat)
	var mesh := ArrayMesh.new()
	walls.commit(mesh)
	shaft.commit(mesh)
	sky.commit(mesh)
	var strip_mesh := strip.commit()
	shell_mesh = MeshInstance3D.new()
	shell_mesh.name = "Shell"
	shell_mesh.mesh = mesh
	var body := StaticBody3D.new()
	body.name = "RingBody"                # the HUD compass reads the station frame from this node
	add_child(body)
	body.add_child(shell_mesh)
	var cs := CollisionShape3D.new()
	var shape := mesh.create_trimesh_shape()
	shape.backface_collision = true
	cs.shape = shape
	body.add_child(cs)
	var cs2 := CollisionShape3D.new()
	var shape2 := strip_mesh.create_trimesh_shape()
	shape2.backface_collision = true
	cs2.shape = shape2
	body.add_child(cs2)


func _spawn_player() -> void:
	## On the ground at (SPAWN_S, SPAWN_X), facing along the ring.  The transform is set before
	## add_child(): StationPlayer._ready() records it as the respawn point.
	var h := MapTerrain.elevation(SPAWN_S, SPAWN_X)
	var up := StationGeo.up(SPAWN_S)
	var feet := StationGeo.point(SPAWN_S, SPAWN_X, h + 0.05)
	player = STATION_PLAYER_SCENE.instantiate() as StationPlayer
	player.global_transform = Transform3D(Basis.looking_at(StationGeo.forward(SPAWN_S), up), feet + up * 1.43)
	add_child(player)
	# see the whole cylinder: straight across (the far side, 2R overhead) and end cap to end cap --
	# Godot's default 4 km far plane cut the view off into black on the 3 km ring
	player.camera.far = 2.0 * StationGeo.R + StationGeo.LENGTH + 2.0 * CapMountains.DEPTH
	ScreenOutline.attach_to_camera(player.camera)
