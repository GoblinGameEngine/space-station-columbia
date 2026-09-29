extends Node
class_name NpcAnimator

## The procedural animation generator for generated people (research/animation/motion_design.md).
## No animation assets: every body is different, so motion comes from rules that fit any
## proportions.
##
## Legs are driven by where the feet must be, not by joint formulas: each foot is planted while
## it bears weight (moving back under the body at exactly the body's speed, so it never slides),
## swings forward low on an arc, lands on the heel toe-up, rolls flat, and rises onto the ball of the
## foot with the toes bending (Johansen 2009's footbase; normative gait, gait_reference.md;
## Muybridge).  Two-bone IK finds the hip and knee for any leg length.  The pelvis bobs (lowest at
## double support), shifts over the standing foot, drops on the swinging side and rotates with the
## step; the feet stay put, so standing contrapposto -- weight on one leg, the other knee easing --
## falls out of the same solve.  The chest counter-rotates, the arms swing across the body
## opposite the legs, and the head stays level.
##
## Style comes from who they are (NpcStyle: personality -> Laban Effort -> PERFORM's motion
## parameters; mood -> Roether's emotion-in-gait features; age and body).  Springs give overlap and
## follow-through, stiffer for Bound people and looser for Free ones.  Optionally the pose is
## sampled at a drawing rate (Ghibli walks are mostly on threes -- principles.md 4).
##
## Space: the character's own (skeleton = model space): +X right, +Y up, -Z forward.

var npc: NpcCharacter
var skel: Skeleton3D
var speed := 0.0            # m/s, set by whoever moves the NPC
var mood := "neutral"
var drawing_rate := 1       # frames of 24 per pose: 1 smooth, 2 twos, 3 threes
var manual := false         # posed by someone else (tools): _process leaves the skeleton alone
var grip := 0.3             # 0 open hand .. 0.3 relaxed .. 1 fist
var phase := 0.0
var t := 0.0
var style: Dictionary
var _held := 0.0
var _rng: NpcRng
var _walk := 0.0
var _look_target := 0.0
var _next_glance := 2.0
var _stance := 1.0
var _next_shift := 8.0
var _springs := {}
var _bone := {}
var _seed := 0.0
var _J: Dictionary
var _L: Dictionary
var _l1 := {}
var _l2 := {}
var _rest_pole := Vector3(0, 0, -1)


static func attach(p_npc: NpcCharacter) -> NpcAnimator:
	var a := NpcAnimator.new()
	a.name = "Animator"
	a.npc = p_npc
	p_npc.add_child(a)
	return a


func _ready() -> void:
	skel = npc.skeleton
	for i in NpcBody.BONES.size():
		_bone[NpcBody.BONES[i]] = i
	_J = npc.built.joints
	_L = npc.built.landmarks
	for side in ["L", "R"]:
		_l1[side] = ((_J["LowerLeg" + side] as Vector3) - (_J["UpperLeg" + side] as Vector3)).length()
		_l2[side] = ((_J["Foot" + side] as Vector3) - (_J["LowerLeg" + side] as Vector3)).length()
	_rng = NpcRng.for_trait(npc.world_seed, npc.pid, "anim")
	set_mood(mood)
	t = _rng.rand() * 10.0                   # people aren't in step with each other
	_seed = _rng.rand() * 100.0
	_next_glance = 1.0 + _rng.rand() * 6.0
	_stance = 1.0 if _rng.rand() < 0.5 else -1.0
	_next_shift = 5.0 + _rng.rand() * 15.0


func set_mood(m: String) -> void:
	mood = m
	style = NpcStyle.params(npc.traits, mood)


func stride_length() -> float:
	## Distance the body moves per full cycle (two steps).
	return float(_L.T) * 0.8 * float(style.stride)


func _process(delta: float) -> void:
	if manual:
		return
	t += delta
	_walk = move_toward(_walk, clampf(speed / 0.9, 0.0, 1.0), delta * 2.5)     # ease in / out
	if speed > 0.02:
		phase = fmod(phase + delta * speed / stride_length(), 1.0)
	elif _walk > 0.02:
		phase = fmod(phase + delta * 0.3 * _walk, 1.0)                           # finishing the step
	if drawing_rate > 1:
		_held += delta
		if _held < drawing_rate / 24.0:
			return
		delta = _held
		_held = 0.0
	pose(phase, _walk, t, delta)


