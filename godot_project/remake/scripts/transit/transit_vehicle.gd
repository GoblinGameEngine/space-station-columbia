extends Node3D
class_name TransitVehicle

## One tram or train in service (TransitSystem places it on its line every frame).
##   tram   remake/vehicles/tram.glb: articulated, bodies body_0 (front) .. body_6, sections and short
##          joint modules alternating, a bellows (strung ribs) across each joint gap. They follow the
##          street one behind another (place()); no joint bends past MAX_BEND, and each body has a collider;
##   train  three cars of remake/vehicles/passenger_train.glb, the last turned round (cab at the back).
## Passengers: generated people seated on the seat_* markers and standing at stand_* holding the
## strap_* above (NpcRide), as many as the hour brings. The player can board at a stop (use the
## vehicle: they take a free seat and ride, looking about) and get off at the next stop (use again).

const TRAM := "res://remake/vehicles/tram.glb"
const TRAIN := "res://remake/vehicles/passenger_train.glb"
const CAR_LEN := 25.0
const SEAT_H := 0.45
const MAX_BEND := deg_to_rad(24.0)   # the most one joint bends: past it the bodies' corners would meet
const RIBS := 6
const GAP := 0.45                    # the bellows gap at each joint (kit/transit.py)
static var _scenes := {}

var line: Dictionary
var index := 0
var d := 0.0
var dwelling := false
var stop := -1
var parts: Array = []                # [node, lead y, trail y (model, m forward), reversed?], front to back
var ribs: Array = []                 # per joint: the bellows rib meshes strung across the gap
var seats: Array = []                # seat marker nodes
var stands: Array = []               # [stand marker, strap marker]
var riders: Array = []               # [npc, animator, marker, pose]
var _pending: Array = []             # [task, job]
var _player: StationPlayer
var _player_seat: Node3D
var world_seed := 1


static func _scene(path: String) -> PackedScene:
	if not _scenes.has(path):
		_scenes[path] = load(path) if ResourceLoader.exists(path) else null
	return _scenes[path]


func setup(p_line: Dictionary, p_index: int, hour: float) -> void:
	line = p_line
	index = p_index
	name = "%s_%d" % [line.id, index]
	if line.kind == "tram":
		var sc := _scene(TRAM)
		if sc:
			var m: Node3D = sc.instantiate()
			add_child(m)
			for k in 16:                         # sections and joint modules, front to back
				var b := m.find_child("body_%d" % k, true, false) as Node3D
				if b == null:
					break
				_add_part(b, false)
			var rib := m.find_child("bellows_rib*", true, false) as MeshInstance3D
			if rib:
				rib.visible = false
				for j in parts.size() - 1:
					var set_: Array = []
					for r in RIBS:
						var c := MeshInstance3D.new()
						c.mesh = rib.mesh
						c.top_level = true
						add_child(c)
						set_.append(c)
					ribs.append(set_)
	else:
		var sc2 := _scene(TRAIN)
		for k in 3:
			if sc2 == null:
				break
			var car: Node3D = sc2.instantiate()
			add_child(car)
			_add_part(car, k == 2)
	for m in find_children("seat_*", "Node3D", true, false):
		if str(m.name) != "seat_driver":
			seats.append(m)
	for m in find_children("stand_*", "Node3D", true, false):
		var strap := (m.get_parent() as Node3D).find_child("strap_" + str(m.name).substr(6), false, false)
		stands.append([m, strap])
	RemakeInteractZone.make(self, "Board", Transform3D.IDENTITY, Vector3(4.0, 3.5, 8.0), _use, _prompt)
	_fill(hour)


func _occupancy(hour: float) -> float:
	var peak := exp(-pow((hour - 8.0) / 1.2, 2.0)) + exp(-pow((hour - 17.3) / 1.4, 2.0))
	return clampf(0.12 + 0.75 * peak + (0.15 if hour > 10.0 and hour < 15.0 else 0.0), 0.05, 0.95)


