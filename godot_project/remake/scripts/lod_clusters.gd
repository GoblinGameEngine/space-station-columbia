class_name RemakeLodClusters
## Hierarchical LOD for many placed buildings (the distance versions gblod.py exports beside each
## glb: <id>.lod1/2/3.glb).
##
## Per building: LOD0 (the full glb, doors and lights -- a RemakeBuilding) and LOD1 (the exterior)
## switch by distance, scaled by the building's size.  Farther out, buildings are drawn by merged
## meshes: every normal-size building's LOD2 in a CELL2 m cell becomes one mesh (one draw call), its
## LOD3 in a CELL3 m cell another.  Visibility parents chain them: a building's LOD1 hides while its
## cell's LOD2 mesh shows, and that hides while the coarser cell's LOD3 mesh shows.  Landmarks (15 m
## tall or 45 m long or more: elevators, spires, towers, silos, factories, long bridges) stay out
## of the merge and keep their own full chain, so they don't coarsen with their cell.
##
## Switch distances are for a ~12 m building (LOD1 from 60 m, LOD2 from 200 m, LOD3 from 600 m); a
## merged cell switches once its farthest building has passed them.

const D1 := 60.0
const D2 := 200.0
const D3 := 600.0
const CELL2 := 150.0
const CELL3 := 400.0
const LANDMARK_H := 15.0            # a landmark: this tall or taller (spires, elevators, towers, silos) ...
const LANDMARK_W := 45.0            # ... or this long (big blocks, factories, long bridges)
const MARGIN := 0.08                 # hysteresis at each switch, a fraction of the distance

## entries: Array of Dictionaries {id: String, xform: Transform3D (in parent's space),
##   key2: Variant, key3: Variant (cell keys: buildings with equal keys merge)}.
## full: build each building's LOD0 too; false: LOD1 draws from 0 m and the returned "records"
## ({id, root, lod1, k}) go to a RemakeDetailStreamer, which loads LOD0 near the player.  With the
## cells baked and full false, an ordinary building gets no nodes at all here (root and lod1 null,
## its xform and parent kept): the streamer puts its LOD1 in while its cell's LOD2 mesh is near
## enough to hand over to it ("cells": key2 -> {node, recs}) -- 50,000 buildings at 1:1 (2026-10-07)
## can't each keep a LOD1 in the scene.
## A coroutine (one building per frame) -- await it; returns {"buildings", "cells2", "cells3", "landmarks"}.
const BAKED := "res://remake/baked/structures.res"
const BAKE_VERSION := 3              # bump when the merge's output changes (3: heights above grade; landmarks tall or bridges)
const LOD0_MAX := 90.0               # full detail (interiors, doors, lights) never past this, however big (Calder:
                                     # a strip centre's 158k-triangle LOD0 was drawn 160 m off, 2026-10-06)


static func lod0_end(k: float) -> float:
	return minf(D1 * k, LOD0_MAX)


static func _is_crossing(id: String) -> bool:
	return id.begins_with("MAJOR-") or id.begins_with("SMALL-") or id.begins_with("CULVERT-") or id.begins_with("RAIL-") or id.begins_with("XBR-")
const BUDGET_USEC := 8000             # main-thread time per frame spent assembling buildings
const LOADING_BUDGET_USEC := 60000    # ... while the loading screen is up
const LOOKAHEAD := 64                 # buildings whose LOD files are loading ahead


static func stamp() -> String:
	## what the merged cells are built from: where everything stands (placement, the graded terrain)
	return BakedMeshes.fingerprint(["res://remake/placement.json", MapTerrain.PATH, "res://remake/terrain_base.bin.gz",
		"res://remake/terrain_level.bin.gz", "res://remake/terrain_depth.bin.gz"], BAKE_VERSION)


const BAKE_BAND := 1200.0            # m of the ring merged at a time (a multiple of CELL2 and CELL3: no cell in two)
# The merged cells are kept a band of the ring a file, streamed round the player by RemakeDetailStreamer: all of the
# 1:1 station's (~8,600 meshes, ~1 GB of vertex buffers) at once ran the Deck out of memory (2026-10-08).  A band is a
# multiple of BAKE_BAND, so a LOD2 cell and the LOD3 cell over it are always in the same file.
const STREAM_BAND := 2400.0


static func band_count() -> int:
	return ceili(StationGeo.CIRC / STREAM_BAND)


static func band_of_s(s: float) -> int:
	return floori(fposmod(s, StationGeo.CIRC) / STREAM_BAND) % band_count()


