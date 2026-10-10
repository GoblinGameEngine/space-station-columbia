shader_type spatial;
// The ground: land cover coloured per pixel from remake/landcover.png (so field and shore edges stay
// sharp whatever the mesh density), MapTerrainMesh's vertex colour where it knows better (town areas,
// mud and river beds, steep earth: vertex alpha 1), and the neutral grass grain over it all.
// UV is (x, s) / TEX_M.  Colours are the same table as MapTerrainMesh._cover_tint (sRGB).

uniform sampler2D detail : source_color, filter_linear_mipmap, repeat_enable;
#include "res://remake/shaders/land_cover.gdshaderinc"

uniform bool coarse = false;          // a coarse tier's material (MapTerrainMesh.coarse_material): cut by terrain_cut

void fragment() {
	if (coarse && cut_here(UV)) {
		discard;
	}
	vec3 c = mix(cover(UV), COLOR.rgb, COLOR.a);
	ALBEDO = to_linear(c) * texture(detail, UV).rgb;
}
