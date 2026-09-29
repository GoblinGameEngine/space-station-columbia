extends RefCounted
class_name NpcGarments

## Clothes for a generated body, built from the body's own rings (NpcBody) plus ease, so a garment
## fits any body the builder can make and can't pass through it: a garment ring has the same frame
## and skin weights as the body ring under it, just larger (generator_design_notes.md 5).  Skirts,
## dresses and coats that must clear both legs are lofted from the waist to a hem ring round both.
##
## What a person wears is chosen from npc_outfits.json by outfit(): per slot a weighted pick on the
## person's own stream ("outfit:<slot>"), so it is the same every time, and a colour and fabric
## pattern for each garment.  The shader draws the pattern (no textures).

const PATH := "res://remake/characters/npc_outfits.json"
const SLOTS := ["bottom", "top", "dress", "over", "feet", "head"]
const PATTERNS := ["solid", "stripes", "pinstripe", "check", "tartan", "dots", "floral", "knit", "denim", "pleats", "weave", "herring"]

static var _data: Dictionary


static func data() -> Dictionary:
	if _data.is_empty():
		_data = JSON.parse_string(FileAccess.get_file_as_string(PATH))
	return _data


# -- choosing ---------------------------------------------------------------------------------------

static func tags(v: Dictionary) -> Array:
	var age := float(v.get("age", 30))
	var t := [v.get("sex", "female"), "style:" + str(v.get("style", "plain"))]
	t.append("child" if age < 13.0 else "teen" if age < 18.0 else "elder" if age >= 65.0 else "adult")
	return t


static func outfit(v: Dictionary, world_seed: int, pid: String, occasion := "work") -> Array:
	## -> [{slot, garment, def, colour: Color, pattern, colours: [Color, Color, Color], scale}], inner first.
	var d := data()
	var key := "casual"
	if occasion == "work":
		var occ: String = str(v.get("occupation", ""))
		var tb: Dictionary = NpcTraits.shared().tables.occupations
		if tb.has(occ):
			key = str(tb[occ][(tb["_cols"] as Array).find("outfit")])
	if not d.outfits.has(key):
		key = "casual"
	var of: Dictionary = d.outfits[key]
	var tg := tags(v)
	var out := []
	var accent_slot := ""
	var patterned := 0
	var pal := _palette(v)
	for slot in SLOTS:
		var opts: Dictionary = of.slots.get(slot, {})
		if opts.is_empty():
			continue
		var w := {}
		for g in opts:
			var o: Variant = opts[g]
			if typeof(o) == TYPE_DICTIONARY:
				var ok := true
				for need in o.get("if", []):
					if not need in tg:
						ok = false
				if ok:
					w[g] = float(o.w)
			else:
				w[g] = float(o)
		if w.is_empty():
			continue
		var rng := NpcRng.for_trait(world_seed, pid, "outfit:" + slot)
		var g: String = rng.pick(w)
		if g == "none" or not d.garments.has(g):
			continue
		var def: Dictionary = d.garments[g]
		# colour
		var src: String = of.colours.get(slot, "palette")
		var col := _colour(src, pal, rng, v, slot, accent_slot)
		if src == "accent" and int(v.get("accent_colour", -1)) >= 0 and accent_slot == "":
			accent_slot = slot
		# pattern: at most one patterned garment (two for children and the flamboyant)
		var pw: Dictionary = def.get("patterns", {"solid": 1})
		var limit := 2 if ("child" in tg or "style:flamboyant" in tg) else 1
		var pat: String = rng.pick(pw)
		if pat != "solid" and pat != "denim" and pat != "knit" and pat != "pleats" and pat != "weave":
			if patterned >= limit:
				pat = "solid"
			else:
				patterned += 1
		if pat == "denim":
			col = Color(d.colours.denim)
		var c2 := _second(col, pal, rng, pat)
		out.append({"slot": slot, "garment": g, "def": def, "colour": _worn(col, float(v.get("wear", 0.3))),
			"colours": [_worn(c2[0], float(v.get("wear", 0.3))), _worn(c2[1], float(v.get("wear", 0.3)))],
			"pattern": pat, "scale": 0.6 + rng.rand() * 0.8})
	# a dress replaces top and bottom
	var has_dress := out.any(func(x): return x.slot == "dress")
	if has_dress:
		out = out.filter(func(x): return x.slot != "top" and x.slot != "bottom")
	# coveralls replace the bottom
	if out.any(func(x): return x.def.build == "top+bottom"):
		out = out.filter(func(x): return x.slot != "bottom")
	return out


