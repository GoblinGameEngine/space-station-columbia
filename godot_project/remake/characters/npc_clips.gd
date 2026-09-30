extends RefCounted
class_name NpcClips

## Authored animation clips for generated people (research/animation/npc_animations.md): key poses
## as data in npc_clips.json, in body-relative terms so one clip fits every body, played by
## NpcAnimator over its procedural layers (feet planted, springs, personality timing).  This is the
## pose-to-pose, hand-keyed approach of RAGE and Overgrowth: strong key poses, the in-betweens by rule.
##
## A key sets any of these channels (all optional; a channel is interpolated between the keys that set
## it, and absent channels leave the procedural pose alone):
##   handL / handR   [frame, x, y, z]   wrist target, in fractions of height, in "upper" (the upper
##                                      chest), "hips", "head" or "root" space  -> arm IK
##   poleL / poleR   [x, y, z]          where the elbow points (the character's axes)
##   wristL / wristR [pitch, yaw, roll] degrees, after IK
##   gripL / gripR   name or 0..1       open, relaxed, cup, pinch, point, fist, wave, hold
##   spine / head    [pitch, yaw, roll] degrees (+pitch forward), added to the procedural pose
##   hips            [x, y, z]          offset from rest, fractions of height (full-body clips)
##   hipsRot         [pitch, yaw, roll] degrees
##   footL / footR   [x, y, z, pitch]   ankle target from the root, fractions of height (full-body)
##   shoulders       [left, right]      degrees the clavicles rise (shrug, cold, fright)
##   face            {mouth, smile, brow, eyes}
##   w               0..1               how much of the clip shows at this key (ease in and out)
## Keys are poses: a channel a key leaves out holds its value from the key before (so {"t", "w"}
## alone is a hold).  A key's "ease" shapes the approach to it: smooth (default), tame (slow build, then release),
## tsume (a snap into the key, bunched spacing at the end), linear, hold (stepped: a drawn hold).
## The cartoon animation filter (Wang et al. 2006) runs on the hand paths: anticipation before a move
## and follow-through after, sized by the person's Effort.

const PATH := "res://remake/characters/npc_clips.json"
const GRIPS := {   # per finger curl (thumb, index, middle, ring, pinky)
	"open": [0.0, 0.0, 0.0, 0.0, 0.0], "relaxed": [0.25, 0.25, 0.3, 0.33, 0.36],
	"cup": [0.35, 0.45, 0.45, 0.45, 0.45], "pinch": [0.6, 0.6, 0.35, 0.4, 0.45],
	"point": [0.7, 0.0, 0.95, 1.0, 1.0], "fist": [0.9, 1.0, 1.0, 1.0, 1.0],
	"wave": [0.05, 0.0, 0.0, 0.05, 0.1], "hold": [0.75, 0.8, 0.85, 0.85, 0.85]}

static var _data: Dictionary


static func data() -> Dictionary:
	if _data.is_empty():
		var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(PATH))
		for id in d.clips:
			_fill_poses(d.clips[id])
		_data = d
	return _data


static func _fill_poses(c: Dictionary) -> void:
	## Keys are poses (pose-to-pose): a channel a key leaves out holds its last value there, so a
	## key of only {"t", "w"} is a hold.  Filled once at load; sample() then interpolates as usual.
	var last := {}
	for k in c.keys:
		for ch in last:
			if not k.has(ch):
				k[ch] = last[ch]
		for ch in k:
			if ch != "t" and ch != "ease":
				last[ch] = k[ch]


static func clip(id: String) -> Dictionary:
	return (data().clips as Dictionary).get(id, {})


static func ambient_weights(age: float) -> Dictionary:
	## The idles a person of this age breaks into, weighted (npc_clips.json "ambient").
	var out := {}
	var amb: Dictionary = data().get("ambient", {})
	for id in amb:
		if id.begins_with("_"):
			continue
		var r: Dictionary = amb[id]
		var w := float(r.get("w", 1.0))
		if age < 13.0:
			w = float(r.get("child", w))
		elif age >= 60.0:
			w += float(r.get("old", 0.0))
		if w > 0.0:
			out[id] = w
	return out


