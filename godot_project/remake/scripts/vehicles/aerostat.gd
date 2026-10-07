extends RemakeFleetCraft
class_name RemakeAerostat

## The personal aerostat (2026-10-05: modular, as the rest of the fleet -- research/vehicles/aerostat/AEROSTATS.md): a
## glazed cabin for four on a Steward keel under a round balloon, four ducted lift fans on arms that tilt forward to
## drive. Its body is the fleet's "personal_aerostat" (remake/blender/fleet/specs.py AP460); it flies as every
## RemakeAirVehicle does (RemakeFleetCraft). The map's aerostats are these; the summoned one is the red variant.


func _init(t := "personal_aerostat") -> void:
	super(t)
	max_speed = 150.0 / 3.6              # 150 km/h
	accel = 5.0
	brake = 7.0
	turn_rate = 0.6
	climb_speed = 5.0
	floats = true                        # (its cabin's hull rides on water)
	buoyant = true                       # (holds its pressure altitude: AirVehicle.buoyant)
