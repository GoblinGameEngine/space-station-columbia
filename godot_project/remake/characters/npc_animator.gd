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
var _arm_rest_pole := Vector3(0, 0, 1)      # elbows point backward
var _stance_pose := "loose"
var _next_stance := 10.0
var _stance_weights := {}
var _blink_at := 3.0
var _blink_t := -1.0
var _skin_mat: ShaderMaterial
var _al1 := {}
var _head_prev := Vector2.ZERO     # last frame's head (yaw, pitch), for the hair's lag
var _antic := -1.0                 # time into an anticipation (-1: none)
var lead_turn := 0.0               # the head turning ahead of the body into a coming turn (rad)
var _talk_until := -1.0
var _beat_next := 0.0
var _beat_t := -1.0
var _beat_side := "R"
var _beat_off := Vector3.ZERO


func talk(seconds: float) -> void:
	## Speaking for a while: beat gestures (Kendon: preparation, stroke, hold, retraction; McNeill's
	## beats mark the rhythm of speech), nods on the beats, the mouth moving.
	_talk_until = t + seconds
	_beat_next = t + 0.3


func anticipate() -> void:
	## Called just before a start (the plan knows it's coming): tame -- the weight rocks back and
	## down -- before the tsume of the first step.
	_antic = 0.0
var _al2 := {}