static func _palette(v: Dictionary) -> Array:
	var tb: Dictionary = NpcTraits.shared().tables.palettes
	var fam: String = str(v.get("palette", "earth"))
	var sw: Array = tb.get(fam, tb.earth)
	return sw.map(func(h): return Color.from_hsv(float(h[0]) / 360.0, float(h[1]), float(h[2])))


static func _colour(src: String, pal: Array, rng: NpcRng, v: Dictionary, slot: String, accent_slot: String) -> Color:
	var d := data()
	if src == "accent":
		var ai := int(v.get("accent_colour", -1))
		if ai >= 0 and accent_slot == "":
			var acc: Array = NpcTraits.shared().tables.palettes.accent
			var a: Array = acc[ai % acc.size()]
			return Color.from_hsv(float(a[0]) / 360.0, float(a[1]), float(a[2]))
		src = "palette"
	if src == "palette":
		return pal[int(rng.rand() * pal.size()) % pal.size()]
	if src == "palette_dark":
		var c: Color = pal[int(rng.rand() * pal.size()) % pal.size()]
		return Color.from_hsv(c.h, minf(c.s * 1.1, 0.5), clampf(c.v * 0.6, 0.18, 0.45))
	if d.colours.has(src):
		return Color(d.colours[src])
	return Color(src) if src.begins_with("#") else pal[0]


static func _second(base: Color, pal: Array, rng: NpcRng, pat: String) -> Array:
	## The pattern's other colours: stripes/checks against cream or a palette swatch; small prints
	## (dots, florals) in a lighter or darker tint.
	var cream := Color("#e6dfcc")
	var other: Color = pal[int(rng.rand() * pal.size()) % pal.size()]
	match pat:
		"stripes", "check", "pinstripe":
			return [cream if base.v < 0.7 else other, other]
		"tartan":
			return [other, Color.from_hsv(fposmod(base.h + 0.08, 1.0), base.s, base.v * 0.6)]
		"dots", "floral":
			return [cream if base.v < 0.6 else base.darkened(0.45), other]
	return [base.darkened(0.15), base.lightened(0.15)]


static func _worn(c: Color, wear: float) -> Color:
	## Faded with wear: less saturated, a little lighter (ghibli_style.md 2.2 rule 5).
	return Color.from_hsv(c.h, c.s * (1.0 - 0.4 * wear), minf(1.0, c.v * (1.0 + 0.1 * wear)))


# -- building ----------------------------------------------------------------------------------------

static func _ring_at(rings: Array, f: float) -> Dictionary:
	## A ring at fractional index f along a part's rings (interpolated).
	f = clampf(f, 0.0, rings.size() - 1.0)
	var i := mini(int(f), rings.size() - 2)
	var t := f - i
	var a: Dictionary = rings[i]
	var b: Dictionary = rings[i + 1]
	return {"c": (a.c as Vector3).lerp(b.c, t), "ax": (a.ax as Vector3).lerp(b.ax, t).normalized(),
		"az": (a.az as Vector3).lerp(b.az, t).normalized(), "a": lerpf(a.a, b.a, t), "b": lerpf(a.b, b.b, t),
		"e": lerpf(a.e, b.e, t), "w": a.w if t < 0.5 else b.w}


static func _grow(r: Dictionary, e: float, ex := 0.0) -> Dictionary:
	var g := r.duplicate()
	g.a = r.a + e + ex
	g.b = r.b + e + ex * 0.7
	return g


static func _range(rings: Array, f0: float, f1: float, e: float, step := 1.0) -> Array:
	## Rings from fractional index f0 to f1 (either direction), grown by ease e.
	var out := []
	var dirn := 1.0 if f1 >= f0 else -1.0
	var f := f0
	while (f - f1) * dirn < -1e-4:
		out.append(_grow(_ring_at(rings, f), e))
		var nxt := floorf(f + 1.0) if dirn > 0 else ceilf(f - 1.0)
		f = minf(nxt, f1) if dirn > 0 else maxf(nxt, f1)
	out.append(_grow(_ring_at(rings, f1), e))
	return out


