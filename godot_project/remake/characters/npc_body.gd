extends RefCounted
class_name NpcBody

## A person's body, built in code from their traits: a humanoid skeleton and a skinned, lofted
## mesh (research/characters/generator_design_notes.md 2).  No modelled assets: every part is a
## loft of rings (a superellipse cross-section) along the skeleton, so every parameter combination
## gives a valid body by construction -- fixed topology, clamped parameters, no rejection loops
## (scale_survey.md 2.6).  The same rings are what garments are built from (NpcGarments), so
## clothes fit any body.
##
## Proportions follow the measured Ghibli figures (ghibli_style.md 5): adults ~6.25 heads tall,
## teens ~5.3, young children ~4.2-4.7; heads bigger again with caricature.
##
## Space: metres, feet on y = 0, facing -Z (Godot's forward), the person's right hand at +X.
##
##   var b := NpcBody.from_traits(traits)      # params from an NpcTraits person
##   var built := NpcBody.build(b)             # {bones, mesh arrays per part, rings, landmarks}

const RING := 14          # vertices round a torso / leg ring
const LIMB := 10          # round an arm, the neck
const HEAD_AROUND := 36        # (fine enough across the face to carry a nose)
const CLOTHES_ROOM := 0.026        # (fraction of height) the most any outfit adds round the hips
const FINGERS := ["Thumb", "Index", "Middle", "Ring", "Pinky"]
const BONES := ["Hips", "Spine", "Chest", "UpperChest", "Neck", "Head", "Jaw",
	"ShoulderL", "UpperArmL", "UpperArmTwistL", "LowerArmL", "LowerArmTwistL", "HandL", "PropL",
	"ShoulderR", "UpperArmR", "UpperArmTwistR", "LowerArmR", "LowerArmTwistR", "HandR", "PropR",
	"UpperLegL", "LowerLegL", "FootL", "ToeL",
	"UpperLegR", "LowerLegR", "FootR", "ToeR",
	"ThumbAL", "ThumbBL", "ThumbCL", "IndexAL", "IndexBL", "IndexCL", "MiddleAL", "MiddleBL", "MiddleCL",
	"RingAL", "RingBL", "RingCL", "PinkyAL", "PinkyBL", "PinkyCL",
	"ThumbAR", "ThumbBR", "ThumbCR", "IndexAR", "IndexBR", "IndexCR", "MiddleAR", "MiddleBR", "MiddleCR",
	"RingAR", "RingBR", "RingCR", "PinkyAR", "PinkyBR", "PinkyCR",
	"HairA", "HairB"]
## 61 bones, the layout of the standard game humanoids (research/animation/npc_animations.md 1): a
## three-part spine, a jaw, clavicles, twist bones in the upper arm and forearm (so a turning wrist
## doesn't collapse the forearm -- the "candy wrapper" of linear skinning), three segments on every
## finger and the thumb, toes, a prop socket in each palm, and a hair chain for secondary motion.
const PARENT := {"Hips": "", "Spine": "Hips", "Chest": "Spine", "UpperChest": "Chest", "Neck": "UpperChest",
	"Head": "Neck", "Jaw": "Head", "HairA": "Head", "HairB": "HairA",
	"ShoulderL": "UpperChest", "UpperArmL": "ShoulderL", "UpperArmTwistL": "UpperArmL", "LowerArmL": "UpperArmL",
	"LowerArmTwistL": "LowerArmL", "HandL": "LowerArmL", "PropL": "HandL",
	"ShoulderR": "UpperChest", "UpperArmR": "ShoulderR", "UpperArmTwistR": "UpperArmR", "LowerArmR": "UpperArmR",
	"LowerArmTwistR": "LowerArmR", "HandR": "LowerArmR", "PropR": "HandR",
	"UpperLegL": "Hips", "LowerLegL": "UpperLegL", "FootL": "LowerLegL", "ToeL": "FootL",
	"UpperLegR": "Hips", "LowerLegR": "UpperLegR", "FootR": "LowerLegR", "ToeR": "FootR",
	"ThumbAL": "HandL", "ThumbBL": "ThumbAL", "ThumbCL": "ThumbBL", "IndexAL": "HandL", "IndexBL": "IndexAL", "IndexCL": "IndexBL",
	"MiddleAL": "HandL", "MiddleBL": "MiddleAL", "MiddleCL": "MiddleBL", "RingAL": "HandL", "RingBL": "RingAL", "RingCL": "RingBL",
	"PinkyAL": "HandL", "PinkyBL": "PinkyAL", "PinkyCL": "PinkyBL",
	"ThumbAR": "HandR", "ThumbBR": "ThumbAR", "ThumbCR": "ThumbBR", "IndexAR": "HandR", "IndexBR": "IndexAR", "IndexCR": "IndexBR",
	"MiddleAR": "HandR", "MiddleBR": "MiddleAR", "MiddleCR": "MiddleBR", "RingAR": "HandR", "RingBR": "RingAR", "RingCR": "RingBR",
	"PinkyAR": "HandR", "PinkyBR": "PinkyAR", "PinkyCR": "PinkyBR"}
const BALL := 0.55          # the ball of the foot (the toe joint), in foot lengths forward of the ankle
# the hand's geometry, in hand lengths / palm half-widths: [across the palm (-1 front .. 1 back),
# knuckle offset along the hand, proximal, intermediate, distal segments] -- relative lengths as in real hands
const FINGER_DEF := {
	"Index": [-0.62, 0.0, 0.2, 0.1, 0.08], "Middle": [-0.2, 0.02, 0.22, 0.11, 0.09],
	"Ring": [0.22, 0.0, 0.21, 0.105, 0.085], "Pinky": [0.62, -0.04, 0.16, 0.08, 0.065]}
