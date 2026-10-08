extends SceneTree

## Bakes what the station would otherwise build afresh at every launch, into res://remake/baked/
## (BakedMeshes resources, each stamped with the data it was made from; a stale bake is ignored and
## the thing built live).  Rerun after the map, road furniture or placement change:
##   godot4 --headless --path . --script res://remake/tools/bake_world.gd [-- roads structures]
##   roads        MapRoads: every road ribbon, curb and gutter, shoulder, line and marking
##   structures   RemakeLodClusters: the merged LOD2 / LOD3 district meshes, each building's size class
##                (needs the real renderer: run it with a display, not --headless)
##   pads         MapTerrain: every structure's pad height and blend (a minute at every launch, worked out live)
##   terrain      MapTerrainMesh: the far tier (T3) of every group
##   trees        MapTrees: every tree's place, size, turn and tint, as MultiMesh buffers
##   walks        CoastalWalks: the boardwalks, piers, docks and breakwaters, and their collision
##   water        MapWater: the creeks, spurs, ponds and oxbows


func _initialize() -> void:
	var what := OS.get_cmdline_user_args()
	var all := what.is_empty()
	if all or what.has("roads"):
		# a file per band of the ring (MapRoads streams them round the player)
		var r := MapRoads.new()
		for k in MapRoads.BAND_N:
			var t0 := Time.get_ticks_msec()
			var b := r.bake_band(k)
			_save(b, MapRoads.band_path(k), "roads band %d" % k, t0)
		r.free()
		var i := 0                                             # (the single file the whole ring's roads were)
		while true:
			var old := MapRoads.BAKED if i == 0 else BakedMeshes.part_path(MapRoads.BAKED, i)
			if not FileAccess.file_exists(old):
				break
			DirAccess.remove_absolute(ProjectSettings.globalize_path(old))
			i += 1
	if all or what.has("pads"):
		var t0 := Time.get_ticks_msec()
		var n := MapTerrain.bake_pads()
		print("BAKED pads: %d in %.1f s -> %s" % [n, (Time.get_ticks_msec() - t0) / 1000.0, MapTerrain.PADS_BAKED])
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
		# the size classes in the one file, the merged cells a band of the ring each (RemakeDetailStreamer streams them)
		var bands := {}
		for i in b.keys.size():
			var k := RemakeLodClusters.band_of_key(b.keys[i])
			if not bands.has(k):
				var bb := BakedMeshes.new()
				bb.stamp = b.stamp
				bands[k] = bb
			bands[k].keys.append(b.keys[i])
			bands[k].meshes.append(b.meshes[i])
		var meta := BakedMeshes.new()
		meta.stamp = b.stamp
		meta.data = b.data
		_save(meta, RemakeLodClusters.BAKED, "structures (size classes)", t0)
		for k in RemakeLodClusters.band_count():
			var path := RemakeLodClusters.band_path(k)
			if bands.has(k):
				_save(bands[k], path, "structures band %d" % k, t0)
			elif FileAccess.file_exists(path):
				DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
	quit()


func _save(b: BakedMeshes, path: String, what: String, t0: int) -> void:
	var err := ResourceSaver.save(b, path, ResourceSaver.FLAG_COMPRESS)
	# too big for one file: in parts of ~BakedMeshes.PART_MB each (BakedMeshes.load_all)
	var mb := FileAccess.get_file_as_bytes(path).size() / 1048576.0
	var n := 1
	if err == OK and mb > BakedMeshes.PART_MB * 1.25:
		n = ceili(mb / BakedMeshes.PART_MB)
		var parts := b.split(n)
		for i in n:
			var e := ResourceSaver.save(parts[i], BakedMeshes.part_path(path, i), ResourceSaver.FLAG_COMPRESS)
			if e != OK:
				err = e
	var i := n                                         # (stale parts of an earlier, bigger bake)
	while FileAccess.file_exists(BakedMeshes.part_path(path, i)):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(BakedMeshes.part_path(path, i)))
		i += 1
	print("BAKED %s: %d meshes, %d data in %.1f s -> %s, %.0f MB in %d part(s) (%s)" % [what, b.meshes.size(), b.data.size(),
		(Time.get_ticks_msec() - t0) / 1000.0, path, mb, n, error_string(err)])