static func band_of_key(key: Array) -> int:
	## a baked key [2, key2, key3] or [3, key3]: its cell's band (by where the cell starts round the ring)
	var cell := (CELL2 if int(key[0]) == 2 else CELL3)
	return band_of_s(float((key[1] as Vector2i).x) * cell + 0.5)


static func band_path(k: int) -> String:
	return "res://remake/baked/structures_b%02d.res" % k


static func lod3_node(mesh: Mesh, key: Vector2i) -> MeshInstance3D:
	var mi := _commit(mesh, "lod3_%s" % str(key))
	var r := _radius(mi)
	mi.visibility_range_begin = D3 + r
	mi.visibility_range_begin_margin = (D3 + r) * MARGIN
	return mi


static func lod2_node(mesh: Mesh, key: Vector2i) -> MeshInstance3D:
	var mi := _commit(mesh, "lod2_%s" % str(key))
	var r := _radius(mi)
	mi.visibility_range_begin = D2 + r
	mi.visibility_range_begin_margin = (D2 + r) * MARGIN
	return mi


static func bake(parent: Node3D, entries: Array) -> BakedMeshes:
	## The merged LOD2 / LOD3 cells and each building's size class, for build() to load next time
	## (remake/tools/bake_world.gd).  A band of the ring at a time, its cells committed to meshes before the next and
	## only the LOD2 / LOD3 of each model loaded: the whole 1:1 station's cells at once, with every model's LOD1 too,
	## ran past the Deck's memory (2026-10-08).
	var out := BakedMeshes.new()
	out.stamp = stamp()
	out.data["meta"] = {}
	var bands := {}
	for e in entries:
		var s := fposmod(float((e.key2 as Vector2i).x) * CELL2 + 1.0, StationGeo.CIRC)
		var b := floori(s / BAKE_BAND)
		if not bands.has(b):
			bands[b] = []
		bands[b].append(e)
	var lods := {}                                       # model -> [lod2, lod3] (PackedScene or null)
	var keys := bands.keys()
	keys.sort()
	for bk in keys:
		var cells2 := {}
		var cells3 := {}
		for e in bands[bk]:
			var id: String = e.id
			var model: String = e.get("model", id)
			if not lods.has(model):
				var two := []
				for l in [2, 3]:
					var p := "res://remake/buildings/%s.lod%d.glb" % [model, l]
					two.append(load(p) if ResourceLoader.exists(p) else null)
				lods[model] = two
			var sc: Array = lods[model]
			var l2: Node3D = sc[0].instantiate() if sc[0] else null
			var probe: Node3D = l2
			if probe == null:
				var p1 := "res://remake/buildings/%s.lod1.glb" % model
				if not ResourceLoader.exists(p1):
					continue
				probe = (load(p1) as PackedScene).instantiate()
			var ab := _aabb(probe)
			var wide := maxf(ab.size.x, ab.size.z)
			var tall := ab.end.y
			var k := clampf(maxf(tall, wide * 0.8) / 12.0, 0.7, 4.0)
			var landmark := tall >= LANDMARK_H or (wide >= LANDMARK_W and _is_crossing(id))
			out.data.meta[id] = [k, landmark]
			if probe != l2:
				probe.free()
			if landmark:
				if l2:
					l2.free()
				continue
			if l2:
				if not cells2.has(e.key2):
					cells2[e.key2] = {"st": SurfaceTool.new(), "key3": e.key3}
					cells2[e.key2].st.begin(Mesh.PRIMITIVE_TRIANGLES)
				_append(cells2[e.key2].st, l2, e.xform)            # (frees the instance)
			if sc[1]:
				if not cells3.has(e.key3):
					cells3[e.key3] = SurfaceTool.new()
					cells3[e.key3].begin(Mesh.PRIMITIVE_TRIANGLES)
				_append(cells3[e.key3], sc[1].instantiate(), e.xform)
		for key in cells3:
			out.keys.append([3, key])
			out.meshes.append(cells3[key].commit())
		for key in cells2:
			out.keys.append([2, key, cells2[key].key3])
			out.meshes.append(cells2[key].st.commit())
		cells2.clear()
		cells3.clear()
	return out


static func _load_baked() -> BakedMeshes:
	if not ResourceLoader.exists(BAKED):
		return null
	var b := BakedMeshes.load_all(BAKED)
	if b == null or b.stamp != stamp():
		push_warning("RemakeLodClusters: the baked cells are of other data -- merging them (rerun remake/tools/bake_world.gd)")
		return null
	return b


