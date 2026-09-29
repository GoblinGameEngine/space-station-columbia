extends Node
class_name NpcAnimator

## Procedural motion for a generated person: no animation assets, because the bodies are all
## different (Spore's lesson -- Hecker et al. 2008 -- in miniature: motion from rules that fit any
## morphology).  The pose is built from targets and then passed through damped springs, so parts lag
## and settle (overlap, follow-through) instead of tracking the formula exactly:
##   walking -- the gait trait (stride, cadence, bounce, arm swing), weight over the stance foot,
##     the pelvis dropping on the swing side, heel strike with a straight knee, heel-to-toe roll,
##     shoulders counter-rotating the pelvis, ease in / out;
##   idling -- contrapposto (weight on one leg, hip cocked, shifting now and then), breathing,
##     glances, and long still holds: ma, the Ghibli pause (ghibli_style.md 4);
##   hands -- relaxed cascade curl, grip for holding;
##   everywhere -- slow noise so no two moments repeat.
## Optionally held "on twos" (poses sampled at 12 fps) for the drawn-animation feel.
## The rest rotations are identity: bone axes are the character's (+X right, +Y up, -Z forward); a
## positive rotation about X swings a hanging limb forward.

var npc: NpcCharacter
var skel: Skeleton3D
var speed := 0.0            # m/s, set by whoever moves the NPC
var on_twos := false
var manual := false         # posed by someone else (tools): _process leaves the skeleton alone
var grip := 0.3             # 0 open hand .. 0.3 relaxed .. 1 fist
var phase := 0.0
var t := 0.0
var _held := 0.0
var _rng: NpcRng
var _gait: Array
var _posture := 0.0
var _stride := 0.7
var _walk := 0.0            # eased 0 idle .. 1 walking
var _look_target := 0.0
var _next_glance := 2.0
var _stance := 1.0          # idle weight side: +1 on the left leg, -1 on the right
var _next_shift := 8.0
var _springs := {}          # name -> [value, velocity]
var _bone := {}
var _seed := 0.0


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
	_rng = NpcRng.for_trait(npc.world_seed, npc.pid, "anim")
	_gait = npc.traits.get("gait", [1.0, 1.0, 1.0, 1.0])
	_posture = float(npc.traits.get("posture", 0.2))
	_stride = float(npc.params.height) * 0.42 * float(_gait[0])
	t = _rng.rand() * 10.0                   # people aren't in step with each other
	_seed = _rng.rand() * 100.0
	_next_glance = 1.0 + _rng.rand() * 6.0
	_stance = 1.0 if _rng.rand() < 0.5 else -1.0
	_next_shift = 5.0 + _rng.rand() * 15.0


func _process(delta: float) -> void:
	if manual:
		return
	t += delta
	_walk = move_toward(_walk, clampf(speed / 1.3, 0.0, 1.0), delta * 2.2)     # ease in / out
	if speed > 0.05 or _walk > 0.02:
		phase = fmod(phase + delta * maxf(speed, 0.4 * _walk) / maxf(_stride, 0.2), 1.0)
	if on_twos:
		_held += delta
		if _held < 1.0 / 12.0:
			return
		delta = _held
		_held = 0.0
	pose(phase, _walk, t, delta)


func _spring(sname: String, target: float, dt: float, freq := 3.0, damp := 0.55) -> float:
	## A damped spring toward target (freq Hz, damping ratio): the part lags and settles.  dt 0:
	## no spring (tools posing single frames).
	if dt <= 0.0:
		return target
	var s: Array = _springs.get(sname, [target, 0.0])
	var w := TAU * freq
	var steps := maxi(1, ceili(dt / 0.02))                   # stable at low frame rates
	var h := dt / steps
	for i in steps:
		var acc: float = w * w * (target - float(s[0])) - 2.0 * damp * w * float(s[1])
		s[1] = float(s[1]) + acc * h
		s[0] = float(s[0]) + float(s[1]) * h
	_springs[sname] = s
	return s[0]


func _noise(ch: float, rate: float) -> float:
	## Smooth, slow noise in -1..1 (a sum of incommensurate sines): no repeats.
	var x := t * rate + _seed + ch * 17.0
	return (sin(x) + sin(x * 1.618 + 1.3) * 0.6 + sin(x * 2.718 + 0.7) * 0.3) / 1.9


