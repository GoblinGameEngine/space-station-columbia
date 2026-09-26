extends RefCounted
class_name StationGeo

## The remake station's geometry: an O'Neill cylinder spun about the x axis -- a true cylinder, no
## facets.  Map coordinates are (s, x): s the arc length round the floor (0..CIRC), x along the axis
## (-HALF_LEN..HALF_LEN, 0 midway between the end caps).  Height h is measured up from the nominal
## floor, toward the axis.  Pure leaf: calls no other class_name script.
##
##   radius 3 km (the floor), length 8 km wall to wall, central shaft radius 50 m (the
##   "ceiling", 2,950 m above the floor); the far side of the floor is 6 km overhead.
##
## Conventions (the same as the earlier RingCoords, so yaws and the player's gravity carry over):
## point(s, x, 0) = (x, R cos th, R sin th) with th = s / R; up points at the axis; forward is +s;
## basis(s) = (right = +x, up, -forward).

const R := 3000.0
const LENGTH := 8000.0
const HALF_LEN := 4000.0
const SHAFT_R := 50.0
const CIRC := TAU * R


## Spin gravity (the user's spec): 0 G at the axis to TARGET_G at the floor, stepping up by
## TARGET_G / GRAVITY_BANDS across GRAVITY_BANDS equal concentric bands -- a step function, not a
## smooth ramp.  (static vars: tunable live from DevBridge.)
static var TARGET_G := 9.8
static var GRAVITY_BANDS := 10
const AXIS := Vector3.RIGHT
## true while the loading screen is up (RemakeStation sets it): builders that spread their work over
## frames to keep the game smooth may then take much longer frames -- nobody is watching them
static var loading := true          # the cylinder's axis (world x)


static func gravity_at(radial_len: float) -> float:
	var band_width := R / float(GRAVITY_BANDS)
	var band := clampi(ceili(radial_len / band_width), 0, GRAVITY_BANDS)
	return (float(band) / GRAVITY_BANDS) * TARGET_G


static func point(s: float, x: float, h: float = 0.0) -> Vector3:
	var th := s / R
	var r := R - h
	return Vector3(x, r * cos(th), r * sin(th))


static func up(s: float) -> Vector3:
	var th := s / R
	return Vector3(0.0, -cos(th), -sin(th))


static func forward(s: float) -> Vector3:
	var th := s / R
	return Vector3(0.0, -sin(th), cos(th))


static func basis(s: float, yaw: float = 0.0) -> Basis:
	## (right = +x, up, back = -forward), turned by yaw about up (a front at local -z then faces
	## (x: -sin yaw, s: cos yaw) on the map).
	var b := Basis(Vector3.RIGHT, up(s), -forward(s))
	return b if yaw == 0.0 else b.rotated(up(s), yaw)


static func s_of(p: Vector3) -> float:
	return fposmod(atan2(p.z, p.y), TAU) * R


static func h_of(p: Vector3) -> float:
	return R - Vector2(p.y, p.z).length()


static func wrap_ds(ds: float) -> float:
	return fposmod(ds + CIRC * 0.5, CIRC) - CIRC * 0.5


## The far-side image (remake/farside.png, baked by remake/scenes/FarsideBake.tscn): 1 m / px,
## FARSIDE_W m of s across (the circumference, padded), FARSIDE_H m of x down from -FARSIDE_H/2.
const FARSIDE_W := 18944.0         # farside_bake.gd: TILES_S x TILE_M
const FARSIDE_H := 8192.0


static func farside_uv(s: float, x: float) -> Vector2:
	return Vector2(fposmod(s, CIRC) / FARSIDE_W, (x + FARSIDE_H * 0.5) / FARSIDE_H)

