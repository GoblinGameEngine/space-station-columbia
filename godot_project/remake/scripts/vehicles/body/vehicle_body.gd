extends Node3D
class_name VehicleBody

## A vehicle body assembled in the game from its blueprint (research/vehicles/MODULAR_VEHICLES.md): the
## class standard's tube frame (TubeFrame) carrying the components the blueprint places -- exterior panels,
## interior panels, glazing, roof, ends, seats, fittings -- from the component library (VehicleLibrary).
##
## Drawn frugally: every fixed component is bound to the frame's joints and merged with the rest of its
## material into one skinned mesh (a Skeleton3D whose bones are the joints), so a whole section is a few
## dozen draws and bends on the GPU when the frame does. Moving parts (door leaves, their glass, ramps) are
## their own nodes, named by their instance id. The frame's tubes are drawn too: hidden inside the walls,
## seen where panels have come off.
##
##   VehicleBody.prepare(blueprint)     the shared plan (cached; safe on a worker thread)
##   VehicleBody.make(plan)             a body (one per vehicle part)
##   impact(p, dir, energy) -> [ids]    bend the frame; the components shaken loose
##   break_off(id, how, velocity)       a component comes off (falls as debris) or shatters

const MOVING := ["door_leaf", "door_glass", "ramp"]
const INSIDE := ["lining_bay", "door_head_lining", "ceiling_bay", "end_lining", "cap_lining", "seat", "stanchion", "fittings", "podium", "cab", "floor"]
const INSIDE_RANGE := 45.0
const TUBE_SIDES := 6

static var _plans := {}
static var _plans_mx := Mutex.new()

var plan: Dictionary
var frame: TubeFrame
var skel: Skeleton3D
var lamp_mats := {}                   # material name -> [this body's own copies] (TramSection.set_lights)
var _groups := {}                     # group key -> MeshInstance3D
var _gone := {}                       # instance ids no longer on the body
var _own_mesh := false                # (rebuilt after damage: no longer the shared one)


# -- the plan (shared by every body of a blueprint) --------------------------------------------------------

static var _tasks := {}


static func warm(bp_path: String) -> void:
	## Prepare a blueprint's plan on a worker thread (at load), so the first vehicle built from it waits for
	## nothing.
	_plans_mx.lock()
	if not _tasks.has(bp_path) and not _plans.has(bp_path):
		_tasks[bp_path] = WorkerThreadPool.add_task(func(): prepare(bp_path, true), false, "plan " + bp_path.get_file())
	_plans_mx.unlock()


