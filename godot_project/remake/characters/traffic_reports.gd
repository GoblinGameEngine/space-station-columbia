extends RefCounted
class_name TrafficReports

## What the road users find wrong with the roads, reported as they drive (the user, 2026-10-09: "Have the NPCs report to
## you misplaced road signs and malfunctioning road layouts. This way we can allow the game to run on it's own and
## playtest itself."). Every report is a kind at a place -- the same kind within 10 m is one report, counted -- with the
## town, the road, what the reporter saw, and who saw it. Saved to user://traffic_reports.json (SAVE_S apart, and on
## quit); tools/traffic_reports.py reads it, and the self-playtest (TrafficSelfTest: --selftest) tours the towns to
## gather them.
##
## Kinds:
##   sign_no_junction   a stop or yield sign facing traffic with no junction within 30 m of it
##   sign_in_lane       a sign standing in the lane a driver is driving
##   sign_hit           a sign knocked down by a vehicle (it stood where vehicles go)
##   turn_too_tight     a route's turn tighter than a car can steer (under MIN_R), after rounding
##   no_route           no road route between two places a trip links
##   off_route          a car on its wheels more than 3 m off its route for 2 s: the road can't be driven as drawn
##   stuck              a car stood unable to go for 60 s with its driver wanting to (what blocks it is noted)
##   crash_static       a car driven into something fixed (a building, a pole, a bridge rail ...)
##   no_parking         nowhere legal to park within reach of a door

const PATH := "user://traffic_reports.json"
const SAVE_S := 30.0
const MIN_R := 2.6                   # m: the tightest turn a town car steers (its lock)

static var items := {}               # key -> report
static var _dirty := false
static var _saved_ms := 0


static func file(kind: String, at: Vector2, what: String, by := "") -> void:
	var key := "%s@%d,%d" % [kind, floori(fposmod(at.x, StationGeo.CIRC) / 10.0), floori(at.y / 10.0)]
	var now := Time.get_unix_time_from_system()
	var r: Dictionary = items.get(key, {})
	if r.is_empty():
		r = {"kind": kind, "s": snappedf(fposmod(at.x, StationGeo.CIRC), 0.1), "x": snappedf(at.y, 0.1), "what": what, "n": 0,
			"first": now, "by": [], "town": _town(at), "road": _road_name(at)}
		items[key] = r
	r.n = int(r.n) + 1
	r.last = now
	if by != "" and (r.by as Array).size() < 5 and not (r.by as Array).has(by):
		(r.by as Array).append(by)
	_dirty = true


static func tick() -> void:
	## Saved now and then (NpcTraffic calls this every frame: it's one clock test).
	if _dirty and Time.get_ticks_msec() - _saved_ms > SAVE_S * 1000.0:
		save()


static func save() -> void:
	_saved_ms = Time.get_ticks_msec()
	_dirty = false
	var f := FileAccess.open(PATH, FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify({"_about": "Road users' reports of what's wrong with the roads (TrafficReports)",
		"saved": Time.get_datetime_string_from_system(), "reports": items.values()}, "\t"))
	f.close()


static func load_saved() -> void:
	## Carry on from the last session's reports (the counts add up across runs).
	if not FileAccess.file_exists(PATH):
		return
	var d = JSON.parse_string(FileAccess.get_file_as_string(PATH))
	if typeof(d) != TYPE_DICTIONARY:
		return
	for r in d.get("reports", []):
		var key := "%s@%d,%d" % [r.kind, floori(float(r.s) / 10.0), floori(float(r.x) / 10.0)]
		items[key] = r


static func clear() -> void:
	items.clear()
	_dirty = true


static func summary() -> String:
	var by_kind := {}
	for r in items.values():
		by_kind[r.kind] = int(by_kind.get(r.kind, 0)) + 1
	return "%d reports: %s" % [items.size(), str(by_kind)]


static var _centres := {}


static func _town(at: Vector2) -> String:
	if _centres.is_empty() and FileAccess.file_exists("res://remake/law/settlements.json"):
		for st in JSON.parse_string(FileAccess.get_file_as_string("res://remake/law/settlements.json")).settlements:
			if st.get("centre") != null:
				_centres[str(st.name)] = Vector2(float(st.centre[0]), float(st.centre[1]))
	var best := ""
	var bd := 4000.0
	for t in _centres:
		var c: Vector2 = _centres[t]
		var d := Vector2(StationGeo.wrap_ds(c.x - at.x), c.y - at.y).length()
		if d < bd:
			bd = d
			best = str(t)
	return best


static func _road_name(at: Vector2) -> String:
	var a := NpcPlaces._attach_on(at, ["street", "main", "county", "hwy", "gravel", "alley"])
	if a.is_empty():
		return ""
	var e: Array = NpcPlaces._edge(int(a[0]))
	var rd := NpcPlaces._road(int(e[2]))
	return "%s (%s)" % [str(rd.get("name", "")), str(rd.get("cls", ""))]
