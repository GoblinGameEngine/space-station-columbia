extends Node3D
class_name RemakeClouds

## The station's weather.  North is the Marlowe end cap (-x); east is +s (RemakeStation.compass_bearing).
##
##   Cumulus, in LOW_LAYERS (the lowest 200..300 m up, the rest stacked up the air column), LOW_COUNT
##   each: a few puffs blended into one smooth cartoon skin (a smooth-union distance field,
##   shrink-wrapped by a sphere of rays -- no facets, no seams) with a flat base, opaque and
##   cel-shaded (cumulus.gdshader) so the outline pass inks only the silhouette.  Skins are built on
##   worker threads.  Each is also a WaterVolume (the lake's trigger), so whatever flies into one
##   treats it as water, and the camera inside one whites out.
##
##   Every cumulus drifts on its own: the prevailing wind carries it east to west (-s) -- only the
##   lowest layer's clouds may run west to east -- while it wanders north and south.
##
##   Storms (cumulus only).  Two clouds that touch (same layer) or line up one above the other
##   (different layers) reach a merge trigger; an RNG decides whether they merge.  Merging, they drift
##   together (the upper one sinking to the lower one's height) and become one cloud: a formed cell,
##   darker, with a rainstorm under it.  Two cells that merge make a supercell: a thunderstorm.
##   Storms form only in the daytime, at most MAX_STORMS_A_DAY a day (none at night) -- only
##   enough clouds for a couple of cells.  A rainstorm begins to break up after RAIN_HOURS
##   in-game hours, a thunderstorm after THUNDER_HOURS; the break-up takes BREAKUP_HOURS, the rain
##   fading, and the cell splits back into the clouds it was made of, which drift apart.
##   The rain itself (particles, shafts, lightning, sound) is RemakeRain, reading storms().
##
##   High cirrus, CIRRUS_SHELLS: sparse shells of flat translucent ribbons wrapped round the axis,
##   the way the spinning air carries them (cirrus.gdshader), drifting very slowly.
##
## Positions and the weather's dice are fixed-seed RNGs, so the same sky comes back every launch.

const LOW_COUNT := 5                   # per layer
## cumulus layers: [base, lowest top, wind m/s, size] -- the clouds grow with height (size scales a
## cloud's length, and its puffs with it)
const LOW_LAYERS := [[200.0, 300.0, 12.0, 8.0], [500.0, 600.0, 15.0, 11.0], [900.0, 1000.0, 18.0, 14.0],
	[1400.0, 1500.0, 21.0, 17.0], [2000.0, 2100.0, 24.0, 20.0]]
const CUMULUS_CEILING := StationGeo.R - StationGeo.SHAFT_R - 300.0   # tops kept under the lower cirrus shell
const CIRRUS_ROWS := 24              # a cirrus shell: bands along the axis ...
const CIRRUS_COLS := 6               # ... by slots round it, one jittered ribbon each
const CIRRUS_H := StationGeo.R - StationGeo.SHAFT_R - 100.0  # 100 m off the central shaft
## cirrus shells: [height, wind m/s east, size] -- 100 m and 250 m off the central shaft
const CIRRUS_SHELLS := [[CIRRUS_H, 1.8, 3.0], [CIRRUS_H - 150.0, 2.4, 2.5]]
const END_CLEAR := 40.0              # m kept between a cloud and an end cap
const SEED := 20260924

# the weather
const MERGE_CHANCE := 0.35           # the RNG at a merge trigger
const MERGE_SPEED := 20.0            # m/s the two clouds close at
const SINK_SPEED := 12.0             # m/s the upper one sinks at
const MAX_STORMS_A_DAY := 2
const RAIN_HOURS := 3.0
const THUNDER_HOURS := 1.0
const BREAKUP_HOURS := 0.5
const DRIFT_NS := 7.5                # m/s: the north-south wander's range
const CELL_COLOR := Color(0.5, 0.52, 0.58)
const SUPERCELL_COLOR := Color(0.34, 0.35, 0.41)