# -- helpers ------------------------------------------------------------------------------------

func _spring(sname: String, target: float, dt: float, freq := 3.0, damp := 0.55) -> float:
	## A damped spring toward target: the part lags and settles (overlap, follow-through).  dt 0:
	## no spring (tools posing single frames).
	if dt <= 0.0:
		return target
	freq *= float(style.stiff)
	damp = clampf(damp * float(style.damp) / 0.55, 0.15, 1.2)
	var s: Array = _springs.get(sname, [target, 0.0])
	var w := TAU * freq
	var steps := maxi(1, ceili(dt / 0.02))
	var h := dt / steps
	for i in steps:
		var acc: float = w * w * (target - float(s[0])) - 2.0 * damp * w * float(s[1])
		s[1] = float(s[1]) + acc * h
		s[0] = float(s[0]) + float(s[1]) * h
	_springs[sname] = s
	return s[0]


func _noise(ch: float, rate: float) -> float:
	var x := t * rate + _seed + ch * 17.0
	return (sin(x) + sin(x * 1.618 + 1.3) * 0.6 + sin(x * 2.718 + 0.7) * 0.3) / 1.9


static func _frame(dir: Vector3, pole: Vector3) -> Basis:
	## An orthonormal frame for a limb segment pointing along dir with its bend toward pole.
	var y := -dir.normalized()
	var z := -(pole - dir * pole.dot(dir)).normalized()
	return Basis(y.cross(z), y, z)


func _set_rot(bone: String, q: Quaternion) -> void:
	skel.set_bone_pose_rotation(_bone[bone], q)


# -- the pose ------------------------------------------------------------------------------------

