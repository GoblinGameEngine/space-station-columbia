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
var _clip: Dictionary = {}          # the authored clip playing (NpcClips), if any
var _clip_id := ""
var _clip_t := 0.0
var _clip_loop := false
var _clip_env := 0.0               # blend envelope 0..1
var _clip_out := false
var _cs: Dictionary = {}           # this frame's sampled channels
var _props: Array = []             # prop nodes the clip put in the hands
var ambient := true                # break into idles (check a watch, stretch...) when standing
var _next_idle := 0.0
var _idle_weights := {}
var _brow0 := 0.0                  # the face's own brow height (the clip's brow adds to it)


func play(id: String, loop := false) -> float:
	## Play an authored clip (npc_clips.json) over the procedural layers; returns its length in
	## seconds (at this person's pace).  Always interruptible: play another, or stop_clip().
	var c := NpcClips.clip(id)
	if c.is_empty():
		return 0.0
	_clip = c
	_clip_id = id
	_clip_t = 0.0
	_clip_loop = loop or bool(c.get("loop", false))
	_clip_out = false
	_set_props(c.get("props", {}))
	return float(c.length) / _clip_rate()


func _set_props(props: Dictionary) -> void:
	## The clip's props (cup, broom...) on the Prop bones, sized to the person.
	for p in _props:
		if is_instance_valid(p):
			p.queue_free()
	_props = []
	for side in props:
		var kind := str(props[side])
		var prop := NpcProps.make(kind, float(_L.T), str(side))
		if kind in NpcProps.TWO_HANDED:
			# a long tool lies along the line from this hand through the other (_aim_props)
			skel.add_child(prop)
			prop.set_meta("aim", str(side))
			_props.append(prop)
			continue
		var att := BoneAttachment3D.new()
		att.bone_name = "Prop" + str(side)
		skel.add_child(att)
		att.add_child(prop)
		_props.append(att)


func _aim_props() -> void:
	for p in _props:
		if not is_instance_valid(p) or not p.has_meta("aim"):
			continue
		var side: String = p.get_meta("aim")
		var other := "L" if side == "R" else "R"
		var a := skel.get_bone_global_pose(_bone["Prop" + side]).origin
		var b := skel.get_bone_global_pose(_bone["Prop" + other]).origin
		if b.y > a.y:                      # held from the upper hand, the working end down past the lower
			var tmp := a
			a = b
			b = tmp
		var z := b - a
		if z.length() < 0.02:
			z = skel.get_bone_global_pose(_bone["Prop" + side]).basis.z
		z = z.normalized()
		var x := Vector3.UP.cross(z)
		if x.length() < 0.01:
			x = Vector3.RIGHT
		x = x.normalized()
		var sc := (p as Node3D).scale
		(p as Node3D).transform = Transform3D(Basis(x, z.cross(x), z).scaled(sc), a)


func stop_clip() -> void:
	_clip_out = true


func greet(persona: Dictionary = {}) -> float:
	## Meeting someone: warm extraverts wave, very warm people may touch their heart, others nod.
	## persona: the L2 traits if made (warmth lives there), else the body's own.  Returns the length.
	var p: Dictionary = persona.get("personality", npc.traits.get("personality", {}))
	var warm := float(p.get("warmth", p.get("agreeableness", 0.5)))
	var ext := float(p.get("extraversion", 0.5))
	if warm > 0.55 and ext > 0.5:
		return play("wave")
	if warm > 0.7:
		return play("hand_on_heart") if _rng.rand() < 0.3 else play("nod")
	return play("nod")


func _idle_gap() -> float:
	## Seconds between idles: restless (extravert, Sudden) people fidget more often.
	var ext := float((npc.traits.get("personality", {}) as Dictionary).get("extraversion", 0.5))
	return (14.0 + 30.0 * _rng.rand()) * lerpf(1.4, 0.7, ext)


