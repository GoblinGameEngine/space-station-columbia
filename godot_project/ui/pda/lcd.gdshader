// The NYNEX Communicator's screen: a passive-matrix STN LCD of the mid-90s.  The System draws in 4
// greys; this maps them to 4 shades of dark ink on a green-grey panel, and the green
// electroluminescent backlight glow at night (backlight 0..1).
// Each LCD dot is drawn as a solid block px_scale screen pixels across.  At a whole-number scale
// that is exact; between whole numbers each block keeps its solid middle and blends with its
// neighbour over just one screen pixel at its edge ("sharp bilinear"), so type stays crisp at any
// size instead of dots coming out one and two pixels wide by turns.  The gaps between the dots show
// only when a dot is at least 3 screen pixels across.
shader_type canvas_item;

uniform vec2 screen_px = vec2(240.0, 320.0);    // the LCD's pixels
uniform float px_scale = 2.0;                    // screen pixels per LCD pixel
uniform float backlight = 0.0;

// panel (day, reflective) and backlit (night) palettes, darkest ink -> the bare panel
const vec3 DAY_INK = vec3(0.07, 0.10, 0.06);
const vec3 DAY_BG = vec3(0.64, 0.71, 0.52);
const vec3 NIGHT_INK = vec3(0.02, 0.08, 0.04);
const vec3 NIGHT_BG = vec3(0.45, 0.96, 0.64);

float level_at(sampler2D tex, vec2 dot) {
	// the 4-shade level of LCD dot `dot` (integer coordinates)
	dot = clamp(dot, vec2(0.0), screen_px - 1.0);
	float lum = dot(texture(tex, (dot + 0.5) / screen_px).rgb, vec3(0.299, 0.587, 0.114));
	return floor(lum * 3.0 + 0.5) / 3.0;
}

void fragment() {
	vec2 px = UV * screen_px;
	// sharp bilinear: flat across a dot, a one-screen-pixel ramp at its edge
	vec2 cell = fract(px);
	float edge = 0.5 - 0.5 / max(px_scale, 1.0);
	vec2 d = cell - 0.5;
	vec2 f = (d - clamp(d, -edge, edge)) * px_scale;      // -0.5..0.5 only within the edge pixel
	vec2 base = floor(px);
	vec2 other = base + sign(f);
	vec2 w = abs(f);
	float l00 = level_at(TEXTURE, base);
	float l10 = level_at(TEXTURE, vec2(other.x, base.y));
	float l01 = level_at(TEXTURE, vec2(base.x, other.y));
	float l11 = level_at(TEXTURE, other);
	float level = mix(mix(l00, l10, w.x), mix(l01, l11, w.x), w.y);
	vec3 ink = mix(DAY_INK, NIGHT_INK, backlight);
	vec3 bg = mix(DAY_BG, NIGHT_BG, backlight);
	vec3 c = mix(ink, bg, level);
	if (px_scale >= 3.0) {
		float g = 1.0 / px_scale;
		float gap = step(1.0 - g, cell.x) + step(1.0 - g, cell.y);
		c = mix(c, mix(c, bg, 0.3), clamp(gap, 0.0, 1.0) * (1.0 - l00));
	}
	// the reflective panel's slight shading, and the backlight's spread
	vec2 v = UV - 0.5;
	c *= 1.0 - dot(v, v) * mix(0.18, 0.3, backlight);
	COLOR = vec4(c, 1.0);
}