var target: Node3D                   # the camera the inside-a-cloud whiteout follows
var env: Environment
var sky: DaySkySystem                # the time of day (day / night)
var _low: Array = []                 # every cumulus: see _new_cloud
var _layers: Array = []              # the cumulus layer nodes
var _high_layers: Array = []         # [node, angular speed]
var _cumulus_mat: ShaderMaterial
var _cell_mat: ShaderMaterial
var _super_mat: ShaderMaterial
var _cirrus_mat: ShaderMaterial
var _rng := RandomNumberGenerator.new()
var _wx := RandomNumberGenerator.new()      # the weather's dice
var _fogged := false
var _skin_task := -1
var _skins: Array = []
var _jobs: Array = []                # [task id, cloud] skins being built for merged clouds
var _contacts := {}                  # "a:b" -> true while two clouds stay at a trigger
var _hours := 0.0                    # in-game hours since start
var _storms_today := 0
var _was_day := false
var _next_id := 0


func setup(p_target: Node3D, p_env: Environment, p_sky: DaySkySystem = null) -> void:
	target = p_target
	env = p_env
	sky = p_sky
	_rng.seed = SEED
	_wx.seed = SEED + 1
	_cumulus_mat = ShaderMaterial.new()
	_cumulus_mat.shader = load("res://remake/shaders/cumulus.gdshader")
	_cell_mat = _cumulus_mat.duplicate()
	_cell_mat.set_shader_parameter("body_color", CELL_COLOR)
	_super_mat = _cumulus_mat.duplicate()
	_super_mat.set_shader_parameter("body_color", SUPERCELL_COLOR)
	_cirrus_mat = ShaderMaterial.new()
	_cirrus_mat.shader = load("res://remake/shaders/cirrus.gdshader")
	for li in LOW_LAYERS.size():
		var lay := Node3D.new()
		lay.name = "Cumulus_%d" % li
		add_child(lay)
		_layers.append(lay)
		for i in LOW_COUNT:
			_low.append(_make_cumulus(li))
	for si in CIRRUS_SHELLS.size():
		var lay := Node3D.new()
		lay.name = "Cirrus_%d" % si
		lay.rotation.x = si * 1.3                              # the shells' gaps don't line up
		add_child(lay)
		var hh: float = CIRRUS_SHELLS[si][0]
		_high_layers.append([lay, CIRRUS_SHELLS[si][1] / (StationGeo.R - hh)])
		for row in CIRRUS_ROWS:
			_make_cirrus_band(row, lay, hh, CIRRUS_SHELLS[si][2])
	var all_puffs := []
	for c in _low:
		all_puffs.append(c.puffs)
	_skin_task = WorkerThreadPool.add_task(_make_skins.bind(all_puffs), false, "cloud skins")
	set_process(true)


# ------------------------------------------------------------------ cumulus
func _new_cloud(li: int, puffs: Array, s: float, x: float, h: float, kind: int) -> Dictionary:
	## A cumulus on layer li: its node (placed each frame from s, x, h), skin mesh, water volume.
	## kind 0 a plain cloud, 1 a cell (rain), 2 a supercell (thunder).
	var node := Node3D.new()
	node.name = "cumulus_%d" % _next_id
	_next_id += 1
	(_layers[li] as Node3D).add_child(node)
	var mi := MeshInstance3D.new()
	mi.material_override = [_cumulus_mat, _cell_mat, _super_mat][kind]
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	node.add_child(mi)
	var area := WaterVolume.new()
	area.name = "volume"
	area.flat_base = true                # drawn cut flat underneath: only what's above that is cloud
	for p in puffs:
		var cs := CollisionShape3D.new()
		var sph := SphereShape3D.new()
		sph.radius = p[1]
		cs.shape = sph
		cs.position = p[0]
		area.add_child(cs)
	node.add_child(area)
	var reach := 0.0
	var foot := 0.0
	var fa := 0.0                    # the footprint under its base: half-length along the wind (s) ...
	var fb := 0.0                    # ... and half-width across it (x)
	for p in puffs:
		reach = maxf(reach, Vector2(p[0].x, p[0].z).length() + p[1])
		foot = maxf(foot, Vector2(p[0].x, p[0].z).length() + p[1] * 0.8)
		var fr: float = sqrt(maxf(p[1] * p[1] - p[0].y * p[0].y, 0.0))   # the puff's circle on the base plane
		fa = maxf(fa, absf(p[0].x) + fr)
		fb = maxf(fb, absf(p[0].z) + fr)
	var wind: float = LOW_LAYERS[li][2]
	var vs: float = -wind * _rng.randf_range(0.7, 1.3)                # east to west ...
	if li == 0 and _rng.randf() < 0.5:
		vs = -vs                                                      # ... the lowest layer either way
	var c := {"node": node, "mesh": mi, "area": area, "puffs": puffs, "reach": reach + 25.0, "foot": foot, "fa": fa, "fb": fb,
		"layer": li, "s": s, "x": x, "h": h, "vs": vs, "vx": _rng.randf_range(-DRIFT_NS, DRIFT_NS),
		"kind": kind, "state": "free", "members": [], "partner": null, "storm": {}}
	_place(c)
	return c