func _ambient(time: float, walk: float, talking: bool) -> void:
	## Everything interruptible: walking off cuts a clip short; standing a while starts an idle.
	if walk > 0.3 and _clip_id != "" and not _clip_out:
		stop_clip()
	if not ambient or _idle_weights.is_empty() or walk > 0.05 or talking or _clip_id != "":
		if walk > 0.05 or talking:
			_next_idle = maxf(_next_idle, time + 4.0)
		return
	if time > _next_idle:
		play(str(_rng.pick(_idle_weights)))
		_next_idle = time + _idle_gap()


func clip_playing() -> String:
	return _clip_id if not _clip.is_empty() and not _clip_out else ""


func _clip_rate() -> float:
	## Sudden people act faster, Sustained ones slower (PERFORM: speed follows Time).
	return clampf(float(style.get("speed", 1.0)), 0.7, 1.4)


func _clip_step(dt: float) -> void:
	if _clip.is_empty():
		_cs = {}
		return
	var length := float(_clip.length)
	_clip_t += dt * _clip_rate()
	if _clip_t >= length:
		if _clip_loop and not _clip_out:
			_clip_t = fmod(_clip_t, length)
		else:
			_clip_out = true
	var fade := float(_clip.get("blend", 0.25))
	if _clip_out:
		_clip_env = move_toward(_clip_env, 0.0, dt / fade) if dt > 0.0 else 0.0
		if _clip_env <= 0.0:
			_set_props({})
			_clip = {}
			_clip_id = ""
			_cs = {}
			return
	else:
		_clip_env = move_toward(_clip_env, 1.0, dt / fade) if dt > 0.0 else 1.0
	_cs = NpcClips.sample_filtered(_clip, minf(_clip_t, length), 0.5 + float(style.anticipation))
	_cs["_w"] = _clip_env * float(_cs.get("w", 1.0))


func _clip_target(hv: Array, t_hips: Transform3D, t_upper: Transform3D) -> Vector3:
	## A clip's hand target [frame, x, y, z] in skeleton space.
	var fr := str(hv[0])
	if fr == "mix":
		return Vector3.ZERO
	var frame: Transform3D = t_upper if fr == "upper" else t_hips if fr == "hips" else Transform3D.IDENTITY
	if fr == "head":
		frame = Transform3D(t_upper.basis, t_upper * ((_J.Head as Vector3) - (_J.UpperChest as Vector3)))
	return frame.basis * (Vector3(float(hv[1]), float(hv[2]), float(hv[3])) * float(_L.T)) + frame.origin


