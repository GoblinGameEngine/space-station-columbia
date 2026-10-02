extends Node3D
class_name TransitVehicle

## One tram or train in service (TransitSystem places it on its line every physics tick).
##   tram   the Carrow Coach Company road tram (the user, 2026-10-01): two to four TramSections --
##          a front section (the driver's cab, the headlights), any number of mid sections, a rear
##          section (the tail lights) -- each a Carrow body on its own Steward board, joined by
##          TramJoints (covered walkways). Every section steers for itself: both its axles stand on
##          the line (a "virtual track", as on the guided road trams of Earth), so the bodies follow
##          the street round any bend and every wheel steers. People walk about inside, moving or
##          standing still; at a stop the curbside doors open, riders get off and new ones get on on
##          that side, and the doors close before it moves on.
##   train  three cars of remake/vehicles/passenger_train.glb, the last turned round (cab at the back).
## Passengers: generated people seated on the seat_* markers and standing at stand_* holding the
## strap_* above (NpcRide), as many as the hour brings. The player can sit on any free seat (use it)
## and stand up again (use); on a train they board at a stop and get off at the next.

const TRAIN := "res://remake/vehicles/passenger_train.glb"
const CAR_LEN := 25.0
const SEAT_H := 0.45
const AXLE := 2.25                   # the tram board's axles, either side of a section's middle
const WB := 4.5
const WHEEL_R := 0.48
const JOINT_GAP := 0.55              # between two sections' portal faces
const WALK := 1.2                    # m/s, people walking in and out
const AISLE_X := 0.21
static var _scenes := {}

var line: Dictionary
var index := 0
var d := 0.0
var dwelling := false
var stop := -1
var parts: Array = []                # [node, lead y, trail y (model, m forward), reversed?], front to back (traffic reads these)
var sections: Array = []             # TramSection, front to back
var joints: Array = []               # TramJoint
var seats: Array = []                # seat marker nodes
var stands: Array = []               # [stand marker, strap marker]
var riders: Array = []               # [npc, animator, marker]
var built := false                   # all its sections made (_build_tram)
var _placed := false
var _aboard := {}                    # player -> [section index, their place in its frame] (_keep_aboard)
var walkers: Array = []              # {npc, an, sec, pts, i, mode ("on"/"off"), seat}
var driver_npc: Node3D
var _pending: Array = []             # jobs
var _player: StationPlayer
var _player_seat: Node3D
var world_seed := 1
var drv: RoadDriver                  # the operator (trams)
var _heights := {}                   # section index -> [front axle h, rear axle h]
var _last_d := 0.0
var _at_stop := false
var _plan: Array = []                # [time left, Callable]
var _prev_v := 0.0
var _braking := false
var _rng := RandomNumberGenerator.new()
var _holding := false                # standing at a stop (trams keep their own stops; the timetable only paces them)
var _hold_t := 0.0
var _leaving := false                # the doors closing before it pulls away
var _stop_d := -1.0                  # the stop being held at


static func _scene(path: String) -> PackedScene:
	if not _scenes.has(path):
		_scenes[path] = load(path) if ResourceLoader.exists(path) else null
	return _scenes[path]


func setup(p_line: Dictionary, p_index: int, hour: float) -> void:
	line = p_line
	index = p_index
	name = "%s_%d" % [line.id, index]
	_rng.seed = hash(name)
	if line.kind == "tram":
		var n := 2 + absi(hash("%s#%d" % [line.id, index])) % 3          # two to four sections
		var kinds := ["front"]
		for k in n - 2:
			kinds.append("mid")
		kinds.append("rear")
		_build_tram(kinds, hour)
		return
	else:
		_build_train(hour)