static func build(def: Dictionary, body: Dictionary, layer_ease := 0.0) -> Array:
	## -> Array of NpcBody.Part for one garment.  layer_ease: extra room for layers worn under it.
	var parts: Dictionary = {}
	for p: NpcBody.Part in body.parts:
		parts[p.name] = p
	var L: Dictionary = body.landmarks
	var e: float = float(def.get("ease", 0.015)) + layer_ease
	def = def.duplicate()
	def["_sleeve_ease"] = float(def.get("ease", 0.015)) * 0.8 + layer_ease * 0.35    # layering room is for the torso
	var out: Array = []
	match str(def.build):
		"top":
			out.append_array(_top(def, parts, L, e))
		"bottom":
			out.append_array(_bottom(def, parts, L, e))
		"top+bottom":
			out.append_array(_top(def, parts, L, e))
			var bd := def.duplicate()
			bd.top = def.torso[0] + 3.4
			out.append_array(_bottom(bd, parts, L, e + 0.002))
		"skirt":
			out.append(_skirt(float(def.top), float(def.hem), float(def.get("flare", 0.3)), parts, L, e + 0.004, "skirt"))
		"dress":
			out.append_array(_top(def, parts, L, e))
			out.append(_skirt(float(def.torso[0]) + 0.2, float(def.hem), float(def.get("flare", 0.4)), parts, L, e + 0.002, "dress_skirt"))
		"coat":
			out.append_array(_top(def, parts, L, e))
			if float(def.get("hem", 0.0)) > 0.02:
				out.append(_skirt(float(def.torso[0]) + 0.6, float(def.hem), float(def.get("flare", 0.25)), parts, L, e + 0.012, "coat_skirt"))
		"overalls":
			var bd := def.duplicate()
			out.append_array(_bottom(bd, parts, L, e))
		"apron":
			out.append(_apron(def, parts, L, e * 0.5 + 0.006))
		"shoes":
			out.append_array(_shoes(def, parts, L, e))
		"cap", "brim_hat", "headscarf":
			out.append_array(_headwear(def, parts, L))
	return out


static func _top(def: Dictionary, parts: Dictionary, L: Dictionary, e: float) -> Array:
	var torso: NpcBody.Part = parts.torso
	var t0: float = def.torso[0]
	var t1: float = def.torso[1]
	var rs := _range(torso.rings, t0, t1, e)
	# the neck opening: the top ring pulled in to sit round the neck, collars stand up a little
	var neck: String = def.get("neck", "round")
	var top: Dictionary = rs[-1]
	if neck == "collar" or neck == "sailor":
		var col := _grow(top, 0.004)
		col.c = (top.c as Vector3) + Vector3(0, 0.018 * L.T, 0)
		col.a = top.a * 0.92
		col.b = top.b * 0.95
		rs.append(col)
	elif neck == "v" or neck == "square":
		var low := _grow(top, 0.0)
		low.c = (top.c as Vector3) - Vector3(0, 0.03 * L.T, 0)
		rs[-1] = low
	# hem: tucked-in tops end at the waistband; others hang a little looser at the bottom
	(rs[0] as Dictionary).a *= 1.03
	(rs[0] as Dictionary).b *= 1.03
	var out := [NpcBody.loft("top", rs, NpcBody.RING, false, false)]
	var sl: float = def.get("sleeve", 0.0)
	for side in ["L", "R"]:
		var arm: NpcBody.Part = parts["arm" + side]
		if sl > 0.01:
			var end := 0.2 + sl * (arm.rings.size() - 1.2)
			var srs := _range(arm.rings, 0.0, end, float(def.get("_sleeve_ease", e * 0.9)))
			(srs[0] as Dictionary).a = (arm.rings[0] as Dictionary).a + e * 0.3      # (a full-ease start stood up as a wing)
			(srs[0] as Dictionary).b = (arm.rings[0] as Dictionary).b + e * 0.3
			# short sleeves flare open at the hem
			if sl < 0.6:
				(srs[-1] as Dictionary).a += 0.003 * L.T
				(srs[-1] as Dictionary).b += 0.003 * L.T
			out.append(NpcBody.loft("sleeve" + side, srs, NpcBody.LIMB, true, false))
	return out


static func _bottom(def: Dictionary, parts: Dictionary, L: Dictionary, e: float) -> Array:
	var torso: NpcBody.Part = parts.torso
	var out := [NpcBody.loft("pants_top", _range(torso.rings, 0.0, float(def.top), e + 0.002), NpcBody.RING, true, false)]
	var ln: float = def.get("legs", 1.0)
	for side in ["L", "R"]:
		var leg: NpcBody.Part = parts["leg" + side]
		var end := ln * (leg.rings.size() - 1.0)
		var lrs := _range(leg.rings, 0.0, end, e)
		# trouser legs hang straight below the knee rather than hugging the calf
		for r in lrs:
			r.a = maxf(r.a, L.knee_r * 1.3 + e)
			r.b = maxf(r.b, L.knee_r * 1.3 + e)
		out.append(NpcBody.loft("pants" + side, lrs, NpcBody.LIMB, false, false))
	return out