static func prepare(bp_path: String, from_task := false) -> Dictionary:
	_plans_mx.lock()
	var got = _plans.get(bp_path)
	var task: int = _tasks.get(bp_path, -1)
	_plans_mx.unlock()
	if got != null:
		return got
	if task >= 0 and not from_task:
		WorkerThreadPool.wait_for_task_completion(task)
		_plans_mx.lock()
		_tasks.erase(bp_path)
		got = _plans.get(bp_path)
		_plans_mx.unlock()
		if got != null:
			return got
	var bp = JSON.parse_string(FileAccess.get_file_as_string(bp_path))
	if not bp is Dictionary:
		return {}
	var std := VehicleLibrary.standard(str(bp.standard))
	var cat := VehicleLibrary.catalog(str(bp.standard))
	# where the sides are open: the doors (from the blueprint) and the windows (the glazing's extent)
	var openings := {"R": [], "L": []}
	for d in bp.doors:
		var z := float(d.z)
		openings[str(d.side)].append([z - float(d.width) / 2, z + float(d.width) / 2, "door"])
	for pl in bp.placements:
		var e: Dictionary = cat.get(str(pl[1]), {})
		if e.is_empty() or str(e.role) != "glazing" or not openings.has(str(e.side)):
			continue                                     # (a windscreen is in an end, not a side)
		var geo := VehicleLibrary.geometry(str(bp.standard), str(pl[1]))
		var lo := INF
		var hi := -INF
		for m in geo:
			for p in geo[m][0]:
				lo = minf(lo, p.z)
				hi = maxf(hi, p.z)
		openings[str(e.side)].append([lo + float(pl[2]), hi + float(pl[2]), "window"])
	var proto := TubeFrame.build(std, bp, openings)
	var plan := {"bp": bp, "std": std, "style": str(bp.style), "frame_proto": proto, "modules": {}, "groups": {},
				 "moving": {}, "mounts": {}, "ranges": {}}
	var bind_cache := {}
	for pl in bp.placements:
		var mid := str(pl[0])
		var cid := str(pl[1])
		var anchor := float(pl[2])
		var e: Dictionary = cat.get(cid, {})
		if e.is_empty():
			continue
		var boxes: Array = []
		for b in e.boxes:
			boxes.append([b[0], b[1], float(b[2]) + anchor, b[3], b[4], b[5]])
		plan.modules[mid] = {"kind": _kind_of(str(e.role)), "role": e.role, "hp": e.hp, "mass_kg": e.mass_kg, "breaks": e.breaks,
							 "tolerance": e.tolerance, "boxes": boxes, "component": cid}
		var geo := VehicleLibrary.geometry(str(bp.standard), cid)
		if str(e.role) in MOVING:
			plan.moving[mid] = {"geo": geo, "anchor": anchor}
			continue
		var inside := str(e.role) in INSIDE
		var mounts := {}
		for m in geo:
			var key := "%s|%s" % [m, inside]
			if not plan.groups.has(key):
				plan.groups[key] = {"mat": m, "inside": inside, "pos": PackedVector3Array(), "nor": PackedVector3Array(),
									"bones": PackedInt32Array(), "weights": PackedFloat32Array()}
			var gr: Dictionary = plan.groups[key]
			var gp: PackedVector3Array = gr.pos
			var gn: PackedVector3Array = gr.nor
			var gb: PackedInt32Array = gr.bones
			var gw: PackedFloat32Array = gr.weights
			var start := gp.size()
			var pos: PackedVector3Array = geo[m][0]
			var nor: PackedVector3Array = geo[m][1]
			for i in pos.size():
				var p := pos[i] + Vector3(0, 0, anchor)
				var qk := Vector3i(roundi(p.x * 200.0), roundi(p.y * 200.0), roundi(p.z * 200.0))
				var bd = bind_cache.get(qk)
				if bd == null:
					bd = proto.bind(p)
					bind_cache[qk] = bd
				gp.append(p)
				gn.append(nor[i])
				for k in 4:
					gb.append(int(bd[0][k]))
					gw.append(float(bd[1][k]))
					if float(bd[1][k]) > 0.2:
						mounts[int(bd[0][k])] = true
			gr.pos = gp
			gr.nor = gn
			gr.bones = gb
			gr.weights = gw
			plan.ranges[mid] = plan.ranges.get(mid, []) + [[key, start, gp.size()]]
		plan.mounts[mid] = PackedInt32Array(mounts.keys())
	# the tubes, bound to their two joints
	var tg := {"mat": "frame_tube", "inside": true, "pos": PackedVector3Array(), "nor": PackedVector3Array(),
			   "bones": PackedInt32Array(), "weights": PackedFloat32Array()}
	for b in proto.beams:
		_tube(tg, proto.nodes_rest[b[0]], proto.nodes_rest[b[1]], float(b[3]) * 0.5, int(b[0]), int(b[1]))
	plan.groups["frame_tube|true"] = tg
	_plans_mx.lock()
	_plans[bp_path] = plan
	_plans_mx.unlock()
	return plan


static func _kind_of(role: String) -> String:
	## (the old module kinds the tram's code knows: glass shatters, panels detach)
	if role in ["glazing", "door_glass"]:
		return "glass"
	return role


