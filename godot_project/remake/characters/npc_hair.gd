extends RefCounted
class_name NpcHair

## Hair for a generated head: a shell grown from the head's own rings (so it fits any head),
## standing off the scalp wherever the style's hairline puts hair and tucked just inside the head
## everywhere else -- the tuck makes a clean hairline edge.  The hairline and the hem are cut into
## clumps with points, as Ghibli draws hair (ghibli_style.md 1.6).  Long styles add a curtain down
## the back that clears the shoulders; ponytails, buns and braids are small lofts.
##
## Hair is the most looked-at part of a person in a crowd (McDonnell et al. 2009; scale_survey.md
## 2.5), so styles aim at distinct silhouettes first.

const STYLES := {
	# hairline heights (fractions of head height from the chin) at the front, sides and back; shell
	# thickness (head heights); clumps round the hem and their depth; curtain length below the chin
	# (head heights); extras
	"crop":            {"front": 0.80, "side": 0.50, "back": 0.16, "thick": 0.030, "clumps": 11, "amp": 0.020},
	"short_side_part": {"front": 0.76, "side": 0.46, "back": 0.12, "thick": 0.045, "clumps": 8, "amp": 0.035, "part": 0.05},
	"bob":             {"front": 0.60, "side": 0.08, "back": 0.04, "thick": 0.060, "clumps": 12, "amp": 0.030},
	"shoulder":        {"front": 0.64, "side": 0.06, "back": 0.00, "thick": 0.060, "clumps": 10, "amp": 0.040, "curtain": 0.75},
	"long_loose":      {"front": 0.70, "side": 0.06, "back": 0.00, "thick": 0.055, "clumps": 9, "amp": 0.05, "curtain": 1.5},
	"ponytail":        {"front": 0.72, "side": 0.40, "back": 0.22, "thick": 0.040, "clumps": 8, "amp": 0.02, "tail": "ponytail"},
	"braids":          {"front": 0.64, "side": 0.34, "back": 0.20, "thick": 0.040, "clumps": 9, "amp": 0.03, "tail": "braids"},
	"bun":             {"front": 0.76, "side": 0.40, "back": 0.24, "thick": 0.035, "clumps": 6, "amp": 0.015, "tail": "bun"},
	"curly_short":     {"front": 0.74, "side": 0.38, "back": 0.10, "thick": 0.085, "clumps": 14, "amp": 0.035, "curl": 1.0},
	"curly_long":      {"front": 0.66, "side": 0.06, "back": 0.00, "thick": 0.090, "clumps": 14, "amp": 0.04, "curl": 1.0, "curtain": 0.8},
	"balding":         {"front": 1.10, "side": 0.44, "back": 0.12, "thick": 0.030, "clumps": 9, "amp": 0.02, "bald_top": 0.70},
	"bald":            {},
	"tied_scarf":      {"front": 0.76, "side": 0.40, "back": 0.24, "thick": 0.035, "clumps": 6, "amp": 0.015, "tail": "bun"},
}
const SUB := 3          # sub-rings per head ring: a crisp hairline


