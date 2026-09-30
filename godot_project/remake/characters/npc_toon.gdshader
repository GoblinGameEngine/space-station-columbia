shader_type spatial;
// Generated people: two flat cel tones from the scene's sun (and its shadows), the shadow tone
// being the paint's own measured shade colour (NpcColor.shade, ghibli_style.md 2.3), plus the face
// drawn procedurally where the head mesh carries face coordinates in UV2 (x, y in head heights,
// origin between the eyes; UV2 = -10 elsewhere).  Outlines come from the screen-space outline pass
// (ScreenOutline), not from this shader.
render_mode specular_disabled, cull_disabled;   // garments are open at hems and cuffs: their insides show

uniform vec3 lit_color : source_color = vec3(0.9, 0.78, 0.68);
uniform vec3 shade_mul = vec3(0.8, 0.75, 0.72);    // shade / lit, linear, per channel
uniform float threshold = 0.05;                     // N.L where the shadow edge sits
uniform float softness = 0.02;                      // half-width of the edge (cel paint: hard)

// face (only drawn where UV2.x > -5)
uniform vec3 eye_color : source_color = vec3(0.2, 0.15, 0.13);
uniform vec3 line_color : source_color = vec3(0.18, 0.11, 0.1);
uniform vec3 brow_color : source_color = vec3(0.2, 0.14, 0.12);
uniform vec3 mouth_color : source_color = vec3(0.55, 0.28, 0.25);
uniform vec3 blush_color : source_color = vec3(0.92, 0.55, 0.5);
uniform float eye_size = 0.0;        // -1..1
uniform float eye_spacing = 0.0;     // -1..1
uniform float mouth_width = 0.0;     // -1..1
uniform float brow_thick = 0.5;      // 0..1
uniform float brow_arch = 0.3;       // 0..1
uniform float brow_height = 0.0;     // -1..1
uniform float blush = 0.5;           // 0..1
uniform float freckles = 0.0;        // 0 or 1
uniform float age_lines = 0.0;       // 0..1
uniform float glasses = 0.0;         // 0 or 1
uniform vec2 gaze = vec2(0.0);       // pupils' offset, -1..1 of their travel (the animator's eyes)
uniform float blink = 0.0;           // 0 open .. 1 closed
uniform float mouth_open = 0.0;      // 0 closed .. 1 open (speech)
uniform float smile = 0.0;           // -1 frown .. 1 smile (the mouth line's curve)
uniform int debug_view = 0;          // 1: show UV2

// fabric (UV in metres: u round the garment from the front, v along it)
uniform int pattern = 0;   // 0 solid 1 stripes 2 pinstripe 3 check 4 tartan 5 dots 6 floral 7 knit 8 denim 9 pleats 10 weave 11 herring
uniform vec3 col2 : source_color = vec3(0.9, 0.87, 0.8);
uniform vec3 col3 : source_color = vec3(0.3, 0.3, 0.35);
uniform float pat_scale = 1.0;

float ellipse(vec2 p, vec2 c, vec2 r) {
	vec2 d = (p - c) / r;
	return dot(d, d);
}

float aa(float d, float w) {             // 1 inside (d < 0), antialiased by screen derivative
	return clamp(0.5 - d / max(w, 1e-5), 0.0, 1.0);
}

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