static func _tube(g: Dictionary, a: Vector3, b: Vector3, r: float, ia: int, ib: int) -> void:
	var ax := (b - a)
	if ax.length() < 1e-4:
		return
	var t := ax.normalized()
	var u := t.cross(Vector3.UP if absf(t.y) < 0.9 else Vector3.RIGHT).normalized()
	var v := t.cross(u)
	for k in TUBE_SIDES:
		var a0 := TAU * k / TUBE_SIDES
		var a1 := TAU * (k + 1) / TUBE_SIDES
		var o0 := (u * cos(a0) + v * sin(a0))
		var o1 := (u * cos(a1) + v * sin(a1))
		var quad := [[a + o0 * r, ia, o0], [b + o0 * r, ib, o0], [b + o1 * r, ib, o1], [a + o1 * r, ia, o1]]
		var gp: PackedVector3Array = g.pos
		var gn: PackedVector3Array = g.nor
		var gb: PackedInt32Array = g.bones
		var gw: PackedFloat32Array = g.weights
		for q in [0, 2, 1, 0, 3, 2]:
			gp.append(quad[q][0])
			gn.append(quad[q][2])
			gb.append_array(PackedInt32Array([quad[q][1], 0, 0, 0]))
			gw.append_array(PackedFloat32Array([1.0, 0.0, 0.0, 0.0]))
		g.pos = gp
		g.nor = gn
		g.bones = gb
		g.weights = gw


static func shared_mesh(plan: Dictionary, key: String) -> ArrayMesh:
	## The group's mesh as built (shared by every undamaged body of the plan; made on the main thread).
	var gr: Dictionary = plan.groups[key]
	if gr.has("mesh"):
		return gr.mesh
	var m := _mesh_of(gr.pos, gr.nor, gr.bones, gr.weights)
	gr["mesh"] = m
	return m


static func _mesh_of(pos: PackedVector3Array, nor: PackedVector3Array, bones: PackedInt32Array, weights: PackedFloat32Array) -> ArrayMesh:
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = pos
	arr[Mesh.ARRAY_NORMAL] = nor
	arr[Mesh.ARRAY_BONES] = bones
	arr[Mesh.ARRAY_WEIGHTS] = weights
	var m := ArrayMesh.new()
	if pos.size() > 0:
		m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	return m


# -- a body ------------------------------------------------------------------------------------------------

static func make(p_plan: Dictionary) -> VehicleBody:
	var vb := VehicleBody.new()
	vb.name = "Body"
	vb.plan = p_plan
	vb._build()
	return vb


func _build() -> void:
	var proto: TubeFrame = plan.frame_proto
	frame = TubeFrame.new()
	frame.std = proto.std
	frame.nodes_rest = proto.nodes_rest
	frame.nodes = proto.nodes_rest.duplicate()
	frame.inv_mass = proto.inv_mass
	frame.beams = proto.beams.duplicate(true)
	frame.stations = proto.stations
	frame.ring_n = proto.ring_n
	frame.names = proto.names
	frame.profile = proto.profile
	frame.bind_segs = proto.bind_segs
	skel = Skeleton3D.new()
	skel.name = "Frame"
	var skin := Skin.new()
	for i in frame.nodes_rest.size():
		skel.add_bone("j%d" % i)
		skel.set_bone_rest(i, Transform3D(Basis(), frame.nodes_rest[i]))
		skin.add_bind(i, Transform3D(Basis(), -frame.nodes_rest[i]))
	skel.reset_bone_poses()
	add_child(skel)
	var style: String = plan.style
	for key in plan.groups:
		var gr: Dictionary = plan.groups[key]
		var mi := MeshInstance3D.new()
		mi.name = "Skin_" + str(gr.mat) + ("_in" if gr.inside else "")
		mi.mesh = shared_mesh(plan, key)
		mi.skin = skin
		mi.material_override = _material(style, str(gr.mat))
		if gr.inside or str(gr.mat).begins_with("glass"):
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		if gr.inside:
			mi.visibility_range_end = INSIDE_RANGE
		skel.add_child(mi)
		_groups[key] = mi
	for mid in plan.moving:
		var mv: Dictionary = plan.moving[mid]
		var node := MeshInstance3D.new()
		node.name = mid
		var am := ArrayMesh.new()
		for m in mv.geo:
			var arr := []
			arr.resize(Mesh.ARRAY_MAX)
			arr[Mesh.ARRAY_VERTEX] = mv.geo[m][0]
			arr[Mesh.ARRAY_NORMAL] = mv.geo[m][1]
			am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
			am.surface_set_material(am.get_surface_count() - 1, _material(style, str(m)))
		node.mesh = am
		node.position = Vector3(0, 0, float(mv.anchor))
		add_child(node)
	for mk in plan.bp.markers:
		var n := Node3D.new()
		n.name = str(mk[0])
		n.position = Vector3(mk[1][0], mk[1][1], mk[1][2])
		n.rotation.y = float(mk[2])
		add_child(n)


