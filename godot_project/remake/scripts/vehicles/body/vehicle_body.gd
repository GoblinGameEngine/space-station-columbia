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

const MOVING := ["door_leaf", "door_glass", "ramp", "hatch", "hatch_glass", "frunk_lid", "engine"]   # (their own nodes: they swing, or tilt)
const INSIDE := ["lining_bay", "door_head_lining", "ceiling_bay", "end_lining", "cap_lining", "seat", "stanchion", "fittings", "podium", "cab", "floor"]
const INSIDE_RANGE := 45.0
## The cabin's own render layer (the user, 2026-10-05: "the cars taillights are leaking into the cabin ... all the
## illumination should be external from the exterior lights"): every interior surface draws on this layer, and every
## exterior lamp (head, tail, brake, reverse, beacons) leaves it out of its light_cull_mask. The sun, moon and the
## cabin's own dome light still reach it. Chosen by material, so a door's inner lining (one module with its skin) is
## split off too.
const INTERIOR_LAYER := 1 << 9
const EXTERIOR_LIGHT_MASK := 0xFFFFF & ~INTERIOR_LAYER
const INTERIOR_MATS := ["lining", "headliner", "carpet", "seat", "dash", "upholstery", "lcd", "gauge", "tub"]


static func is_interior_mat(m: String) -> bool:
	return m in INTERIOR_MATS
const TUBE_SIDES := 6
const PAIR_REACH := 1.6               # m: a panel's fastenings are judged between mount joints this near ...
const PAIR_MIN := 0.05                # m: ... and no nearer (the standard's "pair_min": a car's, 0.25 -- on a short
                                      # baseline a centimetre reads as a tear, and the wagon's nose hoops are 7 cm apart)

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


static var _bp_time := {}


static func prepare(bp_path: String, from_task := false) -> Dictionary:
	# (a blueprint rebuilt since its plan was made: plan it again, from a refreshed library)
	var mt := FileAccess.get_modified_time(bp_path)
	_plans_mx.lock()
	if _plans.has(bp_path) and int(_bp_time.get(bp_path, mt)) != mt:
		_plans.erase(bp_path)
	_bp_time[bp_path] = mt
	_plans_mx.unlock()
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
	VehicleLibrary.refresh(str(bp.standard))
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
	var plan := {"bp": bp, "std": std, "style": "%s/%s" % [bp.standard, bp.style], "frame_proto": proto, "modules": {}, "groups": {},
				 "moving": {}, "mounts": {}, "lines": {}, "ranges": {}}
	var pair_min := float(std.get("pair_min", PAIR_MIN))
	var bind_cache := {}
	# (everything a closer carries is its own node, whatever its role -- a door's handle and belt moulding are trim, and
	#  merged into the skin they stayed in the doorway when the door swung open)
	var on_closers := {}
	for c in bp.get("closers", []):
		for pid in c.get("parts", []):
			on_closers[str(pid)] = true
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
							 "tolerance": (std.get("tolerance", {}) as Dictionary).get(str(e.role), e.tolerance),   # (the standard's, live)
							 "boxes": boxes, "component": cid}
		var geo := VehicleLibrary.geometry(str(bp.standard), cid)
		if str(e.role) in MOVING or on_closers.has(mid):
			plan.moving[mid] = {"geo": geo, "anchor": anchor}
			continue
		var inside := str(e.role) in INSIDE
		var mounts := {}
		for m in geo:
			var key := "%s|%s" % [m, inside]
			if not plan.groups.has(key):
				plan.groups[key] = {"mat": m, "inside": inside, "pos": PackedVector3Array(), "nor": PackedVector3Array(),
									"bones": PackedInt32Array(), "weights": PackedFloat32Array(), "wear": PackedFloat32Array()}
			var gr: Dictionary = plan.groups[key]
			var gp: PackedVector3Array = gr.pos
			var gn: PackedVector3Array = gr.nor
			var gb: PackedInt32Array = gr.bones
			var gw: PackedFloat32Array = gr.weights
			var start := gp.size()
			var pos: PackedVector3Array = geo[m][0]
			var nor: PackedVector3Array = geo[m][1]
			var gwr: PackedFloat32Array = gr.wear
			var wr: PackedFloat32Array = geo[m][2] if (geo[m] as Array).size() > 2 else PackedFloat32Array()
			if wr.size() == pos.size():
				gwr.append_array(wr)
			else:
				var z := PackedFloat32Array()
				z.resize(pos.size())
				gwr.append_array(z)
			gr.wear = gwr
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
		# its fastening: pairs of its mount joints near each other (within PAIR_REACH): a sheet fastened
		# across them tears loose when the frame distorts it -- a dent far off doesn't
		var ms: Array = mounts.keys()
		var pairs := PackedInt32Array()
		for i in ms.size():
			for j in range(i + 1, ms.size()):
				var d := proto.nodes_rest[ms[i]].distance_to(proto.nodes_rest[ms[j]])
				if d > pair_min and d < PAIR_REACH:
					pairs.append(ms[i])
					pairs.append(ms[j])
		plan.lines[mid] = pairs
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
	if role in ["glazing", "door_glass", "hatch_glass"]:
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
	var m := _mesh_of(gr.pos, gr.nor, gr.bones, gr.weights, gr.get("wear", PackedFloat32Array()))
	gr["mesh"] = m
	return m


