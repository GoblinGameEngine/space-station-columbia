extends Node3D
class_name WaterAmbience

## The sound of the water right beside the listener (user: only a few metres away; the seas up to
## 15 m): surf on the seas (heard to SEA_RANGE), lapping waves on Lake Tamsin and the broad rivers
## and a babbling stream on the creeks (heard to NEAR_RANGE).  Several times a second it samples the
## water round the listener (MapTerrain.water_at on a SCAN m grid out to SEA_RANGE) and sorts each wet
## sample (kind_at): a sea, the lake, or a stream (the rivers and the carved creeks);
## one 3D emitter of each kind sits at the nearest such water.  Muffled under a roof.

const SEA_RANGE := 15.0
const NEAR_RANGE := 5.0
const RADIUS := SEA_RANGE + 2.0
const SCAN := 2.0
const CREEK_CELL := 100.0
const SEA_LEVEL := -0.5
const LAKE_S := PI / 4.0 * StationGeo.R    # Lake Tamsin's centre round the ring
const LAKE_REACH := 1100.0

var listener: Node3D
var _sea: AudioStreamPlayer3D
var _waves: AudioStreamPlayer3D
var _stream: AudioStreamPlayer3D
var _t := 0.0


func setup(p_listener: Node3D) -> void:
	listener = p_listener
	_sea = _player("res://remake/audio/waves_loop.wav", 4.0, SEA_RANGE)
	_waves = _player("res://remake/audio/waves_loop.wav", 1.5, NEAR_RANGE)
	_waves.pitch_scale = 1.15                                 # smaller waves than the sea's
	_stream = _player("res://remake/audio/stream_loop.wav", 1.5, NEAR_RANGE)


func _player(path: String, unit: float, far: float) -> AudioStreamPlayer3D:
	var s: AudioStreamWAV = load(path)
	s.loop_mode = AudioStreamWAV.LOOP_FORWARD
	s.loop_end = s.data.size() / 2
	var p := AudioStreamPlayer3D.new()
	p.stream = s
	p.unit_size = unit
	p.max_distance = far
	p.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_SQUARE_DISTANCE
	p.attenuation_filter_cutoff_hz = 20500.0
	add_child(p)
	return p


static var _creeks := {}              # Vector2i cell -> [[a, b, half-width]] creek segments


static func _load_creeks() -> void:
	var d: Dictionary = MapTerrain.data()                      # (the one copy: parsing its own was ~500 MB more)
	for cr in d.creeks:
		var pts: Array = cr.pts
		for k in pts.size() - 1:
			var a := Vector2(pts[k][0], pts[k][1])
			var b := Vector2(pts[k + 1][0], pts[k + 1][1])
			var seg := [a, b, float(cr.hw)]
			var lo := Vector2(minf(a.x, b.x), minf(a.y, b.y)) - Vector2(20, 20)
			var hi := Vector2(maxf(a.x, b.x), maxf(a.y, b.y)) + Vector2(20, 20)
			for ci in range(floori(lo.x / CREEK_CELL), floori(hi.x / CREEK_CELL) + 1):
				for cj in range(floori(lo.y / CREEK_CELL), floori(hi.y / CREEK_CELL) + 1):
					var key := Vector2i(ci, cj)
					if not _creeks.has(key):
						_creeks[key] = []
					_creeks[key].append(seg)


static func _creek(s: float, x: float) -> bool:
	var q := Vector2(fposmod(s, StationGeo.CIRC), x)
	for seg in _creeks.get(Vector2i(floori(q.x / CREEK_CELL), floori(q.y / CREEK_CELL)), []):
		var a: Vector2 = seg[0]
		var b: Vector2 = seg[1]
		var ab := b - a
		var t := clampf((q - a).dot(ab) / maxf(ab.length_squared(), 1e-6), 0.0, 1.0)
		if q.distance_to(a + ab * t) <= float(seg[2]) + 0.5:
			return true
	return false


static func _sea_at(s: float, x: float) -> bool:
	if absf(x) <= 2600.0:
		return false
	var w := MapTerrain.water_at(fposmod(s, StationGeo.CIRC), x)
	return w.x > -9000.0 and w.x <= SEA_LEVEL + 0.05


static func kind_at(s: float, x: float) -> int:
	## 0 dry, 1 a stream (a river or a creek), 2 the lake (waves), 3 a sea (surf).  The seas are the
	## water at the sea level out by the end caps; the lake is the water over Lake Tamsin's reach
	## (tools/map_expanded.py LAKE_S +- its half-length); the creeks are their map lines (carved in
	## the floor, not in the water raster) -- not the road ditches.
	var sm := fposmod(s, StationGeo.CIRC)
	var w := MapTerrain.water_at(sm, x)
	if w.x > -9000.0:
		if absf(x) > 2600.0 and w.x <= SEA_LEVEL + 0.05:
			return 3
		if absf(StationGeo.wrap_ds(sm - LAKE_S)) < LAKE_REACH and absf(x) < 2000.0:
			return 2
		return 1
	return 1 if _creek(sm, x) else 0


func _process(delta: float) -> void:
	if listener == null:
		return
	_t -= delta
	if _t > 0.0:
		return
	_t = 0.25
	var p := listener.global_position
	var cs := StationGeo.s_of(p)
	var cx := p.x
	if _creeks.is_empty():
		_load_creeks()
	var best := [[INF, 0.0, 0.0], [INF, 0.0, 0.0], [INF, 0.0, 0.0], [INF, 0.0, 0.0]]   # by kind
	var n := int(RADIUS / SCAN)
	var near := NEAR_RANGE + 1.0
	for i in range(-n, n + 1):
		for j in range(-n, n + 1):
			var d := Vector2(i, j).length() * SCAN
			if d > RADIUS:
				continue
			var s := cs + i * SCAN
			var x := cx + j * SCAN
			var k := kind_at(s, x) if d <= near else (3 if _sea_at(s, x) else 0)
			if k > 0 and d < best[k][0]:
				best[k] = [d, s, x]
	var roofed := not get_world_3d().direct_space_state.intersect_ray(
		PhysicsRayQueryParameters3D.create(p + StationGeo.up(cs) * 0.5, p + StationGeo.up(cs) * 30.0)).is_empty()
	_put(_sea, best[3], roofed)
	_put(_waves, best[2], roofed)
	_put(_stream, best[1], roofed)


func _put(pl: AudioStreamPlayer3D, best: Array, roofed: bool) -> void:
	if best[0] == INF:
		if pl.playing:
			pl.stop()
		return
	var lv := MapTerrain.water_at(fposmod(best[1], StationGeo.CIRC), best[2]).x
	if lv < -9000.0:
		lv = MapTerrain.elevation(best[1], best[2])
	pl.global_position = StationGeo.point(best[1], best[2], lv + 0.5)
	pl.volume_db = -12.0 if roofed else 0.0
	if not pl.playing:
		pl.play(randf() * 5.0)