func _fill(hour: float) -> void:
	## Passengers for this run: a share of the seats, and at the peaks some standing.
	var occ := _occupancy(hour)
	var rng := NpcRng.for_trait(world_seed, "%s#%d" % [line.id, index], "riders:%d" % int(hour))
	var db := NpcTraits.shared()
	var n := 0
	for m in seats:
		if rng.rand() < occ:
			_spawn(m, true, rng, n)
			n += 1
	if occ > 0.6:
		for st in stands:
			if rng.rand() < (occ - 0.6) * 1.6 and st[1] != null:
				_spawn(st, false, rng, n)
				n += 1


func _spawn(marker: Variant, seated: bool, rng: NpcRng, n: int) -> void:
	var pid := "T%s%d_%d:%d" % [str(line.id).substr(0, 3), index, n, int(rng.rand() * 1000)]
	var age := 16 + int(rng.rand() * 64)
	var v := NpcTraits.shared().person(world_seed, pid, ["L0", "L1"], "", {"age": age})
	var job := {"v": v, "pid": pid, "marker": marker, "seated": seated, "data": {}}
	job.task = WorkerThreadPool.add_task(func(): job.data = NpcCharacter.prepare(v, pid, world_seed, "work"), false, "rider " + pid)
	_pending.append(job)


func _collect() -> void:
	for job in _pending.duplicate():
		if not WorkerThreadPool.is_task_completed(job.task):
			continue
		WorkerThreadPool.wait_for_task_completion(job.task)
		_pending.erase(job)
		if job.data.is_empty():
			continue
		var npc := NpcCharacter.from_prepared(job.data)
		var an := NpcAnimator.attach(npc)
		an.ambient = false
		var holder: Node3D
		if job.seated:
			holder = job.marker as Node3D
			holder.get_parent().add_child(npc)
			npc.transform = holder.transform * Transform3D(Basis(), Vector3(0, -(SEAT_H + 0.02), 0))
			an.ride = NpcRide.seated(npc, SEAT_H)
		else:
			holder = job.marker[0] as Node3D
			holder.get_parent().add_child(npc)
			npc.transform = holder.transform
			var strap := job.marker[1] as Node3D
			an.ride = NpcRide.strap(npc, npc.transform.affine_inverse() * strap.position)
		riders.append([npc, an, holder])
		return                          # one a frame


func _add_part(node: Node3D, reversed: bool) -> void:
	## A rigid body of the vehicle: its lead and trail pivots (on the road) and a collider from its meshes.
	var lead := node.find_child("pivot_lead*", false, false) as Node3D
	var trail := node.find_child("pivot_trail*", false, false) as Node3D
	var yl := -lead.position.z if lead else CAR_LEN / 2
	var yt := -trail.position.z if trail else -CAR_LEN / 2
	if reversed:
		var t := yl
		yl = yt
		yt = t
	parts.append([node, yl, yt, reversed])
	var box := AABB()
	var first := true
	for mi in node.find_children("*", "MeshInstance3D", true, false):
		if str(mi.name).begins_with("wheel_") or str(mi.name).begins_with("bellows"):
			continue
		var bb: AABB = (node.global_transform.affine_inverse() * (mi as MeshInstance3D).global_transform) * (mi as MeshInstance3D).get_aabb()
		box = bb if first else box.merge(bb)
		first = false
	if first:
		return
	var body := AnimatableBody3D.new()
	body.sync_to_physics = false
	body.collision_layer = 1 | RemakeGroundVehicle.HULL_LAYER      # people and vehicles both bump it
	body.collision_mask = 0
	var cs := CollisionShape3D.new()
	var sh := BoxShape3D.new()
	sh.size = box.size - Vector3(0.04, 0.04, 0.04)
	cs.shape = sh
	cs.position = box.get_center()
	body.add_child(cs)
	node.add_child(body)


func _back_along(a: Vector2, s0: float, length: float) -> float:
	## The distance along the line, behind s0, of the point `length` metres in a straight line from a.
	var s := s0 - length
	for i in 4:
		var p := TransitNet.point_at(line, s)
		var dist := Vector2(StationGeo.wrap_ds(p.x - a.x), p.y - a.y).length()
		s -= length - dist
	return s