static func wear_colors(wr: PackedFloat32Array, n: int) -> PackedColorArray:
	## The edge wear as the vertex colour the surface shader reads (COLOR.r = 1 - wear: a mesh without it wears nothing).
	var c := PackedColorArray()
	c.resize(n)
	for i in n:
		c[i] = Color(1.0 - (wr[i] if i < wr.size() else 0.0), 1.0, 1.0, 1.0)
	return c


static func _mesh_of(pos: PackedVector3Array, nor: PackedVector3Array, bones: PackedInt32Array, weights: PackedFloat32Array,
		wr := PackedFloat32Array()) -> ArrayMesh:
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = pos
	arr[Mesh.ARRAY_NORMAL] = nor
	arr[Mesh.ARRAY_BONES] = bones
	arr[Mesh.ARRAY_WEIGHTS] = weights
	if wr.size() == pos.size() and pos.size() > 0:
		arr[Mesh.ARRAY_COLOR] = wear_colors(wr, pos.size())
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
	vb.weather(randf_range(0.03, 0.5), randf_range(0.03, 0.55))
	return vb


var grime := 0.3
var wear := 0.3


func weather(g: float, w: float) -> void:
	## How dirty and how worn this one is (0..1 each; the surface shader's instance uniforms): set at random when it's
	## made, so no two in a car park look alike; a caller may set its own (a fresh delivery, a farm truck).
	grime = g
	wear = w
	for mi in find_children("*", "MeshInstance3D", true, false):
		(mi as GeometryInstance3D).set_instance_shader_parameter("grime", g)
		(mi as GeometryInstance3D).set_instance_shader_parameter("wear", w)


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
	frame.centres = proto.centres
	frame.orders = proto.orders
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
		if gr.inside or is_interior_mat(str(gr.mat)):
			mi.layers = INTERIOR_LAYER
		skel.add_child(mi)
		_groups[key] = mi
	for mid in plan.moving:
		var mv: Dictionary = plan.moving[mid]
		var node := MeshInstance3D.new()
		node.name = mid
		var am := ArrayMesh.new()
		var am_in := ArrayMesh.new()                              # (its interior surfaces: the cabin layer)
		for m in mv.geo:
			var arr := []
			arr.resize(Mesh.ARRAY_MAX)
			arr[Mesh.ARRAY_VERTEX] = mv.geo[m][0]
			arr[Mesh.ARRAY_NORMAL] = mv.geo[m][1]
			if (mv.geo[m] as Array).size() > 2 and (mv.geo[m][2] as PackedFloat32Array).size() == (mv.geo[m][0] as PackedVector3Array).size():
				arr[Mesh.ARRAY_COLOR] = wear_colors(mv.geo[m][2], (mv.geo[m][0] as PackedVector3Array).size())
			var tgt := am_in if is_interior_mat(str(m)) else am
			tgt.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
			tgt.surface_set_material(tgt.get_surface_count() - 1, _material(style, str(m)))
		node.mesh = am
		node.position = Vector3(0, 0, float(mv.anchor))
		add_child(node)
		if am_in.get_surface_count() > 0:
			var inner := MeshInstance3D.new()
			inner.name = mid + "_in"
			inner.mesh = am_in
			inner.layers = INTERIOR_LAYER
			inner.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			node.add_child(inner)
	for mk in plan.bp.markers:
		var n := Node3D.new()
		n.name = str(mk[0])
		n.position = Vector3(mk[1][0], mk[1][1], mk[1][2])
		n.rotation.y = float(mk[2])
		add_child(n)
	_decals()
	_gauges()


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
	frame.update_turns()
	for i in frame.nodes.size():
		skel.set_bone_pose_position(i, frame.nodes[i])
		skel.set_bone_pose_rotation(i, frame.rot[i])                # (the skin's normals turn with the dent)
	var out: Array = []
	var proto: TubeFrame = plan.frame_proto
	var share := float(plan.std.get("detach_share", 0.3))
	for mid in plan.mounts:
		if _gone.has(mid):
			continue
		var m: Dictionary = plan.modules[mid]
		var tol := float(m.tolerance)
		var pairs: PackedInt32Array = plan.lines.get(mid, PackedInt32Array())
		var brittle := str(m.breaks) == "shatter"
		var n_pairs := pairs.size() / 2
		if n_pairs == 0:
			continue
		var over := 0
		for k in n_pairs:
			var a := pairs[k * 2]
			var b := pairs[k * 2 + 1]
			var r := proto.nodes_rest[a].distance_to(proto.nodes_rest[b])
			if absf(frame.nodes[a].distance_to(frame.nodes[b]) / r - 1.0) > tol:
				over += 1
		if (brittle and over >= 1) or over >= mini(int(plan.std.get("detach_count", 3)), maxi(2, ceili(n_pairs * share))):
			out.append(mid)
	return out


