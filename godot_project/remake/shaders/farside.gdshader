// The terrain's coarse far tier.  Beyond flat_arc of arc round the ring from the player it is
// the far side of the cylinder, drawn flat: the baked top-down image of the finished world
// (remake/farside.png, via UV2) -- roofs, roads, fields, trees and water as surface colour, lit
// by the station's sun like everything else.  Nearer, the ordinary ground: land cover per pixel
// (or the vertex colour where it says so, alpha 1) on the neutral detail texture.  The switch is per pixel, so it lands exactly where the
// far side's objects are hidden (RemakeFarSide).
shader_type spatial;
render_mode cull_back;

uniform sampler2D farside : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D detail : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float player_s = 0.0;
uniform float flat_arc = 916.0;
uniform float image_w = 3200.0;
global uniform float daylight;            // 1 by day, 0 at night (DaySkySystem): the far side darkens at night
#include "res://remake/shaders/land_cover.gdshaderinc"

void fragment() {
	float s = UV2.x * image_w;
	float d = abs(mod(s - player_s + circ * 0.5, circ) - circ * 0.5);
	if (d > flat_arc) {
		ALBEDO = texture(farside, UV2).rgb * mix(0.1, 1.0, daylight);
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
