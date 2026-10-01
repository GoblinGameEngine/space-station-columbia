extends SceneTree

## Writes res://remake/transit.json (TransitNet.export_json): the tram and train lines with their
## stops, for the map tools (tools/parking_lots.py) and to check the network. Run after the places and
## paths are baked:
##   godot4 --headless --path . --script res://remake/tools/bake_transit.gd


func _init() -> void:
	TransitNet.export_json()
	for l in TransitNet.lines():
		var pnr := 0
		for sp in l.stops:
			if sp.get("pnr", false):
				pnr += 1
		print("%s: %.1f km, %d stops (%d park & ride)" % [l.name, float(l.length) / 1000.0, (l.stops as Array).size(), pnr])
	quit()
