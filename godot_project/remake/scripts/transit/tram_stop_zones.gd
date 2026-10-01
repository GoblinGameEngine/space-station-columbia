extends RefCounted
class_name TramStopZones

## The kerb at every tram stop where no one may park (research/law 02_cities.md, "tram stop zones":
## the law's tram_stop_zone, both kerbs, either side of the stop). The stops come from
## remake/transit.json (remake/tools/bake_transit.gd).

static var _stops: Array = []              # Vector2 (s, x)
static var _half := -1.0


static func _load() -> void:
	if _half >= 0.0:
		return
	_half = 45.72
	var law = JSON.parse_string(FileAccess.get_file_as_string("res://remake/law/ordinances.json"))
	if law is Dictionary and law.has("tram_stop_zone"):
		_half = float(law.tram_stop_zone.half_length_m)
	var tr = JSON.parse_string(FileAccess.get_file_as_string("res://remake/transit.json"))
	if tr is Dictionary:
		for l in tr.get("lines", []):
			for sp in l.stops:
				_stops.append(Vector2(float(sp.s), float(sp.x)))


static func inside(p: Vector2, margin := 0.0) -> bool:
	## Is the kerb at (s, x) within a stop's zone (plus margin m: half a car)?
	_load()
	for q in _stops:
		if Vector2(StationGeo.wrap_ds(p.x - q.x), p.y - q.y).length() < _half + margin:
			return true
	return false