func _build_tram(kinds: Array, hour: float) -> void:
	## A section a frame (each is some 5 ms to build; a tram all at once was a dropped frame). It's
	## made far off (TransitSystem.RANGE); place() waits for it.
	for k in kinds:
		var sec := TramSection.new()
		add_child(sec)
		sec.setup(k, self)
		sections.append(sec)
		parts.append([sec, TramSection.length_front(k), -TramSection.length_back(k), false])
		await get_tree().process_frame
		if not is_inside_tree():
			return
	if true:
		for i in sections.size() - 1:
			var j := TramJoint.new()
			add_child(j)
			j.setup(sections[i], sections[i + 1])
			joints.append(j)
		for sec in sections:
			for m in (sec as TramSection).body.find_children("seat_*", "Node3D", true, false):
				if str(m.name) == "seat_driver":
					_spawn(m, true, null, -1, "driver")
					continue
				seats.append(m)
				var z := RemakeInteractZone.make(m.get_parent(), "Sit_" + str(m.name), m.transform * Transform3D(Basis(), Vector3(0, 0.1, 0)),
					Vector3(0.5, 0.55, 0.5), _sit.bind(m), _sit_prompt.bind(m))
				z.gives_way = false
		_finish_setup(hour)
		built = true


func _build_train(hour: float) -> void:
	if true:
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
		RemakeInteractZone.make(self, "Board", Transform3D.IDENTITY, Vector3(4.0, 3.5, 8.0), _use, _prompt)
	_finish_setup(hour)
	built = true


func _finish_setup(hour: float) -> void:
	for m in find_children("stand_*", "Node3D", true, false):
		var strap := (m.get_parent() as Node3D).find_child("strap_" + str(m.name).substr(6), false, false)
		stands.append([m, strap])
	_fill(hour)


func length() -> float:
	var total := 0.0
	for p in parts:
		total += float(p[1]) - float(p[2])
	return total + JOINT_GAP * maxi(0, sections.size() - 1)


# -- passengers -----------------------------------------------------------------------------------

func _occupancy(hour: float) -> float:
	var peak := exp(-pow((hour - 8.0) / 1.2, 2.0)) + exp(-pow((hour - 17.3) / 1.4, 2.0))
	return clampf(0.12 + 0.75 * peak + (0.15 if hour > 10.0 and hour < 15.0 else 0.0), 0.05, 0.95)


func _demand(at_d: float) -> float:
	## The share of seats taken here, now (TransitDemand: the towns round about, the hour, the events).
	var sys := get_parent()
	var h: float = sys.hour() if sys.has_method("hour") else 12.0
	var dy: int = sys.day() if sys.has_method("day") else 0
	return TransitDemand.load_at(TransitNet.point_at(line, at_d), h, dy)


func _fill(hour: float) -> void:
	## Passengers for this run: as many as ride here at this hour (TransitDemand), and when it's
	## crowded some standing.
	var occ := _demand(d) if str(line.kind) == "tram" else _occupancy(hour)
	var rng := NpcRng.for_trait(world_seed, "%s#%d" % [line.id, index], "riders:%d" % int(hour))
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


var _to_spawn: Array = []             # riders waiting to be made (a few a frame: _process)


func _spawn(marker: Variant, seated: bool, rng: NpcRng, n: int, mode := "", extra := {}) -> void:
	## (queued: a person's traits take ~1.5 ms to draw, and a full tram is dozens)
	var r := rng.rand() if rng else _rng.randf()
	_to_spawn.append([marker, seated, r, n, mode, extra])


func _spawn_now(marker: Variant, seated: bool, r: float, n: int, mode: String, extra: Dictionary) -> void:
	var pid := "T%s%d_%s%d:%d" % [str(line.id).substr(0, 3), index, mode, n if n >= 0 else _rng.randi() % 100000, int(r * 1000)]
	var age := 16 + int(r * 64) if mode != "driver" else 28 + int(r * 30)
	var v := NpcTraits.shared().person(world_seed, pid, ["L0", "L1"], "", {"age": age})
	var job := {"v": v, "pid": pid, "marker": marker, "seated": seated, "mode": mode, "extra": extra, "data": {}}
	var seed := world_seed                           # (the job may outlive this tram: it captures values only)
	job.task = WorkerThreadPool.add_task(func(): job.data = NpcCharacter.prepare(v, pid, seed, "work"), false, "rider " + pid)
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
		if job.mode == "board":
			var sec: TramSection = job.extra.sec
			if not is_instance_valid(sec) or not _at_stop:
				npc.queue_free()
				return
			sec.body.add_child(npc)
			var pts: Array = job.extra.pts
			npc.position = pts[0]
			walkers.append({"npc": npc, "an": an, "sec": sec, "pts": pts, "i": 1, "mode": "on", "seat": job.marker})
			return
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
		if job.mode == "driver":
			driver_npc = npc
		else:
			riders.append([npc, an, holder])
		return                          # one a frame


