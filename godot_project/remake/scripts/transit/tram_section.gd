extends Node3D
class_name TramSection

## One section of a road tram: a Carrow Coach Company body (remake/vehicles/tram/carrow_tram_*.glb,
## built by remake/blender/tram/carrow_tram.py) bolted onto a Steward tram board (remake/vehicles/
## chassis/steward_tram.glb). TransitVehicle places it every physics tick; it does the rest:
##   - its body is modules (carrow_tram.json): each panel, pane, door leaf, seat and roof bay has its
##     own collision boxes and hit points; a hit (a vehicle's knock, a shot) damages the modules
##     near it, and a module at 0 hp shatters (glass) or comes off as a loose piece with its mass;
##   - the doors: double plug doors on both sides; the curbside ones open by themselves when the
##     tram stands at a stop (open_curbside), the others only by hand (E) and only when it stands;
##     an open door's ramp folds out (a slope people walk up);
##   - the glass is transparent; the lamps light (headlights, tail and brake lights, the cabin);
##   - both axles steer (steer()), the wheels turn with the distance run;
##   - anyone standing inside is carried (StationPlayer.carrier_velocity), and sheltered.
## Frame: the board's -- y up, -z forward, the origin on the ground midway between the axles.

const SPEC := "res://remake/vehicles/tram/carrow_tram.json"
const BOARD := "res://remake/vehicles/chassis/steward_tram.glb"
const DOOR_TIME := 1.0
const RAMP_LAYER := 1 << 4
const LOD_NEAR := 70.0                # m: closer, the full section; farther, the one-mesh model (body and wheels)
const LOD_FAR := 600.0
static var _spec: Dictionary
static var _scenes := {}
static var _glass: StandardMaterial3D

var kind := "mid"
var spec: Dictionary
var body: Node3D
var board: Node3D
var hull: AnimatableBody3D
var hp := {}                          # module -> hp left
var shapes := {}                      # module -> [CollisionShape3D]
var meshes := {}                      # module -> MeshInstance3D
var doors: Array = []                 # {spec, open (target), t (0..1), leaves: [[nodes, shapes, closed xfs, offset]], ramp, ramp_body}
var wheels := {}                      # "F"/"B" -> [Node3D wheel, ...]
var lamps := {}                       # "head" / "tail" / "cabin" / "brake" -> [Light3D]
var lamp_mats := {}                   # "lamp_head" ... -> [StandardMaterial3D] (this section's copies)
var vehicle: Node                     # the TransitVehicle
var _spin := 0.0
var _prev := Transform3D()
var _have_prev := false
var _riders: Array = []
var _merged: Array = []               # the merged meshes (_merge)
var _merged_from := {}                # the module meshes drawn by them
var _lod_on := false
var _debris: Array = []


static func load_spec() -> Dictionary:
	if _spec.is_empty():
		_spec = JSON.parse_string(FileAccess.get_file_as_string(SPEC))
	return _spec


static func _scene(path: String) -> PackedScene:
	if not _scenes.has(path):
		_scenes[path] = load(path)
	return _scenes[path]


static func length_front(k: String) -> float:
	return float(load_spec().sections[k].length_front)


static func length_back(k: String) -> float:
	return float(load_spec().sections[k].length_back)