func _clip_euler(ch: String) -> Vector3:
	## A channel of [pitch, yaw, roll] degrees, weighted, as radians.
	if not _cs.has(ch):
		return Vector3.ZERO
	var v: Array = _cs[ch]
	# authored pitch is + forward (bow, nod down); the rig's +x rotation leans back
	return Vector3(-deg_to_rad(float(v[0])), deg_to_rad(float(v[1])), deg_to_rad(float(v[2]))) * float(_cs._w)
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
	_idle_weights = NpcClips.ambient_weights(float(npc.traits.get("age", 30)))
	_next_idle = t + _idle_gap()
	var m := npc.body_mesh.mesh as ArrayMesh
	if m and m.get_surface_count() > 0:
		_skin_mat = m.surface_get_material(0) as ShaderMaterial
		var b0: Variant = _skin_mat.get_shader_parameter("brow_height")
		_brow0 = float(b0) if b0 != null else 0.0
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
	_clip_step(dt)
	var cw := float(_cs.get("_w", 0.0))
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
	if _cs.has("hips"):
		var hh: Array = _cs.hips
		hip_pos += Vector3(float(hh[0]), float(hh[1]), float(hh[2])) * T * cw
	var hq := Quaternion.from_euler(Vector3(deg_to_rad(2.5) * walk, yaw, list) + _clip_euler("hipsRot"))
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
		var fpitch := pitch * walk
		if _cs.has("foot" + side):
			var ft: Array = _cs["foot" + side]
			target = target.lerp(Vector3(float(ft[0]), float(ft[1]), float(ft[2])) * T, cw)
			fpitch = lerpf(fpitch, deg_to_rad(float(ft[3]) if ft.size() > 3 else 0.0), cw)
		_leg_ik(side, target, hip_pos, hb, fpitch, toe * walk)
	# -- spine, chest, arms, head
	# the lean into the walk goes through a spring: on stopping it carries on forward and settles
	# (follow-through), more for Free people (PERFORM overshoot)
	var lean_t: float = float(style.lean) + deg_to_rad(4.0) * walk * float(style.speed) - deg_to_rad(5.0) * ak
	var lean := _spring("lean", lean_t, dt, 1.6, clampf(0.9 - float(style.overshoot), 0.25, 0.9))
	var turn := _spring("chest_turn", -yaw * 0.9 * float(style.torso_turn) / 0.29, dt, 2.2, 0.5)
	var sp := _clip_euler("spine")
	var q_spine := Quaternion.from_euler(Vector3(lean * 0.5, -yaw * 0.4, -list * 0.6) + sp * 0.35)
	var q_chest := Quaternion.from_euler(Vector3(lean * 0.3, turn * 0.6, -list * 0.15) + sp * 0.35)
	# the upper chest carries the breath and the rest of the lean and counter-turn
	var q_upper := Quaternion.from_euler(Vector3(lean * 0.2 + deg_to_rad(1.8) * breathe * idle * float(style.breath), turn * 0.4, -list * 0.1) + sp * 0.3)
	_set_rot("Spine", q_spine)
	_set_rot("Chest", q_chest)
	_set_rot("UpperChest", q_upper)
	var t_hips := Transform3D(hb, hip_pos)
	var t_spine := t_hips * Transform3D(Basis(q_spine), (_J.Spine as Vector3) - (_J.Hips as Vector3))
	var t_chest := t_spine * Transform3D(Basis(q_chest), (_J.Chest as Vector3) - (_J.Spine as Vector3))
	var t_upper := t_chest * Transform3D(Basis(q_upper), (_J.UpperChest as Vector3) - (_J.Chest as Vector3))
	var st: Variant = STANCES.get(_stance_pose)
	# talking: a beat every 0.5-1.4 s (extraverts faster, bigger); a beat is a quick stroke out and
	# down from a raised hand, a short hold, a slower retraction
	var talking := time < _talk_until
	if dt > 0.0 and not manual:
		_ambient(time, walk, talking)
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
	var shr: Array = _cs.get("shoulders", [0.0, 0.0])
	for side in ["L", "R"]:
		var k := -1.0 if side == "L" else 1.0
		# the clavicle: raised by a clip (shrugs, cold, fright), the arm carried with it
		var q_sh := Quaternion(Vector3.BACK, k * deg_to_rad(float(shr[0 if side == "L" else 1])) * cw)
		_set_rot("Shoulder" + side, q_sh)
		var t_sh := t_upper * Transform3D(Basis(q_sh), (_J["Shoulder" + side] as Vector3) - (_J.UpperChest as Vector3))
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
				var ik := _arm_ik(side, tgt, t_sh, Vector3(-pole.x if side == "L" else pole.x, pole.y, pole.z))
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
			var ik := _arm_ik(side, tgt, t_sh, Vector3(k * 0.7, -0.6, 0.3))
			var w := clampf(gesture_w, 0.0, 1.0)
			q_up = q_up.slerp(ik[0], w)
			q_lo = q_lo.slerp(ik[1], w)
			q_ha = q_ha.slerp(Quaternion.from_euler(Vector3(deg_to_rad(-15.0) * beat, 0, 0)), w)
		# an authored clip's hand: arm IK to its target in its frame, blended by the clip's weight
		if cw > 0.001 and _cs.has("hand" + side):
			var hv: Array = _cs["hand" + side]
			var tgt := _clip_target(hv, t_hips, t_upper)
			if str(hv[0]) == "mix":
				tgt = _clip_target(hv[1], t_hips, t_upper).lerp(_clip_target(hv[2], t_hips, t_upper), float(hv[3]))
			var pv: Array = _cs.get("pole" + side, [0.5, -0.5, 0.4])
			# elbow directions are authored for the right arm (+x outward) and mirrored for the left
			var ik := _arm_ik(side, tgt, t_sh, Vector3(float(pv[0]) * k, float(pv[1]), float(pv[2])))
			q_up = q_up.slerp(ik[0], cw)
			q_lo = q_lo.slerp(ik[1], cw)
			q_ha = q_ha.slerp(Quaternion.from_euler(_clip_euler("wrist" + side) / maxf(cw, 1e-3)), cw)
		_set_rot("UpperArm" + side, q_up)
		_set_rot("LowerArm" + side, q_lo)
		_set_rot("Hand" + side, q_ha)
		_twist(side, q_ha)
	var look := _spring("look", _look_target * (1.0 - 0.6 * walk) + lead_turn, dt, 1.4, 0.8)
	# the head stays level as the body bobs and leans; sad people look down
	var nod := _spring("nod", -lean * 0.7 - bob * 1.5 + float(style.head_down) + deg_to_rad(1.5) * _noise(3.0, 0.2) * idle + deg_to_rad(4.0) * beat, dt, 2.5, 0.6)
	var hd := _clip_euler("head")
	_set_rot("Neck", Quaternion.from_euler(Vector3(nod * 0.6, look * 0.4 - turn * 0.5, list * 0.4) + hd * 0.4))
	_set_rot("Head", Quaternion.from_euler(Vector3(nod * 0.4, look * 0.6, list * 0.3) + hd * 0.6))
	# hair: hangs back from the head, lags its turns and bounces with the step (loose, underdamped)
	var head_now := Vector2(look + yaw * 0.5, nod + lean)
	var hv := (head_now - _head_prev) / maxf(dt, 1e-3) if dt > 0.0 else Vector2.ZERO
	_head_prev = head_now
	var hair_pitch := _spring("hair_p", -hv.y * 0.12 + deg_to_rad(5.0) * sin(2.0 * a) * walk * float(style.bounce) - lean * 0.6, dt, 1.3, 0.28)
	var hair_yaw := _spring("hair_y", -hv.x * 0.15 - yaw * 0.5, dt, 1.1, 0.3)
	var hair_roll := _spring("hair_r", -list * 1.2, dt, 1.2, 0.3)
	_set_rot("HairA", Quaternion.from_euler(Vector3(hair_pitch * 0.5, hair_yaw * 0.5, hair_roll * 0.5)))
	_set_rot("HairB", Quaternion.from_euler(Vector3(hair_pitch, hair_yaw, hair_roll)))
	var g0 := grip + 0.08 * breathe * idle + 0.1 * walk
	var base_curls := NpcClips.grip_curls(g0)
	var curls := {"L": base_curls, "R": base_curls}
	for side in ["L", "R"]:
		if cw > 0.001 and _cs.has("grip" + side):
			var cg: Variant = _cs["grip" + side]
			var cc: Array = cg if typeof(cg) == TYPE_ARRAY else NpcClips.grip_curls(cg)
			var mixed := []
			for i in 5:
				mixed.append(lerpf(float(base_curls[i]), float(cc[i]), cw))
			curls[side] = mixed
	_hands_curls(curls)
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
			var face: Dictionary = _cs.get("face", {})
			if cw > 0.001 and not face.is_empty():
				mo = lerpf(mo, float(face.get("mouth", mo)), cw)
				_skin_mat.set_shader_parameter("mouth_open", mo)
				_skin_mat.set_shader_parameter("smile", float(face.get("smile", 0.0)) * cw)
				_skin_mat.set_shader_parameter("brow_height", clampf(_brow0 + float(face.get("brow", 0.0)) * cw, -1.0, 1.0))
				if face.has("eyes"):
					_skin_mat.set_shader_parameter("blink", maxf(bl, float(face.eyes) * cw))
			else:
				_skin_mat.set_shader_parameter("smile", 0.0)
				_skin_mat.set_shader_parameter("brow_height", _brow0)
			_set_rot("Jaw", Quaternion(Vector3.RIGHT, deg_to_rad(7.0) * mo))       # the chin drops as the mouth opens
	if not _props.is_empty():
		_aim_props()