func _material(style: String, m: String) -> Material:
	var base := VehicleLibrary.material(style, m)
	if m.begins_with("lamp_") or m == "dest":
		var c := base.duplicate() as StandardMaterial3D
		if not lamp_mats.has(m):
			lamp_mats[m] = []
		lamp_mats[m].append(c)
		return c
	return base


func section_spec(spec: Dictionary) -> Dictionary:
	## The tram section's spec with its modules as this blueprint has them (hp, mass, boxes...).
	var out := spec.duplicate()
	out["modules"] = plan.modules
	out["doors"] = plan.bp.doors
	return out


# -- damage ------------------------------------------------------------------------------------------------

func impact(p: Vector3, dir: Vector3, energy: float) -> Array:
	## Bend the frame (section frame point and direction); the skin follows; returns the components whose
	## mounts are now strained past their tolerance.
	frame.impact(p, dir, energy)
	for i in frame.nodes.size():
		skel.set_bone_pose_position(i, frame.nodes[i])
	var out: Array = []
	for mid in plan.mounts:
		if _gone.has(mid):
			continue
		var m: Dictionary = plan.modules[mid]
		if frame.strain(plan.mounts[mid]) > float(m.tolerance):
			out.append(mid)
	return out


func displaced(rest: Vector3) -> Vector3:
	## Where a point of the section (as built) is now.
	return rest + frame.displacement(frame.bind(rest))


func break_off(mid: String, how: String, velocity: Vector3) -> void:
	## The component leaves the body: as debris with its mass (detach), or in shards (shatter).
	if _gone.has(mid) or not plan.ranges.has(mid):
		return
	_gone[mid] = true
	if how == "shatter":
		_shards(mid, velocity)
	elif how != "none":
		_debris(mid, velocity)
	_rebuild()


func _rebuild() -> void:
	## The groups without the components gone (this body's own meshes from now on).
	var drop := {}
	for mid in _gone:
		for r in plan.ranges.get(mid, []):
			if not drop.has(r[0]):
				drop[r[0]] = []
			drop[r[0]].append([r[1], r[2]])
	for key in drop:
		var gr: Dictionary = plan.groups[key]
		var keep := PackedByteArray()
		keep.resize((gr.pos as PackedVector3Array).size())
		keep.fill(1)
		for rg in drop[key]:
			for i in range(rg[0], rg[1]):
				keep[i] = 0
		var pos := PackedVector3Array()
		var nor := PackedVector3Array()
		var bones := PackedInt32Array()
		var weights := PackedFloat32Array()
		for i in keep.size():
			if keep[i] == 0:
				continue
			pos.append(gr.pos[i])
			nor.append(gr.nor[i])
			for k in 4:
				bones.append(gr.bones[i * 4 + k])
				weights.append(gr.weights[i * 4 + k])
		(_groups[key] as MeshInstance3D).mesh = _mesh_of(pos, nor, bones, weights)
	_own_mesh = true


var _last_pts := PackedVector3Array()     # (the last _component_mesh's vertices: no read-back from the renderer)


