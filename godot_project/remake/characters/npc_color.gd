extends RefCounted
class_name NpcColor

## Colours for generated people: the measured Ghibli shade rule and the skin / hair / eye ramps
## that the colour traits (2D "colour genes", as in CK3) point into.
##
## Shade rule, measured on 29 lit/shade paint pairs across 7 films (ghibli_style.md 2.3,
## research/characters/data/shade_pairs.csv): in daylight a cel shadow is the same paint with
## L* about -13, chroma a little up, hue kept; skin also a little redder and less yellow.
## Shadows are shallow -- 15-25% darker in value.

const SKIN_RAMP := [   # light -> dark lit skin tones (the first four sampled from the films)
	Color("#f0d3b8"), Color("#ecc6a3"), Color("#dfb99c"), Color("#d4a987"),
	Color("#c09172"), Color("#a67556"), Color("#875a3f"), Color("#694330"), Color("#4f3226")]
const HAIR_DARK_LIGHT := [
	Color("#1d1a22"), Color("#2c2226"), Color("#3f2b24"), Color("#5a3b2a"),
	Color("#7c5436"), Color("#a07a4e"), Color("#c6a36e"), Color("#dcc28e")]
const HAIR_RED := Color("#8e4228")
const HAIR_GREY := Color("#b9b5ad")
const HAIR_WHITE := Color("#e6e2d8")
const EYES := [Color("#2a211f"), Color("#3b2a22"), Color("#4a3a2c"), Color("#34403f"), Color("#3c4c5c"), Color("#5a6b72")]


static func ramp(stops: Array, t: float) -> Color:
	t = clampf(t, 0.0, 1.0) * (stops.size() - 1)
	var i := mini(int(t), stops.size() - 2)
	return (stops[i] as Color).lerp(stops[i + 1], t - i)


static func skin(gene: Array) -> Color:
	## gene = [light..dark, cool..warm undertone]
	var c := ramp(SKIN_RAMP, float(gene[0]))
	var lab := to_lab(c)
	var u := float(gene[1]) - 0.5
	lab.y += 4.0 * u              # warmer: redder
	lab.z += 5.0 * u              # and yellower
	return from_lab(lab)


static func hair(gene: Array, grey: float) -> Color:
	## gene = [dark..light, ash..red]; grey 0..1 from hair_grey.
	var c := ramp(HAIR_DARK_LIGHT, float(gene[0]))
	var red := clampf((float(gene[1]) - 0.6) / 0.4, 0.0, 1.0) * clampf(float(gene[0]) * 2.0, 0.0, 1.0)
	c = c.lerp(HAIR_RED, red * 0.55)
	return c.lerp(HAIR_GREY.lerp(HAIR_WHITE, grey), smoothstep(0.1, 1.0, grey) * 0.95)


static func eyes(gene: Array) -> Color:
	return ramp(EYES, float(gene[0]) * 0.6 + float(gene[1]) * 0.4)


static func shade(lit: Color, is_skin := false) -> Color:
	## The cel shadow colour of a paint, by the measured rule.
	var lab := to_lab(lit)
	var chroma := sqrt(lab.y * lab.y + lab.z * lab.z)
	var f := 1.12 if chroma > 1.0 else 1.0
	lab.x -= 13.0 if is_skin else 12.5
	lab.y *= f
	lab.z *= f
	if is_skin:
		lab.y += 2.0
		lab.z -= 2.8
	elif chroma < 8.0 and lab.x > 70.0:
		lab.z -= 1.4          # near-white fabric: a slightly cool grey in shadow
	return from_lab(lab)


# -- sRGB <-> CIE Lab (D65) -------------------------------------------------------------------------

static func _lin(c: float) -> float:
	return pow((c + 0.055) / 1.055, 2.4) if c > 0.04045 else c / 12.92


static func _gam(c: float) -> float:
	return 1.055 * pow(maxf(c, 0.0), 1.0 / 2.4) - 0.055 if c > 0.0031308 else 12.92 * c


static func _f(t: float) -> float:
	return pow(t, 1.0 / 3.0) if t > 0.008856 else 7.787 * t + 16.0 / 116.0


static func _finv(t: float) -> float:
	return t * t * t if t > 0.2069 else (t - 16.0 / 116.0) / 7.787


static func to_lab(c: Color) -> Vector3:
	var r := _lin(c.r)
	var g := _lin(c.g)
	var b := _lin(c.b)
	var x := (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
	var y := 0.2126 * r + 0.7152 * g + 0.0722 * b
	var z := (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
	var fx := _f(x)
	var fy := _f(y)
	var fz := _f(z)
	return Vector3(116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


static func from_lab(lab: Vector3) -> Color:
	var fy := (lab.x + 16.0) / 116.0
	var x := _finv(fy + lab.y / 500.0) * 0.95047
	var y := _finv(fy)
	var z := _finv(fy - lab.z / 200.0) * 1.08883
	var r := 3.2406 * x - 1.5372 * y - 0.4986 * z
	var g := -0.9689 * x + 1.8758 * y + 0.0415 * z
	var b := 0.0557 * x - 0.2040 * y + 1.0570 * z
	return Color(clampf(_gam(r), 0, 1), clampf(_gam(g), 0, 1), clampf(_gam(b), 0, 1))