func pose(ph: float, walk: float, time: float, dt := 0.0) -> void:
	var T: float = _L.T
	var S := stride_length()
	var amp: float = style.amp
	var idle := 1.0 - walk
	var breathe := sin(time * TAU / (3.6 + 1.2 * (1.0 - float(style.breath))))
	# idle life: balance shifts and glances, with long still holds between
	if time > _next_glance:
		_look_target = 0.0 if absf(_look_target) > 0.1 else (_rng.rand() - 0.5) * 1.1 * float(style.look_far)
		var hold := 2.5 + _rng.rand() * 7.0
		_next_glance = time + (hold / float(style.look_often) if _look_target == 0.0 else 0.8 + _rng.rand() * 1.5)
	if time > _next_shift:
		_stance = -_stance
		_next_shift = time + 6.0 + _rng.rand() * 18.0
	var stance := _spring("stance", _stance, dt, 0.6, 0.9)
	# -- pelvis: bob, weight shift, list (drop on the swing side), rotation with the step
	var a := ph * TAU
	var bob := -0.5 * (1.0 + cos(2.0 * TAU * (ph - 0.05))) * 0.024 * T * float(style.bounce) * amp * walk
	var shift_walk := -cos(TAU * (ph - 0.3)) * 0.016 * T * float(style.sway) * amp
	var shift := shift_walk * walk + (-0.02 * T * stance) * idle
	var list := -cos(TAU * (ph - 0.3)) * deg_to_rad(4.5) * float(style.sway) * amp * walk + deg_to_rad(4.0) * stance * idle
	var yaw := -cos(a) * deg_to_rad(5.0) * float(style.stride) * amp * walk
	var hips_rest: Vector3 = _J.Hips
	var sag := 0.006 * T * idle * absf(stance) + 0.01 * T * (1.0 - float(style.rise)) * 0.5
	var hip_pos := hips_rest + Vector3(shift, bob - sag, 0)
	var hq := Quaternion.from_euler(Vector3(deg_to_rad(2.5) * walk, yaw, list))
	skel.set_bone_pose_position(_bone.Hips, hip_pos)
	_set_rot("Hips", hq)
	var hb := Basis(hq)
	# -- legs: foot targets, then IK
	var foot_x := 0.024 * T * float(style.base)
	for side in ["L", "R"]:
		var k := -1.0 if side == "L" else 1.0
		var lt := fposmod(ph + (0.0 if side == "L" else 0.5), 1.0)       # 0 = heel strike
		var ank_rest: Vector3 = _J["Foot" + side]
		# walking target
		var z := 0.0
		var lift := 0.0
		var pitch := 0.0                                                # + toes up
		var toe := 0.0
		if lt < 0.6:
			z = -0.3 * S + S * lt
			if lt < 0.08:
				pitch = deg_to_rad(14.0) * (1.0 - lt / 0.08)             # heel strike, rolling down
			elif lt > 0.45:
				var r := (lt - 0.45) / 0.15
				pitch = -deg_to_rad(32.0) * r * r                         # heel rising onto the ball
				toe = -pitch
		else:
			var u := (lt - 0.6) / 0.4
			z = 0.3 * S - 0.6 * S * (u - sin(TAU * u) / TAU)             # cycloid: slow-fast-slow
			lift = sin(PI * u) * 0.035 * T * float(style.knee_swing) * amp
			pitch = lerpf(-deg_to_rad(32.0), deg_to_rad(14.0), smoothstep(0.1, 1.0, u)) if u > 0.1 else -deg_to_rad(32.0) * (1.0 - u / 0.1 * 0.3)
			toe = maxf(0.0, -pitch) * (1.0 - smoothstep(0.0, 0.3, u))
		var walk_target := Vector3(k * foot_x, ank_rest.y + lift, ank_rest.z + z)
		# the ankle rises when the foot pitches: about the heel (toes up) or the ball (heel up)
		if pitch > 0.0:
			var heel := Vector3(0, 0, 0.22 * float(_L.foot_len))
			walk_target += (_rot_x(-heel, pitch) + heel)
		elif pitch < 0.0:
			var ball := Vector3(0, -ank_rest.y + 0.01, -NpcBody.BALL * float(_L.foot_len))
			walk_target += (_rot_x(-ball, pitch) + ball)
		var idle_target := Vector3(k * float(_L.leg_sep) * 0.85, ank_rest.y, ank_rest.z)
		var target := idle_target.lerp(walk_target, walk)
		_leg_ik(side, target, hip_pos, hb, pitch * walk, toe * walk)
	# -- spine, chest, arms, head
	var lean: float = float(style.lean) + deg_to_rad(4.0) * walk * float(style.speed)
	var turn := _spring("chest_turn", -yaw * 0.9 * float(style.torso_turn) / 0.29, dt, 2.2, 0.5)
	_set_rot("Spine", Quaternion.from_euler(Vector3(lean * 0.5, -yaw * 0.4, -list * 0.6)))
	_set_rot("Chest", Quaternion.from_euler(Vector3(lean * 0.5 + deg_to_rad(1.6) * breathe * idle * float(style.breath), turn, -list * 0.25)))
	var arm_amp := deg_to_rad(17.0) * float(style.arm_swing) * amp * clampf(speed / 1.3 + 0.2, 0.4, 1.0)
	var spread := deg_to_rad(4.0) * float(style.spread)
	for side in ["L", "R"]:
		var k := -1.0 if side == "L" else 1.0
		var ls := 0.0 if side == "L" else PI
		var sw := -cos(a + ls)                                         # +1: this arm fully forward
		var arm_t := arm_amp * sw * walk + deg_to_rad(1.5) * _noise(1.0 + ls, 0.3) * idle
		var arm := _spring("arm" + side, arm_t, dt, 1.8, 0.45)
		# the arm swings a little across the body on its forward swing (Muybridge)
		var across := deg_to_rad(5.0) * maxf(0.0, arm / maxf(arm_amp, 0.01)) * walk
		_set_rot("UpperArm" + side, Quaternion.from_euler(Vector3(arm, -k * across * 0.5, -k * (spread + deg_to_rad(1.5) * idle) + k * across)))
		var elbow := _spring("elbow" + side, deg_to_rad(12.0 + 10.0 * walk) + maxf(0.0, arm) * 0.8 + float(style.elbow), dt, 2.2, 0.5)
		_set_rot("LowerArm" + side, Quaternion.from_euler(Vector3(elbow, 0, 0)))
		_set_rot("Hand" + side, Quaternion.from_euler(Vector3(_spring("wrist" + side, elbow * 0.3, dt, 2.6, 0.4), 0, 0)))
	var look := _spring("look", _look_target * (1.0 - 0.6 * walk), dt, 1.2, 0.8)
	# the head stays level as the body bobs and leans; sad people look down
	var nod := _spring("nod", -lean * 0.7 - bob * 1.5 + float(style.head_down) + deg_to_rad(1.5) * _noise(3.0, 0.2) * idle, dt, 2.5, 0.6)
	_set_rot("Neck", Quaternion.from_euler(Vector3(nod * 0.6, look * 0.4 - turn * 0.5, list * 0.4)))
	_set_rot("Head", Quaternion.from_euler(Vector3(nod * 0.4, look * 0.6, list * 0.3)))
	_hands(grip + 0.08 * breathe * idle + 0.1 * walk)


