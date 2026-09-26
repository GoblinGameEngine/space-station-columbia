// The NYNEX Communicator's case, after the Apple Newton MessagePad: matte slate-grey plastic, lit
// from above -- a soft falloff down the face, fine grain, rounded edges that catch the light on top
// and fall into shade below -- the deep well the glass sits in (its upper wall in shadow, its lower
// lip lit), the glass strip under the screen the soft keys are printed on, the drilled speaker
// grille, the stylus silo along the left side, and a soft shadow under it all.
// Drawn over the device's rect grown by `margin` (for the shadow); positions are in the device's
// own pixels.
shader_type canvas_item;

uniform vec2 body_size = vec2(300.0, 480.0);
uniform float radius = 22.0;
uniform float k = 1.0;                       // the case's scale
uniform vec4 well = vec4(20.0, 50.0, 260.0, 360.0);     // x, y, w, h
uniform float well_radius = 6.0;
uniform vec4 strip = vec4(30.0, 380.0, 240.0, 30.0);    // the soft keys' glass
uniform vec4 grille = vec4(200.0, 12.0, 60.0, 24.0);
uniform vec4 silo = vec4(4.0, 120.0, 8.0, 240.0);
uniform float backlight = 0.0;

varying vec2 p;

const vec3 PLASTIC = vec3(0.205, 0.218, 0.226);
const vec3 DAY_BG = vec3(0.64, 0.71, 0.52);
const vec3 NIGHT_BG = vec3(0.45, 0.96, 0.64);

void vertex() {
	p = VERTEX;
}

float rrect(vec2 q, vec4 r, float rad) {
	vec2 c = r.xy + r.zw * 0.5;
	vec2 d = abs(q - c) - r.zw * 0.5 + rad;
	return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0) - rad;
}

vec2 rrect_normal(vec2 q, vec4 r, float rad) {
	float d0 = rrect(q, r, rad);
	return normalize(vec2(rrect(q + vec2(1.0, 0.0), r, rad) - d0, rrect(q + vec2(0.0, 1.0), r, rad) - d0) + 1e-6);
}

float hash(vec2 q) {
	return fract(sin(dot(q, vec2(12.9898, 78.233))) * 43758.5453);
}

void fragment() {
	vec4 body = vec4(0.0, 0.0, body_size);
	float d = rrect(p, body, radius);
	// the shadow under the device, a little below it
	float ds = rrect(p - vec2(0.0, 6.0 * k), body, radius);
	float shadow = 0.55 * (1.0 - smoothstep(-2.0 * k, 16.0 * k, ds));
	if (d > 0.5) {
		COLOR = vec4(0.0, 0.0, 0.0, shadow);
	} else {
		// the plastic: brighter toward the top, a broad soft sheen, fine grain
		float t = p.y / body_size.y;
		vec3 c = PLASTIC * (1.1 - 0.2 * t);
		c += vec3(0.02) * exp(-pow((p.x / body_size.x - 0.32) * 3.0, 2.0)) * (1.0 - t);
		c *= 0.985 + 0.03 * hash(floor(p));
		// the rounded edge: over its last few pixels it turns away -- toward the light on top
		float edge = clamp(-d / (7.0 * k), 0.0, 1.0);
		vec2 n = rrect_normal(p, body, radius);
		float facing = dot(n, normalize(vec2(-0.25, -1.0)));
		float roll = (1.0 - edge) * (1.0 - edge);
		c += roll * (max(facing, 0.0) * 0.16 - max(-facing, 0.0) * 0.1 - 0.03);
		c += vec3(0.12) * (1.0 - smoothstep(0.0, 1.2, -d)) * max(facing, 0.0);   // the rim catching light
		// the stylus silo down the left side: a groove, shadowed on its left wall, lit on its right
		float dsi = rrect(p, silo, silo.z * 0.5);
		if (dsi < 0.0) {
			float u = (p.x - silo.x) / silo.z;
			c = PLASTIC * mix(0.45, 1.05, smoothstep(0.1, 0.9, u)) * (1.0 - 0.15 * t);
		} else if (dsi < 1.2) {
			c *= 0.8;
		}
		// the speaker: drilled holes, each dark with a lit lower edge
		if (all(greaterThan(p, grille.xy)) && all(lessThan(p, grille.xy + grille.zw))) {
			float pitch = 7.0 * k;
			vec2 g = mod(p - grille.xy, pitch) - pitch * 0.5;
			float hole = length(g) - 1.7 * k;
			if (hole < 0.0) {
				c = mix(vec3(0.03), vec3(0.14), smoothstep(0.0, 1.7 * k, g.y) * 0.6);
			} else if (hole < 1.0) {
				c *= 0.85;
			}
		}
		// the well the glass sits in: its lip, then the dark frame, deepest under the top wall
		float dw = rrect(p, well, well_radius);
		if (dw < 0.0) {
			vec3 frame = vec3(0.065, 0.07, 0.072);
			float from_top = p.y - well.y;
			frame *= 0.6 + 0.4 * smoothstep(0.0, 7.0 * k, from_top);
			frame += vec3(0.05) * (1.0 - smoothstep(0.0, 3.0 * k, well.y + well.w - p.y));
			c = frame;
			// the soft keys' glass: the panel's own colour (lit at night like the screen), a touch dimmer
			float dg = rrect(p, strip, 2.0 * k);
			if (dg < 0.0) {
				c = mix(DAY_BG, NIGHT_BG, backlight) * 0.9;
				c *= 1.0 - 0.12 * (1.0 - smoothstep(0.0, 4.0 * k, p.y - strip.y));
			}
		} else if (dw < 2.5 * k) {
			// the lip round the well: its lower edge faces up and catches the light
			vec2 nw = rrect_normal(p, well, well_radius);
			c += (nw.y > 0.0 ? 0.07 : -0.05) * (1.0 - dw / (2.5 * k));
		}
		float a = clamp(0.5 - d, 0.0, 1.0);
		COLOR = vec4(mix(vec3(0.0), c, a), max(a, shadow));
	}
}
