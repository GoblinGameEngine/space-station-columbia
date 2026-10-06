extends Node
class_name DaySkySystem

# Drives the station's circadian sky cycle -- requested directly: a
# ceiling sky (shaders/ceiling_sky.gdshader) and wall cliff-to-sky blend
# (shaders/wall_cliff_sky.gdshader) sharing one time_of_day, plus a real
# shadow-casting DirectionalLight3D whose angle sweeps to match the
# visible sun band, a matching moon band at night, and bulk on/off
# toggling for every streetlight (StreetFurniture.gd's lamp posts).
#
# time_of_day: 0=midnight, 0.25=dawn ends/full day begins, 0.75=day ends/
# dusk begins, wraps at 1.0.

static var DAY_LENGTH_SECONDS := 2880.0  # 24 in-game hours: 1 hour every 2 real minutes (user). Live-tunable, e.g. gcmd.py run "DaySkySystem.DAY_LENGTH_SECONDS = 120.0"
static var lamp_light_on: bool = false  # read by StreetFurniture.gd when a NEW lamp post spawns, so it starts in the right state

const SKY_DAY_TEX := preload("res://assets/textures/sky_day.png")
const SKY_NIGHT_TEX := preload("res://assets/textures/sky_night.png")
const CLIFF_TEX := preload("res://assets/textures/cliff_rock.png")

const CEILING_SKY_SHADER := preload("res://shaders/ceiling_sky.gdshader")
const WALL_CLIFF_SKY_SHADER := preload("res://shaders/wall_cliff_sky.gdshader")

const DAWN_START := 0.15
const DAY_START := 0.25
const DAY_END := 0.75
const DUSK_END := 0.85

# Color/night-mix only -- "blue during the day -> red at dusk -> night ->
# red at dawn -> blue" (day and night entries are pure white/night-
# texture; the ONLY place red shows up is the dawn/dusk entries in
# between). Interpolated with smoothstep easing, not raw linear, between
# entries -- requested directly ("make sure the transition from day to
# night is smooth"). Band POSITION is intentionally NOT in this table --
# see _sun_moon_state()'s own comment for why that has to be computed
# separately.
const COLOR_KEYFRAMES := [
	[0.0,  1.0, 1.0, 1.0, 1.0],
	[DAWN_START, 1.0, 1.0, 1.0, 1.0],
	[0.20, 0.5, 1.6, 0.6, 0.4],
	[DAY_START,  0.0, 1.0, 1.0, 1.0],
	[DAY_END,    0.0, 1.0, 1.0, 1.0],
	[0.80, 0.5, 1.6, 0.6, 0.4],
	[DUSK_END,   1.0, 1.0, 1.0, 1.0],
	[1.0,  1.0, 1.0, 1.0, 1.0],
]

## The sky's colour through the day (the user, 2026-10-05: the caps' sky "will change color with the central
## cylinder"; "make the nights darker"): the shaft and the caps' sky discs share ceiling_material.
const SKY_KEYS := [
	[0.0,  0.018, 0.026, 0.06],
	[DAWN_START, 0.03, 0.035, 0.08],
	[0.18, 0.28, 0.20, 0.34],
	[0.205, 0.94, 0.56, 0.40],
	[0.23, 0.70, 0.70, 0.82],
	[DAY_START, 0.45, 0.68, 0.92],
	[DAY_END, 0.45, 0.68, 0.92],
	[0.77, 0.74, 0.66, 0.74],
	[0.795, 0.96, 0.50, 0.32],
	[0.82, 0.36, 0.20, 0.36],
	[DUSK_END, 0.04, 0.04, 0.09],
	[1.0,  0.018, 0.026, 0.06],
]

var time_of_day: float = 0.27  # start mid-morning, already light out
## Days since the game began; day 0 is a Monday (NpcLife schedules: weekdays, weekends, errands).
var day: int = 0
var ceiling_material: StandardMaterial3D
var sun: DirectionalLight3D
## Optional: returns the frame (right, up, back) the sun's angles are taken in. A
## cylinder station passes the local floor frame at the player -- one directional
## light can't be "overhead" everywhere on a curved floor, so it follows the
## viewer and is always overhead there. Unset: the world frame (a flat world).
var sun_frame: Callable
var station: Node3D
var env: Environment