func displaced(rest: Vector3) -> Vector3:
	## Where a point of the section (as built) is now.
	return frame.deformed(rest, frame.bind(rest))


func break_off(mid: String, how: String, velocity: Vector3) -> void:
	## The component leaves the body: as debris with its mass (detach), or in shards (shatter).
	if _gone.has(mid) or not plan.ranges.has(mid):
		return
	_gone[mid] = true
	if how == "shatter":
		_shards(mid, velocity)
	elif how != "none":
		_debris(mid, velocity)
		if not str(plan.modules[mid].role) in NO_FLANGE:
			_flange(mid)                                     # (it tore off: its edges stay on the frame)
	_rebuild()


const NO_FLANGE := ["seat", "stanchion", "fittings", "podium", "cab", "floor", "glazing", "door_glass"]
var _extra := {}                      # group key -> {pos, nor, bones, weights}: torn flanges left on the frame


func _flange(mid: String) -> void:
	## The torn edge a panel leaves where it was fastened: along each of its outline edges (the edges only
	## one of its triangles has -- its perimeter and the edges of its openings), a jagged strip of its own
	## sheet, 1-4 cm wide, bound to the frame like the rest of the skin.
	var proto: TubeFrame = plan.frame_proto
	for r in plan.ranges.get(mid, []):
		var gr: Dictionary = plan.groups[r[0]]
		var edges := {}
		for i in range(r[1], r[2] - 2, 3):
			var t := [gr.pos[i], gr.pos[i + 1], gr.pos[i + 2]]
			var n: Vector3 = gr.nor[i]
			for k in 3:
				var a: Vector3 = t[k]
				var b: Vector3 = t[(k + 1) % 3]
				var ka := Vector3i(roundi(a.x * 1000), roundi(a.y * 1000), roundi(a.z * 1000))
				var kb := Vector3i(roundi(b.x * 1000), roundi(b.y * 1000), roundi(b.z * 1000))
				var key := [ka, kb] if str(ka) < str(kb) else [kb, ka]
				var ks := str(key)
				if edges.has(ks):
					edges[ks][0] += 1
				else:
					edges[ks] = [1, a, b, t[(k + 2) % 3], n]
		if not _extra.has(r[0]):
			_extra[r[0]] = {"pos": PackedVector3Array(), "nor": PackedVector3Array(), "bones": PackedInt32Array(), "weights": PackedFloat32Array()}
		var ex: Dictionary = _extra[r[0]]
		var ep: PackedVector3Array = ex.pos
		var en: PackedVector3Array = ex.nor
		var eb: PackedInt32Array = ex.bones
		var ew: PackedFloat32Array = ex.weights
		for ks in edges:
			var e: Array = edges[ks]
			if int(e[0]) != 1:
				continue
			var a: Vector3 = e[1]
			var b: Vector3 = e[2]
			var n: Vector3 = e[4]
			var along := b - a
			var L := along.length()
			if L < 0.01:
				continue
			var inward := n.cross(along).normalized()
			if inward.dot((e[3] as Vector3) - a) < 0.0:
				inward = -inward
			var steps := maxi(1, ceili(L / 0.06))
			for st in steps:
				var pa := a.lerp(b, float(st) / steps)
				var pb := a.lerp(b, float(st + 1) / steps)
				var qa := pa + inward * _tear(pa)
				var qb := pb + inward * _tear(pb)
				for v in [pa, pb, qb, pa, qb, qa]:
					var bd := proto.bind(v)
					ep.append(v)
					en.append(n)
					for k in 4:
						eb.append(int(bd[0][k]))
						ew.append(float(bd[1][k]))
		ex.pos = ep
		ex.nor = en
		ex.bones = eb
		ex.weights = ew