static func grip_curls(g: Variant) -> Array:
	if typeof(g) == TYPE_STRING:
		return GRIPS.get(g, GRIPS.relaxed)
	var x := float(g)
	return [x * 0.8, x, x, x, x]


static func _ease(u: float, mode: String) -> float:
	match mode:
		"linear":
			return u
		"tame":                  # hold back, then release
			return u * u * u
		"tsume":                 # rush in, bunching into the key
			return 1.0 - pow(1.0 - u, 3.0)
		"hold":
			return 0.0 if u < 1.0 else 1.0
	return u * u * (3.0 - 2.0 * u)


static func sample(c: Dictionary, t: float) -> Dictionary:
	## Every channel's value at time t (seconds into the clip).
	var keys: Array = c.keys
	var out := {}
	var chans := {}
	for k in keys:
		for ch in k:
			if ch != "t" and ch != "ease":
				chans[ch] = true
	for ch in chans:
		var prev = null
		var nxt = null
		for k in keys:
			if not k.has(ch):
				continue
			if float(k.t) <= t:
				prev = k
			elif nxt == null:
				nxt = k
		if prev == null:
			prev = nxt
		if nxt == null:
			out[ch] = prev[ch]
			continue
		var t0 := float(prev.t)
		var t1 := float(nxt.t)
		var u := clampf((t - t0) / maxf(t1 - t0, 1e-4), 0.0, 1.0)
		u = _ease(u, str(nxt.get("ease", "smooth")))
		out[ch] = _lerp_val(prev[ch], nxt[ch], u)
	return out


static func sample_filtered(c: Dictionary, t: float, strength: float) -> Dictionary:
	## sample(), with the cartoon animation filter on the hand targets: x* = x - k * x''
	## (smoothed second derivative over a +-h window).  The clip's own future is known, so the
	## anticipation lobe is exact.
	var s := sample(c, t)
	if strength <= 0.0:
		return s
	var h := 0.09
	var a := sample(c, maxf(t - h, 0.0))
	var b := sample(c, t + h)
	for ch in ["handL", "handR", "hips"]:
		if not s.has(ch) or not a.has(ch) or not b.has(ch):
			continue
		var cur: Array = s[ch]
		var pa: Array = a[ch]
		var pb: Array = b[ch]
		if cur[0] is String and (cur[0] == "mix" or not pa[0] is String or not pb[0] is String or pa[0] != cur[0] or pb[0] != cur[0]):
			continue      # across a change of frame: no filter (the neighbours are in other frames)
		var off := 1 if typeof(cur[0]) == TYPE_STRING else 0
		var f := cur.duplicate()
		for i in range(off, cur.size()):
			var acc := (float(pb[i]) - 2.0 * float(cur[i]) + float(pa[i])) / (h * h)
			f[i] = float(cur[i]) - strength * 0.0018 * acc
		s[ch] = f
	return s


static func _lerp_val(a: Variant, b: Variant, u: float) -> Variant:
	if typeof(a) == TYPE_ARRAY and typeof(b) == TYPE_ARRAY:
		if a.size() == 4 and typeof(a[0]) == TYPE_STRING and a[0] != b[0]:
			# a hand passing from one frame to another: both ends kept, blended in skeleton space
			# by the animator (lerping coordinates of different frames would swing the hand wide)
			return ["mix", a, b, u]
		var out := []
		for i in a.size():
			if typeof(a[i]) == TYPE_STRING:
				out.append(a[i] if u < 0.5 else b[i])
			else:
				out.append(lerpf(float(a[i]), float(b[i]), u))
		return out
	if typeof(a) == TYPE_DICTIONARY and typeof(b) == TYPE_DICTIONARY:
		var d := {}
		for k in a:
			d[k] = lerpf(float(a[k]), float(b.get(k, a[k])), u)
		for k in b:
			if not d.has(k):
				d[k] = lerpf(0.0, float(b[k]), u)
		return d
	if typeof(a) == TYPE_STRING or typeof(b) == TYPE_STRING:
		# grips by name: blend through the curl arrays
		var ca := grip_curls(a)
		var cb := grip_curls(b)
		var o := []
		for i in 5:
			o.append(lerpf(float(ca[i]), float(cb[i]), u))
		return o
	return lerpf(float(a), float(b), u)