vec3 face(vec2 p, vec3 base) {
	vec3 col = base;
	float fw = fwidth(p.x) * 1.5;
	float ax = abs(p.x);
	// blush: hatched strokes in a soft oval under each eye
	float bo = ellipse(vec2(ax, p.y), vec2(0.16, -0.09), vec2(0.075, 0.035));
	float hatch = step(0.55, fract((p.x * 1.0 - p.y * 0.6) * 90.0));
	col = mix(col, blush_color, blush * 0.55 * hatch * smoothstep(1.0, 0.5, bo));
	// freckles
	if (freckles > 0.5) {
		vec2 g = floor(p * 60.0);
		float fr = step(0.82, hash(g)) * step(ellipse(vec2(ax, p.y), vec2(0.13, -0.08), vec2(0.1, 0.05)), 1.0);
		col = mix(col, base * 0.78, fr * 0.8);
	}
	// eyes
	float ex = 0.135 + 0.02 * eye_spacing;
	vec2 er = vec2(0.056, 0.074) * (1.0 + 0.2 * eye_size);
	vec2 q = vec2(ax, p.y);
	float white = ellipse(q, vec2(ex, 0.0), er);
	// gaze: the iris moves within the eye (x mirrored per side: q uses |x|)
	vec2 g = vec2(gaze.x * sign(p.x), gaze.y) * er * vec2(0.32, 0.25);
	float iris = ellipse(q, vec2(ex - 0.004, -0.004) + g, vec2(er.x * 0.72, er.y * 0.84));
	float pupil = ellipse(q, vec2(ex - 0.004, -0.004) + g, vec2(er.x * 0.36, er.y * 0.44));
	float hl = ellipse(q, vec2(ex + 0.01, 0.022) + g * 0.6, vec2(er.x * 0.2, er.y * 0.18));
	col = mix(col, vec3(0.96, 0.94, 0.9), aa((white - 1.0) * er.x, fw));
	col = mix(col, eye_color, aa((iris - 1.0) * er.x * 0.7, fw) * step(white, 1.0));
	col = mix(col, eye_color * 0.35, aa((pupil - 1.0) * er.x * 0.35, fw));
	col = mix(col, vec3(1.0), aa((hl - 1.0) * er.x * 0.2, fw * 0.5));
	// upper lid: a thick line on the top of the eye; a blink brings it down over the eye (skin
	// above the lid line, the line itself travelling down)
	float lid_y = er.y * (1.0 - 2.1 * blink);
	float lidded = step(white, 1.0) * step(lid_y, p.y);
	col = mix(col, base, lidded * step(0.02, blink));
	float lid = abs(sqrt(white) - 1.0) * er.x;
	float top = step(-0.01, p.y - 0.0 + 0.012);
	col = mix(col, line_color, aa(lid - 0.006, fw) * top * step(white, 1.6) * step(blink, 0.5));
	col = mix(col, line_color, aa(abs(p.y - lid_y) - 0.005, fw) * step(white, 1.05) * step(0.02, blink));
	// brows
	float by = 0.11 + 0.012 * brow_height;
	float bx = ax - ex;
	float arch = by + brow_arch * 0.02 * (1.0 - (bx / 0.06) * (bx / 0.06));
	float bt = 0.009 + 0.012 * brow_thick;
	float brow = abs(p.y - arch) - bt * (1.0 - smoothstep(0.03, 0.07, abs(bx)));
	col = mix(col, brow_color, aa(brow, fw) * step(abs(bx), 0.07));
	// age lines: crow's feet and nasolabial hints
	if (age_lines > 0.05) {
		float cf = abs(fract((p.y + 0.02) * 70.0) - 0.5) * 2.0;
		float cfz = step(ex + er.x + 0.005, ax) * step(ax, ex + er.x + 0.03) * step(abs(p.y), 0.03);
		col = mix(col, base * 0.8, age_lines * cfz * step(0.8, cf));
		float nl = abs(ax - (0.07 + (-p.y - 0.14) * 0.35)) ;
		col = mix(col, base * 0.82, age_lines * 0.8 * aa(nl - 0.003, fw) * step(-0.26, p.y) * step(p.y, -0.14));
	}
	// mouth: a short line, slightly curved
	float mw = 0.045 * (1.0 + 0.3 * mouth_width);
	float my = -0.215 + (0.01 + 0.018 * smile) * (p.x / mw) * (p.x / mw);
	float mouth = abs(p.y - my) - 0.0035;
	col = mix(col, mouth_color, aa(mouth, fw) * step(ax, mw) * step(mouth_open, 0.05));
	if (mouth_open > 0.05) {                                  // speaking: the mouth opens as a soft oval
		float mo = ellipse(p, vec2(0.0, -0.22), vec2(mw * 0.75, 0.006 + 0.026 * mouth_open));
		col = mix(col, mouth_color * 0.55, aa((sqrt(mo) - 1.0) * 0.02, fw));
	}
	// glasses: round rims
	if (glasses > 0.5) {
		float rim = abs(sqrt(ellipse(q, vec2(ex, -0.005), vec2(0.075, 0.07))) - 1.0) * 0.075;
		col = mix(col, line_color, aa(rim - 0.004, fw));
		float bridge = abs(p.y - 0.01) - 0.003;
		col = mix(col, line_color, aa(bridge, fw) * step(ax, ex - 0.07));
	}
	return col;
}

float band(float x, float period, float width, float fw) {
	// 1 inside a band of the given width (fraction of the period), antialiased
	float f = abs(fract(x / period) - 0.5) * 2.0;           // 0 at band centre .. 1 between
	return clamp((width - f) / max(fw / period * 2.0, 1e-4) + 0.5, 0.0, 1.0);
}

