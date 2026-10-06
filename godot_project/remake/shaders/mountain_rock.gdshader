shader_type spatial;
// The end caps' mountains (CapMountains; the user, 2026-10-06: "The texture is also wrong, it should be more natural like
// a mountain"). World-space (triplanar) rock at two scales -- the near one for the face's blocks and cracks, the far
// one so the repeat never lines up across a 1.5 km wall -- tinted by a macro colour field over hundreds of metres and by
// the mesh's vertex colours (the strata: CapMountains.tone). Benches and ledges that face the station's axis carry
// scrub and grass, thinning with height. No UVs: nothing stretches on the sheer faces.

uniform sampler2D rock_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D rock_far : source_color, filter_linear_mipmap, repeat_enable;      // (the same texture, plain mipmaps)
uniform sampler2D rock_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D macro_tint : source_color, filter_linear_mipmap, repeat_enable;
uniform float near_m = 60.0;
uniform float far_m = 260.0;
uniform float macro_m = 900.0;
uniform float station_r = 3000.0;
uniform float normal_strength = 0.8;
uniform float brightness = 2.3;

varying vec3 wp;
varying vec3 wn;

void vertex() {
	wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wn = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

// biplanar: the two strongest of the three projections only (Quilez) -- 2 samples, not 3. (One function per sampler:
// Godot won't pass samplers with different hints through one parameter.)
void bi_axes(vec3 n, out ivec3 ma, out ivec3 mi, out vec2 w) {
	vec3 an = abs(n);
	ma = (an.x > an.y && an.x > an.z) ? ivec3(0, 1, 2) : (an.y > an.z) ? ivec3(1, 2, 0) : ivec3(2, 0, 1);
	ivec3 me = (an.x < an.y && an.x < an.z) ? ivec3(0, 1, 2) : (an.y < an.z) ? ivec3(1, 2, 0) : ivec3(2, 0, 1);
	mi = ivec3(3) - me - ma;
	w = vec2(an[ma.x], an[mi.x]);
	w = clamp((w - 0.5773) / (1.0 - 0.5773), 0.0, 1.0);
	w = pow(w, vec2(4.0));
}

vec3 bi_rock(vec3 p, vec3 n) {
	ivec3 ma; ivec3 mi; vec2 w;
	bi_axes(n, ma, mi, w);
	vec3 x = texture(rock_albedo, vec2(p[ma.y], p[ma.z])).rgb;
	vec3 y = texture(rock_albedo, vec2(p[mi.y], p[mi.z])).rgb;
	return (x * w.x + y * w.y) / (w.x + w.y + 1e-4);
}

vec3 bi_normal(vec3 p, vec3 n) {
	ivec3 ma; ivec3 mi; vec2 w;
	bi_axes(n, ma, mi, w);
	vec3 x = texture(rock_normal, vec2(p[ma.y], p[ma.z])).rgb;
	vec3 y = texture(rock_normal, vec2(p[mi.y], p[mi.z])).rgb;
	return (x * w.x + y * w.y) / (w.x + w.y + 1e-4);
}

void fragment() {
	float dist = length(wp - CAMERA_POSITION_WORLD);
	float fd = smoothstep(300.0, 3000.0, dist);
	vec3 a_near = bi_rock(wp / near_m, wn);
	// the faces look along x (the caps): the far rock, the macro tint and the scrub patches on the yz plane, 1 sample each
	vec3 a_far = texture(rock_far, wp.yz / far_m + vec2(0.37, 0.73)).rgb;
	vec3 macro = texture(macro_tint, wp.yz / macro_m).rgb * 2.0;
	float patchy = texture(macro_tint, wp.yz / 110.0 + vec2(0.5)).g;
	vec3 rock = mix(a_near * mix(0.8, 1.2, dot(a_far, vec3(0.33))), a_far, 0.2 + 0.45 * fd);
	rock *= macro * COLOR.rgb * brightness;
	rock = mix(vec3(dot(rock, vec3(0.33))), rock, 1.15);                // (a little more colour)
	// the station's up here: toward the axis
	vec3 up = normalize(vec3(0.0, -wp.y, -wp.z) + vec3(1e-4));
	float facing_up = dot(wn, up);
	float hgt = station_r - length(wp.yz);                     // height above the floor (the caps' frame)
	float veg = smoothstep(0.55, 0.85, facing_up) * smoothstep(0.25, 0.6, patchy) * (1.0 - smoothstep(500.0, 1300.0, hgt));
	vec3 scrub = mix(vec3(0.30, 0.38, 0.20), vec3(0.46, 0.44, 0.28), patchy) * (0.85 + 0.4 * a_near.g);
	ALBEDO = mix(rock, scrub, veg);
	ROUGHNESS = 0.93;
	if (fd < 0.95) {                                           // (rock normals near only: no shimmer, no cost far off)
		vec3 nn = bi_normal(wp / near_m, wn) * 2.0 - 1.0;
		vec3 n = normalize(wn + normal_strength * (1.0 - fd) * vec3(nn.x * (1.0 - abs(wn.x)), nn.y, nn.x * abs(wn.x)));
		NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	}
}
