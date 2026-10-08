extends Node3D

## Bakes the far side: the finished world seen straight down, unshaded (its surface colours only --
## the station lights it at runtime), at StationGeo.FARSIDE_M (4) m / px over the whole floor, cut into one
## small image per terrain far tile (remake/farside/f_SS_XX.webp, StationGeo.farside_px of
## MapTerrainMesh.far_rect: ~400 x 600 px each, so any GPU takes them -- the 20 km ring whole is 15,708 px wide).
## Builds the world like RemakeStation (terrain, water, roads, trees, structures), then renders
## TILE_M m x TILE_M m shots through an orthographic camera 250 m up, moving the terrain's streaming
## probe to each first (its 8 m tier: the 2 m one is off -- nothing it adds shows at 4 m / px).  Run:
##   godot4 --path . res://remake/scenes/FarsideBake.tscn          (a window; an hour or two)

const TILE := 128                    # px per shot
const TILE_M := 512.0                # m per shot (4 m / px)
var TILES_S := ceili(StationGeo.CIRC / TILE_M)       # (the last runs past the seam: it wraps)
var TILES_X := ceili(StationGeo.LENGTH / TILE_M)
const CAM_H := 250.0
const COLS := "user://farside_cols"
const IMPORT := """[remap]

importer="texture"
type="CompressedTexture2D"

[params]

compress/mode=2
compress/high_quality=false
mipmaps/generate=true
mipmaps/limit=-1
"""

var probe: Node3D
var terrain: MapTerrainMesh
var world: Node3D


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.3, 0.3, 0.3)
	add_child(env)
	probe = Node3D.new()
	add_child(probe)
	probe.global_position = StationGeo.point(0.0, 0.0, 0.0)
	var floor_mat := MapTerrainMesh.make_material(RemakeStation._neutral_detail("res://assets/textures/grass_tinted.png"))
	terrain = MapTerrainMesh.new()
	terrain.near_tier = false
	add_child(terrain)
	terrain.setup(probe, floor_mat)
	MapWater.build(self)
	MapWater.build_small(self)
	var roads := MapRoads.new()
	add_child(roads)
	roads.target = probe                                   # (streamed round the probe: the whole ring's don't fit)
	roads.fine_everywhere = true                           # (the bands' kerbs, walks and paint whole, not only near it)
	roads.setup()
	var trees := MapTrees.new()
	trees.target = probe
	add_child(trees)
	trees.setup()
	var walks := CoastalWalks.new()
	add_child(walks)
	walks.setup()
	var bridges := GreatBridges.new()
	add_child(bridges)
	bridges.setup()
	world = Node3D.new()
	add_child(world)
	_bake(roads, trees, walks)


var streamer: RemakeDetailStreamer


func _bake(roads: MapRoads, trees: MapTrees, walks: CoastalWalks) -> void:
	var tree := get_tree()
	var info: Dictionary = await RemakeWorld.build(world, [])
	# the merged district cells and the buildings' LOD1s come a band at a time round the probe, as round the player
	streamer = RemakeDetailStreamer.new()
	streamer.parent_node = world
	streamer.bake_mode = true
	add_child(streamer)
	streamer.setup(probe, info.records, info.get("cells", {}))
	while (roads._streaming and not roads.near_done) or (not roads._streaming and roads.is_processing()) or not trees.loaded() \
			or walks.is_processing():
		await tree.process_frame
	var vp := SubViewport.new()
	vp.size = Vector2i(TILE, TILE)
	vp.debug_draw = Viewport.DEBUG_DRAW_UNSHADED
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(vp)
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = TILE_M
	cam.near = 1.0
	cam.far = CAM_H + 80.0
	vp.add_child(cam)
	var img := Image.create(TILES_S * TILE, TILES_X * TILE, false, Image.FORMAT_RGB8)
	var t0 := Time.get_ticks_msec()
	# each finished column is kept (user://farside_cols/), so an interrupted bake resumes where it stopped
	DirAccess.make_dir_recursive_absolute(COLS)
	for ts in TILES_S:
		var col_path := COLS + "/col_%02d.png" % ts
		if FileAccess.file_exists(col_path):
			img.blit_rect(Image.load_from_file(col_path), Rect2i(0, 0, TILE, TILES_X * TILE), Vector2i(ts * TILE, 0))
			continue
		for tx in TILES_X:
			var s := (ts + 0.5) * TILE_M
			var x := -StationGeo.HALF_LEN + (tx + 0.5) * TILE_M
			# the ground under the tile at full detail first
			probe.global_position = StationGeo.point(s, x, 0.0)
			terrain._update()
			while terrain.busy():
				await tree.process_frame
			# and the streamed roads and buildings round it (by s: only a new column brings new bands)
			if tx == 0:
				for f in 2:
					await tree.create_timer(0.6).timeout
				while roads.bands_busy() or streamer.bands_pending() or trees.busy():
					await tree.process_frame
			# straight down: screen right = +s, screen up = -x, looking along -up
			var up := StationGeo.up(s)
			var b := Basis(StationGeo.forward(s), -Vector3.RIGHT, up)
			cam.global_transform = Transform3D(b, StationGeo.point(s, x, CAM_H))
			for f in 3:
				await RenderingServer.frame_post_draw
			var tile := vp.get_texture().get_image()
			tile.convert(Image.FORMAT_RGB8)
			img.blit_rect(tile, Rect2i(0, 0, TILE, TILE), Vector2i(ts * TILE, tx * TILE))
		img.get_region(Rect2i(ts * TILE, 0, TILE, TILES_X * TILE)).save_png(col_path)
		print("farside bake: column %d/%d  %.0f s" % [ts + 1, TILES_S, (Time.get_ticks_msec() - t0) / 1000.0])
	# one image per far tile
	DirAccess.make_dir_recursive_absolute(StationGeo.FARSIDE_DIR)
	var n := 0
	for key in terrain.all_far():
		var px := StationGeo.farside_px(terrain.far_rect(key)).intersection(Rect2i(Vector2i.ZERO, img.get_size()))
		var path := StationGeo.farside_path(key)
		img.get_region(px).save_webp(ProjectSettings.globalize_path(path), true, 0.9)
		if not FileAccess.file_exists(path + ".import"):
			var f := FileAccess.open(path + ".import", FileAccess.WRITE)
			f.store_string(IMPORT)
			f.close()
		n += 1
	print("FARSIDE_BAKED ", n, " tiles in ", StationGeo.FARSIDE_DIR, " from ", img.get_size())
	for f in DirAccess.get_files_at(COLS):
		DirAccess.remove_absolute(COLS + "/" + f)
	get_tree().quit()