## Idle stances as hand targets relative to the body's own landmarks (so one stance fits every
## body): [which frame ("hips" or "chest"), left wrist offset, right wrist offset, elbow direction]
## -- offsets in fractions of height from that frame's joint; null = that arm hangs loose.
const STANCES := {
	"loose": null,
	"clasped_front": ["hips", Vector3(-0.022, -0.06, -0.085), Vector3(0.022, -0.06, -0.085), Vector3(0.55, -0.2, 0.8)],
	"behind_back": ["hips", Vector3(-0.018, 0.0, 0.085), Vector3(0.018, 0.0, 0.085), Vector3(0.75, -0.25, 0.6)],
	"folded": ["chest", Vector3(0.04, -0.045, -0.085), Vector3(-0.045, -0.03, -0.1), Vector3(0.5, -0.85, 0.1)],
	"hand_on_hip": ["hips", null, Vector3(0.13, 0.055, 0.0), Vector3(0.9, 0.0, 0.45)],
}


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
	for side in ["L", "R"]:
		_al1[side] = ((_J["LowerArm" + side] as Vector3) - (_J["UpperArm" + side] as Vector3)).length()
		_al2[side] = ((_J["Hand" + side] as Vector3) - (_J["LowerArm" + side] as Vector3)).length()
	_rng = NpcRng.for_trait(npc.world_seed, npc.pid, "anim")
	set_mood(mood)
	# which stances this person falls into (personality; elders clasp their hands behind them)
	var p: Dictionary = npc.traits.get("personality", {})
	var agr := float(p.get("agreeableness", 0.5))
	var ext := float(p.get("extraversion", 0.5))
	var con := float(p.get("conscientiousness", 0.5))
	var old := smoothstep(55.0, 80.0, float(npc.traits.get("age", 30)))
	_stance_weights = {"loose": 3.0, "clasped_front": 1.0 + 2.0 * agr + (1.0 - ext),
		"behind_back": 0.5 + 2.0 * con + 3.0 * old, "folded": 0.3 + 2.0 * (1.0 - agr) + (1.0 - ext),
		"hand_on_hip": 0.2 + 2.0 * ext * (1.0 - 0.5 * agr)}
	if float(npc.traits.get("age", 30)) < 8.0:
		_stance_weights = {"loose": 1.0}
	_next_stance = 3.0 + _rng.rand() * 10.0
	var m := npc.body_mesh.mesh as ArrayMesh
	if m and m.get_surface_count() > 0:
		_skin_mat = m.surface_get_material(0) as ShaderMaterial
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
		if _rng.rand() < 0.6:
			_blink_t = 0.0                                  # blinks come with gaze shifts (Ruhland 2015)
	if time > _next_stance:
		_stance_pose = _rng.pick(_stance_weights)
		_next_stance = time + 8.0 + _rng.rand() * 25.0
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
	# anticipation: back and down over ~0.4 s, sized by the person's anticipation (Strong: more)
	var ak := 0.0
	if _antic >= 0.0:
		_antic += dt
		ak = sin(PI * clampf(_antic / 0.4, 0.0, 1.0)) * (0.4 + 1.2 * float(style.anticipation))
		if _antic >= 0.4:
			_antic = -1.0
	var hip_pos := hips_rest + Vector3(shift, bob - sag - 0.012 * T * ak, 0.018 * T * ak)
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
	# the lean into the walk goes through a spring: on stopping it carries on forward and settles
	# (follow-through), more for Free people (PERFORM overshoot)
	var lean_t: float = float(style.lean) + deg_to_rad(4.0) * walk * float(style.speed) - deg_to_rad(5.0) * ak
	var lean := _spring("lean", lean_t, dt, 1.6, clampf(0.9 - float(style.overshoot), 0.25, 0.9))
	var turn := _spring("chest_turn", -yaw * 0.9 * float(style.torso_turn) / 0.29, dt, 2.2, 0.5)
	var q_spine := Quaternion.from_euler(Vector3(lean * 0.5, -yaw * 0.4, -list * 0.6))
	var q_chest := Quaternion.from_euler(Vector3(lean * 0.5 + deg_to_rad(1.6) * breathe * idle * float(style.breath), turn, -list * 0.25))
	_set_rot("Spine", q_spine)
	_set_rot("Chest", q_chest)
	var t_hips := Transform3D(hb, hip_pos)
	var t_spine := t_hips * Transform3D(Basis(q_spine), (_J.Spine as Vector3) - (_J.Hips as Vector3))
	var t_chest := t_spine * Transform3D(Basis(q_chest), (_J.Chest as Vector3) - (_J.Spine as Vector3))
	var st: Variant = STANCES.get(_stance_pose)
	# talking: a beat every 0.5-1.4 s (extraverts faster, bigger); a beat is a quick stroke out and
	# down from a raised hand, a short hold, a slower retraction
	var talking := time < _talk_until
	var ext := float((npc.traits.get("personality", {}) as Dictionary).get("extraversion", 0.5))
	if talking and time > _beat_next:
		_beat_t = 0.0
		_beat_side = "R" if _rng.rand() < 0.7 else "L"
		_beat_off = Vector3((_rng.rand() - 0.5) * 0.03, (_rng.rand() - 0.5) * 0.03, 0)
		_beat_next = time + lerpf(1.4, 0.5, ext) * (0.7 + 0.6 * _rng.rand())
	var beat := 0.0
	if _beat_t >= 0.0:
		_beat_t += dt
		var bt := _beat_t / lerpf(0.9, 0.6, ext)
		beat = smoothstep(0.0, 0.25, bt) * (1.0 - smoothstep(0.55, 1.0, bt))
		if bt >= 1.0:
			_beat_t = -1.0
	var gesture_w := _spring("gesture_w", 1.0 if talking else 0.0, dt, 1.0, 0.8)
	var stance_w := _spring("stance_w", idle if st != null else 0.0, dt, 1.1, 0.8)
	var arm_amp := deg_to_rad(17.0) * float(style.arm_swing) * amp * clampf(speed / 1.3 + 0.2, 0.4, 1.0)
	var spread := deg_to_rad(4.0) * float(style.spread)
	for side in ["L", "R"]:
		var k := -1.0 if side == "L" else 1.0
		var ls := 0.0 if side == "L" else PI
		var sw := -cos(a + ls)                                         # +1: this arm fully forward
		var arm_t := arm_amp * sw * walk + deg_to_rad(1.5) * _noise(1.0 + ls, 0.3) * idle
		var arm := _spring("arm" + side, arm_t, dt, 1.8, 0.62)
		# the arm swings a little across the body on its forward swing (Muybridge)
		var across := deg_to_rad(5.0) * maxf(0.0, arm / maxf(arm_amp, 0.01)) * walk
		var elbow := _spring("elbow" + side, deg_to_rad(12.0 + 10.0 * walk) + maxf(0.0, arm) * 0.8 + float(style.elbow), dt, 2.2, 0.5)
		var q_up := Quaternion.from_euler(Vector3(arm, -k * across * 0.5, -k * (spread + deg_to_rad(1.5) * idle) + k * across))
		var q_lo := Quaternion.from_euler(Vector3(elbow, 0, 0))
		var q_ha := Quaternion.from_euler(Vector3(_spring("wrist" + side, elbow * 0.3, dt, 2.6, 0.4), 0, 0))
		# an idle stance: the hand goes to its place by arm IK, blended in and out
		if st != null and stance_w > 0.01:
			var off: Variant = st[1] if side == "L" else st[2]
			if off != null:
				var frame: Transform3D = t_hips if st[0] == "hips" else t_chest
				var local: Vector3 = (off as Vector3) * float(_L.T)
				var tgt := frame.basis * local + frame.origin
				var pole: Vector3 = st[3]
				var ik := _arm_ik(side, tgt, t_chest, Vector3(-pole.x if side == "L" else pole.x, pole.y, pole.z))
				var w := clampf(stance_w, 0.0, 1.0)
				q_up = q_up.slerp(ik[0], w)
				q_lo = q_lo.slerp(ik[1], w)
				q_ha = q_ha.slerp(Quaternion.IDENTITY, w)
		# the gesturing hand: raised in front of the body, stroking out and down on each beat
		if gesture_w > 0.01 and side == _beat_side:
			var amp_g := lerpf(0.6, 1.3, ext)
			var stroke := Vector3(0.02, -0.035, -0.025) * amp_g * beat
			var local := Vector3(k * 0.07, -0.07, -0.13) + stroke + _beat_off
			var tgt := t_chest.basis * (local * float(_L.T)) + t_chest.origin
			var ik := _arm_ik(side, tgt, t_chest, Vector3(k * 0.7, -0.6, 0.3))
			var w := clampf(gesture_w, 0.0, 1.0)
			q_up = q_up.slerp(ik[0], w)
			q_lo = q_lo.slerp(ik[1], w)
			q_ha = q_ha.slerp(Quaternion.from_euler(Vector3(deg_to_rad(-15.0) * beat, 0, 0)), w)
		_set_rot("UpperArm" + side, q_up)
		_set_rot("LowerArm" + side, q_lo)
		_set_rot("Hand" + side, q_ha)
	var look := _spring("look", _look_target * (1.0 - 0.6 * walk) + lead_turn, dt, 1.4, 0.8)
	# the head stays level as the body bobs and leans; sad people look down
	var nod := _spring("nod", -lean * 0.7 - bob * 1.5 + float(style.head_down) + deg_to_rad(1.5) * _noise(3.0, 0.2) * idle + deg_to_rad(4.0) * beat, dt, 2.5, 0.6)
	_set_rot("Neck", Quaternion.from_euler(Vector3(nod * 0.6, look * 0.4 - turn * 0.5, list * 0.4)))
	_set_rot("Head", Quaternion.from_euler(Vector3(nod * 0.4, look * 0.6, list * 0.3)))
	# hair: hangs back from the head, lags its turns and bounces with the step (loose, underdamped)
	var head_now := Vector2(look + yaw * 0.5, nod + lean)
	var hv := (head_now - _head_prev) / maxf(dt, 1e-3) if dt > 0.0 else Vector2.ZERO
	_head_prev = head_now
	var hair_pitch := _spring("hair_p", -hv.y * 0.12 + deg_to_rad(5.0) * sin(2.0 * a) * walk * float(style.bounce) - lean * 0.6, dt, 1.3, 0.28)
	var hair_yaw := _spring("hair_y", -hv.x * 0.15 - yaw * 0.5, dt, 1.1, 0.3)
	var hair_roll := _spring("hair_r", -list * 1.2, dt, 1.2, 0.3)
	_set_rot("HairA", Quaternion.from_euler(Vector3(hair_pitch * 0.5, hair_yaw * 0.5, hair_roll * 0.5)))
	_set_rot("HairB", Quaternion.from_euler(Vector3(hair_pitch, hair_yaw, hair_roll)))
	_hands(grip + 0.08 * breathe * idle + 0.1 * walk)
	# the eyes lead: they jump to where the head is going and centre again as it arrives
	if _skin_mat:
		var eye_x := clampf((_look_target * (1.0 - 0.6 * walk) + lead_turn - look) * 2.4, -1.0, 1.0)
		var eye_y := clampf(-float(style.head_down) * 1.5, -1.0, 0.0)
		_skin_mat.set_shader_parameter("gaze", Vector2(eye_x, eye_y))
		if dt > 0.0:
			if _blink_t < 0.0 and time > _blink_at:
				_blink_t = 0.0
			var bl := 0.0
			if _blink_t >= 0.0:
				_blink_t += dt
				bl = sin(PI * clampf(_blink_t / 0.16, 0.0, 1.0))
				if _blink_t >= 0.16:
					_blink_t = -1.0
					_blink_at = time + 1.5 + _rng.rand() * 4.5              # ~15-20 a minute
			_skin_mat.set_shader_parameter("blink", bl)
			var mo := 0.0
			if talking:                                           # syllables, roughly: open-close at ~5 Hz
				mo = clampf(0.55 + 0.45 * sin(time * 31.0) * sin(time * 7.3 + 1.0), 0.0, 1.0) * (0.6 + 0.4 * absf(_noise(5.0, 3.0)))
			_skin_mat.set_shader_parameter("mouth_open", mo)


