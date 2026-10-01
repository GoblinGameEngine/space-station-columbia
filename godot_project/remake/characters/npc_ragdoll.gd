extends Node3D
class_name NpcRagdoll

## A person who can be knocked down (the user, 2026-10-01: "pedestrians should have ragdoll
## physics. We are going to be making a chaotic fun game"). A sensor around them notices a vehicle
## (or a flying wreck) coming through; they go limp -- physical bones on the body's twelve main
## segments, each with its share of their weight (Dempster's segment masses) -- and take the
## vehicle's momentum: the legs its speed, the body and head a little lift (the wrap of a real
## pedestrian impact); the vehicle loses what they gained. Once they've lain still for a moment they
## get up where they came to rest and carry on (after a hard hit, a while later).
##
##   var rag := NpcRagdoll.attach(npc, weight_kg); rag.got_up.connect(...)   rag.down -> bool

signal knocked(speed: float)
signal got_up(at: Vector3)

const RAG_LAYER := 1 << 10
# bone, child (the segment's far end; "" = along +Y), radius m, share of the body's mass, joint
const SEGS := [
	["Hips", "Spine", 0.14, 0.142, "cone"],
	["Spine", "Chest", 0.13, 0.139, "cone"],
	["Chest", "Neck", 0.15, 0.216, "cone"],
	["Head", "", 0.11, 0.081, "cone"],
	["UpperArmL", "LowerArmL", 0.05, 0.028, "cone"],
	["LowerArmL", "HandL", 0.045, 0.022, "hinge"],
	["UpperArmR", "LowerArmR", 0.05, 0.028, "cone"],
	["LowerArmR", "HandR", 0.045, 0.022, "hinge"],
	["UpperLegL", "LowerLegL", 0.075, 0.1, "cone"],
	["LowerLegL", "FootL", 0.055, 0.061, "hinge"],
	["UpperLegR", "LowerLegR", 0.075, 0.1, "cone"],
	["LowerLegR", "FootR", 0.055, 0.061, "hinge"],
]

var npc: Node3D
var weight := 70.0
var down := false
var _sk: Skeleton3D
var _sim: PhysicalBoneSimulator3D
var _bones := {}
var _still := 0.0
var _t := 0.0
var _stay := 2.0


static func attach(p_npc: Node3D, weight_kg: float) -> NpcRagdoll:
	var r := NpcRagdoll.new()
	r.name = "Ragdoll"
	r.npc = p_npc
	r.weight = clampf(weight_kg, 15.0, 200.0)
	p_npc.add_child(r)
	return r


func _ready() -> void:
	var a := Area3D.new()
	a.name = "Sensor"
	a.collision_layer = 0
	a.collision_mask = RemakeGroundVehicle.HULL_LAYER | 1
	a.monitorable = false
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.32
	cap.height = 1.7
	cs.shape = cap
	cs.position = Vector3(0, 0.9, 0)
	a.add_child(cs)
	add_child(a)
	a.body_entered.connect(_on_body)
	set_physics_process(false)


func _on_body(b: Node3D) -> void:
	if down:
		return
	var v := Vector3.ZERO
	var m := 1000.0
	if b is NpcCarBody:
		v = (b as NpcCarBody).v_now if (b as NpcCarBody).freeze else (b as NpcCarBody).linear_velocity
		m = (b as NpcCarBody).mass
	elif b is RigidBody3D:
		v = (b as RigidBody3D).linear_velocity
		m = (b as RigidBody3D).mass
	else:
		return
	if v.length() < 1.5:
		return                                       # a nudge, not a knock
	knock_down(v, m, b)