func pose(ph: float, walk: float, time: float, dt := 0.0) -> void:
	## The whole pose for a walk phase, walk amount (0..1), time; dt > 0 runs the springs.
	var g0: float = _gait[0]
	var g2: float = _gait[2]
	var g3: float = _gait[3]
	var a := ph * TAU
	var H: float = npc.params.height
	var idle := 1.0 - walk
	# idle life: breathing, weight shifts, glances with long holds between
	var breathe := sin(time * TAU / (3.6 + 0.8 * float(_gait[1])))
	if time > _next_glance:
		_look_target = 0.0 if absf(_look_target) > 0.1 else (_rng.rand() - 0.5) * 1.4
		_next_glance = time + (2.5 + _rng.rand() * 7.0 if _look_target == 0.0 else 0.8 + _rng.rand() * 1.5)
	if time > _next_shift:
		_stance = -_stance
		_next_shift = time + 6.0 + _rng.rand() * 18.0
	var stance := _spring("stance", _stance, dt, 0.7, 0.9)                 # a slow, settled shift
	var stoop := clampf(-_posture, 0.0, 1.0)
	var lean := deg_to_rad(4.0) * walk + deg_to_rad(14.0) * stoop
	# -- legs: swing, knee (straight at heel strike, bent in swing), heel-toe roll
	var swing := deg_to_rad(24.0) * g0 * walk
	for side in ["L", "R"]:
		var s := 0.0 if side == "L" else PI
		var sgn := 1.0 if side == "L" else -1.0
		var sw := sin(a + s)                                    # +1: this leg fully forward
		var leg := swing * sw
		# the leg is in the air while it swings forward (cos > 0), knee most bent at mid-swing as it
		# passes under the body
		var swing_phase := maxf(0.0, cos(a + s))
		var knee := deg_to_rad(42.0) * walk * swing_phase + deg_to_rad(3.0 + 6.0 * stoop)
		var roll := walk * (deg_to_rad(12.0) * maxf(0.0, -cos(a + s)) - deg_to_rad(10.0) * maxf(0.0, sw) * (1.0 - swing_phase))
		# idle contrapposto: the weight leg straight, the other knee eased and turned out a touch
		var relaxed := maxf(0.0, -stance * sgn)
		knee += idle * deg_to_rad(9.0) * relaxed
		var splay := idle * deg_to_rad(4.0) * relaxed * sgn
		_rot(side, "UpperLeg", Vector3(leg - knee * 0.2, splay, 0))
		_rot(side, "LowerLeg", Vector3(-knee, 0, 0))
		_rot(side, "Foot", Vector3(-leg * 0.45 + knee * 0.55 + roll, 0, 0))
		# arms: swing opposite the legs, lagging behind the shoulders (a spring); the elbow bends
		# more on the forward swing; the wrist trails
		var arm_t := -swing * 0.55 * g3 * sw + deg_to_rad(2.5) * breathe * idle + deg_to_rad(1.5) * _noise(1.0 + s, 0.3) * idle
		var arm := _spring("arm" + side, arm_t, dt, 1.9 * float(_gait[1]), 0.45)
		_rot(side, "UpperArm", Vector3(arm, 0, deg_to_rad(2.0) * idle * sgn))
		var elbow := _spring("elbow" + side, deg_to_rad(10.0 + 12.0 * walk) + maxf(0.0, arm) * 0.8, dt, 2.2, 0.5)
		_rot(side, "LowerArm", Vector3(elbow, 0, 0))
		_rot(side, "Hand", Vector3(_spring("wrist" + side, elbow * 0.25, dt, 2.6, 0.4), 0, 0))
	# -- pelvis and spine: bob (lowest at double support), weight over the stance foot, the pelvis
	# dropping on the swing side (list), twist; the chest counter-rotates; idle hip cocked
	var bob := -absf(sin(a)) * 0.022 * H * g2 * walk
	var weight_x := 0.014 * H * sin(a) * walk + 0.018 * H * stance * idle
	var hips := skel.get_bone_rest(_bone.Hips).origin
	var hx := _spring("hipx", weight_x, dt, 2.0, 0.7)
	var hy := _spring("hipy", bob - 0.006 * H * idle * absf(stance), dt, 4.0, 0.6)
	skel.set_bone_pose_position(_bone.Hips, hips + Vector3(-hx, hy, 0))
	var list := deg_to_rad(4.0) * cos(a) * walk + deg_to_rad(4.5) * stance * idle
	var twist := deg_to_rad(7.0) * sin(a) * walk * g0
	skel.set_bone_pose_rotation(_bone.Hips, Quaternion.from_euler(Vector3(deg_to_rad(2.0) * walk, twist, list)))
	var spine_z := _spring("spinez", -list * 0.7, dt, 2.2, 0.6)
	skel.set_bone_pose_rotation(_bone.Spine, Quaternion.from_euler(Vector3(lean * 0.5, -twist * 0.6, spine_z)))
	var chest_twist := _spring("chesty", -twist * 0.9, dt, 2.4, 0.5)
	skel.set_bone_pose_rotation(_bone.Chest, Quaternion.from_euler(Vector3(lean * 0.5 + deg_to_rad(1.4) * breathe * idle, chest_twist, -spine_z * 0.3)))
	# -- head: steadies itself against the body (the eyes stay level), turns to look, lags a little
	var yaw := _spring("look", _look_target * idle, dt, 1.2, 0.8)
	var nod := _spring("nod", -lean * 0.6 + deg_to_rad(6.0) * stoop - bob * 2.0 + deg_to_rad(2.0) * _noise(3.0, 0.2) * idle, dt, 2.5, 0.5)
	skel.set_bone_pose_rotation(_bone.Neck, Quaternion.from_euler(Vector3(nod, yaw * 0.4 - chest_twist * 0.5, -spine_z * 0.5)))
	skel.set_bone_pose_rotation(_bone.Head, Quaternion.from_euler(Vector3(-lean * 0.3, yaw * 0.6, -list * 0.3)))
	_hands(grip + 0.08 * breathe * idle + 0.1 * walk)


func _hands(g: float) -> void:
	## Fingers curl toward the palm (the palm faces the body, so the curl is about the character's
	## Z axis, opposite ways for the two hands); a relaxed hand cascades -- the index straightest,
	## the pinky most curled -- and the second joints curl more than the first.
	var cascade := {"Index": 0.8, "Middle": 0.95, "Ring": 1.05, "Pinky": 1.2}
	for side in ["L", "R"]:
		var k := 1.0 if side == "L" else -1.0
		for fn in cascade:
			var c: float = g * cascade[fn]
			_rot(side, fn + "A", Vector3(0, 0, k * deg_to_rad(70.0) * c))
			_rot(side, fn + "B", Vector3(0, 0, k * deg_to_rad(95.0) * c))
		_rot(side, "ThumbA", Vector3(deg_to_rad(20.0) * g, 0, k * deg_to_rad(25.0) * g))
		_rot(side, "ThumbB", Vector3(0, 0, k * deg_to_rad(35.0) * g))


func _rot(side: String, bone: String, euler: Vector3) -> void:
	skel.set_bone_pose_rotation(_bone[bone + side], Quaternion.from_euler(euler))