func setup(p_kind: String, p_vehicle: Node) -> void:
	kind = p_kind
	vehicle = p_vehicle
	spec = load_spec().sections[kind]
	name = "Section_" + kind
	Prof.begin("sec.board")
	board = _scene(BOARD).instantiate()
	add_child(board)
	# frugal up close (the user): the board's deck, caps and socket are hidden under the body's floor,
	# skirts and podiums -- only the pods and wheels show, through the arches
	for n in board.find_children("*", "Node3D", true, false):
		var nm := str(n.name)
		if nm.begins_with("span_") or nm.begins_with("cap_") or nm == "socket" or nm.begins_with("mount_"):
			n.queue_free()
	Prof.end("sec.board")
	Prof.begin("sec.body")
	body = _scene(spec.glb).instantiate()
	add_child(body)
	for tag in ["F", "B"]:
		wheels[tag] = []
		for s in ["L", "R"]:
			var w := board.find_child("wheel_%s%s" % [tag, s], true, false) as Node3D
			if w:
				wheels[tag].append([w, w.transform])
	Prof.end("sec.body")
	Prof.begin("sec.modules")
	hull = TramHull.new()
	hull.name = "Hull"
	hull.section = self
	hull.sync_to_physics = true
	hull.top_level = true                # a synced body doesn't follow its parent: sync_bodies() moves it
	hull.collision_layer = 1 | RemakeGroundVehicle.HULL_LAYER
	hull.collision_mask = 0
	var mods: Dictionary = spec.modules
	var by_name := {}                      # (one walk of the body, not one search per module)
	for n in body.find_children("*", "", true, false):
		by_name[str(n.name)] = n
	for mid in mods:
		var m: Dictionary = mods[mid]
		hp[mid] = float(m.hp)
		var mi: Node = by_name.get(mid)
		if mi:
			meshes[mid] = mi
		var list: Array = []
		for b in m.boxes:
			var cs := CollisionShape3D.new()
			var sh := BoxShape3D.new()
			sh.size = Vector3(b[3], b[4], b[5]).max(Vector3.ONE * 0.02)
			cs.shape = sh
			cs.position = Vector3(b[0], b[1], b[2])
			hull.add_child(cs)
			list.append(cs)
		shapes[mid] = list
		if str(m.kind) == "ramp" and mi:
			(mi as Node3D).visible = false
			for cs in list:
				(cs as CollisionShape3D).disabled = true
	add_child(hull)                       # (into the world with all its shapes: one by one, the physics
	                                      # rebuilt the hull's compound shape at every box -- 14 ms a tram)
	Prof.end("sec.modules")
	Prof.begin("sec.materials")
	_materials()
	Prof.end("sec.materials")
	Prof.begin("sec.doors")
	_doors()
	_lights()
	_cheap()
	Prof.end("sec.doors")
	Prof.begin("sec.merge")
	_merge()
	Prof.end("sec.merge")
	Prof.begin("sec.lod")
	_lod()
	Prof.end("sec.lod")


# -- looks ------------------------------------------------------------------------------------------

func _materials() -> void:
	## Glass made transparent; the lamps' materials copied per section (so each can light on its own).
	if _glass == null:
		_glass = StandardMaterial3D.new()
		_glass.albedo_color = Color(0.72, 0.84, 0.86, 0.22)
		_glass.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		_glass.cull_mode = BaseMaterial3D.CULL_DISABLED
		_glass.roughness = 0.05
		_glass.metallic_specular = 0.9
	# (a kind merged before draws its modules from the shared merge: only what moves -- door leaves
	# and their glass, the ramps -- needs its own materials now; a module gets them if it comes loose)
	var cached := _merge_cache.has(kind)
	for mi in body.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		var nm0 := str(m.name)
		var moves: bool = nm0.begins_with("door_") or (nm0.begins_with("glass_") and (nm0.ends_with("_9") or nm0.ends_with("_16"))) \
			or (spec.modules.has(nm0) and str(spec.modules[nm0].kind) == "ramp")
		_apply_materials(m, cached and not moves)


func _apply_materials(m: MeshInstance3D, lamps_only := false) -> void:
	## Glass made transparent; the lamps' materials copied per section (one copy per lamp name when
	## lamps_only: the merged body's lamps use those).
	for i in m.mesh.get_surface_count():
		var mat := m.mesh.surface_get_material(i)
		if mat == null:
			continue
		var nm := str(mat.resource_name)
		if nm.begins_with("glass"):
			if not lamps_only:
				m.set_surface_override_material(i, _glass)
		elif nm.begins_with("lamp_") or nm == "dest":
			if lamps_only and lamp_mats.has(nm):
				continue
			var c := (mat as BaseMaterial3D).duplicate() as BaseMaterial3D
			if not lamps_only:
				m.set_surface_override_material(i, c)
			if not lamp_mats.has(nm):
				lamp_mats[nm] = []
			lamp_mats[nm].append(c)