func _taken() -> Dictionary:
	var t := {}
	for r in riders:
		t[r[2]] = true
	for w in walkers:
		if w.seat:
			t[w.seat] = true
	if _player_seat:
		t[_player_seat] = true
	return t


# -- stops: the curbside doors, people getting off and on ---------------------------------------------

func _arrive() -> void:
	_at_stop = true
	for sec in sections:
		(sec as TramSection).open_curbside(true)
	# who gets off and who gets on: the load the run ahead calls for (TransitDemand) -- leaving a town
	# it empties, coming into one it fills; some get off anywhere
	var here := _demand(d)
	var ahead := 0.0
	for k in 4:
		ahead += _demand(d + 250.0 * (k + 1)) * 0.25
	var target := int(round(seats.size() * ahead))
	var all := riders.duplicate()
	all.shuffle()
	var leave_share := clampf(0.08 + 0.6 * maxf(0.0, here - ahead) / maxf(here, 0.05), 0.0, 0.9)
	var n_off := int(round(all.size() * leave_share)) + maxi(0, all.size() - target - 2)
	n_off = mini(mini(n_off, all.size()), 8)
	for k in n_off:
		var r: Array = all[k]
		_plan.append([0.4 + k * 0.8, _alight.bind(r)])
	var n_on := clampi(target - (riders.size() - n_off), 0, 8)
	var crowds: StopCrowds = get_parent().crowds if "crowds" in get_parent() else null
	var sidx := _stop_index()
	if crowds and sidx >= 0 and crowds.tracked(str(line.id), sidx):
		# the people waiting here (as many as there are)
		var who := crowds.take(str(line.id), sidx, n_on)
		for k in who.size():
			_plan.append([1.2 + k * 1.0, _board_person.bind(who[k])])
	else:
		for k in n_on:
			_plan.append([1.2 + k * 1.1, _board])


func _depart() -> void:
	_at_stop = false
	_plan.clear()
	for w in walkers.duplicate():
		if w.mode == "on" and int(w.i) >= 3 and is_instance_valid(w.npc):
			_seat_walker(w)                                  # already aboard: sit straight down
		elif w.mode == "off" and int(w.i) >= 4 and is_instance_valid(w.npc):
			_hand_off(w)                                     # out of the door: on their way
		elif is_instance_valid(w.npc):
			(w.npc as Node).queue_free()
		walkers.erase(w)
	for sec in sections:
		(sec as TramSection).close_all()


func _door_for(sec: TramSection, z: float) -> Dictionary:
	var best: Dictionary = {}
	var bd := INF
	for dd in sec.curbside_doors():
		var dz := absf(float(dd.spec.z) - z)
		if dz < bd:
			bd = dz
			best = dd
	return best


func _path_out(sec: TramSection, from: Vector3, door_z: float) -> Array:
	## From a seat (its floor point) to the aisle, along it to the door, down the ramp and away.
	var fl := float(TramSection.load_spec().floor_y)
	return [Vector3(from.x, fl, from.z), Vector3(AISLE_X, fl, from.z), Vector3(AISLE_X, fl, door_z), Vector3(0.85, fl, door_z),
		Vector3(1.3, fl - 0.03, door_z), Vector3(2.25, 0.12, door_z), Vector3(4.2, 0.0, door_z + 1.2)]


func _alight(r: Array) -> void:
	if not riders.has(r) or not is_instance_valid(r[0]):
		return
	var marker := (r[2][0] if r[2] is Array else r[2]) as Node3D
	var sec := _section_of(marker)
	if sec == null:
		return
	var door := _door_for(sec, marker.position.z)
	if door.is_empty():
		return
	riders.erase(r)
	var npc := r[0] as Node3D
	var an = r[1]
	an.ride = {}
	var pts := _path_out(sec, marker.position, float(door.spec.z))
	npc.position = pts[0]
	walkers.append({"npc": npc, "an": an, "sec": sec, "pts": pts, "i": 1, "mode": "off", "seat": null})