func _make_cumulus(li: int) -> Dictionary:
	var base: float = LOW_LAYERS[li][0]
	var size: float = LOW_LAYERS[li][3]
	# simple on purpose: a row of 2-4 big puffs along its length (local x, turned to run with the
	# wind round the ring) and a few smaller heads on top, all pressed flat underneath.  A cloud is
	# straight while the air it rides curves round the axis: kept short enough of its radius that
	# its ends don't droop out of its layer
	var length := minf(_rng.randf_range(45.0, 110.0) * size, 0.8 * (StationGeo.R - base))
	var puffs := []
	var n_base := clampi(roundi(length / 30.0), 2, 4)
	var r0 := length / (n_base + 1.0)
	for k in n_base:
		var r := r0 * _rng.randf_range(0.85, 1.15)
		var px := (k - (n_base - 1) * 0.5) * r0 * 1.1
		puffs.append([Vector3(px, r * 0.3, 0.0), r])
	for k in _rng.randi_range(2, 4):
		var r := r0 * _rng.randf_range(0.45, 0.8)
		puffs.append([Vector3(_rng.randf_range(-0.45, 0.45) * length * 0.5, r0 * _rng.randf_range(0.7, 1.0), _rng.randf_range(-0.25, 0.25) * r0), r])
	var top := 0.0
	for p in puffs:
		top = maxf(top, p[0].y + p[1])
	if base + top > CUMULUS_CEILING:
		var k := (CUMULUS_CEILING - base) / top
		for p in puffs:
			p[0] *= k
			p[1] *= k
		top *= k
		r0 *= k
	var top_h: float = LOW_LAYERS[li][1]
	var h := _rng.randf_range(base, maxf(base, top_h - top))
	var lim := StationGeo.HALF_LEN - END_CLEAR - r0 - 20.0
	return _new_cloud(li, puffs, _rng.randf() * StationGeo.CIRC, _rng.randf_range(-lim, lim), h, 0)


func _place(c: Dictionary) -> void:
	(c.node as Node3D).transform = Transform3D(StationGeo.basis(c.s, PI * 0.5), StationGeo.point(c.s, c.x, c.h))


const BLEND := 3.0                   # m: how softly neighbouring puffs merge (small: the bulges stay)
const BASE_BLEND := 3.0              # m: the rounding where the sides meet the flat base


static func _field(p: Vector3, puffs: Array) -> float:
	## Signed distance (roughly) to the cloud: the puffs' smooth union, cut flat at y = 0.
	var d := 1.0e9
	for pf in puffs:
		var e: float = p.distance_to(pf[0]) - pf[1]
		var h := clampf(0.5 + 0.5 * (e - d) / BLEND, 0.0, 1.0)      # polynomial smooth min
		d = lerpf(e, d, h) - BLEND * h * (1.0 - h)
	var b := -p.y
	var h2 := clampf(0.5 - 0.5 * (b - d) / BASE_BLEND, 0.0, 1.0)     # smooth max with the base
	return lerpf(b, d, h2) + BASE_BLEND * h2 * (1.0 - h2)


