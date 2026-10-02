extends RefCounted
class_name TransitDemand

## How full the trams are, where and when (the user, 2026-10-01: "fewer people the further it gets from
## centers of population ... centers of population change with specific events and times of day").
##
##   load_at(p, hour, day)   0..1: the share of a tram's seats taken at (s, x)
##
## Every settlement draws riders by its population, falling off with distance from its centre (a
## walking catchment, CATCH m); the draw changes with the hour (the towns of work fill in the morning,
## the home villages in the evening, everyone sleeps) and with the station's calendar of events
## (remake/events.json, tools/make_events.py: a fair, a regatta, a game day multiplies a town's draw
## for its hours). Open country between towns rides nearly empty.

const CATCH := 700.0                  # m: a centre's draw falls to 1/e this far out
const FULL := 30000.0                # weighted draw that fills a tram (calibrated: a city centre at the morning peak ~0.9, a village ~0.3, open country at noon <0.1)
const WORK_TIERS := ["city", "town"]

static var _sets: Array = []          # [centre Vector2, pop, tier, name]
static var _events: Array = []
static var _start := {"y": 2752, "m": 5, "d": 24}
static var _start_wd := 2             # a Wednesday (0 = Monday)
static var _date_cache := {}


static func _load() -> void:
	if not _sets.is_empty():
		return
	var st = JSON.parse_string(FileAccess.get_file_as_string("res://remake/law/settlements.json"))
	if st is Dictionary:
		for r in st.settlements:
			if r.get("centre") != null:
				_sets.append([Vector2(float(r.centre[0]), float(r.centre[1])), float(r.pop), str(r.tier), str(r.name)])
	var ev = JSON.parse_string(FileAccess.get_file_as_string("res://remake/events.json")) if FileAccess.file_exists("res://remake/events.json") else null
	if ev is Dictionary:
		_events = ev.events
		var parts := str(ev.get("start_date", "2752-05-24")).split("-")
		_start = {"y": int(parts[0]), "m": int(parts[1]), "d": int(parts[2])}
		_start_wd = int(ev.get("start_weekday", 2))


static func load_at(p: Vector2, hour: float, day: int) -> float:
	## The share of seats taken at p.
	_load()
	var h := fposmod(hour, 24.0)
	var draw := 0.0
	for st in _sets:
		var c: Vector2 = st[0]
		var d := Vector2(StationGeo.wrap_ds(p.x - c.x), p.y - c.y).length()
		if d > CATCH * 4.0:
			continue
		draw += float(st[1]) * _when(str(st[2]), h) * _events_draw(str(st[3]), h, day) * exp(-d / CATCH)
	var awake := _awake(h)
	return clampf(1.0 - exp(-draw * awake / FULL), 0.02, 0.97)


static func _awake(h: float) -> float:
	## How much of the station is about at all: the night is empty, the peaks full.
	var peak := exp(-pow((h - 8.0) / 1.2, 2.0)) + exp(-pow((h - 17.3) / 1.4, 2.0))
	var day := smoothstep(5.0, 7.0, h) * (1.0 - smoothstep(22.0, 24.0, h))
	return 0.08 + day * (0.45 + 0.9 * peak)


static func _when(tier: String, h: float) -> float:
	## A town's draw by the hour: the towns of work pull in the morning and through the day, the home
	## villages in the evening.
	var morning := exp(-pow((h - 8.0) / 1.5, 2.0))
	var evening := exp(-pow((h - 17.5) / 1.8, 2.0))
	if tier in WORK_TIERS:
		return 1.0 + 0.6 * morning + 0.3 * smoothstep(9.0, 11.0, h) * (1.0 - smoothstep(16.0, 18.0, h))
	return 1.0 + 0.7 * evening


static func _events_draw(town: String, h: float, day: int) -> float:
	var k := 1.0
	for e in _events:
		var tw := str(e.town)
		if tw != "*" and tw != town:
			continue
		var hr: Array = e.hours
		var h0 := float(hr[0])
		var h1 := float(hr[1])
		var on_today := _on(e.when, day) and h >= h0 and h < h1
		var on_eve := h1 > 24.0 and _on(e.when, day - 1) and h + 24.0 < h1      # (past midnight)
		if on_today or on_eve:
			k += float(e.draw)
	return k