static func _tear(p: Vector3) -> float:
	## How far the torn strip reaches in from the edge at p (jagged, the same every time at the same place).
	var h := fposmod(sin(p.dot(Vector3(12.9898, 78.233, 37.719))) * 43758.5453, 1.0)
	return 0.012 + 0.03 * h


func _rebuild() -> void:
	## The groups without the components gone, with the torn flanges they left (this body's own meshes from
	## now on).
	var drop := {}
	for mid in _gone:
		for r in plan.ranges.get(mid, []):
			if not drop.has(r[0]):
				drop[r[0]] = []
			drop[r[0]].append([r[1], r[2]])
	for key in _extra:
		if not drop.has(key):
			drop[key] = []
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
		var wr := PackedFloat32Array()
		var gwr: PackedFloat32Array = gr.get("wear", PackedFloat32Array())
		for i in keep.size():
			if keep[i] == 0:
				continue
			pos.append(gr.pos[i])
			nor.append(gr.nor[i])
			wr.append(gwr[i] if i < gwr.size() else 0.0)
			for k in 4:
				bones.append(gr.bones[i * 4 + k])
				weights.append(gr.weights[i * 4 + k])
		if _extra.has(key):
			pos.append_array(_extra[key].pos)
			nor.append_array(_extra[key].nor)
			bones.append_array(_extra[key].bones)
			weights.append_array(_extra[key].weights)
			var torn := PackedFloat32Array()                  # (a torn edge: worn bright, the whole of it)
			torn.resize((_extra[key].pos as PackedVector3Array).size())
			torn.fill(1.0)
			wr.append_array(torn)
		(_groups[key] as MeshInstance3D).mesh = _mesh_of(pos, nor, bones, weights, wr)
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
			pos.append(frame.deformed(gr.pos[i], b))
			var nq := Quaternion.IDENTITY                             # (its normal turned as the skin draws it)
			if frame.rot.size() > 0:
				nq = frame.rot[int(b[0][0])]
			nor.append(nq * gr.nor[i])
		if pos.is_empty():
			continue
		_last_pts.append_array(pos)
		var arr := []
		arr.resize(Mesh.ARRAY_MAX)
		arr[Mesh.ARRAY_VERTEX] = pos
		arr[Mesh.ARRAY_NORMAL] = nor
		var gw: PackedFloat32Array = gr.get("wear", PackedFloat32Array())
		if gw.size() >= r[2]:
			arr[Mesh.ARRAY_COLOR] = wear_colors(gw.slice(r[1], r[2]), pos.size())
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


# -- decals ------------------------------------------------------------------------------------------------
const DECAL_DIR := "res://remake/vehicles/decals/"
const DECAL_FADE := 45.0                 # m: past this they fade out (they're cheap, but a car park is many)
static var _decal_tex := {}


static func _decal_texture(name: String) -> Texture2D:
	if not _decal_tex.has(name):
		var path := DECAL_DIR + name + ".png"
		_decal_tex[name] = load(path) if ResourceLoader.exists(path) else null
	return _decal_tex[name]