func _twist(side: String, q_hand: Quaternion) -> void:
	## Swing-twist: the hand's roll about the forearm goes half to the forearm twist bone, so the
	## wrist's skin turns with it instead of collapsing (the candy-wrapper artefact).
	var axis: Vector3 = ((_J["Hand" + side] as Vector3) - (_J["LowerArm" + side] as Vector3)).normalized()
	var v := Vector3(q_hand.x, q_hand.y, q_hand.z)
	var p := axis * v.dot(axis)
	var tw := Quaternion(p.x, p.y, p.z, q_hand.w)
	if tw.length_squared() < 1e-8:
		tw = Quaternion.IDENTITY
	tw = tw.normalized()
	_set_rot("LowerArmTwist" + side, Quaternion.IDENTITY.slerp(tw, 0.5))


func _arm_ik(side: String, target: Vector3, t_chest: Transform3D, pole: Vector3) -> Array:
	## Two-bone arm IK -> [UpperArm local, LowerArm local] rotations; t_chest is the clavicle's
	## (Shoulder bone's) transform in skeleton space.
	var shoulder := t_chest * ((_J["UpperArm" + side] as Vector3) - (_J["Shoulder" + side] as Vector3))
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


func _hands_curls(curls: Dictionary) -> void:
	## Per hand: [thumb, index, middle, ring, pinky] curl 0..1; each finger's three joints share it
	## (the second joint most), the thumb across the palm.
	var names := ["Index", "Middle", "Ring", "Pinky"]
	for side in ["L", "R"]:
		var k := 1.0 if side == "L" else -1.0
		var c: Array = curls[side]
		for i in 4:
			var cc := float(c[i + 1])
			_set_rot(names[i] + "A" + side, Quaternion.from_euler(Vector3(0, 0, k * deg_to_rad(65.0) * cc)))
			_set_rot(names[i] + "B" + side, Quaternion.from_euler(Vector3(0, 0, k * deg_to_rad(85.0) * cc)))
			_set_rot(names[i] + "C" + side, Quaternion.from_euler(Vector3(0, 0, k * deg_to_rad(55.0) * cc)))
		var th := float(c[0])
		_set_rot("ThumbA" + side, Quaternion.from_euler(Vector3(deg_to_rad(25.0) * th, 0, k * deg_to_rad(28.0) * th)))
		_set_rot("ThumbB" + side, Quaternion.from_euler(Vector3(0, 0, k * deg_to_rad(32.0) * th)))
		_set_rot("ThumbC" + side, Quaternion.from_euler(Vector3(0, 0, k * deg_to_rad(35.0) * th)))


func _hands(g: float) -> void:
	## Fingers curl toward the palm; a relaxed hand cascades, the index straightest.
	var cascade := {"Index": 0.8, "Middle": 0.95, "Ring": 1.05, "Pinky": 1.2}
	for side in ["L", "R"]:
		var k := 1.0 if side == "L" else -1.0
		for fn in cascade:
			var c: float = g * cascade[fn]
			_set_rot(fn + "A" + side, Quaternion.from_euler(Vector3(0, 0, k * deg_to_rad(65.0) * c)))
			_set_rot(fn + "B" + side, Quaternion.from_euler(Vector3(0, 0, k * deg_to_rad(80.0) * c)))
			_set_rot(fn + "C" + side, Quaternion.from_euler(Vector3(0, 0, k * deg_to_rad(55.0) * c)))
		_set_rot("ThumbA" + side, Quaternion.from_euler(Vector3(deg_to_rad(20.0) * g, 0, k * deg_to_rad(25.0) * g)))
		_set_rot("ThumbB" + side, Quaternion.from_euler(Vector3(0, 0, k * deg_to_rad(30.0) * g)))
		_set_rot("ThumbC" + side, Quaternion.from_euler(Vector3(0, 0, k * deg_to_rad(30.0) * g)))