static func _skin(puffs: Array, rings := 22, segs := 40) -> Array:
	## The cloud's surface arrays: a sphere of rays from inside the cloud, each sphere-traced in
	## from outside to the field's outermost zero; normals from the field's gradient.
	var c := Vector3.ZERO
	var reach := 0.0
	for pf in puffs:
		c += pf[0]
	c /= puffs.size()
	c.y = 3.0
	for pf in puffs:
		reach = maxf(reach, c.distance_to(pf[0]) + pf[1] + 4.0)
	var grid := []
	for a in rings + 1:
		var row := []
		var th := PI * a / rings
		for b in segs + 1:
			var ph := TAU * b / segs
			var dir := Vector3(sin(th) * cos(ph), cos(th), sin(th) * sin(ph))
			var t := reach
			for it in 60:
				var d := _field(c + dir * t, puffs)
				if d < 0.05:
					break
				t -= maxf(d, 0.2)
				if t <= 0.5:
					t = 0.5
					break
			var v := c + dir * t
			var e := 0.4
			var n := Vector3(_field(v + Vector3(e, 0, 0), puffs) - _field(v - Vector3(e, 0, 0), puffs),
				_field(v + Vector3(0, e, 0), puffs) - _field(v - Vector3(0, e, 0), puffs),
				_field(v + Vector3(0, 0, e), puffs) - _field(v - Vector3(0, 0, e), puffs)).normalized()
			row.append([v, n])
		grid.append(row)
	var verts := PackedVector3Array()
	var norms := PackedVector3Array()
	for a in rings:
		for b in segs:
			var q := [grid[a][b], grid[a + 1][b], grid[a + 1][b + 1], grid[a][b + 1]]
			for k in [0, 2, 1, 0, 3, 2]:
				verts.append(q[k][0])
				norms.append(q[k][1])
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = norms
	return arrays


func _make_skins(all_puffs: Array) -> void:
	var out := []
	for puffs in all_puffs:
		out.append(_skin(puffs))
	_skins = out


func _skin_job(job: Dictionary) -> void:
	## (a holder of its own: the worker never touches a cloud the main thread is moving)
	job["skin"] = _skin(job.puffs, 44, 88)          # a storm cell is big: a finer skin


# ------------------------------------------------------------------ high cirrus
func _make_cirrus_band(row: int, layer: Node3D, height: float, size: float) -> void:
	## One band of a shell along the axis: CIRRUS_COLS ribbons round it, each on the cylinder
	## `height` up -- its span round the axis, its width along it -- in one mesh (UV2.x: the
	## ribbon's seed for the shader's wisps).
	var r := StationGeo.R - height
	var band := (StationGeo.LENGTH - 2.0 * END_CLEAR) / CIRRUS_ROWS
	var x0 := -StationGeo.HALF_LEN + END_CLEAR + band * row
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n := 24
	for col in CIRRUS_COLS:
		var span := minf(_rng.randf_range(0.45, 1.2) * size, 3.0)   # radians round the axis
		var th0 := TAU * (col + _rng.randf_range(0.15, 0.85)) / CIRRUS_COLS + row * 0.37
		var width := minf(_rng.randf_range(25.0, 60.0) * size, band * 0.9)
		var skew := _rng.randf_range(-0.3, 0.3) * width    # wisps lie a little aslant the wind
		var xc := x0 + width * 0.5 + absf(skew) * 0.5 + _rng.randf() * maxf(0.0, band - width - absf(skew))
		var seed := _rng.randf() * 50.0
		for k in n:
			for tri in [[0, 0], [1, 1], [1, 0], [0, 0], [0, 1], [1, 1]]:
				var u: float = (k + tri[0]) / float(n)
				var v: float = tri[1]
				var th: float = th0 + span * (u - 0.5)
				st.set_normal(Vector3(0.0, cos(th), sin(th)))  # toward the floor below it
				st.set_uv(Vector2(u, v))
				st.set_uv2(Vector2(seed, 0.0))
				st.add_vertex(Vector3(xc + (v - 0.5) * width + skew * (u - 0.5), r * cos(th), r * sin(th)))
	var mi := MeshInstance3D.new()
	mi.name = "cirrus_%d_%d" % [roundi(height), row]
	mi.mesh = st.commit()
	mi.material_override = _cirrus_mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	layer.add_child(mi)


