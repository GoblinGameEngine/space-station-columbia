extends SceneTree

## Bakes what the station would otherwise build afresh at every launch, into res://remake/baked/
## (BakedMeshes resources, each stamped with the data it was made from; a stale bake is ignored and
## the thing built live).  Rerun after the map, road furniture or placement change:
##   godot4 --headless --path . --script res://remake/tools/bake_world.gd [-- roads structures]
##   roads        MapRoads: every road ribbon, curb and gutter, shoulder, line and marking
##   structures   RemakeLodClusters: the merged LOD2 / LOD3 district meshes, each building's size class
##                (needs the real renderer: run it with a display, not --headless)
##   terrain      MapTerrainMesh: the far tier (T3) of every group
##   trees        MapTrees: every tree's place, size, turn and tint, as MultiMesh buffers
##   walks        CoastalWalks: the boardwalks, piers, docks and breakwaters, and their collision
##   water        MapWater: the creeks, spurs, ponds and oxbows


func _initialize() -> void:
	var what := OS.get_cmdline_user_args()
	var all := what.is_empty()
	if all or what.has("roads"):
		var t0 := Time.get_ticks_msec()
		var r := MapRoads.new()
		var b := r.bake()
		r.free()
		_save(b, MapRoads.BAKED, "roads", t0)
	if all or what.has("terrain"):
		var t0 := Time.get_ticks_msec()
		var tm := MapTerrainMesh.new()
		var b := tm.bake_far()
		tm.free()
		_save(b, MapTerrainMesh.BAKED_FAR, "terrain far tier", t0)
	if all or what.has("trees"):
		var t0 := Time.get_ticks_msec()
		var tr := MapTrees.new()
		var b := tr.bake()
		tr.free()
		_save(b, MapTrees.BAKED, "trees", t0)
	if all or what.has("walks"):
		var t0 := Time.get_ticks_msec()
		var cw := CoastalWalks.new()
		var b := cw.bake()
		cw.free()
		_save(b, CoastalWalks.BAKED, "walks", t0)
	if all or what.has("water"):
		var t0 := Time.get_ticks_msec()
		_save(MapWater.bake_small(), MapWater.BAKED_SMALL, "small water", t0)
	if all or what.has("structures"):
		var t0 := Time.get_ticks_msec()
		var holder := Node3D.new()
		root.add_child(holder)
		var b: BakedMeshes = await RemakeLodClusters.bake(holder, RemakeWorld.entries_for([]))
		holder.queue_free()
		_save(b, RemakeLodClusters.BAKED, "structures", t0)
	quit()


func _save(b: BakedMeshes, path: String, what: String, t0: int) -> void:
	var err := ResourceSaver.save(b, path, ResourceSaver.FLAG_COMPRESS)
	print("BAKED %s: %d meshes in %.1f s -> %s (%s)" % [what, b.meshes.size(), (Time.get_ticks_msec() - t0) / 1000.0,
		path, error_string(err)])