const PALM := 0.54          # palm length in hand lengths (fingers ~0.4 of the hand, as in real hands)


# -- parameters ---------------------------------------------------------------------------------

static func from_traits(v: Dictionary) -> Dictionary:
	## The body-shaping subset of a person's traits, clamped: whatever the trait file says, the
	## builder only ever sees values inside the ranges it was tested at (the corner test).
	var build: Array = v.get("build", [0.43, 0.27, 0.30])
	var prop: Array = v.get("proportions", [0.0, 0.0, 0.0, 0.0])
	var face: Array = v.get("face", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
	return {
		"female": v.get("sex", "female") == "female",
		"age": clampf(float(v.get("age", 30)), 0.5, 99.0),
		"height": clampf(float(v.get("height", 1.65)), 0.7, 2.05),
		"thin": clampf(float(build[0]), 0.0, 1.0),
		"muscular": clampf(float(build[1]), 0.0, 1.0),
		"heavy": clampf(float(build[2]), 0.0, 1.0),
		"legs": clampf(float(prop[0]), -1.0, 1.0),
		"shoulders": clampf(float(prop[1]), -1.0, 1.0),
		"hips": clampf(float(prop[2]), -1.0, 1.0),
		"head": clampf(float(prop[3]), -1.0, 1.0),
		"caricature": clampf(float(v.get("caricature", 0.2)), 0.0, 1.0),
		"face": face.map(func(x): return clampf(float(x), -1.0, 1.0)),
		"posture": clampf(float(v.get("posture", 0.2)), -1.0, 1.0),
	}


static func _age_curve(age: float, pts: Array) -> float:
	## Piecewise-linear in age: pts = [[age, value], ...] ascending.
	if age <= pts[0][0]:
		return pts[0][1]
	for i in range(1, pts.size()):
		if age <= pts[i][0]:
			var t: float = (age - pts[i - 1][0]) / (pts[i][0] - pts[i - 1][0])
			return lerpf(pts[i - 1][1], pts[i][1], t)
	return pts[-1][1]


static func landmarks(p: Dictionary) -> Dictionary:
	## Heights, lengths and girths in metres.  The age curves come from the measured stills
	## (ghibli_style.md 5) and ordinary growth proportions; sex differences fade in with puberty.
	var age: float = p.age
	var T: float = p.height
	var fem := 1.0 if p.female else 0.0
	var pub := smoothstep(10.0, 16.0, age)                     # 0 child .. 1 adult
	var sexd := (fem - 0.5) * 2.0 * pub                          # -1 man .. +1 woman, 0 for children
	# heads tall
	var n := _age_curve(age, [[1.0, 3.8], [3.0, 4.2], [5.0, 4.5], [8.0, 4.9], [10.0, 5.2], [13.0, 5.35], [16.0, 5.8], [19.0, 6.15], [60.0, 6.25], [80.0, 6.05]])
	n -= 0.07 * sexd                                             # women drawn a touch shorter in heads
	n *= 1.0 - 0.10 * p.caricature
	n *= 1.0 - 0.05 * p.head
	var H := T / n
	# the body mass triangle: deltas from the population's mean mix
	var dt: float = p.thin - 0.43
	var dm: float = p.muscular - 0.27
	var dh: float = p.heavy - 0.30
	var girth := clampf(1.0 + 0.9 * dh + 0.7 * dm - 0.45 * dt, 0.7, 1.7)
	var belly := clampf(1.0 + 1.8 * dh - 0.6 * dt, 0.75, 2.2)
	var hipsg := clampf(1.0 + 0.8 * dh - 0.3 * dt + 0.12 * p.hips, 0.8, 1.6)
	var chestg := clampf(1.0 + 0.4 * dh + 0.6 * dm - 0.3 * dt, 0.8, 1.5)
	var shoul := clampf(1.0 + 0.35 * dm + 0.1 * p.shoulders, 0.85, 1.3)
	# heights
	var crotch: float = T * (_age_curve(age, [[1.0, 0.32], [3.0, 0.37], [5.0, 0.40], [10.0, 0.44], [13.0, 0.46], [18.0, 0.47]]) - 0.006 * sexd + 0.02 * p.legs)
	var chin: float = T - H
	var neck_base := T - 1.23 * H
	var shoulder_y := T - 1.37 * H
	var span: float = shoulder_y - crotch
	var L := {
		"T": T, "H": H, "heads": n, "pub": pub, "sexd": sexd, "girth": girth, "belly": belly,
		"crotch": crotch, "chin": chin, "neck_base": neck_base, "shoulder_y": shoulder_y,
		"chest_y": crotch + 0.70 * span, "waist_y": crotch + 0.42 * span, "hip_y": crotch + 0.14 * span,
		"leg_joint_y": crotch + 0.07 * span, "knee_y": crotch * 0.55, "ankle_y": T * 0.042,
	}
	# half-widths and half-depths (fractions of T blend child -> adult man / woman)
	var sw: float = T * lerpf(0.112, 0.118 - 0.012 * (sexd + 1.0) * 0.5, pub) * shoul * (1.0 + 0.04 * p.shoulders)
	L.shoulder_w = sw
	L.chest_w = sw * 0.86 * chestg
	L.chest_d = T * lerpf(0.058, 0.064 - 0.003 * sexd, pub) * chestg
	L.bust = maxf(0.0, sexd) * T * 0.012 * (0.7 + 0.6 * p.heavy)
	L.waist_w = T * lerpf(0.074, 0.084 - 0.012 * (sexd + 1.0) * 0.5, pub) * belly
	L.waist_d = T * lerpf(0.058, 0.058, pub) * belly
	L.belly_fwd = T * 0.03 * maxf(0.0, belly - 1.0)
	L.hip_w = T * lerpf(0.086, 0.094 + 0.012 * (sexd + 1.0) * 0.5, pub) * hipsg
	L.hip_d = T * lerpf(0.060, 0.068 + 0.004 * sexd, pub) * hipsg
	L.leg_sep = L.hip_w * 0.52                                   # hip joint x
	L.thigh_r = T * lerpf(0.046, 0.050 + 0.004 * sexd, pub) * girth
	L.knee_r = T * 0.026 * sqrt(girth)
	L.calf_r = T * 0.032 * girth
	L.ankle_r = T * 0.017
	L.neck_r = T * lerpf(0.024, 0.026 - 0.003 * sexd, pub) * sqrt(girth)
	L.upperarm_r = T * lerpf(0.024, 0.027 - 0.003 * sexd, pub) * girth
	L.elbow_r = T * 0.019 * sqrt(girth)
	L.forearm_r = T * 0.021 * girth
	L.wrist_r = T * 0.0145
	# arms: elbow near the waist, wrist near the crotch (the anime rule, true across ages)
	L.upperarm_len = (shoulder_y - L.waist_y) * 1.02
	L.forearm_len = (L.waist_y - crotch) * 0.98
	L.hand_len = H * 0.72
	L.foot_len = T * 0.145
	L.head_w = H * (0.40 + 0.03 * (1.0 - pub))                   # children's heads rounder
	L.head_d = H * 0.43
	return L


# -- skeleton -------------------------------------------------------------------------------------

static func skeleton_rest(L: Dictionary) -> Dictionary:
	## Bone name -> global rest position (the joint), for the builder and for Skeleton3D.
	var sx: float = L.shoulder_w * 0.78
	var j := {}
	j["Hips"] = Vector3(0, L.hip_y, 0)
	j["Spine"] = Vector3(0, L.waist_y, 0)
	j["Chest"] = Vector3(0, L.chest_y, 0)
	j["UpperChest"] = Vector3(0, lerpf(L.chest_y, L.shoulder_y, 0.55), 0.004 * L.T)
	j["Neck"] = Vector3(0, L.neck_base, 0.01 * L.T)
	j["Head"] = Vector3(0, L.chin + 0.05 * L.H, 0.02 * L.H)
	j["Jaw"] = Vector3(0, L.chin + 0.3 * L.H, 0.03 * L.H + float(L.head_d) * 0.3)      # the hinge, in front of the ear
	# a short chain behind the head for long hair, ponytails and braids to swing on (secondary motion)
	j["HairA"] = Vector3(0, L.chin + 0.62 * L.H, 0.03 * L.H + float(L.head_d) * 0.9)
	j["HairB"] = Vector3(0, L.chin - 0.15 * L.H, 0.03 * L.H + float(L.head_d) * 0.95 + 0.05 * L.H)
	for s in [["L", -1.0], ["R", 1.0]]:
		var side: String = s[0]
		var k: float = s[1]
		j["Shoulder" + side] = Vector3(k * L.neck_r * 1.1, L.shoulder_y + 0.02 * L.T, 0)
		var sh := Vector3(k * sx, L.shoulder_y, 0.004 * L.T)
		j["UpperArm" + side] = sh
		# arms hang out from the body just enough that the hand clears the hips and whatever is worn
		# over them (the corner test found fixed 8 deg failing heavy builds and toddlers)
		var need: float = L.hip_w + CLOTHES_ROOM * L.T + L.wrist_r * 1.6 - sx
		var reach: float = L.upperarm_len + L.forearm_len
		var ang := maxf(deg_to_rad(8.0), asin(clampf(need / reach, 0.0, 0.6)))
		var dir := Vector3(k * sin(ang), -cos(ang), 0)
		var el: Vector3 = sh + dir * L.upperarm_len
		j["LowerArm" + side] = el
		j["Hand" + side] = el + (dir + Vector3(0, 0, -0.04)).normalized() * L.forearm_len
		j["UpperArmTwist" + side] = sh.lerp(el, 0.5)
		j["LowerArmTwist" + side] = el.lerp(j["Hand" + side], 0.75)
		_hand_joints(j, L, side, dir)
		var hip := Vector3(k * L.leg_sep, L.leg_joint_y, 0)
		j["UpperLeg" + side] = hip
		j["LowerLeg" + side] = Vector3(k * L.leg_sep * 0.92, L.knee_y, -0.004 * L.T)
		j["Foot" + side] = Vector3(k * L.leg_sep * 0.9, L.ankle_y, 0.004 * L.T)
		# the ball of the foot: heel-to-toe roll pivots here, and the toes bend at push-off
		j["Toe" + side] = Vector3(k * L.leg_sep * 0.9, L.ankle_r * 0.5, 0.004 * L.T - BALL * L.foot_len)
	return j


# -- lofting ----------------------------------------------------------------------------------------

class Part:
	## One lofted mesh part: vertex arrays, and the rings it was built from (garments reuse them).
	var name: String
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()
	var uv2s := PackedVector2Array()
	var bones := PackedInt32Array()
	var weights := PackedFloat32Array()
	var indices := PackedInt32Array()
	var rings: Array = []          # the ring dictionaries used
	var around := 0


static func ring(c: Vector3, ax: Vector3, az: Vector3, a: float, b: float, w: Array, e := 2.0, off := Vector3.ZERO) -> Dictionary:
	## A cross-section: centre c, frame (ax: half-width direction, az: half-depth direction), half
	## sizes a, b, superellipse exponent e (2 = ellipse, higher = boxier), skin weights w = [[bone, w],..].
	return {"c": c + off, "ax": ax, "az": az, "a": maxf(a, 0.002), "b": maxf(b, 0.002), "w": w, "e": e}


static var _trig := {}     # around -> [PackedFloat32Array sin, cos] for t = k / around
static var _cache_lock := Mutex.new()   # the static caches are shared by generator threads


static func _table(around: int) -> Array:
	_cache_lock.lock()
	var tb: Array = _trig.get(around, [])
	_cache_lock.unlock()
	if tb.is_empty():
		var sn := PackedFloat32Array()
		var cs := PackedFloat32Array()
		for k in around:
			var ang := TAU * k / around
			sn.append(sin(ang))
			cs.append(-cos(ang))
		tb = [sn, cs]
		_cache_lock.lock()
		_trig[around] = tb
		_cache_lock.unlock()
	return tb


static func ring_point(r: Dictionary, t: float) -> Vector3:
	## t in [0,1): 0 = the front (-az), going round through +ax.
	var ang := TAU * t
	return _ring_point_sc(r, sin(ang), -cos(ang))


static func _ring_point_sc(r: Dictionary, sn: float, cs: float) -> Vector3:
	var e: float = r.e
	var px := sn
	var pz := cs
	if absf(e - 2.0) > 0.01:                                 # superellipse; plain ellipses skip the pow
		var q := 2.0 / e
		px = signf(sn) * pow(absf(sn), q)
		pz = signf(cs) * pow(absf(cs), q)
	return (r.c as Vector3) + (r.ax as Vector3) * (px * float(r.a)) + (r.az as Vector3) * (pz * float(r.b))


static func loft(name: String, rings: Array, around: int, cap_start := false, cap_end := false) -> Part:
	var p := Part.new()
	p.name = name
	p.rings = rings
	p.around = around
	var vlen: Array = []
	var acc := 0.0
	for i in rings.size():
		if i > 0:
			acc += (rings[i].c - rings[i - 1].c).length()
		vlen.append(acc)
	# UV in metres: along the loft, and round it at the part's mean perimeter (one scale for the
	# whole part, so vertical stripes stay vertical), so fabric patterns match on every body
	var per := 0.0
	for r in rings:
		per += _perimeter(r)
	per /= rings.size()
	for i in rings.size():
		var r: Dictionary = rings[i]
		var tb := _table(around)
		var sn: PackedFloat32Array = tb[0]
		var cs: PackedFloat32Array = tb[1]
		# the ring's fields unpacked once (dictionary reads per vertex were most of the cost)
		var c: Vector3 = r.c
		var ax: Vector3 = (r.ax as Vector3) * float(r.a)
		var az: Vector3 = (r.az as Vector3) * float(r.b)
		var e: float = r.e
		var q := 2.0 / e
		var ellipse := absf(e - 2.0) <= 0.01
		var wb := weights_of(r.w)
		var bi: PackedInt32Array = wb[0]
		var bw: PackedFloat32Array = wb[1]
		var v: float = vlen[i]
		for k in around + 1:                                  # +1: the UV seam column
			var px: float = sn[k % around]
			var pz: float = cs[k % around]
			if not ellipse:
				px = signf(px) * pow(absf(px), q)
				pz = signf(pz) * pow(absf(pz), q)
			p.verts.append(c + ax * px + az * pz)
			p.uvs.append(Vector2(float(k) / around * per, v))
			p.uv2s.append(Vector2(-10, -10))
			p.bones.append_array(bi)
			p.weights.append_array(bw)
	var row := around + 1
	for i in rings.size() - 1:
		for k in around:
			var a := i * row + k
			var b := a + 1
			var c := a + row
			var d := c + 1
			p.indices.append_array([a, c, b, b, c, d])
	_orient_outward(p, rings, 0, p.indices.size())
	if cap_start:
		_cap(p, 0, rings[0], rings[0].c - rings[1].c)
	if cap_end:
		_cap(p, (rings.size() - 1) * row, rings[-1], rings[-1].c - rings[-2].c)
	_smooth_normals(p, rings.size())
	return p


static func _perimeter(r: Dictionary) -> float:
	## Ramanujan's ellipse perimeter (close enough for superellipses here).
	var a: float = r.a
	var b: float = r.b
	return PI * (3.0 * (a + b) - sqrt((3.0 * a + b) * (a + 3.0 * b)))


static func _orient_outward(p: Part, rings: Array, from: int, to: int) -> void:
	## The tube's winding follows the ring direction, which differs between parts built upward
	## (torso, head) and downward (limbs).  Whichever it is, make every face point away from its
	## ring centre -- decided by the sum over the tube, then applied to all of it.
	var row := p.around + 1
	var s := 0.0
	for t in range(from, to, 3):
		var a := p.indices[t]
		var b := p.indices[t + 1]
		var c := p.indices[t + 2]
		var fn := (p.verts[b] - p.verts[a]).cross(p.verts[c] - p.verts[a])
		var ri := mini(a / row, rings.size() - 1)
		s += fn.dot(p.verts[a] - (rings[ri].c as Vector3))
	if s < 0.0:
		for t in range(from, to, 3):
			var tmp := p.indices[t + 1]
			p.indices[t + 1] = p.indices[t + 2]
			p.indices[t + 2] = tmp


static var _wcache := {}   # weights list (by its text) -> [PackedInt32Array bones, PackedFloat32Array weights]


static func _push_weights(p: Part, w: Array) -> void:
	var c := weights_of(w)
	p.bones.append_array(c[0])
	p.weights.append_array(c[1])


static func weights_of(w: Array) -> Array:
	## A ring's skin weights normalised to 4 bones: [PackedInt32Array, PackedFloat32Array]; resolved
	## once per distinct list.
	var key := str(w)
	_cache_lock.lock()
	var c: Array = _wcache.get(key, [])
	_cache_lock.unlock()
	if c.is_empty():
		var bi := PackedInt32Array()
		var bw := PackedFloat32Array()
		var tot := 0.0
		for x in w:
			tot += float(x[1])
		for i in 4:
			if i < w.size():
				bi.append(BONES.find(w[i][0]))
				bw.append(float(w[i][1]) / tot)
			else:
				bi.append(0)
				bw.append(0.0)
		c = [bi, bw]
		_cache_lock.lock()
		_wcache[key] = c
		_cache_lock.unlock()
	return c


static func _cap(p: Part, start: int, r: Dictionary, outward: Vector3) -> void:
	## Close a ring with a domed fan (fingertips, the crown, the shoulder end of an arm), the dome
	## along the loft's own direction; each triangle wound to face outward.
	var n := outward.normalized()
	var ci := p.verts.size()
	p.verts.append(r.c + n * minf(r.a, r.b) * 0.45)
	p.uvs.append(Vector2(0.5, 0.0))
	p.uv2s.append(Vector2(-10, -10))
	_push_weights(p, r.w)
	for k in p.around:
		var a := start + k
		var b := start + k + 1
		var fn := (p.verts[b] - p.verts[a]).cross(p.verts[ci] - p.verts[a])
		if fn.dot(n) >= 0.0:
			p.indices.append_array([a, b, ci])
		else:
			p.indices.append_array([a, ci, b])


static func _smooth_normals(p: Part, nrings: int) -> void:
	## Face normals summed per welded position, so the UV seam column never shows as a crease (the
	## screen-space outline draws a line wherever normals jump).
	var nv := p.verts.size()
	var acc := PackedVector3Array()
	acc.resize(nv)
	var row := p.around + 1
	var ring_end := nrings * row
	var ix := p.indices
	var vs := p.verts
	for t in range(0, ix.size(), 3):
		var a := ix[t]
		var b := ix[t + 1]
		var c := ix[t + 2]
		var fn := (vs[b] - vs[a]).cross(vs[c] - vs[a])
		acc[a - p.around if (a < ring_end and a % row == p.around) else a] += fn
		acc[b - p.around if (b < ring_end and b % row == p.around) else b] += fn
		acc[c - p.around if (c < ring_end and c % row == p.around) else c] += fn
	p.normals.resize(nv)
	for v in nv:
		var key: int = v - p.around if (v < ring_end and v % row == p.around) else v
		var n := acc[key]
		p.normals[v] = n.normalized() if n.length_squared() > 1e-12 else Vector3.UP


static func _weld(v: int, around: int, nrings: int) -> int:
	var row := around + 1
	if v < nrings * row and v % row == around:
		return v - around
	return v


# -- the body -------------------------------------------------------------------------------------

static func build(p: Dictionary) -> Dictionary:
	var L := landmarks(p)
	var J := skeleton_rest(L)
	var parts: Array[Part] = []
	parts.append(_torso(L, J))
	parts.append(_neck(L, J))
	parts.append(_head(L, J, p))
	for side in ["L", "R"]:
		parts.append(_arm(L, J, side))
		for hp in _hand(L, J, side):
			parts.append(hp)
		parts.append(_leg(L, J, side))
		parts.append(_foot(L, J, side))
	return {"landmarks": L, "joints": J, "parts": parts}


static func _torso(L: Dictionary, J: Dictionary) -> Part:
	var T: float = L.T
	var rs := []
	var x := Vector3.RIGHT
	var z := Vector3.BACK            # +Z is the back; ring front is -az... see ring_point: front = -az
	# crotch to neck base; y, half-width, half-depth, forward offset (-z), boxiness, weights
	var bf: float = L.belly_fwd
	var rows := [
		[L.crotch - 0.01 * T, L.hip_w * 0.55, L.hip_d * 0.55, 0.0, 2.0, [["Hips", 1.0]]],
		[L.crotch + 0.02 * T, L.hip_w * 0.86, L.hip_d * 0.9, 0.0, 2.2, [["Hips", 1.0]]],
		[L.hip_y, L.hip_w, L.hip_d, 0.004 * T, 2.3, [["Hips", 1.0]]],
		[lerpf(L.hip_y, L.waist_y, 0.55), lerpf(L.hip_w, L.waist_w, 0.6), lerpf(L.hip_d, L.waist_d, 0.5), 0.004 * T - bf * 0.6, 2.2, [["Hips", 0.5], ["Spine", 0.5]]],
		[L.waist_y, L.waist_w, L.waist_d, -bf, 2.1, [["Spine", 1.0]]],
		[lerpf(L.waist_y, L.chest_y, 0.5), lerpf(L.waist_w, L.chest_w, 0.55), lerpf(L.waist_d, L.chest_d, 0.6), -bf * 0.5, 2.2, [["Spine", 0.6], ["Chest", 0.4]]],
		[L.chest_y, L.chest_w, L.chest_d + L.bust * 0.5, -L.bust * 0.5, 2.3, [["Chest", 1.0]]],
		[lerpf(L.chest_y, L.shoulder_y, 0.6), L.shoulder_w * 0.9, L.chest_d * 0.9, 0.0, 2.25, [["Chest", 0.35], ["UpperChest", 0.65]]],
		[L.shoulder_y + 0.012 * T, L.shoulder_w * 0.82, L.chest_d * 0.7, 0.004 * T, 2.1, [["UpperChest", 0.8], ["ShoulderL", 0.1], ["ShoulderR", 0.1]]],
		[L.neck_base - 0.005 * T, L.neck_r * 2.2, L.neck_r * 1.6, 0.008 * T, 2.0, [["UpperChest", 0.7], ["Neck", 0.3]]],
	]
	for r in rows:
		rs.append(ring(Vector3(0, r[0], r[3]), x, z, r[1], r[2], r[5], r[4]))
	return loft("torso", rs, RING, true, true)


static func _neck(L: Dictionary, J: Dictionary) -> Part:
	var rs := []
	var nr: float = L.neck_r
	var base: Vector3 = J.Neck
	var top: Vector3 = Vector3(0, L.chin + 0.12 * L.H, 0.05 * L.H)
	for i in 5:
		var t := i / 4.0
		var c := base.lerp(top, t) - Vector3(0, 0.02 * L.T, 0) * (1.0 - t)
		rs.append(ring(c, Vector3.RIGHT, Vector3.BACK, nr * (1.08 - 0.08 * t), nr * (1.0 - 0.05 * t), [["Neck", 1.0 - 0.6 * t], ["Head", 0.6 * t]] if t > 0 else [["Neck", 0.7], ["UpperChest", 0.3]]))
	return loft("neck", rs, LIMB)


static func _head(L: Dictionary, J: Dictionary, p: Dictionary) -> Part:
	## The head: rings from under the jaw to the crown, shaped by the face parameters (width, jaw,
	## chin, cheek) scaled by caricature, with a small nose bump for the profile.  UV2 carries
	## head-space face coordinates (x, y in head heights, 0,0 at the eye line centre) for the face
	## shader; other parts carry UV2 = (-10, -10).
	var H: float = L.H
	var f: Array = p.face
	var car: float = 1.0 + 1.2 * p.caricature
	var wmul: float = 1.0 + 0.08 * f[0] * car
	var jaw: float = 1.0 + 0.14 * f[1] * car
	var chin: float = 0.03 * f[2] * car
	var cheek: float = 1.0 + 0.10 * f[3] * car
	var base: float = L.chin
	var w: float = L.head_w * wmul
	var d: float = L.head_d
	# y (from chin, in H), half-width, half-depth, forward shift of the ring centre (in H, -z), exponent
	var rows := [
		[-0.02, 0.13 * jaw, 0.11, 0.20 + chin, 2.0],
		[0.04, 0.23 * jaw, 0.21, 0.17 + chin * 0.8, 2.1],
		[0.12, 0.31 * jaw, 0.31, 0.12 + chin * 0.4, 2.2],
		[0.22, 0.34 * cheek, 0.37, 0.08, 2.2],
		# (finer rings through the nose, for the mesh only -- the part's published rings stay the
		# coarse set that hats and hair index; the trailing true marks these)
		[0.26, 0.352 * cheek, 0.386, 0.068, 2.18, true],
		[0.30, 0.364 * cheek, 0.402, 0.056, 2.16, true],
		[0.34, 0.375 * cheek, 0.414, 0.046, 2.14, true],
		[0.38, (0.38 * cheek + 0.395) * 0.5, 0.422, 0.038, 2.12, true],
		[0.42, 0.395, 0.43, 0.03, 2.1],
		[0.52, 0.40, 0.44, 0.02, 2.05],
		[0.62, 0.40, 0.445, 0.01, 2.0],
		[0.72, 0.385, 0.435, 0.005, 2.0],
		[0.82, 0.35, 0.40, 0.0, 2.0],
		[0.90, 0.29, 0.34, 0.0, 2.0],
		[0.96, 0.19, 0.23, 0.0, 2.0],
		[0.995, 0.07, 0.09, 0.0, 2.0],
	]
	var rs := []
	var main := []
	var scale_w := w / (0.40 * H)
	var scale_d := d / (0.44 * H)
	for r in rows:
		var y: float = base + r[0] * H
		var c := Vector3(0, y, 0.03 * H - r[3] * H)
		# the jaw carries the chin and the lower face (and the shader's mouth with it)
		var wt := [["Head", 1.0]] if r[0] > 0.2 else [["Jaw", 0.9], ["Neck", 0.1]] if r[0] < 0.0 else [["Jaw", 0.75], ["Head", 0.25]] if r[0] < 0.08 else [["Jaw", 0.4], ["Head", 0.6]]
		var rg := ring(c, Vector3.RIGHT, Vector3.BACK, r[1] * H * scale_w, r[2] * H * scale_d, wt, r[4])
		rs.append(rg)
		if r.size() < 6:
			main.append(rg)
	var part := loft("head", rs, HEAD_AROUND, true, true)
	part.rings = main
	# the nose (ghibli_style.md 1.5: small, a single line in front view, a clear little shape in
	# profile): the bridge rises from between the eyes to a slightly upturned tip, then tucks back
	# under it to the lip; narrow, so it reads in profile and takes a small shade on its far side.
	# Face coordinates for the shader come from the undisplaced surface.
	var eye_y: float = base + 0.46 * H
	var nose_y: float = base + 0.32 * H                          # the tip
	var nose: float = 0.11 * H * clampf(1.0 + 0.45 * f[4] * car, 0.55, 1.8)      # (bigger, 2026-09-30)
	for i in part.verts.size():
		var v := part.verts[i]
		var n := part.normals[i]
		part.uv2s[i] = Vector2(v.x / H, (v.y - eye_y) / H) if n.z < 0.35 else Vector2(-10, -10)
		if n.z < -0.2:                                        # the front half
			var t := (v.y - nose_y) / H                       # 0 at the tip, + up the bridge
			var prof := 0.0
			if t >= 0.0:
				prof = pow(clampf(1.0 - t / 0.16, 0.0, 1.0), 1.6)            # the bridge, from the eye line
			else:
				prof = exp(-pow(t / 0.035, 2.0))                           # tucked under the tip
			var half_w := 0.058 * H * (0.8 + 0.4 * clampf(1.0 - t / 0.16, 0.0, 1.0))  # wider at the tip
			var dx := v.x / half_w
			part.verts[i] = v + Vector3(0, 0.12 * nose * prof * exp(-dx * dx) * float(t < 0.0), -nose * prof * exp(-dx * dx))
	return part


static func _arm(L: Dictionary, J: Dictionary, side: String) -> Part:
	var sh: Vector3 = J["UpperArm" + side]
	var el: Vector3 = J["LowerArm" + side]
	var wr: Vector3 = J["Hand" + side]
	var rs := []
	var up := (el - sh).normalized()
	var fore := (wr - el).normalized()
	var fwd := Vector3.BACK
	var ax1 := fwd.cross(up).normalized()
	var ax2 := fwd.cross(fore).normalized()
	# start inside the shoulder (a rounded cap hides the join), then deltoid, biceps, elbow, forearm, wrist
	var ua: float = L.upperarm_r
	var rows := [
		[sh - up * ua * 0.6, ua * 0.55, ua * 0.55, ax1, [["Shoulder" + side, 0.5], ["UpperArm" + side, 0.5]]],
		[sh + up * ua * 0.2, ua * 1.0, ua * 0.98, ax1, [["UpperArm" + side, 0.8], ["Shoulder" + side, 0.2]]],
		[sh.lerp(el, 0.35), ua * 1.05, ua, ax1, [["UpperArm" + side, 0.7], ["UpperArmTwist" + side, 0.3]]],
		[sh.lerp(el, 0.75), ua * 0.9, ua * 0.88, ax1, [["UpperArmTwist" + side, 0.6], ["UpperArm" + side, 0.4]]],
		[el, L.elbow_r, L.elbow_r, (ax1 + ax2).normalized(), [["UpperArm" + side, 0.5], ["LowerArm" + side, 0.5]]],
		[el.lerp(wr, 0.25), L.forearm_r * 1.05, L.forearm_r * 0.95, ax2, [["LowerArm" + side, 1.0]]],
		[el.lerp(wr, 0.7), L.forearm_r * 0.82, L.forearm_r * 0.7, ax2, [["LowerArm" + side, 0.35], ["LowerArmTwist" + side, 0.65]]],
		[wr, L.wrist_r * 1.05, L.wrist_r * 0.8, ax2, [["LowerArmTwist" + side, 0.6], ["Hand" + side, 0.4]]],
	]
	for r in rows:
		rs.append(ring(r[0], r[3], fwd, r[1], r[2], r[4]))
	return loft("arm" + side, rs, LIMB, true, false)


static func _hand_frame(J: Dictionary, side: String) -> Array:
	## [wrist, along the hand, across the palm (front: -), palm normal (toward the body)]
	var wr: Vector3 = J["Hand" + side]
	var d := (wr - (J["LowerArm" + side] as Vector3)).normalized()
	var across := (Vector3.BACK - d * d.dot(Vector3.BACK)).normalized()
	var inward := d.cross(across).normalized()
	if inward.x * (1.0 if side == "L" else -1.0) < 0.0:
		inward = -inward
	return [wr, d, across, inward]


static func _hand_joints(j: Dictionary, L: Dictionary, side: String, _arm_dir: Vector3) -> void:
	## Finger joints: knuckles along the palm's end, fanned a little; the thumb from the palm's
	## front edge near the wrist, pointing down and forward.
	var f := _hand_frame(j, side)
	var wr: Vector3 = f[0]
	var d: Vector3 = f[1]
	var across: Vector3 = f[2]
	var inward: Vector3 = f[3]
	var hl: float = L.hand_len
	var pw: float = L.wrist_r * 1.5                                 # palm half-width
	var palm := hl * PALM
	for fn in FINGER_DEF:
		var fd: Array = FINGER_DEF[fn]
		var fan: Vector3 = (d + across * float(fd[0]) * 0.12).normalized()
		var base: Vector3 = wr + d * (palm + float(fd[1]) * hl) + across * float(fd[0]) * pw
		j[fn + "A" + side] = base
		j[fn + "B" + side] = base + fan * float(fd[2]) * hl
		j[fn + "C" + side] = base + fan * (float(fd[2]) + float(fd[3])) * hl
	# the thumb lies along the palm's front edge, pointing down and a little in toward the palm
	var tb: Vector3 = wr + d * hl * 0.16 - across * pw * 0.78 + inward * pw * 0.3
	var tdir: Vector3 = (d * 0.92 - across * 0.18 + inward * 0.35).normalized()
	j["ThumbA" + side] = tb
	j["ThumbB" + side] = tb + tdir * hl * 0.17
	j["ThumbC" + side] = tb + tdir * hl * 0.25
	# the prop socket: the middle of the palm, a little in front of it (cups, handles, tools)
	j["Prop" + side] = wr + d * hl * 0.45 + inward * pw * 0.9


static func _hand(L: Dictionary, J: Dictionary, side: String) -> Array:
	## Palm, four fingers in two segments and a thumb: simple shapes, as Ghibli draws hands, but
	## real fingers the animator can curl (fists, holding, pointing, gestures).
	var f := _hand_frame(J, side)
	var wr: Vector3 = f[0]
	var d: Vector3 = f[1]
	var across: Vector3 = f[2]
	var inward: Vector3 = f[3]
	var hl: float = L.hand_len
	var pw: float = L.wrist_r * 1.5
	var th: float = L.wrist_r * 0.62                               # palm half-thickness
	var hb := "Hand" + side
	var out := []
	var rs := []
	for r in [[-0.06, 0.66, 0.9], [0.12, 0.86, 0.95], [0.34, 0.98, 0.9], [PALM, 0.94, 0.78]]:
		rs.append(ring(wr + d * hl * r[0], across, inward, pw * r[1], th * r[2], [[hb, 1.0]], 2.2))
	out.append(loft("palm" + side, rs, LIMB, false, true))
	var fr := pw * 0.26                                             # finger radius
	for fn in FINGER_DEF:
		var fd: Array = FINGER_DEF[fn]
		out.append(_finger(J, fn, side, float(fd[2]) * hl, float(fd[3]) * hl, fr * (0.85 if fn == "Pinky" else 1.0), across, float(fd[4]) * hl))
	out.append(_finger(J, "Thumb", side, hl * 0.17, hl * 0.08, fr * 1.2, across, hl * 0.07))
	# one rounded normal field for the whole hand: the screen-space outline draws a line wherever
	# normals jump, and at a distance the jumps between fingers filled the hand with ink.  Blended
	# toward "away from the hand's centre", the fingers still shade and move but don't outline each
	# other; the hand's silhouette keeps its line.
	var centre := wr + d * hl * 0.5
	for p: Part in out:
		for i in p.normals.size():
			var radial := (p.verts[i] - centre)
			radial = (radial - d * radial.dot(d) * 0.6).normalized()
			p.normals[i] = (p.normals[i] * 0.3 + radial * 0.7).normalized()
	return out


static func _finger(J: Dictionary, fn: String, side: String, l1: float, l2: float, r: float, across: Vector3, l3 := 0.0) -> Part:
	## A finger in three segments (proximal, intermediate, distal), each ring weighted to its bone
	## and blended across the joints.
	var a: Vector3 = J[fn + "A" + side]
	var b: Vector3 = J[fn + "B" + side]
	var c: Vector3 = J[fn + "C" + side]
	var d1 := (b - a).normalized()
	var ba := fn + "A" + side
	var bb := fn + "B" + side
	var bc := fn + "C" + side
	if l3 <= 0.0:
		l3 = l2 * 0.45
	var ax := (across - d1 * d1.dot(across)).normalized()
	var az := d1.cross(ax).normalized()
	var rs := [
		ring(a - d1 * r * 1.2, ax, az, r * 1.1, r * 1.0, [["Hand" + side, 0.7], [ba, 0.3]]),
		ring(a + d1 * l1 * 0.3, ax, az, r, r * 0.92, [[ba, 1.0]]),
		ring(b, ax, az, r * 0.92, r * 0.86, [[ba, 0.5], [bb, 0.5]]),
		ring(b + (c - b) * 0.5, ax, az, r * 0.88, r * 0.82, [[bb, 1.0]]),
		ring(c, ax, az, r * 0.82, r * 0.77, [[bb, 0.5], [bc, 0.5]]),
		ring(c + d1 * l3 * 0.9, ax, az, r * 0.68, r * 0.64, [[bc, 1.0]]),
	]
	return loft(fn.to_lower() + side, rs, 6, false, true)


static func _leg(L: Dictionary, J: Dictionary, side: String) -> Part:
	var hip: Vector3 = J["UpperLeg" + side]
	var kn: Vector3 = J["LowerLeg" + side]
	var an: Vector3 = J["Foot" + side]
	var rs := []
	var tr: float = L.thigh_r
	var rows := [
		[hip + Vector3(0, 0.03 * L.T, 0), tr * 1.02, tr * 1.05, [["UpperLeg" + side, 0.6], ["Hips", 0.4]]],
		[hip.lerp(kn, 0.15), tr, tr * 1.02, [["UpperLeg" + side, 1.0]]],
		[hip.lerp(kn, 0.5), tr * 0.82, tr * 0.86, [["UpperLeg" + side, 1.0]]],
		[hip.lerp(kn, 0.85), L.knee_r * 1.25, L.knee_r * 1.25, [["UpperLeg" + side, 0.9], ["LowerLeg" + side, 0.1]]],
		[kn, L.knee_r * 1.15, L.knee_r * 1.18, [["UpperLeg" + side, 0.5], ["LowerLeg" + side, 0.5]]],
		[kn.lerp(an, 0.3), L.calf_r, L.calf_r * 1.08, [["LowerLeg" + side, 1.0]]],
		[kn.lerp(an, 0.65), L.calf_r * 0.72, L.calf_r * 0.75, [["LowerLeg" + side, 1.0]]],
		[an + Vector3(0, 0.01 * L.T, 0), L.ankle_r, L.ankle_r * 1.1, [["LowerLeg" + side, 0.6], ["Foot" + side, 0.4]]],
	]
	for r in rows:
		# calves bulge behind: shift the lower-leg rings back a little
		var c: Vector3 = r[0]
		rs.append(ring(c, Vector3.RIGHT, Vector3.BACK, r[1], r[2], r[3]))
	return loft("leg" + side, rs, LIMB, false, false)


static func _foot(L: Dictionary, J: Dictionary, side: String) -> Part:
	var an: Vector3 = J["Foot" + side]
	var fl: float = L.foot_len
	var ar: float = L.ankle_r
	var rs := []
	# along -Z (forward) from behind the ankle to the toes, dropping to the ground
	var rows := [[0.22, 0.9, 0.9, 1.0], [0.1, 1.15, 1.05, 0.95], [-0.15, 1.25, 0.8, 0.7], [-0.45, 1.35, 0.6, 0.45], [-0.7, 1.25, 0.45, 0.3], [-0.82, 0.8, 0.3, 0.25]]
	for r in rows:
		var zc: float = an.z + r[0] * fl
		var yc: float = maxf(r[2] * ar * 0.9, an.y * r[3])
		# rings past the ball of the foot belong to the toe (blended across the joint)
		var tw := clampf((-r[0] - (BALL - 0.12)) / 0.24, 0.0, 1.0)
		var w := [["Foot" + side, 1.0]] if tw <= 0.0 else [["Foot" + side, 1.0 - tw], ["Toe" + side, tw]] if tw < 1.0 else [["Toe" + side, 1.0]]
		rs.append(ring(Vector3(an.x, yc, zc), Vector3.RIGHT, Vector3.UP, ar * r[1], ar * r[2], w, 2.6))
	return loft("foot" + side, rs, LIMB, true, true)