# ------------------------------------------------------------------ the weather
func is_day() -> bool:
	if sky == null:
		return true
	return sky.time_of_day >= DaySkySystem.DAY_START and sky.time_of_day < DaySkySystem.DAY_END


func storms() -> Array:
	## For RemakeRain: every storm now -- {s, x, base (cloud base height), fa / fb (the footprint under
	## the cloud: half-length along s, half-width along x -- the rain falls only there), radius
	## (the larger), intensity 0..1, thunder, id}.
	var out := []
	for c in _low:
		if c.state == "free" and c.kind > 0 and not c.storm.is_empty():
			out.append({"s": c.s, "x": c.x, "base": c.h, "radius": maxf(c.fa, c.fb), "fa": c.fa, "fb": c.fb,
				"intensity": c.storm.intensity,
				"thunder": c.kind == 2, "id": str(c.node.name)})
	return out


static func _ds(a: float, b: float) -> float:
	return StationGeo.wrap_ds(b - a)


func _hdist(a: Dictionary, b: Dictionary) -> float:
	return Vector2(_ds(a.s, b.s), b.x - a.x).length()


func _drift(c: Dictionary, dt: float) -> void:
	var li: int = c.layer
	# the wander north and south: a slow random walk, turned back at the end caps
	c.vx = clampf(c.vx + _wx.randf_range(-0.9, 0.9) * dt, -DRIFT_NS, DRIFT_NS)
	var lim: float = StationGeo.HALF_LEN - END_CLEAR - c.foot
	if c.x > lim and c.vx > 0.0 or c.x < -lim and c.vx < 0.0:
		c.vx = -c.vx
	# the lowest layer's clouds now and then swing round to run west to east (or back)
	if li == 0 and _wx.randf() < dt / 900.0:
		c.vs = -c.vs
	var k: float = StationGeo.R / (StationGeo.R - c.h)       # m/s at its height -> s units on the floor
	c.s = fposmod(c.s + c.vs * k * dt, StationGeo.CIRC)
	c.x = clampf(c.x + c.vx * dt, -lim, lim)


func _merge_kind(a: Dictionary, b: Dictionary) -> int:
	## What a merge of a and b would make (1 cell, 2 supercell), or 0 if they can't merge now.
	if a.kind == 0 and b.kind == 0:
		if not is_day() or _storms_today >= MAX_STORMS_A_DAY or storms().size() >= MAX_STORMS_A_DAY:
			return 0
		return 1
	if a.kind == 1 and b.kind == 1 and not a.storm.get("breaking", false) and not b.storm.get("breaking", false):
		return 2
	return 0


func _triggers() -> void:
	## Clouds at a merge trigger: touching (same layer) or one above the other (different layers).
	## Each trigger is rolled once, when the two first reach it.
	var free := []
	for c in _low:
		if c.state == "free":
			free.append(c)
	for i in free.size():
		for j in range(i + 1, free.size()):
			var a: Dictionary = free[i]
			var b: Dictionary = free[j]
			var key := "%s:%s" % [a.node.name, b.node.name]
			var d := _hdist(a, b)
			var hit: bool = d < (a.foot + b.foot) if a.layer == b.layer else d < maxf(a.foot, b.foot) * 0.5
			if not hit:
				_contacts.erase(key)
				continue
			if _contacts.has(key):
				continue
			_contacts[key] = true
			var kind := _merge_kind(a, b)
			if kind > 0 and _wx.randf() < MERGE_CHANCE:
				a.state = "merging"
				b.state = "merging"
				a.partner = b
				b.partner = a
				a["merge_kind"] = kind
				b["merge_kind"] = kind