func knock_down(v: Vector3, m_hit: float, hitter: Node = null) -> void:
	## Limp, moving off with the momentum a body of m_hit at v gives them (restitution 0.2).
	if down:
		return
	_build()
	if _sim == null:
		return
	down = true
	var anim := npc.get_node_or_null("Animator")
	if anim:
		anim.set_process(false)
		anim.set_physics_process(false)
	_sim.physical_bones_start_simulation()
	var gain := v * (m_hit * 1.2 / (m_hit + weight))
	var up := StationGeo.up(StationGeo.s_of(npc.global_position))
	var sp := gain.length()
	for bn in _bones:
		var pb: PhysicalBone3D = _bones[bn]
		var dv := gain
		if bn in ["Hips", "Spine", "Chest"]:
			dv = gain * 0.85 + up * sp * 0.25
		elif bn == "Head":
			dv = gain * 0.8 + up * sp * 0.3
		elif bn.begins_with("UpperArm") or bn.begins_with("LowerArm"):
			dv = gain * 0.9 + up * sp * 0.2
		pb.apply_central_impulse(dv * pb.mass)
	if hitter is RigidBody3D and not (hitter as RigidBody3D).freeze:
		(hitter as RigidBody3D).apply_central_impulse(-gain * weight)
	_stay = 2.0 if sp < 7.0 else (8.0 if sp < 14.0 else 15.0)   # after a hard hit they lie a while
	_t = 0.0
	_still = 0.0
	set_physics_process(true)
	knocked.emit(sp)
	RoadDriver.tally["people_knocked_down"] = int(RoadDriver.tally.get("people_knocked_down", 0)) + 1


func _physics_process(delta: float) -> void:
	if not down:
		set_physics_process(false)
		return
	_t += delta
	var hips: PhysicalBone3D = _bones.get("Hips")
	if hips == null:
		return
	_still = _still + delta if hips.linear_velocity.length() < 0.4 else 0.0
	if (_still > 1.2 and _t > _stay) or _t > 30.0:
		_get_up(hips.global_position)


func _get_up(at: Vector3) -> void:
	_sim.physical_bones_stop_simulation()
	down = false
	var anim := npc.get_node_or_null("Animator")
	if anim:
		anim.set_process(true)
		anim.set_physics_process(true)
	set_physics_process(false)
	got_up.emit(at)


func _build() -> void:
	## The physical bones, the first time they're needed.
	if _sim != null:
		return
	_sk = npc.find_child("Skeleton*", true, false) as Skeleton3D
	if _sk == null:
		return
	_sim = PhysicalBoneSimulator3D.new()
	_sim.name = "Ragdoll"
	_sk.add_child(_sim)
	for seg in SEGS:
		var bi := _sk.find_bone(seg[0])
		if bi < 0:
			continue
		var rest := _sk.get_bone_global_rest(bi)
		var far := Vector3(0, 0.22, 0)
		if str(seg[1]) != "":
			var ci := _sk.find_bone(seg[1])
			if ci >= 0:
				far = (rest.affine_inverse() * _sk.get_bone_global_rest(ci)).origin
		var dir := far.normalized() if far.length() > 0.01 else Vector3.UP
		var length := maxf(far.length(), 0.08)
		var rot := Basis(Quaternion(Vector3.UP, dir))
		var mid := dir * length * 0.5
		var pb := PhysicalBone3D.new()
		pb.name = "PB_" + str(seg[0])
		pb.bone_name = seg[0]
		pb.mass = maxf(0.3, weight * float(seg[3]))
		pb.friction = 0.8
		pb.bounce = 0.05
		pb.collision_layer = RAG_LAYER
		pb.collision_mask = 1 | RemakeGroundVehicle.HULL_LAYER
		pb.body_offset = Transform3D(rot, mid)
		pb.joint_offset = Transform3D(Basis(), rot.inverse() * -mid)
		if str(seg[4]) == "hinge":
			pb.joint_type = PhysicalBone3D.JOINT_TYPE_HINGE
			pb.set("joint_constraints/angular_limit_enabled", true)
			pb.set("joint_constraints/angular_limit_upper", 0.0)
			pb.set("joint_constraints/angular_limit_lower", -140.0)
		else:
			pb.joint_type = PhysicalBone3D.JOINT_TYPE_CONE
			pb.set("joint_constraints/swing_span", 50.0)
			pb.set("joint_constraints/twist_span", 30.0)
		var cs := CollisionShape3D.new()
		var cap := CapsuleShape3D.new()
		cap.radius = float(seg[2])
		cap.height = maxf(length, float(seg[2]) * 2.0 + 0.02)
		cs.shape = cap
		pb.add_child(cs)
		_sim.add_child(pb)
		_bones[seg[0]] = pb