func _cheap() -> void:
	## Inside fittings cast no shadows and aren't drawn from far off; nor is the glass a shadow.
	const INSIDE := ["seat", "stanchion", "fittings", "podium", "cab", "floor"]
	for mid in meshes:
		var k := str(spec.modules[mid].kind)
		var mi := meshes[mid] as GeometryInstance3D
		if mi == null:
			continue
		if k in INSIDE or k == "glass":
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		if k in INSIDE:
			mi.visibility_range_end = 45.0
	for mi in board.find_children("*", "GeometryInstance3D", true, false):
		(mi as GeometryInstance3D).visibility_range_end = 120.0


func _merge() -> void:
	## Drawn as a few meshes, one per material (and shadow kind): a section is some 270 modules, each
	## its own mesh for the damage -- drawn one by one that was ~800 draw calls a tram. The modules stay,
	## hidden, for damage; a broken one is left out of the next merge. Door leaves and ramps move, so
	## they are drawn on their own.
	var moving := {}
	for d in doors:
		for lf in d.leaves:
			for n in lf.nodes:
				moving[n] = true
		if d.ramp:
			moving[d.ramp] = true
	var damaged := false
	for mid in hp:
		if float(hp[mid]) <= 0.0:
			damaged = true
	if not damaged and _merge_cache.has(kind):
		_merge_from_cache(moving)
		return
	var groups := {}                      # key -> [material, shadow, inside, SurfaceTool]
	for mi in body.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		if moving.has(m) or m.mesh == null or str(m.name).begins_with("Merged_"):
			continue
		var mid := str(m.name)
		if hp.has(mid) and float(hp[mid]) <= 0.0:
			m.visible = false
			continue
		if not m.visible and not _merged_from.has(m):
			continue                                  # (hidden for its own reasons)
		var xf := body.global_transform.affine_inverse() * m.global_transform if m.is_inside_tree() else _rel_xf(m)
		var kind := str(spec.modules[mid].kind) if spec.modules.has(mid) else ""
		var inside := kind in ["seat", "stanchion", "fittings", "podium", "cab", "floor"]
		for i in m.mesh.get_surface_count():
			var mat: Material = m.get_surface_override_material(i)
			if mat == null:
				mat = m.material_override if m.material_override else m.mesh.surface_get_material(i)
			var shadow := m.cast_shadow != GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			var key := "%d|%s|%s" % [mat.get_instance_id() if mat else 0, shadow, inside]
			if not groups.has(key):
				var st := SurfaceTool.new()
				groups[key] = [mat, shadow, inside, st, false]
			(groups[key][3] as SurfaceTool).append_from(m.mesh, i, xf)
			groups[key][4] = true
		m.visible = false
		_merged_from[m] = true
	for n in _merged:
		(n as Node).queue_free()
	_merged.clear()
	var k := 0
	var cached: Array = []
	for key in groups:
		var g: Array = groups[key]
		if not g[4]:
			continue
		var mesh := (g[3] as SurfaceTool).commit()
		var mat_name := str((g[0] as Material).resource_name) if g[0] else ""
		cached.append([mesh, g[0], g[1], g[2], mat_name if mat_name.begins_with("lamp_") or mat_name == "dest" else ""])
		var out := MeshInstance3D.new()
		out.name = "Merged_%d" % k
		k += 1
		out.mesh = mesh
		out.material_override = g[0]
		out.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if g[1] else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		out.visibility_range_end = 45.0 if g[2] else (LOD_NEAR if _lod_on else 0.0)
		body.add_child(out)
		_merged.append(out)
	if not damaged:
		_merge_cache[kind] = cached


static var _merge_cache := {}          # section kind -> [[mesh, material, shadow, inside, lamp name]] (undamaged)


func _merge_from_cache(moving: Dictionary) -> void:
	## An undamaged section of a kind built before: its merged meshes are shared (only the lamp
	## materials are this section's own, so each lights on its own).
	for mi in body.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		if moving.has(m) or m.mesh == null or not m.visible:
			continue
		m.visible = false
		_merged_from[m] = true
	var k := 0
	for g in _merge_cache[kind]:
		var out := MeshInstance3D.new()
		out.name = "Merged_%d" % k
		k += 1
		out.mesh = g[0]
		var lamp: String = g[4]
		out.material_override = (lamp_mats[lamp][0] if lamp != "" and lamp_mats.has(lamp) else g[1])
		out.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if g[2] else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		out.visibility_range_end = 45.0 if g[3] else (LOD_NEAR if _lod_on else 0.0)
		body.add_child(out)
		_merged.append(out)