func _merging(a: Dictionary, dt: float) -> void:
	## Two merging clouds close on each other (the upper one sinking to the lower one's height);
	## once together they become one.
	var b: Dictionary = a.partner
	var low_h := minf(a.h, b.h)
	for c in [a, b]:
		c.h = move_toward(c.h, low_h, SINK_SPEED * dt)
	var mid_s := fposmod(a.s + _ds(a.s, b.s) * 0.5, StationGeo.CIRC)
	var mid_x: float = (a.x + b.x) * 0.5
	for c in [a, b]:
		var to := Vector2(_ds(c.s, mid_s), mid_x - c.x)
		if to.length() > 0.01:
			var mv := to.normalized() * minf(to.length(), MERGE_SPEED * dt)
			c.s = fposmod(c.s + mv.x, StationGeo.CIRC)
			c.x += mv.y
	if _hdist(a, b) < 20.0 and absf(a.h - b.h) < 1.0:
		_combine(a, b)


func _combine(a: Dictionary, b: Dictionary) -> void:
	## One cloud from two: their puffs side by side along the wind, on the lower one's layer.
	var kind: int = a.merge_kind
	var lower: Dictionary = a if a.layer <= b.layer else b
	var la := 0.0
	var lb := 0.0
	for p in a.puffs:
		la = maxf(la, absf(p[0].x) + p[1])
	for p in b.puffs:
		lb = maxf(lb, absf(p[0].x) + p[1])
	var d := 0.35 * minf(la, lb)
	var puffs := []
	for p in a.puffs:
		puffs.append([p[0] - Vector3(d, 0, 0), p[1]])
	for p in b.puffs:
		puffs.append([p[0] + Vector3(d, 0, 0), p[1]])
	var c := _new_cloud(lower.layer, puffs, lower.s, lower.x, minf(a.h, b.h), kind)
	c.vs = lower.vs * 0.8
	c.members = [a, b]
	for m in [a, b]:
		m.state = "hidden"
		m.partner = null
	c.storm = {"kind": "thunder" if kind == 2 else "rain", "start": _hours, "intensity": 0.0, "breaking": false}
	if kind == 1:
		_storms_today += 1
	c.state = "forming"                      # shown once its skin is built
	_low.append(c)
	var holder := {"puffs": puffs.duplicate(true)}
	_jobs.append([WorkerThreadPool.add_task(_skin_job.bind(holder), false, "merged cloud skin"), c, holder])


func _breakup(c: Dictionary) -> void:
	## A storm's end: the cell splits back into the clouds it was made of, which drift apart.
	var parts := []
	for m in c.members:
		if m.kind > 0:                      # a supercell's cells: back to their own clouds
			for mm in m.members:
				parts.append(mm)
			_low.erase(m)
			(m.node as Node3D).queue_free()
		else:
			parts.append(m)
	for i in parts.size():
		var m: Dictionary = parts[i]
		var off: float = (i - (parts.size() - 1) * 0.5) * 2.0 * c.foot / maxf(1.0, parts.size())
		var lim: float = StationGeo.HALF_LEN - END_CLEAR - m.foot
		m.s = c.s
		m.x = clampf(c.x + off, -lim, lim)
		m.h = maxf(m.h, LOW_LAYERS[m.layer][0])
		m.vx = DRIFT_NS * (1.0 if off >= 0.0 else -1.0)
		m.state = "free"
		m.storm = {}
		(m.node as Node3D).visible = true
		_place(m)
	_low.erase(c)
	(c.node as Node3D).queue_free()


func _storm_step(c: Dictionary, dh: float) -> void:
	var st: Dictionary = c.storm
	var life := THUNDER_HOURS if st.kind == "thunder" else RAIN_HOURS
	var age: float = _hours - st.start
	if age < life:
		st.intensity = minf(1.0, st.intensity + dh / 0.25)      # the rain builds over a quarter hour
	else:
		st.breaking = true
		st.intensity = clampf(1.0 - (age - life) / BREAKUP_HOURS, 0.0, 1.0)
		if age >= life + BREAKUP_HOURS:
			_breakup(c)