func _board() -> void:
	if not _at_stop:
		return
	var taken := _taken()
	var free: Array = seats.filter(func(m): return not taken.has(m))
	if free.is_empty():
		return
	var m: Node3D = free[_rng.randi() % free.size()]
	var sec := _section_of(m)
	var door := _door_for(sec, m.position.z)
	if door.is_empty():
		return
	var pts := _path_out(sec, m.position, float(door.spec.z))
	pts.reverse()
	pts[0] = Vector3(4.2, 0.0, float(door.spec.z) - 1.2)
	_spawn(m, true, null, -1, "board", {"sec": sec, "pts": pts})


func _stop_index() -> int:
	var best := -1
	var bd := INF
	var L := float(line.length)
	for i in (line.stops as Array).size():
		var dd := absf(fposmod(float(line.stops[i].d) - _stop_d + L * 0.5, L) - L * 0.5)
		if dd < bd:
			bd = dd
			best = i
	return best if bd < 40.0 else -1


func _board_person(person: Dictionary) -> void:
	## Someone who was waiting at the stop walks to a door and on, to a free seat (or a strap).
	var npc := person.npc as Node3D
	if not is_instance_valid(npc):
		return
	var taken := _taken()
	var free: Array = seats.filter(func(m): return not taken.has(m))
	if free.is_empty() or not _at_stop:
		return                                         # (full: they wait for the next)
	var m: Node3D = free[_rng.randi() % free.size()]
	var sec := _section_of(m)
	var door := _door_for(sec, m.position.z)
	if door.is_empty():
		return
	var xf := npc.global_transform
	npc.get_parent().remove_child(npc)
	sec.body.add_child(npc)
	npc.global_transform = xf
	var pts := _path_out(sec, m.position, float(door.spec.z))
	pts.reverse()
	pts[0] = npc.position
	(person.an as NpcAnimator).ambient = false
	walkers.append({"npc": npc, "an": person.an, "sec": sec, "pts": pts, "i": 1, "mode": "on", "seat": m})


func _section_of(n: Node) -> TramSection:
	var p := n
	while p and not p is TramSection:
		p = p.get_parent()
	return p as TramSection


func _seat_walker(w: Dictionary) -> void:
	var npc := w.npc as Node3D
	var m := w.seat as Node3D
	npc.transform = m.transform * Transform3D(Basis(), Vector3(0, -(SEAT_H + 0.02), 0))
	w.an.speed = 0.0
	w.an.ride = NpcRide.seated(npc, SEAT_H)
	riders.append([npc, w.an, m])


func _walk(delta: float) -> void:
	for w in walkers.duplicate():
		var npc := w.npc as Node3D
		if not is_instance_valid(npc):
			walkers.erase(w)
			continue
		var pts: Array = w.pts
		var tgt: Vector3 = pts[w.i]
		var p := npc.position
		var dv := tgt - p
		var step := WALK * delta
		if dv.length() <= step:
			npc.position = tgt
			w.i = int(w.i) + 1
			if int(w.i) >= pts.size():
				walkers.erase(w)
				if w.mode == "on":
					_seat_walker(w)
				else:
					_hand_off(w)
				continue
		else:
			npc.position = p + dv.normalized() * step
		var flat := Vector3(dv.x, 0, dv.z)
		if flat.length() > 0.02:
			npc.basis = Basis.looking_at(flat.normalized(), Vector3.UP)
		w.an.speed = WALK


func _hand_off(w: Dictionary) -> void:
	## Off the tram: they walk on, along the pavement to somewhere near the stop (StopCrowds).
	walkers.erase(w)
	var crowds: StopCrowds = get_parent().crowds if "crowds" in get_parent() else null
	if crowds == null:
		(w.npc as Node).queue_free()
		return
	crowds.walk_away(w.npc, w.an)


func walking() -> bool:
	return not walkers.is_empty() or not _plan.is_empty()


# -- driving ----------------------------------------------------------------------------------------

