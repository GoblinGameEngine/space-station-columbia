// The NYNEX Communicator's screen: a passive-matrix STN LCD of the mid-90s.  The System draws in 4
// greys; this maps them to 4 shades of dark ink on a green-grey panel, and the green
// electroluminescent backlight glow at night (backlight 0..1).  Each LCD pixel is drawn as a whole
// block of px_scale x px_scale screen pixels (GameMenu sizes it so), sampled once at its centre:
// type stays crisp.  The gaps between the dots show only when a dot is at least 3 screen pixels
// across -- thinner than that they would only smear the letters.
shader_type canvas_item;

uniform vec2 screen_px = vec2(240.0, 320.0);    // the LCD's pixels
uniform float px_scale = 2.0;                    // screen pixels per LCD pixel
uniform float backlight = 0.0;

// panel (day, reflective) and backlit (night) palettes, darkest ink -> the bare panel
const vec3 DAY_INK = vec3(0.07, 0.10, 0.06);
const vec3 DAY_BG = vec3(0.64, 0.71, 0.52);
const vec3 NIGHT_INK = vec3(0.02, 0.08, 0.04);
const vec3 NIGHT_BG = vec3(0.45, 0.96, 0.64);

void fragment() {
	vec2 px = UV * screen_px;
	vec2 cell = fract(px);
	vec2 centre = (floor(px) + 0.5) / screen_px;
	float lum = dot(texture(TEXTURE, centre).rgb, vec3(0.299, 0.587, 0.114));
	float level = floor(lum * 3.0 + 0.5) / 3.0;          // 4 shades
	vec3 ink = mix(DAY_INK, NIGHT_INK, backlight);
	vec3 bg = mix(DAY_BG, NIGHT_BG, backlight);
	vec3 c = mix(ink, bg, level);
	if (px_scale >= 3.0) {
		// one screen pixel of gap on the dot's right and bottom edges
		float g = 1.0 / px_scale;
		float gap = step(1.0 - g, cell.x) + step(1.0 - g, cell.y);
		c = mix(c, mix(c, bg, 0.3), clamp(gap, 0.0, 1.0) * (1.0 - level));
	}
	// the reflective panel's slight shading, and the backlight's spread
	vec2 v = UV - 0.5;
	c *= 1.0 - dot(v, v) * mix(0.18, 0.3, backlight);
	COLOR = vec4(c, 1.0);
}
