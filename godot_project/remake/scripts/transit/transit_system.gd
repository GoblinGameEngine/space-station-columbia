extends Node3D
class_name TransitSystem

## Trams and trains in service (TransitNet's lines), on a timetable that is a pure function of the
## clock: vehicle j of a line is at TransitNet.state(line, T + j * period / count), T the real
## seconds since day 0 began (a game hour is two real minutes, so they move at their real speeds and
## the same tram is always in the same place at the same time). Only those within RANGE of the player
## are built; the one carrying the player is kept. Service runs 05:30 to 00:30.

const RANGE := 280.0
const LANE_W := 3.6                  # a trolley lane's paved width (m)
const TICK := 0.25

var player: Node3D
var _clock: Node
var live := {}                       # "line#j" -> TransitVehicle
var _t := 0.0
var world_seed := 1


func _ready() -> void:
	name = "TransitSystem"
	TransitNet.lines()
	_clock = get_tree().current_scene.get_node_or_null("DaySkySystem")
	var n := 0
	for l in TransitNet.lines():
		n += int(l.count)
		print("TransitSystem: %s (%s) %.1f km, %d stops, %d vehicles, a loop every %.0f min" % [l.name, l.kind, float(l.length) / 1000.0,
			(l.stops as Array).size(), int(l.count), float(l.period) / 60.0])
	_pave_loops()


func _pave_loops() -> void:
	## The trolley lanes: each turning loop at a tram terminus is paved, a strip LANE_W wide.
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n := 0
	var done: Array = []
	for loop in TransitNet.loops:
		var pts: Array = loop
		var mid: Vector2 = pts[pts.size() / 2]
		if done.any(func(q): return NpcPlaces.dist(q, mid) < 5.0):
			continue                         # a terminus both ways along a line: one lane
		done.append(mid)
		var run := 0.0
		for i in pts.size() - 1:
			var a: Vector2 = pts[i]
			var b: Vector2 = pts[i + 1]
			var t := (b - a)
			if t.length() < 0.05:
				continue
			var side := Vector2(-t.y, t.x).normalized() * LANE_W * 0.5
			var q: Array = []
			var wet := false
			for p in [a - side, a + side, b + side, b - side]:
				var s2 := fposmod((p as Vector2).x, StationGeo.CIRC)
				var g := MapTerrain.elevation(s2, (p as Vector2).y)
				wet = wet or MapTerrain.water_at(s2, (p as Vector2).y).x > g + 0.05
				q.append(StationGeo.point(s2, (p as Vector2).y, g + 0.07))
			var r2 := run + t.length()
			if wet:                                      # over a river or the lake: the bridge carries it, unpainted
				run = r2
				continue
			var uv := [Vector2(0, run), Vector2(1, run), Vector2(1, r2), Vector2(0, r2)]
			for k in [0, 1, 2, 0, 2, 3]:
				st.set_uv(uv[k] / 4.0)
				st.add_vertex(q[k])
			run = r2
			n += 1
	if n == 0:
		return
	st.generate_normals()
	var mi := MeshInstance3D.new()
	mi.name = "TrolleyLanes"
	mi.mesh = st.commit()
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(0.23, 0.23, 0.24)
	m.roughness = 0.95
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	mi.material_override = m
	mi.top_level = true
	add_child(mi)
	print("TransitSystem: %d trolley lanes (turning loops) paved" % done.size())


func clock_seconds() -> float:
	if _clock == null:
		return Time.get_ticks_msec() / 1000.0
	return (float(_clock.get("day")) + float(_clock.time_of_day)) * DaySkySystem.DAY_LENGTH_SECONDS


func hour() -> float:
	return (float(_clock.time_of_day) if _clock else 0.4) * 24.0


func _process(delta: float) -> void:
	if player == null or StationGeo.loading:
		return
	var T := clock_seconds()
	var h := hour()
	var running := h >= 5.5 or h < 0.5
	var ps := StationGeo.s_of(player.global_position)
	var px := player.global_position.x
	_t -= delta
	var check := _t <= 0.0
	if check:
		_t = TICK
	var want := {}
	for l in TransitNet.lines():
		for j in int(l.count):
			var key := "%s#%d" % [l.id, j]
			var st := TransitNet.state(l, T + j * float(l.period) / int(l.count))
			var v: TransitVehicle = live.get(key)
			if v == null and not check:
				continue
			var near := false
			if v and v.carrying_player():
				near = true
			elif running:
				var p := TransitNet.point_at(l, float(st.d))
				near = Vector2(StationGeo.wrap_ds(p.x - ps), p.y - px).length() < RANGE
			if not near:
				continue
			want[key] = true
			if v == null:
				v = TransitVehicle.new()
				v.world_seed = world_seed
				add_child(v)
				v.setup(l, j, h)
				live[key] = v
			v.place(float(st.d), bool(st.dwelling), int(st.stop))
	for key in live.keys():
		if not want.has(key) and check:
			(live[key] as Node).queue_free()
			live.erase(key)


func stats() -> Dictionary:
	var out := {"live": live.size(), "riders": 0}
	for k in live:
		out.riders += (live[k] as TransitVehicle).riders.size()
	return out