func _component_mesh(mid: String) -> ArrayMesh:
	## The component as it is now (dented with the frame), unskinned: for its debris.
	_last_pts = PackedVector3Array()
	var am := ArrayMesh.new()
	for r in plan.ranges.get(mid, []):
		var gr: Dictionary = plan.groups[r[0]]
		var pos := PackedVector3Array()
		var nor := PackedVector3Array()
		for i in range(r[1], r[2]):
			var b := [[gr.bones[i * 4], gr.bones[i * 4 + 1], gr.bones[i * 4 + 2], gr.bones[i * 4 + 3]],
					  [gr.weights[i * 4], gr.weights[i * 4 + 1], gr.weights[i * 4 + 2], gr.weights[i * 4 + 3]]]
			pos.append(gr.pos[i] + frame.displacement(b))
			nor.append(gr.nor[i])
		if pos.is_empty():
			continue
		_last_pts.append_array(pos)
		var arr := []
		arr.resize(Mesh.ARRAY_MAX)
		arr[Mesh.ARRAY_VERTEX] = pos
		arr[Mesh.ARRAY_NORMAL] = nor
		am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
		am.surface_set_material(am.get_surface_count() - 1, (_groups[r[0]] as MeshInstance3D).material_override)
	return am


func _debris(mid: String, velocity: Vector3) -> void:
	var am := _component_mesh(mid)
	if am.get_surface_count() == 0:
		return
	var aabb := am.get_aabb()
	var rb := RigidBody3D.new()
	rb.name = "Debris_" + mid
	rb.mass = maxf(1.0, float(plan.modules[mid].mass_kg))
	rb.collision_layer = 1 << 10
	rb.collision_mask = 1
	var mi := MeshInstance3D.new()
	mi.mesh = am
	mi.position = -aabb.get_center()
	rb.add_child(mi)
	# its own shape to tumble and land on (a convex hull of the panel as bent -- a ragdoll of it)
	var pts := PackedVector3Array()
	var stride := maxi(1, _last_pts.size() / 64)
	for i in range(0, _last_pts.size(), stride):
		pts.append(_last_pts[i] - aabb.get_center())
	var cs := CollisionShape3D.new()
	if pts.size() >= 4:
		var hull := ConvexPolygonShape3D.new()
		hull.points = pts
		cs.shape = hull
	else:
		var sh := BoxShape3D.new()
		sh.size = aabb.size.max(Vector3.ONE * 0.04)
		cs.shape = sh
	rb.add_child(cs)
	get_tree().current_scene.add_child(rb)
	rb.global_transform = Transform3D(global_transform.basis, global_transform * aabb.get_center())
	var out := (global_transform.basis * Vector3(aabb.get_center().x, 0.3, 0.0)).normalized()
	rb.linear_velocity = velocity + out * 1.5
	rb.angular_velocity = Vector3(randf_range(-1.5, 1.5), randf_range(-1.5, 1.5), randf_range(-1.5, 1.5))
	get_tree().create_timer(60.0).timeout.connect(func(): if is_instance_valid(rb): rb.queue_free())


func _shards(mid: String, velocity: Vector3) -> void:
	var am := _component_mesh(mid)
	var aabb := am.get_aabb()
	var mat: Material = am.surface_get_material(0) if am.get_surface_count() > 0 else null
	for k in 6:
		var rb := RigidBody3D.new()
		rb.mass = 0.4
		rb.collision_layer = 1 << 10
		rb.collision_mask = 1
		var cs := CollisionShape3D.new()
		var sh := BoxShape3D.new()
		sh.size = Vector3(0.12, 0.12, 0.01)
		cs.shape = sh
		rb.add_child(cs)
		var vis := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = sh.size
		vis.mesh = bm
		vis.material_override = mat
		rb.add_child(vis)
		get_tree().current_scene.add_child(rb)
		rb.global_position = global_transform * (aabb.position + Vector3(randf(), randf(), randf()) * aabb.size)
		rb.linear_velocity = velocity + Vector3(randf_range(-1, 1), randf_range(0, 1.5), randf_range(-1, 1))
		get_tree().create_timer(8.0).timeout.connect(rb.queue_free)