func _rel_xf(n: Node3D) -> Transform3D:
	## n's transform relative to the body, up the parent chain (before the section is in the tree).
	var xf := Transform3D.IDENTITY
	var at: Node = n
	while at != null and at != body:
		xf = (at as Node3D).transform * xf
		at = at.get_parent()
	return xf


func _lod() -> void:
	## Far off, the section is one low-poly mesh with its wheels (carrow_tram_*_lod.glb, built with the
	## body); near, the full body and board. (Visibility ranges, so the renderer swaps them per camera.)
	var path := str(spec.get("lod_glb", ""))
	if path == "" or not ResourceLoader.exists(path):
		return
	_lod_on = true
	var lod: Node3D = _scene(path).instantiate()
	lod.name = "LOD"
	add_child(lod)
	for gi in lod.find_children("*", "GeometryInstance3D", true, false):
		(gi as GeometryInstance3D).visibility_range_begin = LOD_NEAR
		(gi as GeometryInstance3D).visibility_range_end = LOD_FAR
		(gi as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	for root in [body, board]:
		for gi in root.find_children("*", "GeometryInstance3D", true, false):
			var g := gi as GeometryInstance3D
			g.visibility_range_end = minf(g.visibility_range_end, LOD_NEAR) if g.visibility_range_end > 0.0 else LOD_NEAR


func _lights() -> void:
	for mk in body.find_children("light_*", "Node3D", true, false):
		var n := str(mk.name)
		var l: Light3D
		var group := ""
		if n.begins_with("light_head"):
			var sp := SpotLight3D.new()
			sp.spot_range = 45.0
			sp.spot_angle = 26.0
			sp.light_color = Color(1.0, 0.96, 0.86)
			l = sp
			group = "head"
		elif n.begins_with("light_tail") or n == "light_brake":
			var om := OmniLight3D.new()
			om.omni_range = 3.5 if n != "light_brake" else 5.0
			om.light_color = Color(1.0, 0.12, 0.08)
			l = om
			group = "brake" if n == "light_brake" else "tail"
		elif n.begins_with("light_cabin"):
			var om2 := OmniLight3D.new()
			om2.omni_range = 6.5
			om2.light_color = Color(1.0, 0.97, 0.9)
			l = om2
			group = "cabin"
		else:
			continue
		l.shadow_enabled = false
		mk.add_child(l)
		if not lamps.has(group):
			lamps[group] = []
		lamps[group].append(l)


func set_lights(night: float, braking: bool) -> void:
	## night 0 (day) .. 1 (night)
	# real lights only when they show (dusk to dawn; the brake lamp when braking): by day the
	# lamps' glowing lenses are enough
	var dark := night > 0.05
	for l in lamps.get("head", []):
		(l as Light3D).visible = dark
		(l as Light3D).light_energy = lerpf(0.4, 3.0, night)
	for l in lamps.get("tail", []):
		(l as Light3D).visible = dark
		(l as Light3D).light_energy = lerpf(0.2, 1.0, night) * (2.0 if braking else 1.0)
	for l in lamps.get("brake", []):
		(l as Light3D).visible = braking and dark
		(l as Light3D).light_energy = 1.5
	for l in lamps.get("cabin", []):
		(l as Light3D).visible = dark
		(l as Light3D).light_energy = lerpf(0.15, 0.9, night)
	for m in lamp_mats.get("lamp_ceiling", []):
		(m as BaseMaterial3D).emission_energy_multiplier = lerpf(0.4, 1.6, night)
	for m in lamp_mats.get("lamp_tail", []):
		(m as BaseMaterial3D).emission_energy_multiplier = (4.0 if braking else 1.8)
	for m in lamp_mats.get("lamp_head", []):
		(m as BaseMaterial3D).emission_energy_multiplier = lerpf(1.5, 4.0, night)


# -- doors --------------------------------------------------------------------------------------------

func _doors() -> void:
	for d in spec.doors:
		var leaves: Array = []
		for lf in d.leaves:
			var nodes: Array = []
			var shp: Array = []
			var base: String = str(lf.node)
			var did: String = base.substr(5)                     # "R0_a"
			for mid in [base, "glass_%s_9" % did, "glass_%s_16" % did]:
				if meshes.has(mid):
					nodes.append(meshes[mid])
				shp.append_array(shapes.get(mid, []))
			var closed: Array = []
			for n in nodes:
				closed.append((n as Node3D).position)
			var sclosed: Array = []
			for s in shp:
				sclosed.append((s as Node3D).position)
			leaves.append({"nodes": nodes, "shapes": shp, "closed": closed, "sclosed": sclosed, "open": Vector3(lf.open[0], lf.open[1], lf.open[2])})
		var ramp_mi: Node3D = meshes.get(str(d.ramp))
		var rb := AnimatableBody3D.new()
		rb.name = "Ramp_" + str(d.id)
		rb.sync_to_physics = true
		rb.top_level = true
		rb.collision_layer = RAMP_LAYER | 1
		rb.collision_mask = 0
		var rbox: Dictionary = d.ramp_box
		var a := Vector2(rbox.from[0], rbox.from[1])
		var b := Vector2(rbox.to[0], rbox.to[1])
		var cs := CollisionShape3D.new()
		var sh := BoxShape3D.new()
		sh.size = Vector3((b - a).length(), 0.05, float(rbox.width))
		cs.shape = sh
		cs.position = Vector3((a.x + b.x) / 2, (a.y + b.y) / 2 - 0.025, float(rbox.z))
		cs.rotation.z = atan2(b.y - a.y, b.x - a.x)
		cs.disabled = true
		rb.add_child(cs)
		add_child(rb)
		var zone := RemakeInteractZone.make(self, "Door_" + str(d.id), Transform3D(Basis(), Vector3(signf(float(rbox.from[0])) * 1.1, 1.5, float(d.z))),
			Vector3(0.6, 2.0, float(d.width)), _door_use.bind(doors.size()), _door_prompt.bind(doors.size()))
		zone.gives_way = true
		doors.append({"spec": d, "open": false, "t": 0.0, "leaves": leaves, "ramp": ramp_mi, "ramp_shape": cs, "ramp_body": rb})


func _door_prompt(i: int) -> String:
	var d: Dictionary = doors[i]
	if not vehicle or not vehicle.stopped():
		return ""
	return "Close the doors" if d.open else "Open the doors"


func _door_use(_by: Node, i: int) -> String:
	if not vehicle or not vehicle.stopped():
		return ""
	doors[i].open = not doors[i].open
	return "doors"


func open_curbside(on: bool) -> void:
	for d in doors:
		if bool(d.spec.curbside):
			d.open = on


func close_all() -> void:
	for d in doors:
		d.open = false


func doors_settled(open: bool) -> bool:
	for d in doors:
		if bool(d.spec.curbside) and (float(d.t) < 1.0 if open else float(d.t) > 0.0):
			return false
	return true


func curbside_doors() -> Array:
	var out: Array = []
	for d in doors:
		if bool(d.spec.curbside):
			out.append(d)
	return out


func _animate_doors(delta: float) -> void:
	for d in doors:
		var target := 1.0 if d.open else 0.0
		if is_equal_approx(float(d.t), target):
			continue
		d.t = move_toward(float(d.t), target, delta / DOOR_TIME)
		var e := smoothstep(0.0, 1.0, float(d.t))
		# the plug door: out first, then along
		var out_k := clampf(e * 4.0, 0.0, 1.0)
		var along_k := clampf((e - 0.15) / 0.85, 0.0, 1.0)
		for lf in d.leaves:
			var off: Vector3 = lf.open
			var v := Vector3(off.x * out_k, 0.0, off.z * along_k)
			for k in lf.nodes.size():
				if is_instance_valid(lf.nodes[k]):
					(lf.nodes[k] as Node3D).position = lf.closed[k] + v
			for k in lf.shapes.size():
				(lf.shapes[k] as Node3D).position = lf.sclosed[k] + v
		var deployed := float(d.t) > 0.85
		if d.ramp:
			(d.ramp as Node3D).visible = float(d.t) > 0.5
		(d.ramp_shape as CollisionShape3D).disabled = not deployed


# -- motion -----------------------------------------------------------------------------------------

func sync_bodies() -> void:
	## After the section is placed (each physics tick): its collision bodies to it, so they move
	## kinematically -- with a velocity people standing on them feel.
	hull.global_transform = global_transform
	for d in doors:
		(d.ramp_body as Node3D).global_transform = global_transform


func steer(front: float, back: float, run: float, wheel_r: float) -> void:
	## Both axles steer (the angles in radians, + to the left); the wheels turn with the distance run.
	_spin = fposmod(_spin + run / wheel_r, TAU)
	for tag in wheels:
		var a := front if tag == "F" else back
		for w in wheels[tag]:
			var n := w[0] as Node3D
			n.transform = (w[1] as Transform3D) * Transform3D(Basis(Vector3.UP, a) * Basis(Vector3.RIGHT, -_spin), Vector3.ZERO)


func _physics_process(delta: float) -> void:
	Prof.begin("tram.section_tick")
	_animate_doors(delta)
	_have_prev = true                    # (TransitVehicle carries the people aboard, before this)
	_prev = global_transform
	for d in _debris.duplicate():
		if not is_instance_valid(d):
			_debris.erase(d)
	Prof.end("tram.section_tick")


func holds(lp: Vector3) -> bool:
	## Is a person's origin (their eyes) at lp -- in the section's frame -- inside it? (Each end 0.4 m
	## past the portal: the two sections' spaces overlap across the joint's walkway.)
	return absf(lp.x) < 1.3 and lp.y > 0.2 and lp.y < 3.0 and lp.z > -float(spec.length_front) - 0.4 \
		and lp.z < float(spec.length_back) + 0.4


func door_exit(lp: Vector3) -> bool:
	## Is lp out through one of the section's doorways, open (more than half)?
	for d in doors:
		if float(d.t) < 0.5:
			continue
		var side := signf(float(d.spec.ramp_box.from[0]))
		if signf(lp.x) == side and absf(lp.z - float(d.spec.z)) < float(d.spec.width) * 0.5 + 0.3:
			return true
	return false


func carry_at(p: StationPlayer, lp: Vector3, delta: float) -> void:
	## Move p with the section: its own motion at lp (lp in last tick's frame).
	p.carrier_velocity = (global_transform * lp - _prev * lp) / delta
	p.sheltered = true
	# and turn with it (a rider faces the same way in the tram round a bend)
	var up := global_transform.basis.y
	var yaw := _prev.basis.z.slide(up).signed_angle_to(global_transform.basis.z.slide(up), up)
	if absf(yaw) > 1e-5 and absf(yaw) < 0.3:
		p.global_rotate(up, yaw)


func velocity() -> Vector3:
	## The section's velocity this tick (it is placed, not simulated).
	var dt := get_physics_process_delta_time()
	return (global_transform.origin - _prev.origin) / dt if _have_prev and dt > 0.0 else Vector3.ZERO


func prev_xf() -> Transform3D:
	return _prev if _have_prev else global_transform


func set_riders(now: Array) -> void:
	_riders = now


func carries(p: Node) -> bool:
	return _riders.has(p)


# -- damage -------------------------------------------------------------------------------------------

func hit_at(local_point: Vector3, amount: float) -> void:
	## Damage spread over the modules near a point (section frame): most to the nearest.
	var near: Array = []
	for mid in shapes:
		if hp.get(mid, 0.0) <= 0.0 or str(spec.modules[mid].breaks) == "none":
			continue
		var best := INF
		for cs in shapes[mid]:
			var c := cs as CollisionShape3D
			var half := (c.shape as BoxShape3D).size * 0.5
			var q := (local_point - c.position).abs() - half
			best = minf(best, Vector3(maxf(q.x, 0.0), maxf(q.y, 0.0), maxf(q.z, 0.0)).length())
		if best < 1.6:
			near.append([best, mid])
	near.sort_custom(func(a, b): return a[0] < b[0])
	var share := 1.0
	for e in near.slice(0, 6):
		var w := share * (0.6 if e[0] > 0.05 else 0.75)
		damage(e[1], amount * w)
		share -= w * 0.8
		if share < 0.05:
			break


func knock_from(by: Node3D, v_by: Vector3, m_by: float) -> void:
	## A vehicle ran into the section: the energy above a slow nudge goes into the panels it hit.
	var rel := v_by - (global_transform.origin - _prev.origin) / maxf(get_physics_process_delta_time(), 1e-3)
	var kmh := rel.length() * 3.6
	if kmh < 8.0:
		return
	var amount := pow(kmh - 8.0, 2.0) * (m_by / 1500.0) * 0.6
	hit_at(global_transform.affine_inverse() * by.global_position, amount)


func damage(mid: String, amount: float) -> void:
	if not hp.has(mid) or hp[mid] <= 0.0:
		return
	hp[mid] -= amount
	if hp[mid] > 0.0:
		return
	var m: Dictionary = spec.modules[mid]
	for cs in shapes[mid]:
		(cs as CollisionShape3D).disabled = true
	var mi: Node3D = meshes.get(mid)
	if mi == null:
		return
	if str(m.breaks) == "shatter":
		_shatter(mi)
	else:
		_detach(mid, mi, float(m.mass_kg))
	_merged_from.erase(mi)
	_merge()                                       # (drawn without it from now on)
	RoadDriver.tally["tram_parts_broken"] = int(RoadDriver.tally.get("tram_parts_broken", 0)) + 1


func _shatter(mi: Node3D) -> void:
	var at := mi.global_transform
	var bb := (mi as MeshInstance3D).get_aabb() if mi is MeshInstance3D else AABB(Vector3.ZERO, Vector3.ONE * 0.3)
	mi.visible = false
	var snd := AudioStreamPlayer3D.new()
	snd.stream = load("res://remake/audio/crash.wav")
	snd.pitch_scale = 1.8
	snd.volume_db = -4.0
	get_tree().current_scene.add_child(snd)
	snd.global_position = at * bb.get_center()
	snd.play()
	snd.finished.connect(snd.queue_free)
	for k in 5:                                    # a few shards fall away
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
		vis.material_override = _glass
		rb.add_child(vis)
		get_tree().current_scene.add_child(rb)
		var p := bb.position + Vector3(randf(), randf(), randf()) * bb.size
		rb.global_position = at * p
		rb.linear_velocity = Vector3(randf_range(-1, 1), randf_range(0, 1.5), randf_range(-1, 1))
		_debris.append(rb)
		get_tree().create_timer(8.0).timeout.connect(rb.queue_free)


func _detach(mid: String, mi: Node3D, mass: float) -> void:
	## The module comes off: its mesh on a rigid body of its own, with its mass, under the station's gravity.
	var at := mi.global_transform
	var rb := RigidBody3D.new()
	rb.name = "Debris_" + mid
	rb.mass = maxf(1.0, mass)
	rb.collision_layer = 1 << 10
	rb.collision_mask = 1
	var bb := AABB()
	var first := true
	for cs in shapes[mid]:
		var c := cs as CollisionShape3D
		var box := AABB(c.position - (c.shape as BoxShape3D).size / 2, (c.shape as BoxShape3D).size)
		bb = box if first else bb.merge(box)
		first = false
	if first:
		bb = (mi as MeshInstance3D).get_aabb() if mi is MeshInstance3D else AABB(Vector3.ZERO, Vector3.ONE * 0.3)
	var cs2 := CollisionShape3D.new()
	var sh := BoxShape3D.new()
	sh.size = bb.size.max(Vector3.ONE * 0.04)
	cs2.shape = sh
	cs2.position = bb.get_center()
	rb.add_child(cs2)
	get_tree().current_scene.add_child(rb)
	rb.global_transform = global_transform
	mi.get_parent().remove_child(mi)
	rb.add_child(mi)
	mi.global_transform = at
	mi.visible = true                              # (it was drawn as part of the merged body)
	if mi is MeshInstance3D:
		_apply_materials(mi as MeshInstance3D)
	var out := (global_transform.basis * bb.get_center()).normalized()
	rb.linear_velocity = (global_transform.origin - _prev.origin) / maxf(get_physics_process_delta_time(), 1e-3) + out * 2.0
	rb.angular_velocity = Vector3(randf_range(-2, 2), randf_range(-2, 2), randf_range(-2, 2))
	_debris.append(rb)
	get_tree().create_timer(60.0).timeout.connect(func(): if is_instance_valid(rb): rb.queue_free())