func place(p_d: float, p_dwelling: bool, p_stop: int) -> void:
	## The bodies follow one another like a train of trailers: the front body's lead pivot is on the
	## line at d; each trail pivot is the point on the line a body length behind its lead, and the next
	## body leads from there. No joint bends past MAX_BEND, so the bodies never cut into each other.
	d = p_d
	dwelling = p_dwelling
	stop = p_stop
	var a := TransitNet.point_at(line, d)
	var s_a := d
	var prev_dir := Vector2.ZERO
	var frames: Array = []
	for pt in parts:
		var node := pt[0] as Node3D
		var yl: float = pt[1]
		var yt: float = pt[2]
		var length := absf(yl - yt)
		var s_b := _back_along(a, s_a, length)
		var b := TransitNet.point_at(line, s_b)
		var dir := Vector2(StationGeo.wrap_ds(a.x - b.x), a.y - b.y).normalized()
		if prev_dir != Vector2.ZERO:
			var bend := prev_dir.angle_to(dir)
			if absf(bend) > MAX_BEND:
				dir = prev_dir.rotated(signf(bend) * MAX_BEND)
				b = a - dir * length
		prev_dir = dir
		var fwd := dir if not pt[3] else -dir
		# the node's origin: the lead pivot is yl ahead of it along the model's forward
		var o := a - fwd * yl
		var yaw := atan2(-fwd.y, fwd.x)
		var mid := (a + b) * 0.5
		var elev := MapTerrain.elevation(mid.x, mid.y)
		node.global_transform = Transform3D(StationGeo.basis(o.x, yaw), StationGeo.point(o.x, o.y, elev))
		frames.append(node.global_transform)
		a = b
		s_a = s_b
	# the bellows: ribs strung across each joint gap, turning from one body's end to the next one's
	for j in ribs.size():
		var pa: Array = parts[j]
		var pb: Array = parts[j + 1]
		var ta: Transform3D = frames[j] * Transform3D(Basis(), Vector3(0, 0, -(pa[2] + GAP / 2)))
		var tb: Transform3D = frames[j + 1] * Transform3D(Basis(), Vector3(0, 0, -(pb[1] - GAP / 2)))
		var qa := ta.basis.get_rotation_quaternion()
		var qb := tb.basis.get_rotation_quaternion()
		for r in RIBS:
			var t := (r + 0.5) / RIBS
			(ribs[j][r] as Node3D).global_transform = Transform3D(Basis(qa.slerp(qb, t)), ta.origin.lerp(tb.origin, t))
	# the Board zone rides with the front part, by its doors
	var z := get_node_or_null("Board") as Node3D
	if z and not parts.is_empty():
		z.global_transform = (parts[0][0] as Node3D).global_transform * Transform3D(Basis(), Vector3(1.4, 1.5, 3.0 if line.kind == "tram" else 0.0))
	if _player:
		_player.global_transform = Transform3D(_player_seat.global_transform.basis, _player_seat.global_transform * Vector3(0, 0.72, 0))


func _process(_delta: float) -> void:
	if not _pending.is_empty():
		_collect()


# -- the player ------------------------------------------------------------------------------------

func _prompt() -> String:
	if _player:
		return ""
	return ("Board the %s" % line.name) if dwelling else ""


func _use(by: Node) -> String:
	if not (by is StationPlayer) or _player or not dwelling:
		return ""
	var taken := {}
	for r in riders:
		taken[r[2]] = true
	for m in seats:
		if not taken.has(m):
			_player_seat = m
			break
	if _player_seat == null:
		return "It's full."
	_player = by
	_player.sit_in(self)
	return "boarded"


func leave_seat() -> void:
	## Off at a stop; between stops the doors stay shut.
	if _player == null:
		return
	if not dwelling:
		var hud := get_tree().root.get_node_or_null("Hud")
		if hud and hud.has_method("toast"):
			hud.toast("The doors open at the next stop.")
		return
	var p := _player
	_player = null
	var exit_n: Node3D = null
	var best := INF
	for e in find_children("exit_*", "Node3D", true, false):
		var dd := (e as Node3D).global_position.distance_to(_player_seat.global_position)
		if dd < best:
			best = dd
			exit_n = e
	var at: Transform3D = exit_n.global_transform if exit_n else (parts[0][0] as Node3D).global_transform
	p.stand_up(at.origin + at.basis.y * 0.9, at.basis)
	_player_seat = null


func carrying_player() -> bool:
	return _player != null