static func build(parent: Node3D, entries: Array, full := true, bake_into: BakedMeshes = null) -> Dictionary:
	# baked: the cells come ready-made and each building's size class is known -- only its LOD1 (and
	# a landmark's LOD2 / LOD3) is loaded
	var baked: BakedMeshes = null if bake_into else _load_baked()
	var meta: Dictionary = baked.data.meta if baked else {}
	# the LOD files load on worker threads, in parallel, LOOKAHEAD buildings ahead of the one being
	# assembled (queueing all ~2,300 at once blocks for seconds)
	var ahead := 0
	var tree := Engine.get_main_loop() as SceneTree
	var frame_start := Time.get_ticks_usec()
	var lod_scenes := {}
	var cells2 := {}
	var cells3 := {}
	var lod1_of_cell2 := {}
	var landmarks := 0
	var records := []
	var stream := baked != null and not full and bake_into == null
	var streamed_of_cell2 := {}
	for idx in entries.size():
		var e: Dictionary = entries[idx]
		# (behind the loading screen they load right here instead: hitches don't matter there, and Godot
		# 4.5 can crash when many scenes sharing materials load on sub-threads at once)
		while not StationGeo.loading and ahead < mini(entries.size(), idx + LOOKAHEAD):
			var am: String = entries[ahead].get("model", entries[ahead].id)
			var am_meta: Array = meta.get(entries[ahead].id, [1.0, true])
			for l in ([] if stream and not am_meta[1] else [1] if baked and not am_meta[1] else [1, 2, 3]):
				var ap := "res://remake/buildings/%s.lod%d.glb" % [am, l]
				if ResourceLoader.exists(ap):
					ResourceLoader.load_threaded_request(ap)
			ahead += 1
		var id: String = e.id
		var model: String = e.get("model", id)             # the glbs it uses (a crossing may reuse another's)
		var known: Array = meta.get(id, [])
		if stream and not known.is_empty() and not known[1]:
			# streamed: nothing in the scene until its cell comes near (RemakeDetailStreamer)
			records.append({"id": id, "model": model, "root": null, "lod1": null, "k": known[0], "landmark": false,
				"xform": e.xform, "parent": parent, "key2": e.key2})
			if not streamed_of_cell2.has(e.key2):
				streamed_of_cell2[e.key2] = []
			streamed_of_cell2[e.key2].append(records.size() - 1)
			continue
		var need := [1] if not known.is_empty() and not known[1] else [1, 2, 3]
		if not lod_scenes.has(model) or lod_scenes[model].size() < need.size():
			lod_scenes[model] = []
			for l in need:
				var p := "res://remake/buildings/%s.lod%d.glb" % [model, l]
				if not ResourceLoader.exists(p):
					lod_scenes[model].append(null)
					continue
				# not loaded yet: let frames go by rather than block on it
				while ResourceLoader.load_threaded_get_status(p) == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
					await tree.process_frame
					frame_start = Time.get_ticks_usec()
				if ResourceLoader.load_threaded_get_status(p) == ResourceLoader.THREAD_LOAD_LOADED:
					lod_scenes[model].append(ResourceLoader.load_threaded_get(p))
				else:
					lod_scenes[model].append(load(p))
		var sc: Array = lod_scenes[model]
		if sc[0] == null:
			continue
		var root := Node3D.new()
		root.name = id
		root.transform = e.xform
		parent.add_child(root)
		var lod1: Node3D = sc[0].instantiate()
		root.add_child(lod1)
		RemakeBuilding.prepare_lod(lod1, "res://remake/buildings/%s.lod1.glb" % model)
		# (set below, once its size is known: ordinary buildings' LOD1 may thin itself with distance)
		# size and prominence from the massing (LOD2 has no yard props): switch distances scale with
		# it, and a tall or very long building is a landmark that keeps its own chain
		var l2: Node3D = null
		var k: float
		var landmark: bool
		if not known.is_empty():
			k = known[0]
			landmark = known[1]
			if landmark and sc.size() > 1 and sc[1]:
				l2 = sc[1].instantiate()
		else:
			l2 = sc[1].instantiate() if sc.size() > 1 and sc[1] else null
			var ab := _aabb(l2 if l2 else lod1)
			var wide := maxf(ab.size.x, ab.size.z)
			var tall := ab.end.y                         # above grade: the foundations reach 4 m below it (FOUND_DEPTH),
			                                             # which made every 12 m house a 16 m 'landmark'
			k = clampf(maxf(tall, wide * 0.8) / 12.0, 0.7, 4.0)
			# a landmark keeps its own chain far out: tall (spires, elevators, towers) or a long bridge (its truss);
			# a long low building -- a strip centre, a big box, a school wing -- merges into its cell like any other
			landmark = tall >= LANDMARK_H or (wide >= LANDMARK_W and _is_crossing(id))
		if bake_into:
			if not bake_into.data.has("meta"):
				bake_into.data["meta"] = {}
			bake_into.data.meta[id] = [k, landmark]
		if full:
			var b := RemakeBuilding.new()
			root.add_child(b)
			b.load_building(load("res://remake/buildings/%s.glb" % model))
			_ranges(b, 0.0, lod0_end(k))
			_light_fade(b)
		else:
			records.append({"id": id, "model": model, "root": root, "lod1": lod1, "k": k, "landmark": landmark,
				"xform": e.xform, "parent": parent, "key2": e.key2})
		var lod1_begin := lod0_end(k) if full else 0.0      # no full detail yet: LOD1 from 0 m (the streamer swaps it)
		if not landmark:
			# Godot's own mesh LOD (generated on import) thins an ordinary building's exterior with distance; only
			# landmarks keep every truss member and pane (the user, 2026-10-06: Calder at 60 fps)
			_lod_bias(lod1, 1.0)
		if landmark:
			# its own chain all the way out
			landmarks += 1
			_ranges(lod1, lod1_begin, D2 * k)
			for l in [2, 3]:
				var inst: Node3D = l2 if l == 2 else (sc[2].instantiate() if sc[2] else null)
				if inst == null:
					continue
				root.add_child(inst)
				RemakeBuilding.prepare_lod(inst, "res://remake/buildings/%s.lod%d.glb" % [model, l])
				_ranges(inst, (D2 if l == 2 else D3) * k, D3 * k if l == 2 else 0.0)
			if Time.get_ticks_usec() - frame_start > (LOADING_BUDGET_USEC if StationGeo.loading else BUDGET_USEC):
				await tree.process_frame
				frame_start = Time.get_ticks_usec()
			continue
		if bake_into:
			# baking: an ordinary building's own nodes aren't kept (the game streams them) -- only its merge
			root.free()
			records.pop_back()
		else:
			_ranges(lod1, lod1_begin, 0.0)
			if not lod1_of_cell2.has(e.key2):
				lod1_of_cell2[e.key2] = []
			lod1_of_cell2[e.key2].append(lod1)
		if baked:
			# its cells come baked
			if Time.get_ticks_usec() - frame_start > (LOADING_BUDGET_USEC if StationGeo.loading else BUDGET_USEC):
				await tree.process_frame
				frame_start = Time.get_ticks_usec()
			continue
		for pair in [[cells2, e.key2, 1], [cells3, e.key3, 2]]:
			var cells: Dictionary = pair[0]
			if sc[pair[2]] == null:
				continue
			if not cells.has(pair[1]):
				cells[pair[1]] = {"st": SurfaceTool.new(), "n": 0, "key3": e.key3}
				cells[pair[1]].st.begin(Mesh.PRIMITIVE_TRIANGLES)
			var c: Dictionary = cells[pair[1]]
			_append(c.st, l2 if pair[2] == 1 else sc[pair[2]].instantiate(), e.xform)
			l2 = null if pair[2] == 1 else l2
			c.n += 1
		# a few milliseconds of assembly per frame: the game keeps running while the map fills in
		if Time.get_ticks_usec() - frame_start > (LOADING_BUDGET_USEC if StationGeo.loading else BUDGET_USEC):
			await tree.process_frame
			frame_start = Time.get_ticks_usec()
	# the merged meshes, and the visibility chain LOD1 -> cell LOD2 -> cell LOD3
	var mesh3 := {}
	var mesh2 := {}
	var key3_of := {}
	if baked:
		for i in baked.keys.size():
			var bk: Array = baked.keys[i]
			if bk[0] == 3:
				mesh3[bk[1]] = baked.meshes[i]
			else:
				mesh2[bk[1]] = baked.meshes[i]
				key3_of[bk[1]] = bk[2]
	else:
		for key in cells3:
			mesh3[key] = cells3[key].st.commit()
		for key in cells2:
			mesh2[key] = cells2[key].st.commit()
			key3_of[key] = cells2[key].key3
	if bake_into:
		for key in mesh3:
			bake_into.keys.append([3, key])
			bake_into.meshes.append(mesh3[key])
		for key in mesh2:
			bake_into.keys.append([2, key, key3_of[key]])
			bake_into.meshes.append(mesh2[key])
	var nodes3 := {}
	var nodes2 := {}
	for key in mesh3:
		var mi := _commit(mesh3[key], "lod3_%s" % str(key))
		parent.add_child(mi)
		var r := _radius(mi)
		mi.visibility_range_begin = D3 + r
		mi.visibility_range_begin_margin = (D3 + r) * MARGIN
		nodes3[key] = mi
	for key in mesh2:
		var mi := _commit(mesh2[key], "lod2_%s" % str(key))
		parent.add_child(mi)
		var r := _radius(mi)
		mi.visibility_range_begin = D2 + r
		mi.visibility_range_begin_margin = (D2 + r) * MARGIN
		var p3: MeshInstance3D = nodes3.get(key3_of[key])
		if p3:
			mi.visibility_parent = mi.get_path_to(p3)
		for lod1 in lod1_of_cell2.get(key, []):
			_parent_all(lod1, mi)
		nodes2[key] = mi
	# the streamed buildings by cell (a cell without a LOD2 mesh: node null -- its LOD1s are wanted at any distance)
	var cells := {}
	for key in streamed_of_cell2:
		cells[key] = {"node": nodes2.get(key), "recs": streamed_of_cell2[key]}
	return {"buildings": entries.size(), "cells2": mesh2.size(), "cells3": mesh3.size(), "landmarks": landmarks,
		"baked": baked != null, "streamed": records.size() - landmarks if stream else 0,
		"records": records, "cells": cells}


