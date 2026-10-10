extends RefCounted
class_name FleetClosers

## A fleet body's closers (its blueprint's "closers"): hinged ("door", "hatch", "lid": a hinge point, an axis, a
## travel) or sliding ("slide": out from the side, then along it or up; "roll": a shutter rolling up into its head).
## Each leaf moves to its own pivot under the body, gets its own collision (an AnimatableBody3D) and its own use
## zone on the vehicle, and eases open and shut. Shared by the road fleet (RemakeModularCar) and the aerostats
## (RemakeFleetCraft).

const DOOR_UP := 0.55                  # s: a door's swing (by hand); the lids and tailgates run slower
const LID_UP := 0.9
const LID_DOWN := 0.7
const SLIDE_T := 1.0

var closers := {}                      # id -> {pivot, axis, deg, slide, t, open, kind, leaf (AnimatableBody3D)}
var vehicle: PhysicsBody3D


func build(v: PhysicsBody3D, body: Node3D, bp: Dictionary) -> void:
	vehicle = v
	for c in bp.closers:
		var pivot := Node3D.new()
		pivot.name = "Hinge_" + str(c.id)
		var h := Vector3(c.hinge[0], c.hinge[1], c.hinge[2])
		pivot.position = h
		body.add_child(pivot)
		var box := AABB()
		var first := true
		for mid in c.parts:
			var mi := body.get_node_or_null(str(mid)) as MeshInstance3D
			if mi == null:
				continue
			var xf := mi.transform
			body.remove_child(mi)
			pivot.add_child(mi)
			mi.transform = Transform3D(Basis(), -h) * xf
			var bb := mi.transform * mi.get_aabb()
			box = bb if first else box.merge(bb)
			first = false
		if first:
			continue
		var leaf := AnimatableBody3D.new()
		leaf.name = "Leaf_" + str(c.id)
		leaf.sync_to_physics = false
		leaf.collision_layer = 1
		leaf.collision_mask = 0
		var cs := CollisionShape3D.new()
		var sh := BoxShape3D.new()
		sh.size = box.size.max(Vector3.ONE * 0.06)
		cs.shape = sh
		cs.position = box.get_center()
		leaf.add_child(cs)
		pivot.add_child(leaf)
		var kind := str(c.kind)
		var sl: Array = c.get("slide", [0, 0, 0])
		closers[str(c.id)] = {"pivot": pivot, "rest": h, "axis": Vector3(c.axis[0], c.axis[1], c.axis[2]).normalized(),
			"deg": float(c.open_deg), "slide": Vector3(sl[0], sl[1], sl[2]), "t": 0.0, "open": false, "kind": kind, "leaf": leaf}
		var cid := str(c.id)
		var wb := Transform3D(Basis(), h) * box
		var z := RemakeInteractZone.make(v, "Use_" + cid, Transform3D(Basis(), wb.get_center()), wb.size + Vector3.ONE * 0.3,
			func(_by: Node) -> String: return use(cid),
			func() -> String: return prompt(cid))
		z.gives_way = true


func prompt(id: String) -> String:
	var c: Dictionary = closers[id]
	var what := "the door"
	if id.begins_with("frunk"):
		what = "the frunk"
	elif id.begins_with("trunk"):
		what = "the trunk"
	elif id.begins_with("cdoor"):
		what = "the locker"
	elif id == "rollup" or id.begins_with("barn") or id.begins_with("cargo_barn"):
		what = "the rear doors"
	elif id in ["hatch", "tailgate", "hopper"]:
		what = "the " + id
	elif str(c.kind) == "slide":
		what = "the sliding door"
	elif str(c.kind) == "roll":
		what = "the shutter"
	return ("Close " if c.open else "Open ") + what


func use(id: String) -> String:
	closers[id].open = not bool(closers[id].open)
	if vehicle is RigidBody3D:
		(vehicle as RigidBody3D).sleeping = false
	return "door"


func open(id: String, on: bool) -> void:
	if closers.has(id):
		closers[id].open = on
		if vehicle is RigidBody3D:
			(vehicle as RigidBody3D).sleeping = false


func animate(delta: float) -> void:
	for id in closers:
		var c: Dictionary = closers[id]
		var target := 1.0 if c.open else 0.0
		var t := float(c.t)
		if t == target:
			continue
		var kind := str(c.kind)
		var dur := DOOR_UP if kind == "door" else (SLIDE_T if kind in ["slide", "roll"] else (LID_UP if c.open else LID_DOWN))
		t = move_toward(t, target, delta / dur)
		if absf(t - target) < 1e-4:
			t = target                                  # (exactly shut: the seal test's closed leaf)
		c.t = t
		var e := smoothstep(0.0, 1.0, t)
		var p := c.pivot as Node3D
		if kind == "roll":                              # a shutter rolls up into its head (the pivot: its top edge)
			p.scale = Vector3(1.0, lerpf(1.0, 0.06, e), 1.0)
			(c.leaf as CollisionObject3D).process_mode = Node.PROCESS_MODE_DISABLED if e > 0.5 else Node.PROCESS_MODE_INHERIT
		elif kind == "slide":                           # out first, then along (or up)
			var s: Vector3 = c.slide
			var out_k := clampf(e * 4.0, 0.0, 1.0)
			var along_k := clampf((e - 0.15) / 0.85, 0.0, 1.0)
			p.position = (c.rest as Vector3) + Vector3(s.x * out_k, s.y * along_k, s.z * along_k)
		else:
			p.transform.basis = Basis(c.axis, deg_to_rad(float(c.deg)) * e)


func doorways(bp: Dictionary, half_w: float, floor_y: float, top: float) -> Array:
	## The body's doorways as RemakeAirVehicle._carry's ways out: [AABB (local: the aperture in the side wall, floor to
	## top), Callable -> its door is open enough to pass]. A doorway with no closer of its own is always open. (The fleet
	## bodies had none: anyone stood up in an aerostat's cabin was put back in at every doorway -- the user, 2026-10-09:
	## "The aerostats have entrances too small for the player to exit".)
	var out: Array = []
	for d in bp.get("doors", []):
		var sx := 1.0 if str(d.side) == "R" else -1.0
		var w := float(d.width)
		var box := AABB(Vector3(sx * half_w - 0.15, floor_y, float(d.z) - w * 0.5), Vector3(0.3, top - floor_y, w))
		var id := str(d.get("id", ""))
		out.append([box, func() -> bool: return not closers.has(id) or float(closers[id].t) > 0.6])
	return out


func rids() -> Array[RID]:
	var ex: Array[RID] = []
	for id in closers:
		ex.append((closers[id].leaf as PhysicsBody3D).get_rid())
	return ex
