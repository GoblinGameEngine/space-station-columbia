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
		_clear_fine()
		for k in MapRoads.BAND_N:
			var t0 := Time.get_ticks_msec()
			_save_split(r.bake_band(k), k, t0)
		r.free()
		var i := 0                                             # (the single file the whole ring's roads were)
		while true:
			var old := MapRoads.BAKED if i == 0 else BakedMeshes.part_path(MapRoads.BAKED, i)
			if not FileAccess.file_exists(old):
				break
			DirAccess.remove_absolute(ProjectSettings.globalize_path(old))
			i += 1
	if what.has("roads_split"):
		# the band files as they are, their fine detail moved out to tiles (MapRoads.split_band)
		_clear_fine()
		for k in MapRoads.BAND_N:
			var t0 := Time.get_ticks_msec()
			var b := BakedMeshes.load_all(MapRoads.band_path(k))
			if b == null or not b.keys.any(func(key): return MapRoads.FINE.has(key[1])):
				push_error("roads band %d: missing, or split already (no fine detail in it): rebake the roads" % k)
				continue
			_save_split(b, k, t0)
	if all or what.has("pads"):
		var t0 := Time.get_ticks_msec()
		MapTerrain.bake_bin()
		RoadFurniture.bake_bin()
		Placement.bake_bin()
		NpcPlaces.bake_bin()
		NpcTraffic.bake_fleet()
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
		# a file per band of the ring (MapTrees streams them round the player)
		var cells: Dictionary = b.data.cells
		var bands := {}
		for c in cells:
			var k := MapTrees.band_of(float(c.x) * MapTrees.CELL + 1.0)
			if not bands.has(k):
				bands[k] = {}
			bands[k][c] = cells[c]
		for k in MapTrees.band_count():
			var path := MapTrees.band_path(k)
			if bands.has(k):
				var bb := BakedMeshes.new()
				bb.stamp = b.stamp
				bb.data["cells"] = bands[k]
				_save(bb, path, "trees band %d" % k, t0)
			elif FileAccess.file_exists(path):
				DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
		var i := 0                                             # (the single file the whole ring's trees were)
		while true:
			var old := MapTrees.BAKED if i == 0 else BakedMeshes.part_path(MapTrees.BAKED, i)
			if not FileAccess.file_exists(old):
				break
			DirAccess.remove_absolute(ProjectSettings.globalize_path(old))
			i += 1
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
		_clear_dir("res://remake/baked/structures_t")
		for k in RemakeLodClusters.band_count():
			var path := RemakeLodClusters.band_path(k)
			if bands.has(k):
				_save_sband(bands[k], k, t0)
			elif FileAccess.file_exists(path):
				DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
	if what.has("structures_split"):
		# the band files as they are, their LOD2 cells moved out to tiles (RemakeLodClusters.split_band)
		_clear_dir("res://remake/baked/structures_t")
		for k in RemakeLodClusters.band_count():
			if ResourceLoader.exists(RemakeLodClusters.band_path(k)):
				var b := BakedMeshes.load_all(RemakeLodClusters.band_path(k))
				if b.data.has("tiles2"):
					push_error("structures band %d is split already: rebake the structures" % k)
					continue
				_save_sband(b, k, Time.get_ticks_msec())
	quit()


func _clear_fine() -> void:
	_clear_dir("res://remake/baked/roads_f")


func _clear_dir(res_dir: String) -> void:
	## the tile files of an earlier bake (b<band>_<tile>.res)
	var dir := ProjectSettings.globalize_path(res_dir)
	DirAccess.make_dir_recursive_absolute(dir)
	for f in DirAccess.get_files_at(dir):
		if f.begins_with("b") and (f.ends_with(".res") or f.ends_with(".res.import")):
			DirAccess.remove_absolute(dir.path_join(f))


func _save_sband(b: BakedMeshes, k: int, t0: int) -> void:
	var sp := RemakeLodClusters.split_band(b)
	_save(sp[0], RemakeLodClusters.band_path(k), "structures band %d" % k, t0)
	for tk in sp[1]:
		var e := ResourceSaver.save(sp[1][tk], RemakeLodClusters.tile2_path(k, tk), ResourceSaver.FLAG_COMPRESS)
		if e != OK:
			push_error("structures tile %s: %s" % [tk, error_string(e)])
	print("  band %d: %d LOD2 tiles" % [k, (sp[1] as Dictionary).size()])


func _save_split(b: BakedMeshes, k: int, t0: int) -> void:
	var sp := MapRoads.split_band(b)
	_save(sp[0], MapRoads.band_path(k), "roads band %d" % k, t0)
	var n := 0
	for tk in sp[1]:
		var e := ResourceSaver.save(sp[1][tk], MapRoads.fine_path(k, tk), ResourceSaver.FLAG_COMPRESS)
		if e != OK:
			push_error("roads tile %s: %s" % [tk, error_string(e)])
		n += 1
	print("  band %d: %d fine tiles" % [k, n])


func _save(b: BakedMeshes, path: String, what: String, t0: int) -> void:
	b.data.erase("_parts")                                 # (a count of its own parts, set below if it needs them)
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