func _add_part(node: Node3D, reversed: bool) -> void:
	## A train car: its lead and trail pivots (on the track) and a collider from its meshes.
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
		if str(mi.name).begins_with("wheel_"):
			continue
		var bb: AABB = (node.global_transform.affine_inverse() * (mi as MeshInstance3D).global_transform) * (mi as MeshInstance3D).get_aabb()
		box = bb if first else box.merge(bb)
		first = false
	if first:
		return
	var body := AnimatableBody3D.new()
	body.sync_to_physics = false
	body.collision_layer = 1 | RemakeGroundVehicle.HULL_LAYER
	body.collision_mask = 0
	var cs := CollisionShape3D.new()
	var sh := BoxShape3D.new()
	sh.size = box.size - Vector3(0.04, 0.04, 0.04)
	cs.shape = sh
	cs.position = box.get_center()
	body.add_child(cs)
	node.add_child(body)


func _back_along(a: Vector2, s0: float, length_: float) -> float:
	## The distance along the line, behind s0, of the point `length_` metres in a straight line from a.
	var s := s0 - length_
	for i in 4:
		var p := TransitNet.point_at(line, s)
		var dist := Vector2(StationGeo.wrap_ds(p.x - a.x), p.y - a.y).length()
		s -= length_ - dist
	return s


func _operate(p_d: float, p_dwelling: bool) -> float:
	## A tram is driven by its operator under the same rules of the road as everyone (RoadDriver,
	## professional), along its line toward the timetable's position p_d -- catching up when held
	## up, never running ahead of it, stopping at its stops, and never moving with a door open or
	## anyone still getting on or off. A train keeps to its timetable on the rails.
	if str(line.kind) != "tram":
		return p_d
	if drv == null:
		drv = RoadDriver.new()
		drv.setup(func(dd): return TransitNet.point_at(line, dd), length(), {}, hash(name), true)
		drv.id = "%s#%d" % [line.id, index]
		drv.t = p_d
	var sp := float(line.speed)
	var L := float(line.length)
	var dt := get_physics_process_delta_time()
	var t_mod := fposmod(drv.t, L)
	# pace: run toward the timetable, a little faster when late, slower when early
	var late := fposmod(p_d - t_mod + L * 0.5, L) - L * 0.5
	drv.v_cap = clampf(sp + late * 0.3, sp * 0.4, sp * 1.3)
	if _holding:
		drv.v_cap = 0.0
		_hold_t += dt
		if not _leaving and _hold_t >= float(line.dwell) and not walking() or _hold_t > 45.0:
			_leaving = true
			_depart()
		if _leaving:
			var closed := true
			for sec in sections:
				if not (sec as TramSection).doors_settled(false):
					closed = false
			if closed:
				_holding = false
				_leaving = false
	else:
		# brake for the next stop, and hold there when the front is at its mark
		var ahead := INF
		for st in line.stops:
			var dd := fposmod(float(st.d) - t_mod, L)
			if dd < ahead and dd < L - 0.5 and absf(float(st.d) - _stop_d) > 1.0:
				ahead = dd
		if ahead < INF:
			drv.v_cap = minf(drv.v_cap, sqrt(2.0 * 1.1 * maxf(0.0, ahead - 0.3)) + 0.2)
			if ahead < 0.8 and drv.v < 0.4:
				_holding = true
				_hold_t = 0.0
				_stop_d = fposmod(t_mod + ahead, L)
				_arrive()
		if _stop_d >= 0.0 and fposmod(t_mod - _stop_d, L) > 30.0 and fposmod(t_mod - _stop_d, L) < L - 30.0:
			_stop_d = -1.0                               # well past it: the next time round it's a stop again
	var tr = get_tree().current_scene.get("traffic")
	var clock: float = get_parent().clock_seconds() if get_parent().has_method("clock_seconds") else Time.get_ticks_msec() / 1000.0
	var t_before := drv.t
	drv.step(get_physics_process_delta_time(), tr.agents if tr != null else [], tr.peds if tr != null else [], clock)
	if _holding:                                     # standing at the stop, doors open: not a creep
		drv.v = 0.0
		drv.t = t_before
	return drv.t


func stopped() -> bool:
	return drv == null or drv.v < 0.3


func _p3(p: Vector2, h: float) -> Vector3:
	return StationGeo.point(fposmod(p.x, StationGeo.CIRC), p.y, h)


func _tangent(s: float) -> Vector3:
	var a := _pulled(s - 0.6)                      # (the path it drives: pulled in at the stops)
	var b := _pulled(s + 0.6)
	var ss := fposmod(b.x, StationGeo.CIRC)
	return (StationGeo.forward(ss) * StationGeo.wrap_ds(b.x - a.x) + Vector3.RIGHT * (b.y - a.y)).normalized()