static func build(style: String, body: Dictionary, rng: NpcRng, under_hat := false) -> Array:
	## -> Array of NpcBody.Part.  rng: the person's "hair" stream (clump phase, small variations).
	var st: Dictionary = STYLES.get(style, STYLES.crop)
	if st.is_empty():
		return []
	var head: NpcBody.Part
	for p: NpcBody.Part in body.parts:
		if p.name == "head":
			head = p
	var L: Dictionary = body.landmarks
	var H: float = L.H
	var out := []
	var phase := rng.rand()
	var vol := 0.85 + 0.3 * rng.rand()
	var rs := head.rings
	var n := (rs.size() - 1) * SUB
	var rings := []
	var hy0: float = (rs[0].c as Vector3).y
	for j in n + 1:
		var f := float(j) / SUB
		rings.append(NpcGarments._ring_at(rs, f))
	# the shell: the head rings' points, pushed out (hair) or in (no hair) per vertex
	var p := NpcBody.Part.new()
	p.name = "hair"
	p.rings = rings
	p.around = 40                     # finer than the head: clump points need the columns
	var around := p.around
	var thick: float = float(st.thick) * H * vol
	if under_hat:
		thick = minf(thick, 0.018 * H)                       # must stay inside the crown's room
	# per column (independent of height): the hairline, the front weight, sin/cos
	var tb := NpcBody._table(around)
	var sns: PackedFloat32Array = tb[0]
	var css: PackedFloat32Array = tb[1]
	var lines := PackedFloat32Array()
	var fronts := PackedFloat32Array()
	for k in around:
		lines.append(_hairline(st, float(k) / around, phase))
		fronts.append(_front_weight(float(k) / around))
	var curly := st.has("curl")
	for j in rings.size():
		var r: Dictionary = rings[j]
		var rc: Vector3 = r.c
		var yf := (rc.y - hy0) / H
		var top := smoothstep(0.55, 0.95, yf) * (0.0 if under_hat else 1.0)   # fuller on top
		var rax: Vector3 = (r.ax as Vector3) * float(r.a)
		var raz: Vector3 = (r.az as Vector3) * float(r.b)
		var wb := NpcBody.weights_of(r.w)
		for k in around + 1:
			var kk := k % around
			var t := float(kk) / around
			# the head's true surface: its rings are superellipses (exponent 2.0-2.2, boxier than an
			# ellipse -- up to ~3.5 mm further out at the cheeks and temples); a plain ellipse here
			# left the hairless shell poking through the skin there, and a sawtooth hairline
			var base := NpcBody._ring_point_sc(r, sns[kk], css[kk])
			var outv := base - rc
			outv.y = 0.0
			var dirn := outv.normalized() if outv.length() > 1e-5 else Vector3.UP
			var line := lines[kk]
			# signed distance to the hairline (in head heights, + where there is hair); a bald crown is
			# a second edge.  The shader cuts at zero (UV2.y = 0.5): interpolated through each
			# triangle, that is the true hairline -- smooth, not a stair of whole vertices
			var sd := yf - line
			if st.has("bald_top") and fronts[kk] > 0.0:
				sd = minf(sd, float(st.bald_top) - yf)
			var has := clampf(sd / 0.02 + 1.0, 0.0, 1.0)            # (geometry: full thickness from the edge up)
			var curl := 0.0
			if curly:
				curl = 0.3 * sin(t * TAU * 7.0 + phase * 20.0) * sin(yf * 25.0)
			# everything kept stands clear of the skin; the cut-away part sinks under it
			var d := lerpf(-0.02 * H, thick * (1.0 + 0.4 * top + curl), has)
			# the crown closes over the top: push the last rings upward too
			var v := base + dirn * d + Vector3(0, d * 0.8 * top, 0)
			p.verts.append(v)
			p.uvs.append(Vector2(t, yf))
			p.uv2s.append(Vector2(-10, 0.5 + sd * 10.0))
			p.bones.append_array(wb[0])
			p.weights.append_array(wb[1])
	var row := around + 1
	for j in rings.size() - 1:
		for k in around:
			var a := j * row + k
			p.indices.append_array([a, a + row, a + 1, a + 1, a + row, a + row + 1])
	NpcBody._orient_outward(p, rings, 0, p.indices.size())
	var top_r: Dictionary = rings[-1]
	NpcBody._cap(p, (rings.size() - 1) * row, {"c": (top_r.c as Vector3) + Vector3(0, thick * 1.2, 0), "a": top_r.a, "b": top_r.b, "w": top_r.w}, Vector3.UP)
	NpcBody._smooth_normals(p, rings.size())
	out.append(p)
	if st.has("curtain"):
		out.append(_curtain(st, rings, L, thick, phase))
	match str(st.get("tail", "")):
		"ponytail":
			out.append(_tube("ponytail", rings, L, 0.5, 0.62, Vector3(0, -1.0, 0.35), 0.11 * H, 1.1 * H, 0.35))
		"bun":
			out.append(_tube("bun", rings, L, 0.5, 0.78, Vector3(0, 0.3, 1.0), 0.16 * H, 0.2 * H, 0.9))
		"braids":
			out.append(_tube("braidL", rings, L, 0.62, 0.4, Vector3(-0.15, -1.0, -0.1), 0.06 * H, 1.0 * H, 0.6))
			out.append(_tube("braidR", rings, L, 0.38, 0.4, Vector3(0.15, -1.0, -0.1), 0.06 * H, 1.0 * H, 0.6))
	return out


static func _chain_weights(t: float) -> Array:
	## Along hanging hair (0 at the head .. 1 at the tip): the head, then the hair chain.
	if t <= 0.0:
		return [["Head", 1.0]]
	if t < 0.5:
		return [["Head", 1.0 - 2.0 * t], ["HairA", 2.0 * t]]
	return [["HairA", 2.0 - 2.0 * t], ["HairB", 2.0 * t - 1.0]]


