extends Node3D

## The Pruett vertical slice: the site (ground, streets, track, signs) plus the ten structures
## and three crossings placed on the lot plan from remake/blender/buildings/P_SITE.py (LOTS).
## Blender (x east, y north, yaw CCW) -> Godot (x, 0, -y), rotation.y = yaw.

const LOTS := {
	"P-SITE": [0.0, 0.0, 0.0],
	"P-TAVERN": [-30.0, 17.0, 180.0], "P-CHURCH": [-2.0, 18.6, 0.0], "P-STORE": [22.0, 18.0, 180.0],
	"P-PO": [-40.0, -19.3, 0.0], "P-DEPOT": [8.0, -59.2, 0.0], "P-ELEV": [58.0, -45.0, 0.0],
	"P-HOUSE1": [72.0, 26.0, 180.0], "P-HOUSE4": [-80.0, 22.0, 180.0], "P-HOUSE2": [-35.2, 55.0, -90.0],
	"P-HOUSE3": [28.0, -35.0, -90.0], "P-BR-US30": [-230.0, 0.0, -90.0], "P-CULVERT": [210.0, 0.0, -90.0],
	"P-BR-RAIL": [-230.0, -130.0, -90.0],
}

var loaded := {}


func _ready() -> void:
	for ui in ["Hud", "GameMenu"]:
		var n := get_node_or_null("/root/" + ui)
		if n and "visible" in n:
			n.visible = false
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	sky.sky_material = ProceduralSkyMaterial.new()
	e.sky = sky
	e.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.environment = e
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 35, 0)
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 150.0
	add_child(sun)
	# safety floor far below (the site glb carries the real ground collision)
	var safety := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	cs.shape = WorldBoundaryShape3D.new()
	safety.add_child(cs)
	safety.position.y = -10.0
	add_child(safety)
	for id in LOTS:
		var l: Array = LOTS[id]
		var b := RemakeBuilding.new()
		b.name = id
		b.position = Vector3(l[0], 0.0, -l[1])
		b.rotation.y = deg_to_rad(l[2])
		add_child(b)
		b.load_building(load("res://remake/buildings/%s.glb" % id))
		loaded[id] = b
	var player: Node3D = load("res://remake/scenes/test_player.tscn").instantiate()
	player.name = "TestPlayer"
	player.position = Vector3(-10, 0.3, -2)
	player.rotation.y = deg_to_rad(90)
	add_child(player)