func place(p_d: float, p_dwelling: bool, p_stop: int) -> void:
	dwelling = p_dwelling
	stop = p_stop
	if not built:
		d = p_d                                      # (still being built: it starts where the timetable has it)
		return
	Prof.begin("tram.operate")
	d = _operate(p_d, p_dwelling)
	Prof.end("tram.operate")
	if str(line.kind) == "tram":
		Prof.begin("tram.place")
		_place_tram()
		_placed = true
		Prof.end("tram.place")
		Prof.begin("tram.aboard")
		_keep_aboard()
		Prof.end("tram.aboard")
	else:
		Prof.begin("train.place")
		_place_train()
		Prof.end("train.place")
	if _player:
		_player.global_transform = Transform3D(_player_seat.global_transform.basis, _player_seat.global_transform * Vector3(0, 0.72, 0))


func _place_tram() -> void:
	## Each section's two axles stand on the line; the next section's front axle is a joint's reach
	## behind this one's rear axle. The wheels steer to the line's heading at each axle.
	var run := absf(d - _last_d) if _last_d != 0.0 else 0.0
	_last_d = d
	var space := get_world_3d().direct_space_state
	var s_fa := d - (TramSection.length_front("front") - AXLE)
	var v := drv.v if drv else 0.0
	_braking = (v < _prev_v - 0.01) or (_holding and v < 0.3)
	_prev_v = v
	var night := _night()
	for i in sections.size():
		var sec := sections[i] as TramSection
		var pf := _pulled(s_fa)
		var s_ra := _back_along(pf, s_fa, WB)
		var pr := _pulled(s_ra)
		var hs: Array = _heights.get(i, [-INF, -INF])
		var hf := _line_h(space, s_fa, hs[0])
		var hr := _line_h(space, s_ra, hs[1])
		_heights[i] = [hf, hr]
		var P_f := _p3(pf, hf)
		var P_r := _p3(pr, hr)
		var fwd := (P_f - P_r).normalized()
		var mid := (P_f + P_r) * 0.5
		var up := StationGeo.up(StationGeo.s_of(mid))
		up = (up - fwd * up.dot(fwd)).normalized()
		var back := -fwd
		sec.global_transform = Transform3D(Basis(up.cross(back), up, back), mid)
		sec.sync_bodies()
		var a_f := fwd.signed_angle_to(_tangent(s_fa), up)
		var a_r := fwd.signed_angle_to(_tangent(s_ra), up)
		sec.steer(clampf(a_f, -0.6, 0.6), clampf(a_r, -0.6, 0.6), run, WHEEL_R)
		sec.set_lights(night, _braking)
		if i + 1 < sections.size():
			var gap := (TramSection.length_back(sec.kind) - AXLE) + JOINT_GAP + (TramSection.length_front((sections[i + 1] as TramSection).kind) - AXLE)
			s_fa = _back_along(pr, s_ra, gap)
	Prof.begin("tram.joints")
	for j in joints:
		(j as TramJoint).update()
	Prof.end("tram.joints")
	dwelling = _holding


static var _heights_along := {}        # line id -> {half-metre index along it: the height a vehicle stands at}
const H_STEP := 0.5


func _line_h(space: PhysicsDirectSpaceState3D, along: float, was: float) -> float:
	## The height a tram stands at, at a distance along its line: RoadSurface.stand_h, looked up once
	## per H_STEP of the line and shared by every tram on it (the line never moves), interpolated.
	var cache: Dictionary = _heights_along.get(line.id, {})
	if cache.is_empty():
		_heights_along[line.id] = cache
	var L := float(line.length)
	var u := fposmod(along, L) / H_STEP
	var k0 := floori(u)
	var out := 0.0
	for j in 2:
		var k := (k0 + j) % maxi(1, int(L / H_STEP))
		var h = cache.get(k)
		if h == null:
			var p := TransitNet.point_at(line, k * H_STEP)
			var q := Vector2(fposmod(p.x, StationGeo.CIRC), p.y)
			h = RoadSurface.stand_h(space, q, was)
			# (over water a small bridge is found by a ray, its body maybe not built yet: asked afresh)
			if MapTerrain.water_at(q.x, q.y).x < -9000.0 or GreatBridges.deck_h(q.x, q.y) > -INF:
				cache[k] = h
		out += float(h) * ((1.0 - (u - k0)) if j == 0 else (u - k0))
	return out


