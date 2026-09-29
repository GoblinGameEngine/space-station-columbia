shader_type spatial;
// Generated people: two flat cel tones from the scene's sun (and its shadows), the shadow tone
// being the paint's own measured shade colour (NpcColor.shade, ghibli_style.md 2.3), plus the face
// drawn procedurally where the head mesh carries face coordinates in UV2 (x, y in head heights,
// origin between the eyes; UV2 = -10 elsewhere).  Outlines come from the screen-space outline pass
// (ScreenOutline), not from this shader.
render_mode specular_disabled;

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
uniform int debug_view = 0;          // 1: show UV2

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
	float iris = ellipse(q, vec2(ex - 0.004, -0.004), vec2(er.x * 0.72, er.y * 0.84));
	float pupil = ellipse(q, vec2(ex - 0.004, -0.004), vec2(er.x * 0.36, er.y * 0.44));
	float hl = ellipse(q, vec2(ex + 0.012 * sign(p.x) * 0.0 + 0.01, 0.022), vec2(er.x * 0.2, er.y * 0.18));
	col = mix(col, vec3(0.96, 0.94, 0.9), aa((white - 1.0) * er.x, fw));
	col = mix(col, eye_color, aa((iris - 1.0) * er.x * 0.7, fw) * step(white, 1.0));
	col = mix(col, eye_color * 0.35, aa((pupil - 1.0) * er.x * 0.35, fw));
	col = mix(col, vec3(1.0), aa((hl - 1.0) * er.x * 0.2, fw * 0.5));
	// upper lid: a thick line on the top of the eye
	float lid = abs(sqrt(white) - 1.0) * er.x;
	float top = step(-0.01, p.y - 0.0 + 0.012);
	col = mix(col, line_color, aa(lid - 0.006, fw) * top * step(white, 1.6));
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
	float my = -0.215 + 0.01 * (p.x / mw) * (p.x / mw);
	float mouth = abs(p.y - my) - 0.0035;
	col = mix(col, mouth_color, aa(mouth, fw) * step(ax, mw));
	// glasses: round rims
	if (glasses > 0.5) {
		float rim = abs(sqrt(ellipse(q, vec2(ex, -0.005), vec2(0.075, 0.07))) - 1.0) * 0.075;
		col = mix(col, line_color, aa(rim - 0.004, fw));
		float bridge = abs(p.y - 0.01) - 0.003;
		col = mix(col, line_color, aa(bridge, fw) * step(ax, ex - 0.07));
	}
	return col;
}

void fragment() {
	vec3 c = lit_color;
	if (UV2.x > -5.0) {
		c = face(UV2, lit_color);
	}
	ALBEDO = c;
	if (debug_view == 1) {
		ALBEDO = UV2.x > -5.0 ? vec3(fract(UV2 * 5.0), 0.0) : vec3(0.0, 0.0, 1.0);
	}
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
}

void light() {
	float ndl = dot(NORMAL, LIGHT);
	float t = smoothstep(threshold - softness, threshold + softness, ndl) * ATTENUATION;
	// two flat tones: full light where lit, the paint's shade ratio where not
	DIFFUSE_LIGHT += LIGHT_COLOR / PI * mix(shade_mul, vec3(1.0), t) * 0.9;
}
