extends Node
class_name NpcAnimator

## Procedural motion for a generated person: no animation assets, because the bodies are all
## different (Spore's lesson -- Hecker et al. 2008 -- in miniature: motion from rules that fit any
## morphology).  Walking follows the person's gait trait (stride, cadence, bounce, arm swing) and
## posture; idling breathes, shifts weight, glances about, and holds still for long stretches -- ma,
## the Ghibli pause (ghibli_style.md 4).  Optionally held "on twos" (poses updated at 12 fps) for the
## drawn-animation feel; to be judged in game.
##
## The skeleton's rest rotations are identity, so bone-local axes are the character's axes:
## +X right, +Y up, -Z forward.  A positive rotation about X swings a hanging limb forward.

var npc: NpcCharacter
var skel: Skeleton3D
var speed := 0.0            # m/s along the ground, set by whoever moves the NPC
var on_twos := false
var manual := false         # posed by someone else (tools): _process leaves the skeleton alone
var phase := 0.0            # walk cycle, 0..1
var t := 0.0
var _held := 0.0
var _rng: NpcRng
var _gait: Array
var _posture := 0.0
var _stride := 0.7          # metres per step pair at gait stride 1
var _look_yaw := 0.0
var _look_target := 0.0
var _next_glance := 2.0
var _bone := {}


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
	_next_glance = 1.0 + _rng.rand() * 6.0


func _process(delta: float) -> void:
	if manual:
		return
	t += delta
	if speed > 0.05:
		phase = fmod(phase + delta * speed / maxf(_stride, 0.2), 1.0)
	if on_twos:
		_held += delta
		if _held < 1.0 / 12.0:
			return
		_held = 0.0
	pose(phase, speed, t)


func pose(ph: float, spd: float, time: float) -> void:
	## The whole pose for a walk phase, speed and time (also used by the lineup to show phases).
	var walk := clampf(spd / 1.3, 0.0, 1.0)             # 0 idle .. 1 full walk
	var g0: float = _gait[0]
	var g2: float = _gait[2]
	var g3: float = _gait[3]
	var a := ph * TAU
	# idle: breathing, a slow weight shift, glances (with long still holds between)
	var breathe := sin(time * TAU / (3.6 + 0.8 * float(_gait[1]))) * (1.0 - walk)
	var shift := sin(time * 0.37) * 0.5 + sin(time * 0.13) * 0.5
	if time > _next_glance:
		_look_target = 0.0 if absf(_look_target) > 0.1 else (_rng.rand() - 0.5) * 1.4
		_next_glance = time + (2.5 + _rng.rand() * 7.0 if _look_target == 0.0 else 0.8 + _rng.rand() * 1.5)
	_look_yaw = lerpf(_look_yaw, _look_target * (1.0 - walk), 0.08)
	# stoop: elders and the tired lean forward from the chest, head pushed forward
	var stoop := clampf(-_posture, 0.0, 1.0)
	var lean := deg_to_rad(4.0) * walk + deg_to_rad(14.0) * stoop
	# legs
	var swing := deg_to_rad(24.0) * g0 * walk
	for side in ["L", "R"]:
		var s := 0.0 if side == "L" else PI
		var leg := swing * sin(a + s)
		var knee := deg_to_rad(38.0) * walk * maxf(0.0, sin(a + s - 0.6 * PI)) + deg_to_rad(3.0 + 6.0 * stoop)
		var foot := -leg * 0.5 + knee * 0.6
		_rot(side, "UpperLeg", Vector3(leg - knee * 0.15 + (deg_to_rad(2.0) * shift * (1.0 if side == "L" else -1.0)) * (1.0 - walk), 0, 0))
		_rot(side, "LowerLeg", Vector3(-knee, 0, 0))
		_rot(side, "Foot", Vector3(foot * 0.6, 0, 0))
		# arms swing against the legs; elbows a little bent
		var arm := -swing * 0.55 * g3 * sin(a + s)
		_rot(side, "UpperArm", Vector3(arm + deg_to_rad(3.0) * breathe, 0, 0))
		_rot(side, "LowerArm", Vector3(deg_to_rad(12.0 + 10.0 * walk) + maxf(0.0, arm) * 0.6, 0, 0))
	# body: bob twice per cycle, a little sway and twist; spine counter-twists
	var bob := -absf(sin(a)) * 0.022 * float(npc.params.height) * g2 * walk
	var hips := skel.get_bone_rest(_bone.Hips).origin
	skel.set_bone_pose_position(_bone.Hips, hips + Vector3(0.012 * sin(a) * walk + 0.01 * shift * (1.0 - walk), bob, 0))
	skel.set_bone_pose_rotation(_bone.Hips, Quaternion.from_euler(Vector3(0, deg_to_rad(6.0) * sin(a) * walk, deg_to_rad(1.5) * shift * (1.0 - walk))))
	skel.set_bone_pose_rotation(_bone.Spine, Quaternion.from_euler(Vector3(lean * 0.5, -deg_to_rad(4.0) * sin(a) * walk, 0)))
	skel.set_bone_pose_rotation(_bone.Chest, Quaternion.from_euler(Vector3(lean * 0.5 + deg_to_rad(1.2) * breathe, -deg_to_rad(4.0) * sin(a) * walk, 0)))
	skel.set_bone_pose_rotation(_bone.Neck, Quaternion.from_euler(Vector3(-lean * 0.6 + deg_to_rad(6.0) * stoop, _look_yaw * 0.4, 0)))
	skel.set_bone_pose_rotation(_bone.Head, Quaternion.from_euler(Vector3(-lean * 0.3, _look_yaw * 0.6, 0)))


func _rot(side: String, bone: String, euler: Vector3) -> void:
	skel.set_bone_pose_rotation(_bone[bone + side], Quaternion.from_euler(euler))