static func _rot_x(v: Vector3, ang: float) -> Vector3:
	return Vector3(v.x, v.y * cos(ang) - v.z * sin(ang), v.y * sin(ang) + v.z * cos(ang))


func _leg_ik(side: String, target: Vector3, hip_pos: Vector3, hb: Basis, pitch: float, toe: float) -> void:
	## Two-bone IK: the hip and knee that put the ankle on target, the knee bending forward.
	var hips_rest: Vector3 = _J.Hips
	var hip_joint := hip_pos + hb * ((_J["UpperLeg" + side] as Vector3) - hips_rest)
	var l1: float = _l1[side]
	var l2: float = _l2[side]
	var d := target - hip_joint
	var dist := clampf(d.length(), absf(l1 - l2) + 0.01, (l1 + l2) * 0.999)
	var dn := d.normalized()
	var a1 := acos(clampf((l1 * l1 + dist * dist - l2 * l2) / (2.0 * l1 * dist), -1.0, 1.0))
	var pole := (Vector3(0, 0, -1) - dn * Vector3(0, 0, -1).dot(dn)).normalized()
	var thigh := (dn * cos(a1) + pole * sin(a1)).normalized()
	var knee := hip_joint + thigh * l1
	var shin := (hip_joint + dn * dist - knee).normalized()
	var r1: Vector3 = ((_J["LowerLeg" + side] as Vector3) - (_J["UpperLeg" + side] as Vector3)).normalized()
	var r2: Vector3 = ((_J["Foot" + side] as Vector3) - (_J["LowerLeg" + side] as Vector3)).normalized()
	var g_thigh := _frame(thigh, pole) * _frame(r1, _rest_pole).inverse()
	var g_shin := _frame(shin, pole) * _frame(r2, _rest_pole).inverse()
	var g_foot := Basis(Vector3.RIGHT, pitch)
	_set_rot("UpperLeg" + side, (hb.inverse() * g_thigh).get_rotation_quaternion())
	_set_rot("LowerLeg" + side, (g_thigh.inverse() * g_shin).get_rotation_quaternion())
	_set_rot("Foot" + side, (g_shin.inverse() * g_foot).get_rotation_quaternion())
	_set_rot("Toe" + side, Quaternion(Vector3.RIGHT, toe))


func _hands(g: float) -> void:
	## Fingers curl toward the palm; a relaxed hand cascades, the index straightest.
	var cascade := {"Index": 0.8, "Middle": 0.95, "Ring": 1.05, "Pinky": 1.2}
	for side in ["L", "R"]:
		var k := 1.0 if side == "L" else -1.0
		for fn in cascade:
			var c: float = g * cascade[fn]
			_set_rot(fn + "A" + side, Quaternion.from_euler(Vector3(0, 0, k * deg_to_rad(70.0) * c)))
			_set_rot(fn + "B" + side, Quaternion.from_euler(Vector3(0, 0, k * deg_to_rad(95.0) * c)))
		_set_rot("ThumbA" + side, Quaternion.from_euler(Vector3(deg_to_rad(20.0) * g, 0, k * deg_to_rad(25.0) * g)))
		_set_rot("ThumbB" + side, Quaternion.from_euler(Vector3(0, 0, k * deg_to_rad(35.0) * g)))