func _process(delta: float) -> void:
	if _skin_task >= 0 and WorkerThreadPool.is_task_completed(_skin_task):
		WorkerThreadPool.wait_for_task_completion(_skin_task)
		_skin_task = -1
		for i in _skins.size():
			var mesh := ArrayMesh.new()
			mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, _skins[i])
			(_low[i].mesh as MeshInstance3D).mesh = mesh
		_skins = []
	# merged clouds whose skins are ready replace their parts
	for job in _jobs.duplicate():
		if WorkerThreadPool.is_task_completed(job[0]):
			WorkerThreadPool.wait_for_task_completion(job[0])
			_jobs.erase(job)
			var c: Dictionary = job[1]
			var mesh := ArrayMesh.new()
			mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, job[2].skin)
			(c.mesh as MeshInstance3D).mesh = mesh
			c.state = "free"
			for m in c.members:
				(m.node as Node3D).visible = false
	var dt := minf(delta, 0.1)
	var dh := dt / DaySkySystem.DAY_LENGTH_SECONDS * 24.0          # in-game hours this frame
	_hours += dh
	var day := is_day()
	if day and not _was_day:
		_storms_today = 0                                           # a new day's storms
	_was_day = day
	for c in _low.duplicate():
		if not _low.has(c):
			continue
		match c.state:
			"free":
				_drift(c, dt)
				if not c.storm.is_empty():
					_storm_step(c, dh)
			"merging":
				if c.partner != null and _low.find(c) < _low.find(c.partner):
					_merging(c, dt)
			"forming":
				_drift(c, dt)
		if _low.has(c) and c.state != "hidden":
			_place(c)
	if _debug_super:
		if _debug_cells.size() == 2 and _debug_cells[0].state == "free" and _debug_cells[1].state == "free":
			_debug_super = false
			_combine_now(_debug_cells[0], _debug_cells[1], 2)
	_triggers()
	for L in _high_layers:
		var lay: Node3D = L[0]
		lay.rotation.x = fposmod(lay.rotation.x + float(L[1]) * dt, TAU)
	_whiteout()


func inside(p: Vector3) -> float:
	## How deep p is inside a low cloud: 0 outside, 1 at a puff's centre.
	var best := 0.0
	for c in _low:
		if c.state == "hidden":
			continue
		var node: Node3D = c.node
		var t := node.global_transform
		if p.distance_to(t.origin) > c.reach + 60.0:
			continue
		var lp := t.affine_inverse() * p
		if lp.y < 0.0:
			continue
		for pf in c.puffs:
			best = maxf(best, 1.0 - lp.distance_to(pf[0]) / pf[1])
	return best


func _whiteout() -> void:
	if env == null or target == null:
		return
	var d := inside(target.global_position)
	if d > 0.0:
		env.fog_enabled = true
		env.fog_light_color = Color(0.9, 0.92, 0.95)
		env.fog_light_energy = 1.0
		env.fog_sky_affect = 1.0
		env.fog_density = 0.03 + 0.25 * d
		_fogged = true
	elif _fogged:
		env.fog_enabled = false
		_fogged = false


func debug_storm(s: float, x: float, thunder := false) -> void:
	## For testing: bring plain clouds over (s, x) and merge them straight away -- two for a
	## rainstorm, four (two cells merged) for a thunderstorm.  Ignores the day / storm limits.
	var picks := []
	for c in _low:
		if c.state == "free" and c.kind == 0 and c.layer <= 1:
			picks.append(c)
		if picks.size() == (4 if thunder else 2):
			break
	if picks.size() < 2:
		return
	for i in picks.size():
		picks[i].s = s + (i % 2) * 30.0
		picks[i].x = x
		picks[i].h = LOW_LAYERS[0][0]
	_combine_now(picks[0], picks[1], 1)
	_debug_cells = [_low[-1]]
	if thunder and picks.size() == 4:
		_combine_now(picks[2], picks[3], 1)
		_debug_cells.append(_low[-1])
		_debug_super = true


var _debug_super := false
var _debug_cells: Array = []


func _combine_now(a: Dictionary, b: Dictionary, kind: int) -> void:
	a.partner = b
	b.partner = a
	a["merge_kind"] = kind
	b["merge_kind"] = kind
	_combine(a, b)


func _exit_tree() -> void:
	if _skin_task >= 0:
		WorkerThreadPool.wait_for_task_completion(_skin_task)
	for job in _jobs:
		WorkerThreadPool.wait_for_task_completion(job[0])
