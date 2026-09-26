extends Node3D

## Lays out catalog buildings on a flat test ground for the acceptance checks
## (remake/tools/checks).  Pass the IDs after `--`:
##   godot4 --path . res://remake/scenes/catalog_test.tscn -- ids=HF-009,HF-011,...  [cols=6] [slope=0.08] [spacing=22] [lod=1..3]
## slope > 0 tilts the ground under each lot (downhill toward the street) to show that foundations
## reach the terrain on a slope.

var SPACING := 22.0


func _ready() -> void:
	var args := {}
	for a in OS.get_cmdline_user_args():
		var kv := a.split("=", true, 1)
		if kv.size() == 2:
			args[kv[0]] = kv[1]
	var ids: PackedStringArray = String(args.get("ids", "")).split(",", false)
	var cols := int(args.get("cols", "6"))
	var slope := float(args.get("slope", "0"))
	var lod := int(args.get("lod", "0"))            # 1..3: load the distance versions (<id>.lodN.glb) instead
	SPACING = float(args.get("spacing", "22"))
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
	var rows := int(ceil(ids.size() / float(max(cols, 1))))
	var grass := StandardMaterial3D.new()
	grass.albedo_color = Color(0.3, 0.42, 0.2)
	for i in ids.size():
		var cx := (i % cols) * SPACING
		var cz := (i / cols) * SPACING
		# ground patch per lot (tilted when slope > 0: high at the back, low at the street)
		var gnd := StaticBody3D.new()
		var mi := MeshInstance3D.new()
		var pm := PlaneMesh.new()
		pm.size = Vector2(SPACING, SPACING)
		mi.mesh = pm
		mi.material_override = grass
		gnd.add_child(mi)
		var cs := CollisionShape3D.new()
		var bs := BoxShape3D.new()
		bs.size = Vector3(SPACING, 0.2, SPACING)
		cs.shape = bs
		cs.position.y = -0.1
		gnd.add_child(cs)
		gnd.position = Vector3(cx, 0, cz)
		gnd.rotation.x = atan(slope)           # the street side (Blender +y = Godot -z) is the low side
		add_child(gnd)
		var b := RemakeBuilding.new()
		b.name = ids[i]
		# on a slope the building sits at the highest ground under its footprint (the back)
		b.position = Vector3(cx, slope * SPACING * 0.3, cz)
		add_child(b)
		var path := "res://remake/buildings/%s.glb" % ids[i]
		if lod > 0:
			path = "res://remake/buildings/%s.lod%d.glb" % [ids[i], lod]
		if not ResourceLoader.exists(path):
			push_warning("missing " + path)
		elif lod > 0:
			var inst: Node = load(path).instantiate()
			b.add_child(inst)
			RemakeBuilding.prepare_lod(inst, path)
		else:
			b.load_building(load(path))
	var safety := StaticBody3D.new()
	var s := CollisionShape3D.new()
	s.shape = WorldBoundaryShape3D.new()
	safety.add_child(s)
	safety.position.y = -20.0
	add_child(safety)
	var player: Node3D = load("res://remake/scenes/test_player.tscn").instantiate()
	player.name = "TestPlayer"
	player.position = Vector3(0, 0.5, 14)
	add_child(player)
	print("CATALOG_TEST loaded %d buildings in %d rows" % [ids.size(), rows])