const PULL_IN := 30.0                 # m over which a tram eases to the kerb before a stop
const PULL_OUT := 25.0                # and back out to its lane after


func _pulled(along: float) -> Vector2:
	## The line's point at `along`, moved to the kerb near a stop (TransitNet.stop_pull): the whole
	## tram stands at the kerb, its doors over the sidewalk, and eases back out once past.
	var p := TransitNet.point_at(line, along)
	var L := float(line.length)
	var tl := length()
	var w := 0.0
	var pull := 0.0
	for i in (line.stops as Array).size():
		var sd := float(line.stops[i].d)
		var x := fposmod(along - sd + L * 0.5, L) - L * 0.5          # (- before the stop's mark)
		if x < -tl - PULL_IN - 6.0 or x > PULL_OUT:
			continue
		var k := 1.0
		if x < -tl - 6.0:
			k = smoothstep(-tl - 6.0 - PULL_IN, -tl - 6.0, x)
		elif x > 1.0:
			k = 1.0 - smoothstep(1.0, PULL_OUT, x)
		if k > w:
			w = k
			pull = TransitNet.stop_pull(line, i)
	if w <= 0.0 or pull <= 0.0:
		return p
	var a := TransitNet.point_at(line, along - 1.0)
	var b := TransitNet.point_at(line, along + 1.0)
	var t := Vector2(StationGeo.wrap_ds(b.x - a.x), b.y - a.y).normalized()
	return p + Vector2(-t.y, t.x) * pull * w


func _night() -> float:
	var h: float = get_parent().hour() if get_parent().has_method("hour") else 12.0
	if h < 5.0 or h > 20.5:
		return 1.0
	if h < 7.0:
		return 1.0 - (h - 5.0) / 2.0
	if h > 18.5:
		return (h - 18.5) / 2.0
	return 0.0


func _place_train() -> void:
	## The cars follow one another like a train of trailers along the rails.
	var a := TransitNet.point_at(line, d)
	var s_a := d
	for pt in parts:
		var node := pt[0] as Node3D
		var yl: float = pt[1]
		var yt: float = pt[2]
		var length_ := absf(yl - yt)
		var s_b := _back_along(a, s_a, length_)
		var b := TransitNet.point_at(line, s_b)
		var dir := Vector2(StationGeo.wrap_ds(a.x - b.x), a.y - b.y).normalized()
		var fwd := dir if not pt[3] else -dir
		var o := a - fwd * yl
		var yaw := atan2(-fwd.y, fwd.x)
		var mid := (a + b) * 0.5
		var elev := RoadSurface.stand_h(node.get_world_3d().direct_space_state, mid, StationGeo.h_of(node.global_position)) \
			if node.is_inside_tree() else MapTerrain.elevation(mid.x, mid.y)
		node.global_transform = Transform3D(StationGeo.basis(o.x, yaw), StationGeo.point(o.x, o.y, elev))
		a = b
		s_a = s_b
	var z := get_node_or_null("Board") as Node3D
	if z and not parts.is_empty():
		z.global_transform = (parts[0][0] as Node3D).global_transform * Transform3D(Basis(), Vector3(1.4, 1.5, 0.0))


func _exit_tree() -> void:
	for job in _pending:                             # (worker tasks must be waited for)
		WorkerThreadPool.wait_for_task_completion(job.task)
	_pending.clear()


func _process(_delta: float) -> void:
	if not _to_spawn.is_empty():
		var t0 := Time.get_ticks_usec()
		while not _to_spawn.is_empty() and Time.get_ticks_usec() - t0 < 2000:
			var j: Array = _to_spawn.pop_front()
			_spawn_now(j[0], j[1], j[2], j[3], j[4], j[5])
	if not _pending.is_empty():
		_collect()