## `ring_mesh` is StationRingBuilder's single "RingMesh" node -- floor/
## ceiling/wall are surfaces 0/1/2 of ONE ArrayMesh (see that file's own
## build() for the exact commit order this depends on), not separate
## nodes, so this sets per-SURFACE overrides rather than a whole-instance
## material_override. Must run AFTER ToonShading.apply_to_world(ring_mesh)
## -- that call overwrites every surface's material uniformly with its
## own toon.gdshader instance; these two custom shaders (already their
## own self-contained cel-banded/unshaded logic, not meant to go through
## that conversion at all) need to land last, or ToonShading clobbers them.
## `p_env` (optional) is the WorldEnvironment's Environment resource --
## ambient light tracks day/night here (bright by day -- "the station is
## too dark in the daytime," requested directly -- gently dimmer by
## night, still nowhere near the old near-black default that caused an
## earlier session's "shadow problem").
func setup(p_station: Node3D, p_sun: DirectionalLight3D, ring_mesh: MeshInstance3D,
		ceiling_height: float, wall_tile: float, p_env: Environment = null) -> void:
	station = p_station
	sun = p_sun
	env = p_env

	# Ceiling: a plain flat sky-blue material, not the cloud-photo shader
	# ("The texture above the cliffs will just be sky blue instead of the
	# cloud texture") -- no day/night texture swap on the ceiling itself;
	# the real day/night cycle (sun/moon DirectionalLight sweep, ambient
	# light) below still runs for actual gameplay lighting, just without
	# a shader-driven ceiling visual tied to it.
	ceiling_material = StandardMaterial3D.new()
	ceiling_material.albedo_color = Color(0.45, 0.68, 0.92)
	ceiling_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	ring_mesh.set_surface_override_material(1, ceiling_material)

	# Walls: explicitly NOT given the sky/cliff blend shader ("We do not
	# need it on the walls") -- surface 2 is left as whatever the station builder set.
	# gd's _build_ring() already applied (station_metal_wall.png, already
	# cel-shaded by ToonShading.apply_to_world() before this setup() call
	# runs), so this function doesn't touch it at all.

	_apply(0.0)  # first frame's worth, before _process() runs

static func sky_color(t: float) -> Color:
	for i in range(SKY_KEYS.size() - 1):
		var a: Array = SKY_KEYS[i]
		var b: Array = SKY_KEYS[i + 1]
		if t >= a[0] and t <= b[0]:
			var f := smoothstep(0.0, 1.0, (t - a[0]) / maxf(b[0] - a[0], 1e-4))
			return Color(lerpf(a[1], b[1], f), lerpf(a[2], b[2], f), lerpf(a[3], b[3], f))
	return Color(SKY_KEYS[0][1], SKY_KEYS[0][2], SKY_KEYS[0][3])


## 1 by day, 0 at night (for the fog, the lights)
func daylight() -> float:
	return 1.0 - float(_lerp_color_keyframes(time_of_day)[0])


static func _lerp_color_keyframes(t: float) -> Array:
	for i in range(COLOR_KEYFRAMES.size() - 1):
		var a: Array = COLOR_KEYFRAMES[i]
		var b: Array = COLOR_KEYFRAMES[i + 1]
		if t >= a[0] and t <= b[0]:
			var span: float = b[0] - a[0]
			var f: float = (t - a[0]) / span if span > 0.0001 else 0.0
			f = smoothstep(0.0, 1.0, f)  # eased, not linear -- smoother crossfade
			var out := []
			for k in range(1, a.size()):
				out.append(lerp(float(a[k]), float(b[k]), f))
			return out
	var last: Array = COLOR_KEYFRAMES[COLOR_KEYFRAMES.size() - 1]
	return last.slice(1)

## Sun position sweeps west->east across the DAY span (dawn->dusk); the
## moon sweeps the SAME west->east path across its own NIGHT span (dusk->
## midnight->dawn) -- "a band of moonlight that travels along the same
## path as the daylight," not literally the sun's own continuing
## position. Computed as explicit, continuous phases rather than read
## from a keyframe table sharing the day's own -- a real bug caught
## before it shipped: a single band_pos keyframe table wrapping at t=1->0
## had DIFFERENT values at those two endpoints (harmless for the sun,
## always zero-intensity at night regardless; NOT harmless for the moon,
## fully visible right through that exact wrap point -- it would have
## visibly teleported from one wall to the other at the stroke of
## midnight).
static func _sun_moon_state(t: float) -> Dictionary:
	var sun_intensity := 0.0
	var sun_pos := 0.0
	if t >= DAWN_START and t <= DUSK_END:
		sun_pos = (t - DAWN_START) / (DUSK_END - DAWN_START)
		if t < DAY_START:
			sun_intensity = smoothstep(DAWN_START, DAY_START, t)
		elif t > DAY_END:
			sun_intensity = 1.0 - smoothstep(DAY_END, DUSK_END, t)
		else:
			sun_intensity = 1.0

	var moon_intensity := 0.0
	var moon_pos := 0.0
	var night_len := (1.0 - DUSK_END) + DAWN_START
	var night_elapsed := -1.0
	if t >= DUSK_END:
		night_elapsed = t - DUSK_END
	elif t <= DAWN_START:
		night_elapsed = (1.0 - DUSK_END) + t
	if night_elapsed >= 0.0:
		moon_pos = night_elapsed / night_len
		var fade_len := night_len * 0.08
		var fade_in := smoothstep(0.0, fade_len, night_elapsed)
		var fade_out := smoothstep(0.0, fade_len, night_len - night_elapsed)
		moon_intensity = minf(fade_in, fade_out)

	return {
		"sun_intensity": sun_intensity, "sun_pos": sun_pos,
		"moon_intensity": moon_intensity, "moon_pos": moon_pos,
	}

