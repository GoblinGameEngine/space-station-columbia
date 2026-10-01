extends Node3D
class_name SignPhysics

## The road signs as things a vehicle can hit. Around the player (RANGE) each standing sign has a
## sensor on its post; a vehicle through it at more than a walk knocks it down: the drawn sign is
## taken out of RoadFurniture's merged meshes and out of TrafficSigns (drivers no longer see it --
## knock down a stop sign and nobody stops there), and the sign itself flies off as a body of
## MASS kg (a breakaway post and its plate) with the momentum the vehicle gives it; the vehicle
## loses as much. Knocked-down signs lie where they fall until the player is far away.

const RANGE := 90.0
const MASS := 25.0
const LITTER := 40                   # the most knocked-down signs kept lying about

var player: Node3D
var furniture: Node                  # RoadFurniture
var _areas := {}                     # sign id -> Area3D
var _down: Array = []                # RigidBody3D
var _t := 0.0


func _process(delta: float) -> void:
	if player == null or StationGeo.loading:
		return
	_t -= delta
	if _t > 0.0:
		return
	_t = 0.4
	TrafficSigns.load_all()
	var here := Vector2(StationGeo.s_of(player.global_position), player.global_position.x)
	var want := {}
	for sg in TrafficSigns.signs_near(here, RANGE):
		want[sg.id] = true
		if not _areas.has(sg.id):
			_areas[sg.id] = _sensor(sg)
	for id in _areas.keys():
		if not want.has(id):
			(_areas[id] as Node).queue_free()
			_areas.erase(id)


func _sensor(sg: Dictionary) -> Area3D:
	var p: Vector2 = sg.p
	var a := Area3D.new()
	a.collision_layer = 0
	a.collision_mask = RemakeGroundVehicle.HULL_LAYER | 1
	a.monitorable = false
	var cs := CollisionShape3D.new()
	var b := BoxShape3D.new()
	b.size = Vector3(0.35, 2.6, 0.35)
	cs.shape = b
	cs.position = Vector3(0, 1.3, 0)
	a.add_child(cs)
	add_child(a)
	a.global_transform = Transform3D(StationGeo.basis(p.x, 0.0), StationGeo.point(p.x, p.y, MapTerrain.elevation(p.x, p.y)))
	var id: int = sg.id
	a.body_entered.connect(func(body: Node3D): _hit(id, body))
	return a


func _hit(id: int, body: Node3D) -> void:
	var v := Vector3.ZERO
	var m := 1000.0
	if body is NpcCarBody:
		v = (body as NpcCarBody).v_now if (body as NpcCarBody).freeze else (body as NpcCarBody).linear_velocity
		m = (body as NpcCarBody).mass
	elif body is RigidBody3D:
		v = (body as RigidBody3D).linear_velocity
		m = (body as RigidBody3D).mass
	else:
		return
	if v.length() < 1.5:
		return
	knock(id, v, m, body)


func knock(id: int, v: Vector3, m_hit: float, hitter: Node = null) -> void:
	if furniture == null or not _areas.has(id):
		return
	(_areas[id] as Node).queue_free()
	_areas.erase(id)
	var i := id - 1                                   # TrafficSigns ids follow the file's order
	var built: Array = furniture.sign_mesh(i)
	TrafficSigns.remove_sign(id)
	furniture.remove_sign(i)
	var rb := RigidBody3D.new()
	rb.mass = MASS
	rb.collision_layer = 1 << 10
	rb.collision_mask = 1 | RemakeGroundVehicle.HULL_LAYER
	var mi := MeshInstance3D.new()
	mi.mesh = built[0]
	rb.add_child(mi)
	var cs := CollisionShape3D.new()
	var b := BoxShape3D.new()
	b.size = Vector3(0.6, 2.8, 0.12)
	cs.shape = b
	cs.position = Vector3(0, 1.4, 0)
	rb.add_child(cs)
	add_child(rb)
	rb.global_transform = built[1]
	var gain := v * (m_hit * 1.3 / (m_hit + MASS))
	var up := StationGeo.up(StationGeo.s_of(rb.global_position))
	rb.linear_velocity = gain + up * minf(gain.length() * 0.3, 4.0)
	rb.angular_velocity = (built[1] as Transform3D).basis.x * randf_range(-6.0, 6.0) + up * randf_range(-3.0, 3.0)
	if hitter is RigidBody3D and not (hitter as RigidBody3D).freeze:
		(hitter as RigidBody3D).apply_central_impulse(-gain * MASS)
	_down.append(rb)
	while _down.size() > LITTER:
		var old: Node = _down.pop_front()
		if is_instance_valid(old):
			old.queue_free()
	RoadDriver.tally["signs_knocked_down"] = int(RoadDriver.tally.get("signs_knocked_down", 0)) + 1