static func _append(st: SurfaceTool, inst: Node, xform: Transform3D) -> void:
	var stack: Array[Node] = [inst]
	while stack.size() > 0:
		var n: Node = stack.pop_back()
		stack.append_array(n.get_children())
		if n is MeshInstance3D and (n as MeshInstance3D).mesh:
			var mi := n as MeshInstance3D
			var local := _local_xform(mi, inst)
			for s in mi.mesh.get_surface_count():
				st.append_from(mi.mesh, s, xform * local)
	inst.free()


static func _local_xform(n: Node3D, top: Node) -> Transform3D:
	var t := n.transform
	var p := n.get_parent()
	while p and p != top and p is Node3D:
		t = (p as Node3D).transform * t
		p = p.get_parent()
	return (top as Node3D).transform * t if top is Node3D else t


static func _commit(mesh: Mesh, name: String) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.name = name
	mi.mesh = mesh
	mi.material_override = RemakeBuilding.lod_vc_material()
	mi.lod_bias = 1000.0
	return mi


static func _radius(mi: MeshInstance3D) -> float:
	var ab := mi.get_aabb()
	return Vector2(ab.size.x, ab.size.z).length() * 0.5


static func _aabb(n: Node) -> AABB:
	var box := AABB()
	var first := true
	var stack: Array[Node] = [n]
	while stack.size() > 0:
		var c: Node = stack.pop_back()
		stack.append_array(c.get_children())
		if c is MeshInstance3D and (c as MeshInstance3D).mesh:
			var ab: AABB = (c as MeshInstance3D).get_aabb()
			box = ab if first else box.merge(ab)
			first = false
	return box