func _decals() -> void:
	## The blueprint's decals (tools/assets/decals.py, remake/blender/fleet/decals.py): each a Decal projected onto the
	## panel under it, riding with the body; one plate and one fleet number of its own per vehicle.
	var plate := "plate_%d" % (randi() % 8)
	var num := "num_%02d" % (1 + randi() % 24)
	for d in plan.bp.get("decals", []):
		var nm := str(d[0])
		var tex := _decal_texture(plate if nm == "plate" else (num if nm == "num" else nm))
		if tex == null:
			continue
		var n := Vector3(d[2][0], d[2][1], d[2][2]).normalized()
		var u := Vector3(d[3][0], d[3][1], d[3][2])
		u = (u - n * u.dot(n)).normalized()
		var dc := Decal.new()
		dc.name = "Decal_" + nm
		dc.texture_albedo = tex
		dc.size = Vector3(float(d[4]), 0.25, float(d[5]))
		dc.transform = Transform3D(Basis(u.cross(n), n, -u), Vector3(d[1][0], d[1][1], d[1][2]))
		if d[6] != null:
			dc.modulate = Color(d[6][0], d[6][1], d[6][2])
		dc.normal_fade = 0.4
		dc.upper_fade = 0.0
		dc.lower_fade = 0.0
		dc.distance_fade_enabled = true
		dc.distance_fade_begin = DECAL_FADE
		dc.distance_fade_length = 15.0
		add_child(dc)


# -- the instruments -----------------------------------------------------------------------------------------
var _needles := {}                       # kind -> the needle's pivot (Node3D)
const SPEED_FULL := 160.0                # km/h at the speedometer's end stop
static var _dial_mats := {}


static func _dial_material(kind: String) -> StandardMaterial3D:
	if not _dial_mats.has(kind):
		var m := StandardMaterial3D.new()
		var tex := _decal_texture("dial_" + kind)
		m.albedo_texture = tex
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
		m.emission_enabled = true                         # (backlit, faintly: readable at night)
		m.emission_texture = tex
		m.emission_energy_multiplier = 0.35
		m.cull_mode = BaseMaterial3D.CULL_BACK
		_dial_mats[kind] = m
	return _dial_mats[kind]


func _gauges() -> void:
	## The binnacle's dials (the blueprint's "gauges", Builder.station): a face square to the driver's eye and a needle
	## the vehicle turns -- the speedometer (0..160 km/h) and the charge (E..F), 270 degrees each.
	var nm := StandardMaterial3D.new()
	nm.albedo_color = Color(0.85, 0.12, 0.08)
	nm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	for gd in plan.bp.get("gauges", []):
		var kind := str(gd[0])
		var n := Vector3(gd[2][0], gd[2][1], gd[2][2]).normalized()
		var u := Vector3(gd[3][0], gd[3][1], gd[3][2])
		u = (u - n * u.dot(n)).normalized()
		var r := float(gd[4])
		var dial := Node3D.new()
		dial.name = "Gauge_" + kind
		# (1.2 cm proud of the binnacle's back panel: on it, the panel won the depth test and hid the face)
		dial.transform = Transform3D(Basis(u.cross(n), u, n), Vector3(gd[1][0], gd[1][1], gd[1][2]) + n * 0.012)
		add_child(dial)
		var face := MeshInstance3D.new()
		var q := QuadMesh.new()
		q.size = Vector2(r * 2.0, r * 2.0)
		face.mesh = q
		face.material_override = _dial_material(kind)
		face.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		dial.add_child(face)
		var piv := Node3D.new()
		piv.name = "Needle"
		piv.position = Vector3(0, 0, 0.004)
		dial.add_child(piv)
		var needle := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = Vector3(r * 0.07, r * 0.82, 0.003)
		needle.mesh = bm
		needle.position = Vector3(0, r * 0.33, 0)
		needle.material_override = nm
		needle.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		piv.add_child(needle)
		_needles[kind] = piv
		for nd in [face, needle]:
			(nd as GeometryInstance3D).visibility_range_end = INSIDE_RANGE
			(nd as GeometryInstance3D).layers = INTERIOR_LAYER
	set_gauges(0.0, 1.0)


func set_gauges(speed_kmh: float, charge: float) -> void:
	## Turn the needles: speed in km/h, charge 0..1 (the needle sweeps from 225 deg, lower left, clockwise to -45).
	for kind in _needles:
		var f := clampf(speed_kmh / SPEED_FULL, 0.0, 1.0) if kind == "speed" else clampf(charge, 0.0, 1.0)
		(_needles[kind] as Node3D).rotation.z = deg_to_rad(135.0 - 270.0 * f)