func _process(delta: float) -> void:
	var t := time_of_day + delta / DAY_LENGTH_SECONDS
	day += int(floor(t))
	time_of_day = fposmod(t, 1.0)
	_apply(delta)

func _apply(_delta: float) -> void:
	if ceiling_material == null:
		return
	var c := _lerp_color_keyframes(time_of_day)
	var night_mix: float = c[0]
	var tint := Color(c[1], c[2], c[3])

	var sm := _sun_moon_state(time_of_day)
	var sun_intensity: float = sm["sun_intensity"]
	var sun_pos: float = sm["sun_pos"]
	var moon_intensity: float = sm["moon_intensity"]
	var moon_pos: float = sm["moon_pos"]


	var sun_color := Color(tint.r, tint.g * 0.95, tint.b * 0.85)
	var moon_color := Color(0.75, 0.8, 0.95)  # pale, cool moonlight -- distinct from the sun's warm arc

	# Ceiling is a plain flat StandardMaterial3D now (see setup()) -- no
	# shader parameters to drive; night_mix/tint/sun_center/etc. above are
	# still computed since the real sun/moon DirectionalLight + ambient
	# light below use them for actual gameplay lighting.

	if sun:
		# ONE real light standing in for whichever celestial body is up --
		# requested directly: "everything needs to be lit with full
		# daylight in the daytime and everything needs to be lit with
		# moonlight at night," not just an ambient wash at night while the
		# actual light source sits nearly off. Whichever of sun/moon is
		# the stronger influence right now drives this light's rotation,
		# color, and energy; the other's fields are simply unused while
		# it's not. -35/40 (pitch/base yaw) matches this project's
		# original static "noon" sun; the sweep just adds/subtracts yaw
		# around that, using whichever body is active's own west->east
		# position.
		var use_moon := moon_intensity > sun_intensity
		var active_pos: float = moon_pos if use_moon else sun_pos
		var active_intensity: float = maxf(sun_intensity, moon_intensity)
		var sweep_deg: float = lerp(-55.0, 55.0, active_pos)
		var local_rot := Basis.from_euler(Vector3(deg_to_rad(-35.0), deg_to_rad(40.0 + sweep_deg), 0.0))
		if sun_frame.is_valid():
			sun.global_transform.basis = (sun_frame.call() as Basis) * local_rot
		else:
			sun.rotation_degrees = Vector3(-35.0, 40.0 + sweep_deg, 0.0)
		if use_moon:
			sun.light_color = moon_color
			sun.light_energy = 0.07 + moon_intensity * 0.16  # (darker nights, the user 2026-10-05: a faint moonlight)
		else:
			sun.light_color = Color(tint.r, tint.g * 0.97, tint.b * 0.9)
			sun.light_energy = 0.2 + sun_intensity * 1.5  # "full daylight" -- brighter peak than before
		sun.shadow_enabled = active_intensity > 0.05

	if env:
		# 2.3 by day, 1.15 by night -- down from 2.8 / 1.6, then 2.0 / 1.0
		# was too dark (user, 2026-09-24); still well above the original
		# near-black 0.6 default that caused an earlier session's
		# "shadow problem", and on top of a real moonlight/daylight
		# DirectionalLight3D rather than carrying the whole scene alone.
		# (2026-10-05, the user: "make the nights darker and the lights ... more pronounced": night ambient 1.15 ->
		#  0.2, cooler; glow blooms the lit windows, signs and lamps as it gets dark)
		env.ambient_light_energy = lerp(0.13, 2.3, 1.0 - night_mix)
		env.ambient_light_color = Color(0.5, 0.5, 0.55).lerp(Color(0.32, 0.38, 0.6), night_mix)
		env.glow_enabled = true
		env.glow_intensity = lerpf(0.25, 1.1, night_mix)
		env.glow_bloom = lerpf(0.0, 0.08, night_mix)
		env.glow_hdr_threshold = lerpf(1.4, 0.9, night_mix)
		env.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	ceiling_material.albedo_color = sky_color(time_of_day)
	RenderingServer.global_shader_parameter_set("daylight", 1.0 - night_mix)
	RemakeBuilding.set_night(night_mix)

	var should_lights_be_on := night_mix > 0.5
	if should_lights_be_on != lamp_light_on:
		lamp_light_on = should_lights_be_on
		if is_inside_tree():
			get_tree().call_group("lamp_lights", "set_visible", lamp_light_on)
