class_name FleetBodies

## The fleet's modular bodies (remake/blender/fleet/build.py writes remake/vehicles/fleet/fleet_bodies.json): a road
## vehicle type -> its blueprint (the tokens the game assembles on the tube frame), its board and its package.
## The Carrow wagon (remake/blender/wagon/carrow_wagon.py) is entered here too.

const PATH := "res://remake/vehicles/fleet/fleet_bodies.json"
const WAGON := {"blueprint": "res://remake/vehicles/wagon/carrow_wagon.blueprint.json", "standard": "SW180", "style": "carrow",
	"board": "carrow_k28", "phys": "station_wagon", "half_w": 0.93, "height": 2.06, "nose": 2.28, "tail": -2.36, "floor": 0.55, "driver": "L"}
static var _types := {}


static func types() -> Dictionary:
	if _types.is_empty():
		if FileAccess.file_exists(PATH):
			var d = JSON.parse_string(FileAccess.get_file_as_string(PATH))
			if d is Dictionary:
				_types = (d.get("types", {}) as Dictionary).duplicate()
		_types["station_wagon"] = WAGON
	return _types


static func has(vtype: String) -> bool:
	return types().has(vtype)


static func of(vtype: String) -> Dictionary:
	return types().get(vtype, {})


static func board_path(board: String) -> String:
	return "res://remake/vehicles/chassis/%s.glb" % board


static func warm_all(only: Array = []) -> void:
	## Prepare bodies' plans on worker threads (at load), so the first of each type built waits for nothing: the given
	## types', or every one.
	for t in types():
		if only.is_empty() or only.has(t):
			VehicleBody.warm(str(types()[t].blueprint))


static func strip_board(board: Node3D) -> void:
	## Only the pods, wheels and motors show (through the arches); the deck and its parts are under the floor.
	for n in board.find_children("*", "Node3D", true, false):
		var nm := str(n.name)
		if nm.begins_with("mount_") or nm.begins_with("rib_") or nm.begins_with("bulkhead_") or nm.begins_with("keel") \
				or nm == "gunwale" or nm == "controller" or nm.begins_with("span_") or nm.begins_with("cap_") or nm == "socket" \
				or nm.begins_with("crate_") or nm.begins_with("cross_") or nm.begins_with("outrigger_") or nm.begins_with("truss_") \
				or nm.begins_with("cassette_"):
			n.queue_free()
