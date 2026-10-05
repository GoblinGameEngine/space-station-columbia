extends Node
class_name VehiclePilot

## An NPC at the controls of any vehicle (2026-10-05: every vehicle takes a player's controls and an NPC's): a child
## of the vehicle that, each physics tick, steers it toward its target through the same inputs a player's keys give --
## drive_input (throttle, steer, handbrake) for a ground vehicle, fly_input (fwd, turn, lift) for one that flies or
## floats. Air: it climbs to its cruise height above the ground first, flies over, and lets down at the target.
## A boat keeps to the water (its own physics refuse land). A trailer has no controls: hitch it to what tows it.
##
##   var p := VehiclePilot.drive(vehicle, target, 40.0)    # start (cruise 40 m up, if it flies)
##   p.arrived  -> emitted on reaching the target (within arrive_r); the vehicle is then left stopped

signal arrived

var vehicle: RemakeAirVehicle
var target := Vector3.ZERO
var cruise := 40.0                   # m above the ground (fliers)
var arrive_r := 6.0                  # m
var speed_kmh := 0.0                 # a ground vehicle's cruising speed; 0: its own (60 % of its top)
var done := false


static func drive(v: RemakeAirVehicle, to: Vector3, cruise_m := 40.0) -> VehiclePilot:
	var old := v.get_node_or_null("VehiclePilot")
	if old:
		old.queue_free()
	var p := VehiclePilot.new()
	p.name = "VehiclePilot"
	p.vehicle = v
	p.target = to
	p.cruise = cruise_m
	v.add_child(p)
	return p


func stop() -> void:
	done = true
	if vehicle is RemakeGroundVehicle:
		(vehicle as RemakeGroundVehicle).drive_input = {"throttle": 0.0, "steer": 0.0, "handbrake": true}
	else:
		vehicle.fly_input = {"fwd": 0.0, "turn": 0.0, "lift": 0.0}


func _physics_process(_delta: float) -> void:
	if done or vehicle == null or vehicle.pilot != null:   # (a player took the seat: theirs to drive)
		return
	var p := vehicle.global_position
	var s := StationGeo.s_of(p)
	var up := StationGeo.up(s)
	var to := target - p
	var flat := to - up * to.dot(up)
	var dist := flat.length()
	var fwd := -vehicle.global_transform.basis.z
	fwd = (fwd - up * fwd.dot(up)).normalized()
	var ang := fwd.signed_angle_to(flat.normalized(), up) if dist > 0.1 else 0.0   # + : the target is to the left
	var ground_h := MapTerrain.elevation(s, p.x)
	var h := StationGeo.h_of(p) - ground_h                  # m above the ground
	if vehicle is RemakeGroundVehicle:
		var gv := vehicle as RemakeGroundVehicle
		if dist < arrive_r:
			stop()
			arrived.emit()
			return
		var top := float(gv.phys.get("top_kmh", 100.0)) / 3.6
		var cruise_v := (speed_kmh / 3.6) if speed_kmh > 0.0 else top * 0.6
		var want_v := minf(cruise_v, maxf(2.0, dist * 0.5)) * (0.4 if absf(ang) > 0.8 else 1.0)
		gv.drive_input = {"throttle": clampf((want_v - gv._speed) * 0.4, -1.0, 1.0), "steer": clampf(-ang * 2.5, -1.0, 1.0)}
		return
	# it flies or floats
	var lift := 0.0
	var fwd_in := 0.0
	if vehicle.can_climb:
		var want_h := cruise if dist > arrive_r * 3.0 else 0.0     # (over the target: down)
		lift = clampf((want_h - h) / 6.0, -1.0, 1.0)
		if dist <= arrive_r * 3.0 and h < 1.0:
			lift = -0.3
		# forward once it's up (or near): never through the treetops on the way up
		fwd_in = clampf(dist / 30.0, 0.15, 1.0) if (h > minf(cruise * 0.6, 15.0) or dist < arrive_r * 3.0) else 0.0
	else:
		fwd_in = clampf(dist / 20.0, 0.2, 1.0)
	fwd_in *= clampf(1.2 - absf(ang), 0.0, 1.0)                   # (turn first, then go)
	if dist < arrive_r and (not vehicle.can_climb or h < 1.5):
		stop()
		arrived.emit()
		return
	vehicle.fly_input = {"fwd": fwd_in, "turn": clampf(-ang * 2.0, -1.0, 1.0), "lift": lift}