vec3 fabric(vec2 uv, vec3 base) {
	float s = pat_scale;
	vec2 fw = fwidth(uv);
	float fwm = max(fw.x, fw.y);
	if (pattern == 1) {                                     // stripes round the body
		return mix(base, col2, band(uv.y, 0.045 * s, 0.45, fw.y));
	} else if (pattern == 2) {                              // pinstripe
		return mix(base, col2, band(uv.x, 0.022 * s, 0.1, fw.x) * 0.8);
	} else if (pattern == 3) {                              // gingham check
		float a = band(uv.x, 0.03 * s, 0.5, fw.x);
		float b = band(uv.y, 0.03 * s, 0.5, fw.y);
		return mix(base, col2, (a + b) * 0.45);
	} else if (pattern == 4) {                              // tartan: wide and narrow sets, both ways
		float p = 0.09 * s;
		float w1 = max(band(uv.x, p, 0.35, fw.x), band(uv.y, p, 0.35, fw.y));
		float w2 = max(band(uv.x + p * 0.5, p, 0.08, fw.x), band(uv.y + p * 0.5, p, 0.08, fw.y));
		return mix(mix(base, col2, w1 * 0.6), col3, w2 * 0.8);
	} else if (pattern == 5) {                              // dots
		vec2 g = uv / (0.035 * s);
		vec2 q = fract(g + vec2(0.5 * mod(floor(g.y), 2.0), 0.0)) - 0.5;
		return mix(base, col2, clamp((0.22 - length(q)) / (fwm / (0.035 * s)) + 0.5, 0.0, 1.0));
	} else if (pattern == 6) {                              // small five-petal flowers
		vec2 g = uv / (0.05 * s);
		vec2 id = floor(g);
		vec2 q = fract(g) - 0.5 + (vec2(hash(id), hash(id + 7.0)) - 0.5) * 0.3;
		float ang = atan(q.y, q.x) + hash(id) * 6.28;
		float r = length(q);
		float petal = 0.2 + 0.08 * cos(ang * 5.0);
		vec3 c = mix(base, col2, clamp((petal - r) / (fwm / (0.05 * s)) + 0.5, 0.0, 1.0));
		return mix(c, col3, clamp((0.06 - r) / (fwm / (0.05 * s)) + 0.5, 0.0, 1.0));
	} else if (pattern == 7) {                              // knit rib: faint vertical ridges
		return base * (0.94 + 0.06 * band(uv.x, 0.012 * s, 0.5, fw.x));
	} else if (pattern == 8) {                              // denim twill
		return base * (0.93 + 0.07 * band(uv.x + uv.y, 0.006, 0.5, fwm));
	} else if (pattern == 9) {                              // pleats: fold lines
		return mix(base, base * 0.78, band(uv.x, 0.045 * s, 0.07, fw.x));
	} else if (pattern == 10) {                             // straw weave
		float a = band(uv.x + uv.y, 0.012, 0.3, fwm);
		float b = band(uv.x - uv.y, 0.012, 0.3, fwm);
		return base * (1.0 - 0.1 * max(a, b));
	} else if (pattern == 11) {                             // herringbone
		float col = floor(uv.x / (0.02 * s));
		float dir = mod(col, 2.0) * 2.0 - 1.0;
		return base * (0.93 + 0.07 * band(uv.y + dir * uv.x, 0.012, 0.5, fwm));
	}
	return base;
}

void fragment() {
	vec3 c = lit_color;
	if (pattern > 0) {
		c = fabric(UV, lit_color);
	}
	if (UV2.x > -5.0) {
		c = face(UV2, lit_color);
	}
	ALBEDO = FRONT_FACING ? c : c * 0.55;                  // the inside of a garment reads darker
	if (debug_view == 1) {
		ALBEDO = UV2.x > -5.0 ? vec3(fract(UV2 * 5.0), 0.0) : vec3(0.0, 0.0, 1.0);
	}
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
}

void light() {
	float ndl = dot(NORMAL, LIGHT);   // (the insides of garments get the lit-side rule; darkened above)
	float t = smoothstep(threshold - softness, threshold + softness, ndl) * ATTENUATION;
	// two flat tones: full light where lit, the paint's shade ratio where not
	DIFFUSE_LIGHT += LIGHT_COLOR / PI * mix(shade_mul, vec3(1.0), t) * 0.9;
}