func _arm_ik(side: String, target: Vector3, t_chest: Transform3D, pole: Vector3) -> Array:
	## Two-bone arm IK -> [UpperArm local, LowerArm local] rotations (the Shoulder bone at rest).
	var shoulder := t_chest * ((_J["UpperArm" + side] as Vector3) - (_J.Chest as Vector3))
	var l1: float = _al1[side]
	var l2: float = _al2[side]
	var d := target - shoulder
	var dist := clampf(d.length(), absf(l1 - l2) + 0.01, (l1 + l2) * 0.999)
	var dn := d.normalized()
	var pn := pole.normalized()
	var perp := (pn - dn * pn.dot(dn))
	if perp.length() < 0.01:
		perp = Vector3(0, 0, 1) - dn * dn.z
	perp = perp.normalized()
	var a1 := acos(clampf((l1 * l1 + dist * dist - l2 * l2) / (2.0 * l1 * dist), -1.0, 1.0))
	var upper := (dn * cos(a1) + perp * sin(a1)).normalized()
	var elbow_p := shoulder + upper * l1
	var fore := (shoulder + dn * dist - elbow_p).normalized()
	var r1: Vector3 = ((_J["LowerArm" + side] as Vector3) - (_J["UpperArm" + side] as Vector3)).normalized()
	var r2: Vector3 = ((_J["Hand" + side] as Vector3) - (_J["LowerArm" + side] as Vector3)).normalized()
	var g_up := _frame(upper, perp) * _frame(r1, _arm_rest_pole).inverse()
	var g_lo := _frame(fore, perp) * _frame(r2, _arm_rest_pole).inverse()
	return [(t_chest.basis.inverse() * g_up).get_rotation_quaternion(), (g_up.inverse() * g_lo).get_rotation_quaternion()]


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