static func _skirt(top_f: float, hem: float, flare: float, parts: Dictionary, L: Dictionary, e: float, pname: String) -> NpcBody.Part:
	## From a torso ring down to a hem ring that encloses both legs; hem = 0 at the crotch, 1 at the
	## ankle.  The lower rings follow the hips and both thighs half each, so walking swings them.
	var torso: NpcBody.Part = parts.torso
	var top := _grow(_ring_at(torso.rings, top_f), e)
	var hip := _grow(_ring_at(torso.rings, 2.0), e + 0.004)
	var T: float = L.T
	var hem_y: float = lerpf(L.crotch, L.ankle_y, clampf(hem, -0.3, 1.0))
	var legs_w: float = L.leg_sep + L.thigh_r * 1.2
	var rs := [top]
	if top_f > 2.2:
		rs.append(hip)
	var n := 4
	var start_y: float = (rs[-1] as Dictionary).c.y
	for i in range(1, n + 1):
		var t := float(i) / n
		var y := lerpf(start_y, hem_y, t)
		var w := maxf(lerpf(hip.a, legs_w + e, t), hip.a) + flare * 0.12 * T * t * t
		var dd := maxf(lerpf(hip.b, L.thigh_r * 1.25 + e, t), hip.b * 0.95) + flare * 0.08 * T * t * t
		var wts := [["Hips", 1.0 - 0.6 * t], ["UpperLegL", 0.3 * t], ["UpperLegR", 0.3 * t]]
		rs.append(NpcBody.ring(Vector3(0, y, (hip.c as Vector3).z), Vector3.RIGHT, Vector3.BACK, w, dd, wts, 2.1))
	return NpcBody.loft(pname, rs, NpcBody.RING + 4, false, false)


static func _apron(def: Dictionary, parts: Dictionary, L: Dictionary, e: float) -> NpcBody.Part:
	## A front panel: the front arc (about 40% of the way round) of rings from the bib or waist down
	## to the hem, standing off the body.
	var torso: NpcBody.Part = parts.torso
	var top_f: float = def.top
	var hem_y: float = lerpf(L.crotch, L.ankle_y, float(def.hem))
	var rs := _range(torso.rings, top_f, 1.0, e)
	var last: Dictionary = rs[-1]
	var hang_w: float = maxf(last.a, L.hip_w * 1.0 + e)
	var hang_d: float = maxf(last.b, L.hip_d * 1.02 + e)
	for i in range(1, 4):
		var t := i / 3.0
		var y := lerpf((last.c as Vector3).y, hem_y, t)
		rs.append(NpcBody.ring(Vector3(0, y, (last.c as Vector3).z), Vector3.RIGHT, Vector3.BACK, hang_w, hang_d, [["Hips", 1.0 - 0.5 * t], ["UpperLegL", 0.25 * t], ["UpperLegR", 0.25 * t]], 2.2))
	return _front_panel("apron", rs, 0.3)


static func _front_panel(pname: String, rings: Array, frac: float) -> NpcBody.Part:
	## A loft over only the front arc (-frac/2 .. +frac/2 of the way round), made two-sided.
	var p := NpcBody.Part.new()
	p.name = pname
	p.rings = rings
	var cols := 9
	p.around = cols - 1
	var acc := 0.0
	for i in rings.size():
		if i > 0:
			acc += ((rings[i].c as Vector3) - (rings[i - 1].c as Vector3)).length()
		for k in cols:
			var t := fposmod(-frac * 0.5 + frac * k / (cols - 1.0), 1.0)
			p.verts.append(NpcBody.ring_point(rings[i], t))
			p.uvs.append(Vector2(k * 0.05, acc))
			p.uv2s.append(Vector2(-10, -10))
			NpcBody._push_weights(p, rings[i].w)
	for i in rings.size() - 1:
		for k in cols - 1:
			var a := i * cols + k
			var b := a + 1
			var c := a + cols
			var d := c + 1
			p.indices.append_array([a, c, b, b, c, d])
	NpcBody._orient_outward(p, rings, 0, p.indices.size())
	p.normals.resize(p.verts.size())
	var acc_n := {}
	for t in range(0, p.indices.size(), 3):
		var fn := (p.verts[p.indices[t + 1]] - p.verts[p.indices[t]]).cross(p.verts[p.indices[t + 2]] - p.verts[p.indices[t]])
		for j in 3:
			acc_n[p.indices[t + j]] = acc_n.get(p.indices[t + j], Vector3.ZERO) + fn
	for i in p.verts.size():
		p.normals[i] = (acc_n.get(i, Vector3.FORWARD) as Vector3).normalized()
	# back faces too (the panel is seen from behind at its edges)
	var n := p.indices.size()
	for t in range(0, n, 3):
		p.indices.append_array([p.indices[t], p.indices[t + 2], p.indices[t + 1]])
	return p


