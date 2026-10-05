// vehicle_surface.gdshader -- the fleet's painted, moulded and upholstered surfaces (research/vehicles/TEXTURES.md):
// a generic tileable surface (tools/assets/surfaces.py) tinted by the palette colour, projected in the vehicle's own
// frame (object-space triplanar: no UVs; the texture rides with the vehicle), with dirt and wear layered over it:
//   grime  road dirt rising from the ground (the lower body, the sills, the wheels' spray) and in streaks under edges
//   dust   a film on the upward faces (roofs, hoods)
//   wear   the paint worn back to primer and bare metal along convex edges and panel seams -- the edge mask is baked
//          per vertex by the Blender pipeline (kit/components.py) and arrives as COLOR.r = 1 - wear
// Each vehicle sets its own `grime` (0 clean .. 1 filthy) and `wear` (instance uniforms), so a fleet isn't uniform.
shader_type spatial;
render_mode cull_disabled;

uniform vec4 tint : source_color = vec4(1.0);
uniform float roughness : hint_range(0.0, 1.0) = 0.5;
uniform float metallic : hint_range(0.0, 1.0) = 0.0;
uniform sampler2D surface_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D surface_rough : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D grime_mask : filter_linear_mipmap, repeat_enable;
uniform float tile = 0.6;                 // m per repeat of the surface
uniform float sharpness = 4.0;            // triplanar blend
uniform bool painted = true;              // wears to primer and metal (paint); else only darkens (plastic, rubber)
uniform vec3 dirt_color : source_color = vec3(0.32, 0.27, 0.21);
uniform vec3 dust_color : source_color = vec3(0.62, 0.58, 0.52);
uniform vec3 primer_color : source_color = vec3(0.55, 0.53, 0.50);
uniform vec3 metal_color : source_color = vec3(0.62, 0.62, 0.64);
uniform float dirt_height = 0.9;          // m: the road dirt fades out by this height above the ground

instance uniform float grime : hint_range(0.0, 1.0) = 0.3;
instance uniform float wear : hint_range(0.0, 1.0) = 0.3;

varying vec3 lp;                          // local position, local normal (after the frame's skinning: dents carry it)
varying vec3 ln;
varying float edge;

void vertex() {
	lp = VERTEX;
	ln = NORMAL;
	edge = 1.0 - COLOR.r;
}

// (one per texture: Godot won't pass samplers of different hints through one function)
vec4 tri_albedo(vec3 p, vec3 w) {
	return texture(surface_albedo, p.zy) * w.x + texture(surface_albedo, p.xz) * w.y + texture(surface_albedo, p.xy) * w.z;
}
vec4 tri_rough(vec3 p, vec3 w) {
	return texture(surface_rough, p.zy) * w.x + texture(surface_rough, p.xz) * w.y + texture(surface_rough, p.xy) * w.z;
}
vec4 tri_grime(vec3 p, vec3 w) {
	return texture(grime_mask, p.zy) * w.x + texture(grime_mask, p.xz) * w.y + texture(grime_mask, p.xy) * w.z;
}

void fragment() {
	vec3 w = pow(abs(normalize(ln)), vec3(sharpness));
	w /= (w.x + w.y + w.z);
	vec3 p = lp / tile;
	vec3 base = tri_albedo(p, w).rgb * tint.rgb;
	float rough = clamp(roughness * tri_rough(p, w).r * 1.0, 0.03, 1.0);
	float metal = metallic;
	// the grime field: big soft splotches with drips, at its own scale
	float g = tri_grime(lp / 1.6, w).r;
	float g2 = tri_grime(lp / 0.45 + vec3(3.1, 7.7, 1.3), w).r;
	// road dirt: from the ground up, ragged at its top, heavier where the grime field says
	float low = 1.0 - smoothstep(0.0, dirt_height * (0.6 + 0.8 * g), lp.y);
	float dirt = clamp(low * (0.35 + 0.65 * g) * grime * 1.6, 0.0, 0.85);
	// dust on what faces up
	float up = smoothstep(0.55, 0.95, normalize(ln).y);
	float dust = up * grime * 0.45 * (0.5 + 0.5 * g2);
	// wear: chips along sharp convex edges only (a low-poly panel's vertices nearly all sit on its seams, and wear
	// spread across them greyed whole panels), broken up by a fine noise so it flecks rather than outlines
	float chips = smoothstep(0.42, 0.72, tri_grime(lp / 0.12 + vec3(5.3, 1.1, 9.7), w).r);
	float wm = smoothstep(0.62, 0.95, edge) * chips * clamp(wear * 1.6, 0.0, 1.0);
	if (painted) {
		vec3 worn = mix(primer_color, metal_color, smoothstep(0.6, 0.95, wm));
		base = mix(base, worn, smoothstep(0.25, 0.6, wm));
		metal = mix(metal, 0.6, smoothstep(0.7, 1.0, wm));
		rough = mix(rough, 0.45, smoothstep(0.7, 1.0, wm));
	} else {
		base *= 1.0 - 0.25 * wm;                  // (scuffed: a moulding or a tyre goes darker at its edges)
		rough = mix(rough, 1.0, 0.5 * wm);
	}
	base = mix(base, dust_color, dust);
	base = mix(base, dirt_color, dirt);
	rough = mix(rough, 0.95, max(dirt, dust));
	ALBEDO = base;
	ROUGHNESS = rough;
	METALLIC = metal * (1.0 - dirt);
}
