extends Node
class_name RemakeFarSide

## The far side of the cylinder, drawn flat.  Beyond FLAT_ARC of arc round the ring from the
## player (central angle ~105 deg, ~790 m away), a building's relief is a few pixels and you see
## the floor almost face-on, so everything there is drawn as the baked top-down image of itself
## (remake/farside/f_SS_XX.webp, one small image per far tile -- FarsideBake.tscn) on the terrain's coarse far tier.  Hidden there:
## every non-landmark building and merged district mesh, the trees, roads and water.  The tall
## landmarks (spires, elevators, towers, silos -- what shows at that range) keep their own far
## versions.  Checked every CHECK s with HYST m of hysteresis.

const FLAT_ARC := 1500.0             # m of arc round the ring: beyond it the far side is the flat baked image (3,000 on the
                                     # 20 km ring doubled the merged district and road cells drawn: Calder fell to ~36 fps)
const HYST := 30.0
const CHECK := 0.25

var target: Node3D
var _entries: Array = []             # [Node3D, s of its centre, far now]
var _terrain: MapTerrainMesh
var _mats := {}                           # far tile key -> its ShaderMaterial (farside.gdshader, its own image)
var _shader: Shader
var _detail: Texture2D
var _t := 0.0
var _sorted := false                 # _entries in order of s (the boundary checks need it)
var _ss := PackedFloat64Array()       # their s, in that order
var _last_sp := INF                  # where the player was at the last check
const BAND := 200.0                  # entries within this of a boundary are rechecked (the player can't cross it in CHECK)


func setup(p_target: Node3D, terrain: MapTerrainMesh, detail: Texture2D) -> void:
	## Call before the terrain builds its far tier (it takes this material for it).
	target = p_target
	_terrain = terrain
	_detail = detail
	_shader = load("res://remake/shaders/farside.gdshader")
	terrain.far_material_for = _material_for


func _material_for(key: Vector2i) -> Material:
	## A far tile's material: its own small baked image, mapped onto the map metres it covers.
	if _mats.has(key):
		return _mats[key]
	var m := ShaderMaterial.new()
	m.shader = _shader
	var path := StationGeo.farside_path(key)
	if ResourceLoader.exists(path):
		m.set_shader_parameter("farside", load(path))
	m.set_shader_parameter("detail", _detail)
	m.set_shader_parameter("flat_arc", FLAT_ARC)
	MapTerrainMesh.set_cover_params(m)
	var px := StationGeo.farside_px(_terrain.far_rect(key))
	var mp := StationGeo.FARSIDE_M
	m.set_shader_parameter("tile_rect", Vector4(px.position.x * mp, px.position.y * mp - StationGeo.HALF_LEN,
		px.size.x * mp, px.size.y * mp))
	_mats[key] = m
	return m


func add_node(n: Node3D) -> void:
	## Something the far side hides; its s is taken from its drawn centre (or its position).
	var c := n.global_position
	if n is GeometryInstance3D:
		c = (n as GeometryInstance3D).global_transform * (n as VisualInstance3D).get_aabb().get_center()
	_entries.append([n, StationGeo.s_of(c), false])
	_sorted = false


func prune() -> void:
	## drop the entries whose nodes are gone (streamed meshes freed with their band)
	_entries = _entries.filter(func(e): return is_instance_valid(e[0]))
	_sorted = false


func add_children_of(parent: Node, skip: Callable = Callable()) -> void:
	for c in parent.get_children():
		if c is Node3D and (not skip.is_valid() or not skip.call(c)):
			add_node(c)


func _process(delta: float) -> void:
	if target == null:
		return
	var sp := StationGeo.s_of(target.global_position)
	# the terrain's far tier switches per pixel (farside.gdshader): tell it where the player is
	RenderingServer.global_shader_parameter_set("farside_player_s", sp)
	_t -= delta
	if _t > 0.0 or _entries.is_empty():
		return
	_t = CHECK
	if not _sorted:
		_entries.sort_custom(func(a, b): return float(a[1]) < float(b[1]))
		_ss = PackedFloat64Array()
		for e in _entries:
			_ss.append(float(e[1]))
		_sorted = true
		_last_sp = INF
	# only what lies near the two boundaries (FLAT_ARC ahead and behind) can change -- all of it after a jump
	# (checking all ~4,500 entries was ~1.4 ms a frame on the 20 km ring)
	if _last_sp == INF or absf(StationGeo.wrap_ds(sp - _last_sp)) > BAND * 0.5:
		for i in _entries.size():
			_check(i, sp)
	else:
		for b in [sp - FLAT_ARC, sp + FLAT_ARC]:
			var lo := fposmod(b - BAND, StationGeo.CIRC)
			var i := _ss.bsearch(lo)
			var n := 0
			while n < _entries.size():
				var k := (i + n) % _entries.size()
				if absf(StationGeo.wrap_ds(_ss[k] - b)) > BAND and n > 0 and StationGeo.wrap_ds(_ss[k] - b) > 0.0:
					break
				_check(k, sp)
				n += 1
	_last_sp = sp


func _check(i: int, sp: float) -> void:
	var e: Array = _entries[i]
	if not is_instance_valid(e[0]):
		return                                           # (a streamed mesh freed with its band)
	var nd: Node3D = e[0]
	var d := absf(StationGeo.wrap_ds(e[1] - sp))
	var far: bool = d > FLAT_ARC + (-HYST if e[2] else HYST)
	if far != e[2]:
		e[2] = far
		nd.visible = not far
