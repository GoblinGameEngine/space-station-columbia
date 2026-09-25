// The NYNEX Communicator's screen: a passive-matrix STN LCD of the mid-90s.  The System draws in 4
// greys (Windows CE 1.0's 2 bits a pixel); this maps them to 4 shades of dark ink on a green-grey
// panel, draws the gaps between the dots (the dot matrix), a faint ghost of the neighbouring pixel
// (slow LCD response), and the green electroluminescent backlight glow at night (backlight 0..1).
shader_type canvas_item;

uniform vec2 screen_px = vec2(240.0, 320.0);    // the LCD's pixels
uniform float backlight = 0.0;
uniform float dot_gap = 0.14;                    // share of a pixel that's the gap between dots

// panel (day, reflective) and backlit (night) palettes, darkest ink -> the bare panel
const vec3 DAY_INK = vec3(0.09, 0.12, 0.07);
const vec3 DAY_BG = vec3(0.60, 0.67, 0.49);
const vec3 NIGHT_INK = vec3(0.03, 0.09, 0.05);
const vec3 NIGHT_BG = vec3(0.42, 0.95, 0.62);

void fragment() {
	vec2 px = UV * screen_px;
	vec2 cell = fract(px);
	vec2 centre = (floor(px) + 0.5) / screen_px;
	float lum = dot(texture(TEXTURE, centre).rgb, vec3(0.299, 0.587, 0.114));
	float ghost = dot(texture(TEXTURE, centre - vec2(1.0 / screen_px.x, 0.0)).rgb, vec3(0.299, 0.587, 0.114));
	lum = mix(lum, ghost, 0.12);
	float level = floor(lum * 3.0 + 0.5) / 3.0;          // 4 shades
	vec3 ink = mix(DAY_INK, NIGHT_INK, backlight);
	vec3 bg = mix(DAY_BG, NIGHT_BG, backlight);
	vec3 c = mix(ink, bg, level);
	// the gaps between dots show the bare panel, a little darker than a lit dot
	float edge = step(dot_gap * 0.5, cell.x) * step(cell.x, 1.0 - dot_gap * 0.5)
		* step(dot_gap * 0.5, cell.y) * step(cell.y, 1.0 - dot_gap * 0.5);
	// dark dots show the gaps between them; the bare panel doesn't
	vec3 gap = mix(c, bg, 0.35);
	c = mix(gap, c, mix(1.0, edge, (1.0 - level) * 0.6));
	// a soft vignette of the backlight panel and the reflective panel's slight shading
	vec2 v = UV - 0.5;
	c *= 1.0 - dot(v, v) * mix(0.35, 0.55, backlight);
	COLOR = vec4(c, 1.0);
}