static func _shoes(def: Dictionary, parts: Dictionary, L: Dictionary, e: float) -> Array:
	var out := []
	var h: float = def.get("height", 0.0)
	for side in ["L", "R"]:
		var foot: NpcBody.Part = parts["foot" + side]
		var rs := _range(foot.rings, 0.0, foot.rings.size() - 1.0, e)
		# a sole: the rings' bottoms flattened onto the ground
		for r in rs:
			r.c = (r.c as Vector3) + Vector3(0, 0.002, 0)
		out.append(NpcBody.loft("shoe" + side, rs, NpcBody.LIMB, true, true))
		if h > 0.01:
			var leg: NpcBody.Part = parts["leg" + side]
			var n := leg.rings.size() - 1.0
			out.append(NpcBody.loft("boot" + side, _range(leg.rings, n, n - h * n * 0.6, e * 1.4), NpcBody.LIMB, false, false))
	return out


static func _headwear(def: Dictionary, parts: Dictionary, L: Dictionary) -> Array:
	var head: NpcBody.Part = parts.head
	var H: float = L.H
	var rs := head.rings
	var out := []
	var hair_room := 0.035 * H                                   # hats sit on hair
	match str(def.build):
		"cap":
			var tall: float = def.get("tall", 0.0)
			var crs := _range(rs, 7.6, rs.size() - 1.0, hair_room + 0.01 * H)
			for i in crs.size():
				var t := float(i) / (crs.size() - 1)
				crs[i].c = (crs[i].c as Vector3) + Vector3(0, tall * H * t, 0)
				if def.get("flat", false):
					crs[i].c = (crs[i].c as Vector3) + Vector3(0, 0, -0.06 * H * t)
			out.append(NpcBody.loft("cap", crs, NpcBody.HEAD_AROUND, false, true))
			var vis: float = def.get("visor", 0.0)
			if vis > 0.01:
				var r0: Dictionary = crs[0]
				var v := _grow(r0, 0.0)
				var v2 := _grow(r0, 0.0)
				v2.c = (r0.c as Vector3) + Vector3(0, -0.02 * H, -vis * 0.35 * H)
				v2.a = r0.a * 0.9
				v2.b = r0.b * 0.6
				out.append(_front_panel("visor", [v, v2], 0.36))
		"brim_hat":
			var crown: float = def.get("crown", 0.4)
			var crs := _range(rs, 7.6, rs.size() - 1.0, hair_room + 0.012 * H)
			for i in crs.size():
				crs[i].c = (crs[i].c as Vector3) + Vector3(0, crown * 0.3 * H * float(i) / (crs.size() - 1), 0)
			out.append(NpcBody.loft("crown", crs, NpcBody.HEAD_AROUND, false, true))
			var r0: Dictionary = crs[0]
			var brim := _grow(r0, float(def.get("brim", 0.3)) * H)
			brim.c = (r0.c as Vector3) - Vector3(0, 0.01 * H, 0)
			var inner := _grow(r0, 0.0)
			var brs := [inner, brim]
			var p := NpcBody.loft("brim", brs, NpcBody.HEAD_AROUND, false, false)
			var n := p.indices.size()                          # two-sided
			for t in range(0, n, 3):
				p.indices.append_array([p.indices[t], p.indices[t + 2], p.indices[t + 1]])
			out.append(p)
		"headscarf":
			var crs := _range(rs, 5.0, rs.size() - 1.0, hair_room + 0.008 * H)
			out.append(NpcBody.loft("scarf", crs, NpcBody.HEAD_AROUND, false, true))
	return out