static func _ranges(n: Node, begin: float, end: float) -> void:
	var stack: Array[Node] = [n]
	while stack.size() > 0:
		var c: Node = stack.pop_back()
		stack.append_array(c.get_children())
		if c is GeometryInstance3D:
			var g := c as GeometryInstance3D
			g.visibility_range_begin = begin
			g.visibility_range_begin_margin = begin * MARGIN
			g.visibility_range_end = end
			g.visibility_range_end_margin = end * MARGIN


static func _lod_bias(n: Node, bias: float) -> void:
	var stack: Array[Node] = [n]
	while stack.size() > 0:
		var c: Node = stack.pop_back()
		stack.append_array(c.get_children())
		if c is GeometryInstance3D:
			(c as GeometryInstance3D).lod_bias = bias


static func _parent_all(n: Node, vis_parent: GeometryInstance3D) -> void:
	var stack: Array[Node] = [n]
	while stack.size() > 0:
		var c: Node = stack.pop_back()
		stack.append_array(c.get_children())
		if c is GeometryInstance3D:
			(c as GeometryInstance3D).visibility_parent = c.get_path_to(vis_parent)


static func _light_fade(n: Node) -> void:
	# room lights out beyond ~40 m (lit windows stand in for them farther out)
	var stack: Array[Node] = [n]
	while stack.size() > 0:
		var c: Node = stack.pop_back()
		stack.append_array(c.get_children())
		if c is Light3D:
			var l := c as Light3D
			l.distance_fade_enabled = true
			l.distance_fade_begin = 35.0
			l.distance_fade_length = 10.0
