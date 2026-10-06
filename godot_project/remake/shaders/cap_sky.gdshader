shader_type spatial;
// The end caps' sky (the user, 2026-10-06: "The sky behind it needs to have a moving cloud texture that mimics a sky
// when viewed from far. The clouds will circle the axis."). The disc round the central shaft, inside the mountains'
// crest: the sky's own colour (DaySkySystem sets the global sky_color with the shaft's), a soft haze toward the rim,
// and two cloud layers seen from far away -- broad cumulus fields and long cirrus streaks -- turning about the
// station's axis (the cirrus a little faster: depth). Procedural noise in the disc's polar frame: no seams, no tiles.
render_mode unshaded, cull_disabled;

global uniform vec4 sky_color;
global uniform float daylight;
uniform float r_in = 100.0;          // the shaft's radius
uniform float r_rim = 1700.0;        // the disc's rim (StationGeo.R - 1300)
uniform float spin = 0.0035;         // rad/s round the axis (~6 m/s at the rim)

varying vec3 wpos;

void vertex() {
	wpos = VERTEX;
}

float hash(vec2 p) {
	p = fract(p * vec2(123.34, 456.21));
	p += dot(p, p + 45.32);
	return fract(p.x * p.y);
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = hash(i);
	float b = hash(i + vec2(1.0, 0.0));
	float c = hash(i + vec2(0.0, 1.0));
	float d = hash(i + vec2(1.0, 1.0));
	return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p, int oct) {
	float s = 0.0;
	float a = 0.5;
	for (int i = 0; i < oct; i++) {
		s += a * vnoise(p);
		p = mat2(vec2(1.6, 1.2), vec2(-1.2, 1.6)) * p;
		a *= 0.5;
	}
	return s;
}

void fragment() {
	vec2 yz = wpos.yz;
	float r = length(yz);
	float th = atan(yz.y, yz.x);
	float rim = smoothstep(r_in, r_rim, r);
	// the sky: deeper toward the axis, a pale haze toward the rim (looking across km of air)
	vec3 sky = sky_color.rgb * mix(0.86, 1.08, rim);
	sky = mix(sky, sky_color.rgb * 1.25 + vec3(0.04), smoothstep(0.75, 1.0, rim) * 0.5);
	// cumulus fields: turning about the axis
	float a1 = th - TIME * spin;
	vec2 p1 = vec2(cos(a1), sin(a1)) * r / 650.0;
	float n1 = fbm(p1 + vec2(13.1, 7.7), 4);
	float cum = smoothstep(0.50, 0.72, n1);
	float body = smoothstep(0.50, 0.95, n1);                       // thicker cores, lit tops
	// cirrus: long streaks along the turn (periodic round the axis), a little faster
	float a2 = th - TIME * spin * 1.6;
	vec2 p2 = vec2(cos(a2), sin(a2)) * 5.0 + vec2(r / 140.0, r / 260.0);
	float n2 = fbm(p2 + vec2(3.3, 1.9), 3);
	float cir = smoothstep(0.55, 0.78, n2) * (0.5 + 0.5 * rim);
	// cloud colour by the light: white by day, the sky's own blue-grey at night, warmed at dawn and dusk
	vec3 day_c = vec3(0.98, 0.97, 0.95) * mix(0.78, 1.0, body);
	vec3 night_c = sky_color.rgb * 1.7 + vec3(0.03, 0.03, 0.04);
	vec3 c = mix(night_c, day_c, daylight);
	vec3 warm = clamp(sky_color.rgb / max(max(sky_color.r, sky_color.g), max(sky_color.b, 0.001)), 0.0, 1.0);
	c *= mix(vec3(1.0), warm * 0.4 + 0.6, 0.35 * (1.0 - abs(daylight * 2.0 - 1.0)));
	vec3 col = mix(sky, c, clamp(cum * 0.92, 0.0, 1.0));
	col = mix(col, c * 1.02, cir * 0.35 * (1.0 - cum));
	ALBEDO = col;
}