func _physics_process(delta: float) -> void:
	Prof.begin("tram.vehicle_tick")
	var ready := true                                # (no one steps off till the doors are open and the ramps down)
	if _at_stop:
		for sec in sections:
			if not (sec as TramSection).doors_settled(true):
				ready = false
	for p in (_plan.duplicate() if ready else []):
		p[0] = float(p[0]) - delta
		if float(p[0]) <= 0.0:
			_plan.erase(p)
			(p[1] as Callable).call()
	if not walkers.is_empty():
		_walk(delta)
	Prof.end("tram.vehicle_tick")


# -- the player ------------------------------------------------------------------------------------

func _sit_prompt(m: Node3D) -> String:
	if _player or _taken().has(m):
		return ""
	return "Sit down"


func _sit(by: Node, m: Node3D) -> String:
	if not (by is StationPlayer) or _player or _taken().has(m):
		return ""
	_player = by
	_player_seat = m
	_player.sit_in(self)
	return "sat"


func _prompt() -> String:
	if _player:
		return ""
	return ("Board the %s" % line.name) if dwelling and stopped() else ""


func _use(by: Node) -> String:
	## (trains) take a free seat at a stop
	if not (by is StationPlayer) or _player or not dwelling or not stopped():
		return ""
	var taken := _taken()
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
	if _player == null:
		return
	var p := _player
	if str(line.kind) == "tram":
		# stand up into the aisle beside the seat; walk off through an open door
		var bt := (_player_seat.get_parent() as Node3D).global_transform
		var fl := float(TramSection.load_spec().floor_y)
		_player = null
		p.stand_up(bt * Vector3(AISLE_X, fl + 0.95, _player_seat.position.z), bt.basis)
		_player_seat = null
		return
	if not dwelling or not stopped():
		var hud := get_tree().root.get_node_or_null("Hud")
		if hud and hud.has_method("toast"):
			hud.toast("The doors open at the next stop.")
		return
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


func _keep_aboard() -> void:
	## Everyone standing in the tram moves with it, and stays in it: out only through an open door
	## (walked or pushed). Crossing a joint is just walking from one section into the next. Anyone
	## who'd leave otherwise -- squeezed through a wall by a crowd or an obstacle, dropped through the
	## floor -- is put back where they stood last tick. A jump of metres in a tick is a teleport (fast
	## travel, a respawn): it lets them go.
	var dt := get_physics_process_delta_time()
	if dt <= 0.0:
		return
	var carried := {}
	for p in get_tree().get_nodes_in_group("player"):
		if not p is StationPlayer:
			continue
		var pl := p as StationPlayer
		if pl.is_seated():
			continue
		var pos := pl.global_position
		var at := -1
		var lp := Vector3.ZERO
		for i in sections.size():
			var sec := sections[i] as TramSection
			var q := sec.prev_xf().affine_inverse() * pos
			if sec.holds(q):
				at = i
				lp = q
				break
		var last: Array = _aboard.get(pl, [])
		if at < 0 and not last.is_empty():
			var sec0 := sections[mini(int(last[0]), sections.size() - 1)] as TramSection
			var q0 := sec0.prev_xf().affine_inverse() * pos
			var jump := q0.distance_to(last[1]) > 3.0
			if not jump and not sec0.door_exit(q0):
				pl.global_position = sec0.prev_xf() * (last[1] as Vector3)   # (carried on below)
				pl.velocity = Vector3.ZERO
				at = int(last[0])
				lp = last[1]
		if at < 0:
			if not last.is_empty():
				_aboard.erase(pl)
				pl.carrier_velocity = Vector3.ZERO
				pl.sheltered = false
			continue
		_aboard[pl] = [at, lp]
		(sections[at] as TramSection).carry_at(pl, lp, dt)
		carried[at] = carried.get(at, []) + [pl]
	for i in sections.size():
		(sections[i] as TramSection).set_riders(carried.get(i, []))


func distance_to_player(at: Vector3) -> float:
	if not built or not _placed:
		return 0.0                                   # (still being made, or not yet put on its line: keep it)
	var best := INF
	for sec in sections:
		best = minf(best, (sec as Node3D).global_position.distance_to(at))
	return best


func carrying_player() -> bool:
	if _player != null:
		return true
	for p in get_tree().get_nodes_in_group("player"):
		for sec in sections:
			if (sec as TramSection).carries(p):
				return true
	return false
