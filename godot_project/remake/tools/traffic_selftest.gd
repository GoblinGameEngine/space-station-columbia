extends Node
class_name TrafficSelfTest

## The game playtesting its own roads (the user, 2026-10-09: "allow the game to run on it's own and playtest itself").
## Started by `godot4 --path . -- --selftest` (or added from DevBridge), once the world is in: it tours every town at
## its rush hours -- fast travel to the town hall, then to the main grocery, DWELL_S at each -- while the drivers about
## report what they find wrong with the roads (TrafficReports). Each stop's crashes, trips and frame rate are logged;
## the reports are saved to user://traffic_reports.json, and `-- --selftest --quit-after-tour` quits at the end.
## tools/traffic_reports.py reads them.

const DWELL_S := 120.0
const RUSH := [0.31, 0.36, 0.70, 0.74]             # 7:26, 8:38, 16:48, 17:45
const STOPS := ["Town Hall", "Grocery", "Tram stop"]

var _plan: Array = []                              # [[town, dest]]
var _i := -1
var _t := 0.0
var _crashes0 := 0
var _fps: Array = []
var log_lines: Array = []


func _ready() -> void:
	name = "TrafficSelfTest"
	var gm := get_tree().root.find_child("GameMenu", true, false)
	if gm == null or not gm.has_method("_fast_travel_groups"):
		push_warning("TrafficSelfTest: no GameMenu to travel with")
		queue_free()
		return
	for g in gm._fast_travel_groups():
		if str(g.name) == "Landmarks":
			continue
		var picked := 0
		for want in STOPS:
			for d in g.dests:
				if str(d.name).begins_with(want) and picked < 2:
					_plan.append([str(g.name), d])
					picked += 1
					break
	print("TrafficSelfTest: %d stops, %.0f s each (%s)" % [_plan.size(), DWELL_S, TrafficReports.summary()])
	_next()


func _next() -> void:
	if _i >= 0:
		_close_stop()
	_i += 1
	if _i >= _plan.size():
		TrafficReports.save()
		print("TrafficSelfTest: tour done -- %s; saved to %s" % [TrafficReports.summary(), ProjectSettings.globalize_path(TrafficReports.PATH)])
		if OS.get_cmdline_user_args().has("--quit-after-tour"):
			get_tree().quit()
		queue_free()
		return
	var stop: Array = _plan[_i]
	var sky := get_tree().current_scene.get_node_or_null("DaySkySystem")
	if sky:
		sky.time_of_day = RUSH[_i % RUSH.size()]
	var gm := get_tree().root.find_child("GameMenu", true, false)
	gm._fast_travel(stop[1], 0, "%s, %s" % [stop[0], stop[1].name])
	if sky:
		sky.time_of_day = RUSH[_i % RUSH.size()]           # (the trip's minutes back off: a rush hour each stop)
	_t = DWELL_S
	_crashes0 = int(RoadDriver.tally.get("crashes", 0))
	_fps.clear()


func _close_stop() -> void:
	var stop: Array = _plan[_i]
	var tr := get_tree().current_scene.find_child("NpcTraffic", true, false)
	var moving := 0
	if tr:
		for id in tr.live:
			if tr.live[id].sim != null:
				moving += 1
	var fps := 0.0
	for f in _fps:
		fps += f
	fps /= maxi(1, _fps.size())
	var line := "%-18s %-22s crashes %d  moving at the end %d  fps %.0f  trips %s  %s" % [stop[0], str(stop[1].name),
		int(RoadDriver.tally.get("crashes", 0)) - _crashes0, moving, fps, str(tr.trips if tr else {}), TrafficReports.summary()]
	log_lines.append(line)
	print("TrafficSelfTest: " + line)
	TrafficReports.save()


func _process(delta: float) -> void:
	if _i < 0 or _i >= _plan.size():
		return
	_fps.append(Engine.get_frames_per_second())
	_t -= delta
	if _t <= 0.0:
		_next()
