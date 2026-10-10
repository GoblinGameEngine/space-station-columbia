// The terrain's coarse far tier.  Beyond flat_arc of arc round the ring from the player it is
// the far side of the cylinder, drawn flat: the baked top-down image of the finished world
// (remake/farside/f_SS_XX.webp, one per far tile: UV2 is map metres, tile_rect where this tile's image lies) -- roofs, roads, fields, trees and water as surface colour, lit
// by the station's sun like everything else.  Nearer, the ordinary ground: land cover per pixel
// (or the vertex colour where it says so, alpha 1) on the neutral detail texture.  The switch is per pixel, so it lands exactly where the
// far side's objects are hidden (RemakeFarSide).
shader_type spatial;
render_mode cull_back;

uniform sampler2D farside : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D detail : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float flat_arc = 916.0;
uniform vec4 tile_rect = vec4(0.0, 0.0, 1.0, 1.0);    // (s0, x0, w, h) m: the area this tile's image covers
global uniform float farside_player_s;      // the player's s (RemakeFarSide)
global uniform float daylight;            // 1 by day, 0 at night (DaySkySystem): the far side darkens at night
#include "res://remake/shaders/land_cover.gdshaderinc"

void fragment() {
	if (cut_here(UV)) {
		discard;                                // (the fine ground is complete here: MapTerrainMesh._cut)
	}
	float s = UV2.x;
	float d = abs(mod(s - farside_player_s + circ * 0.5, circ) - circ * 0.5);
	if (d > flat_arc) {
		ALBEDO = texture(farside, (UV2 - tile_rect.xy) / tile_rect.zw).rgb * mix(0.1, 1.0, daylight);
	} else {
		vec3 c = to_linear(mix(cover(UV), COLOR.rgb, COLOR.a));
		ALBEDO = c * texture(detail, UV).rgb;
	}
	ROUGHNESS = 0.95;
}

void light() {
	// lit from either side: the sun is set overhead at the viewer, which is beneath the far side
	DIFFUSE_LIGHT += LIGHT_COLOR * ATTENUATION * abs(dot(NORMAL, LIGHT)) / PI;
}
