extends SceneTree

## The never-fail test for generated bodies (scale_survey.md 2.6): every corner of the body
## parameter space, plus thousands of real generated people across every population, each built
## with clothes and hair, and checked:
##   finite vertices; feet on the ground; the head top at the stated height; hands clear of the
##   hips; skirt/dress/coat hems round both legs; a vertex budget; build time.
##   ../godot/godot4 --headless --path . --script res://remake/tools/npc_corner_test.gd [-- people]
## Exit code 1 on any failure; prints the first failures and the timing.

const VERT_BUDGET := 14000
var fails: Array = []
var checked := 0
var times: Array = []
var verts_max := 0


func _init() -> void:
	var a := OS.get_cmdline_user_args()
	var people := int(a[0]) if a.size() > 0 else 3000
	# 1. corners of the body space (with a deterministic sign pattern for the many ±1 params)
	var n := 0
	for age in [1.0, 3.0, 5.0, 10.0, 13.0, 16.0, 30.0, 70.0, 99.0]:
		for sex in ["female", "male"]:
			for build in [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]:
				for tall in [false, true]:
					for car in [0.0, 1.0]:
						n += 1
						var s := 1.0 if n % 2 else -1.0
						var hmin := 0.7 if age < 6 else 1.0 if age < 13 else 1.4
						var v := {"sex": sex, "age": age, "height": 2.05 if tall else hmin, "build": build,
							"proportions": [s, -s, s, -s], "caricature": car, "face": [s, -s, s, s, -s, s, -s, s],
							"posture": -s, "hair_style": ["bob", "long_loose", "curly_long", "ponytail", "braids", "bun", "balding", "crop"][n % 8],
							"occupation": ["retired", "farmer", "baker", "nurse", "police", "student", "pastor", "fisher"][n % 8],
							"skin": [0.5, 0.5], "hair_colour": [0.3, 0.5], "palette": "earth", "style": "plain", "wear": 0.5, "accent_colour": 0}
						_check(v, "corner#%d %s %s age %d h %.2f build %s car %d" % [n, sex, v.hair_style, age, v.height, build, car], n)
	print("corners: %d built, %d failures" % [n, fails.size()])
	# 2. real generated people
	var db := NpcTraits.shared()
	var pops := ["", "stable_town", "rust_belt", "exurban", "county_seat", "college_town", "lake_resort"]
	for i in people:
		var pid := "B%d:%d" % [50000 + i, i % 4]
		var pop: String = pops[i % pops.size()]
		var v := db.person(11, pid, ["L0", "L1"], pop)
		_check(v, "%s (%s) %s %d %s %s" % [pid, pop, v.sex, v.age, v.occupation, v.hair_style], 11, pid)
	times.sort()
	var med: float = times[times.size() / 2]
	var p95: float = times[int(times.size() * 0.95)]
	print("people: %d built; total failures %d; max vertices %d; build ms median %.1f p95 %.1f max %.1f" % [checked, fails.size(), verts_max, med, p95, times[-1]])
	for f in fails.slice(0, 25):
		print("  FAIL ", f)
	quit(1 if fails.size() > 0 else 0)


func _check(v: Dictionary, label: String, seed: int, pid := "corner") -> void:
	checked += 1
	var t0 := Time.get_ticks_usec()
	var npc := NpcCharacter.create(v, pid, seed)
	times.append((Time.get_ticks_usec() - t0) / 1000.0)
	var L: Dictionary = npc.built.landmarks
	var J: Dictionary = npc.built.joints
	var nv := 0
	var min_y := 1e9
	var max_y := -1e9
	for mi in [npc.body_mesh, npc.clothes_mesh]:
		var m: ArrayMesh = mi.mesh
		for si in m.get_surface_count():
			var arr := m.surface_get_arrays(si)
			var vs: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
			nv += vs.size()
			for p in vs:
				if not (is_finite(p.x) and is_finite(p.y) and is_finite(p.z)):
					fails.append("%s: non-finite vertex" % label)
					npc.free()
					return
				min_y = minf(min_y, p.y)
				if mi == npc.body_mesh:
					max_y = maxf(max_y, p.y)
	verts_max = maxi(verts_max, nv)
	if nv > VERT_BUDGET:
		fails.append("%s: %d vertices (budget %d)" % [label, nv, VERT_BUDGET])
	var T: float = L.T
	if min_y < -0.03 or min_y > 0.03:
		fails.append("%s: lowest point %.3f m (feet should be on the ground)" % [label, min_y])
	if absf(max_y - T) > 0.06 * T:
		fails.append("%s: head top %.3f m for height %.3f" % [label, max_y, T])
	# hands clear of the hips (clothes included: the widest garment ease)
	for side in ["L", "R"]:
		var hand: Vector3 = J["Hand" + side]
		var clear: float = absf(hand.x) - (L.hip_w + NpcBody.CLOTHES_ROOM * L.T) - L.wrist_r
		if hand.y > L.crotch - 0.1 * T and clear < -0.02 * T:
			fails.append("%s: hand %s inside the hips (%.3f m)" % [label, side, clear])
	# hems round both legs
	for g in npc.outfit:
		if str(g.def.build) in ["skirt", "dress", "coat"]:
			var legs_w: float = L.leg_sep + L.thigh_r
			if legs_w > L.hip_w * 1.6:
				fails.append("%s: legs %.3f wider than the hips allow" % [label, legs_w])
	npc.free()