static func _front_weight(t: float) -> float:
	return pow(maxf(cos(t * TAU), 0.0), 1.5)


static func _hairline(st: Dictionary, t: float, phase: float) -> float:
	## Height (head fractions from the chin) above which there is hair, at the angle t round the head
	## (0 front).  Front / side / back blended; clumped points cut into it.
	var az := t * TAU
	var wf := pow(maxf(cos(az), 0.0), 1.5)
	var wb := pow(maxf(-cos(az), 0.0), 1.5)
	var ws := 1.0 - wf - wb
	var line := wf * float(st.front) + ws * float(st.side) + wb * float(st.back)
	if st.has("part"):
		line += float(st.part) * wf * signf(sin(az))           # a side parting: one side sweeps lower
	var cl: float = st.get("clumps", 8)
	var amp: float = st.get("amp", 0.02)
	var tooth := absf(fmod(t * cl + phase, 1.0) - 0.5) * 2.0   # 0 at a clump's point .. 1 between
	return line + amp * (tooth - 0.5) * 2.0


static func _curtain(st: Dictionary, rings: Array, L: Dictionary, thick: float, phase: float) -> NpcBody.Part:
	## Long hair down the back: the back arc of the head (sides and back, the face left open),
	## continued straight down past the neck, flaring to clear the shoulders; points at the hem.
	var H: float = L.H
	var y_start: float = (rings[0].c as Vector3).y + 0.3 * H
	var hem: float = L.chin - float(st.curtain) * H
	var src: Dictionary = rings[int(rings.size() * 0.3)]
	var rs := []
	var steps := 6
	for i in steps + 1:
		var t := float(i) / steps
		var y := lerpf(y_start, hem, t)
		var w: float = src.a + thick + t * maxf(0.0, L.shoulder_w * 0.95 - src.a) * smoothstep(0.0, 0.5, t)
		var d: float = src.b + thick + t * 0.02 * H
		var c := Vector3(0, y, (src.c as Vector3).z + 0.06 * H * t)
		rs.append(NpcBody.ring(c, Vector3.RIGHT, Vector3.BACK, w, d, _chain_weights(t), 2.0))
	var p := NpcGarments._front_panel("curtain", rs, 0.62)
	# rotate the panel to the back: _front_panel spans the front arc, so mirror z about each ring
	for i in p.verts.size():
		var ri := mini(i / 9, rs.size() - 1)
		var cz: float = (rs[ri].c as Vector3).z
		p.verts[i].z = cz + (cz - p.verts[i].z)
		p.normals[i].z = -p.normals[i].z
	# clumped points along the hem
	var cols := 9
	var last := (rs.size() - 1) * cols
	for k in cols:
		var tooth := absf(fmod(float(k) * 0.5 + phase, 1.0) - 0.5) * 2.0
		p.verts[last + k].y -= 0.05 * H * (1.0 - tooth)
	return p


static func _tube(pname: String, rings: Array, L: Dictionary, t_round: float, yf: float, dir: Vector3, r0: float, length: float, taper: float) -> NpcBody.Part:
	## A ponytail / braid / bun: a tapered loft starting on the head surface at angle t_round and
	## height yf, going in direction dir.
	var H: float = L.H
	var hy0: float = (rings[0].c as Vector3).y
	var ring: Dictionary = rings[clampi(int(yf * (rings.size() - 1)), 0, rings.size() - 1)]
	var start := NpcBody.ring_point(ring, t_round)
	var d := dir.normalized()
	var ax := d.cross(Vector3.UP if absf(d.y) < 0.9 else Vector3.RIGHT).normalized()
	var az := ax.cross(d).normalized()
	var rs := []
	var steps := 5
	for i in steps + 1:
		var t := float(i) / steps
		var c := start + d * length * t + Vector3(0, -0.15 * H * t * t, 0) * (0.0 if pname == "bun" else 1.0)
		var r := r0 * (1.0 - taper * t) * (0.8 + 0.4 * sin(PI * minf(t * 1.5, 1.0)))
		var wt := _chain_weights(t) if pname != "bun" else [["Head", 1.0]]
		rs.append(NpcBody.ring(c, ax, az, r, r, wt, 2.0))
	return NpcBody.loft(pname, rs, 10, true, true)
