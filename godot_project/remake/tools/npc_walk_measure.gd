extends SceneTree

## Measures a generated person's walk the way tools/charref/roto_walk.py measures filmed walkers,
## so the two can be compared curve for curve (tools/charref/walk_compare.py): over one gait cycle,
## head height (bob), head ahead of the pelvis (side), head and chest sideways (front), the
## shoulder line's tilt and apparent width.  Springs run (60 steps a second, several cycles first).
##   ../godot/godot4 --headless --path . --script res://remake/tools/npc_walk_measure.gd -- out.json [pid] [mood] [speed]

var out := ""
var pid := "B1000:0"
var mood := "neutral"
var spd := 1.3
var npc: NpcCharacter
var an: NpcAnimator
var done := false


func _init() -> void:
	var a := OS.get_cmdline_user_args()
	out = a[0] if a.size() > 0 else "/tmp/walk_measure.json"
	pid = a[1] if a.size() > 1 else pid
	mood = a[2] if a.size() > 2 else mood
	spd = float(a[3]) if a.size() > 3 else spd
	# WALK_TUNE="TRUNK_PH=0.1,NECK_ROLL=4" overrides the animator's walk constants for this run
	for kv in OS.get_environment("WALK_TUNE").split(",", false):
		var p := kv.split("=")
		_tune(p[0], float(p[1]))
	npc = NpcCharacter.create(NpcTraits.shared().person(1, pid, ["L0", "L1"], ""), pid, 1)
	root.add_child(npc)
	an = NpcAnimator.attach(npc)
	an.manual = true


func _tune(name: String, v: float) -> void:
	match name:
		"TRUNK_ROLL": NpcAnimator.TRUNK_ROLL = v
		"TRUNK_PH": NpcAnimator.TRUNK_PH = v
		"NECK_ROLL": NpcAnimator.NECK_ROLL = v
		"NECK_PH": NpcAnimator.NECK_PH = v
		"PITCH_OSC": NpcAnimator.PITCH_OSC = v
		"PITCH_PH": NpcAnimator.PITCH_PH = v


func _process(_d: float) -> bool:
	if done:
		return true
	done = true
	an.set_mood(mood)
	an.speed = spd
	var sk := npc.skeleton
	var H: float = npc.built.landmarks.T
	var dt := 1.0 / 60.0
	var t := 0.0
	var ph := 0.0
	var bins := 20
	var acc := {}
	var cycles := 0
	var prev_ph := 0.0
	while cycles < 8:
		ph = fmod(ph + dt * spd / an.stride_length(), 1.0)
		t += dt
		an.pose(ph, 1.0, t, dt)
		if ph < prev_ph:
			cycles += 1
		prev_ph = ph
		if cycles < 3:
			continue
		sk.force_update_all_bone_transforms()
		var g := func(n: String) -> Vector3: return sk.get_bone_global_pose(sk.find_bone(n)).origin
		var head: Vector3 = g.call("Head")
		var hips: Vector3 = g.call("Hips")
		var shL: Vector3 = g.call("UpperArmL")
		var shR: Vector3 = g.call("UpperArmR")
		var chest := (shL + shR) * 0.5
		# phases match the reference's: its 0 is a right heel strike, ours a left -- shift by half and
		# mirror x (so "toward the standing leg" means the same thing)
		var rp := fmod(ph + 0.5, 1.0)
		var b := int(rp * bins) % bins
		var f := {
			"bob": (head.y + 0.1 * H) / H,
			"head_fwd": -(head.z - hips.z) / H,
			"head_lat": (head.x - chest.x) / H,
			"chest_lat": chest.x / H,
			# + : the figure's right shoulder up (as the reference measures it)
			"sh_tilt": rad_to_deg(atan2(shR.y - shL.y, shR.x - shL.x)),
			"sh_width": Vector2(shR.x - shL.x, shR.y - shL.y).length() / H,
		}
		for k in f:
			if not acc.has(k):
				acc[k] = []
				for i in bins:
					acc[k].append([])
			acc[k][b].append(f[k])
	var curves := {}
	for k in acc:
		var means := []
		var tot := 0.0
		for bl in acc[k]:
			var m := 0.0
			for v in bl:
				m += v
			m /= maxf(bl.size(), 1)
			means.append(m)
			tot += m
		var mu := tot / bins
		var c := []
		for m in means:
			c.append(snappedf(m - mu, 0.00001))
		curves[k] = c
		curves[k + "_mean"] = snappedf(mu, 0.00001)
	var f := FileAccess.open(out, FileAccess.WRITE)
	f.store_string(JSON.stringify({"pid": pid, "mood": mood, "speed": spd, "bins": bins, "curves": curves}, " "))
	print("wrote ", out)
	quit()
	return true