static func events_on(day: int) -> Array:
	## The events of a game day (for the PDA, signs and the like).
	_load()
	var out: Array = []
	for e in _events:
		if _on(e.when, day):
			out.append(e)
	return out


# -- the calendar -----------------------------------------------------------------------------------

static func date(day: int) -> Dictionary:
	## {y, m, d, wd (0 = Monday)} of a game day (day 0 = the start date).
	if _date_cache.has(day):
		return _date_cache[day]
	_load()
	var jd := _jdn(int(_start.y), int(_start.m), int(_start.d)) + day
	var out := _from_jdn(jd)
	out["wd"] = posmod(_start_wd + day, 7)
	if _date_cache.size() > 64:
		_date_cache.clear()
	_date_cache[day] = out
	return out


static func _on(rule: Dictionary, day: int) -> bool:
	var dt := date(day)
	var m := int(dt.m)
	var d := int(dt.d)
	if rule.has("months") and not (rule.months as Array).has(float(m)) and not (rule.months as Array).has(m):
		return false
	if rule.has("md"):
		return _md(str(rule.md)) == Vector2i(m, d)
	if rule.has("md_range"):
		var a := _md(str(rule.md_range[0]))
		var b := _md(str(rule.md_range[1]))
		var x := m * 100 + d
		return x >= a.x * 100 + a.y and x <= b.x * 100 + b.y
	if rule.has("weekly"):
		return (rule.weekly as Array).has(float(dt.wd)) or (rule.weekly as Array).has(int(dt.wd))
	if rule.has("nth"):
		var n := int(rule.nth[0])
		var wd := int(rule.nth[1])
		var month := int(rule.nth[2])
		for back in int(rule.get("span_days", 1)):
			var t := date(day - back)
			if int(t.m) == month and int(t.wd) == wd:
				var k := (int(t.d) - 1) / 7 + 1
				if n == k or (n == -1 and int(t.d) + 7 > _month_len(int(t.y), month)):
					return true
		return false
	if rule.has("sat_near"):
		var target := _md(str(rule.sat_near))
		var jt := _jdn(int(dt.y), target.x, target.y)
		var j := _jdn(int(dt.y), m, d)
		return int(dt.wd) == 5 and absi(j - jt) <= 3
	if rule.has("easter_monday"):
		var e := _easter(int(dt.y))
		return _jdn(int(dt.y), m, d) == _jdn(int(dt.y), e.x, e.y) + 1
	return false


static func _md(s: String) -> Vector2i:
	var p := s.split("-")
	return Vector2i(int(p[0]), int(p[1]))


static func _jdn(y: int, m: int, d: int) -> int:
	var a := (14 - m) / 12
	var yy := y + 4800 - a
	var mm := m + 12 * a - 3
	return d + (153 * mm + 2) / 5 + 365 * yy + yy / 4 - yy / 100 + yy / 400 - 32045


static func _from_jdn(j: int) -> Dictionary:
	var a := j + 32044
	var b := (4 * a + 3) / 146097
	var c := a - 146097 * b / 4
	var d := (4 * c + 3) / 1461
	var e := c - 1461 * d / 4
	var m := (5 * e + 2) / 153
	return {"y": 100 * b + d - 4800 + m / 10, "m": m + 3 - 12 * (m / 10), "d": e - (153 * m + 2) / 5 + 1}


static func _month_len(y: int, m: int) -> int:
	return _jdn(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1) - _jdn(y, m, 1)


static func _easter(y: int) -> Vector2i:
	## Western Easter (the computus, kept aboard).
	var a := y % 19
	var b := y / 100
	var c := y % 100
	var d := b / 4
	var e := b % 4
	var f := (b + 8) / 25
	var g := (b - f + 1) / 3
	var h := (19 * a + b - d - g + 15) % 30
	var i := c / 4
	var k := c % 4
	var l := (32 + 2 * e + 2 * i - h - k) % 7
	var m := (a + 11 * h + 22 * l) / 451
	var month := (h + l - 7 * m + 114) / 31
	var day := (h + l - 7 * m + 114) % 31 + 1
	return Vector2i(month, day)
