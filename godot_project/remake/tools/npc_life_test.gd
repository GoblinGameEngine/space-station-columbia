extends SceneTree

## NpcLife: determinism, where people are through the week, how they travel, and routes.
##   ../godot/godot4 --headless --path . --script res://remake/tools/npc_life_test.gd [-- people]


func _initialize() -> void:
	var a := OS.get_cmdline_user_args()
	var n := int(a[0]) if a.size() > 0 else 600
	var t0 := Time.get_ticks_msec()
	var life := NpcLife.shared()
	print("load %d ms, %d people" % [Time.get_ticks_msec() - t0, life.people.size()])
	var pids: Array = life.people.keys()
	pids.sort()
	var step := maxi(1, pids.size() / n)
	var sample := []
	for i in range(0, pids.size(), step):
		sample.append(pids[i])
	# determinism: a fresh instance gives the same timelines
	var fresh := NpcLife.new()
	fresh._load()
	var same := 0
	for pid in sample.slice(0, 100):
		if str(fresh.timeline(pid, 3)) == str(life.timeline(pid, 3)):
			same += 1
	print("determinism: %d/100 identical" % same)
	# the week: share away from home by hour, what they're doing, modes
	var t1 := Time.get_ticks_msec()
	var modes := {}
	var whats := {}
	var trips := 0
	var bad := 0
	for day in 7:
		var row := []
		for h in [3, 7, 8, 10, 12, 15, 17, 19, 21, 23]:
			var away := 0
			var moving := 0
			for pid in sample:
				var s := life.state(pid, day, float(h))
				if s.kind != "home":
					away += 1
				if s.kind == "trip":
					moving += 1
			row.append("%02d:%3d%%%s" % [h, 100 * away / sample.size(), "" if moving == 0 else "(%d)" % moving])
		print("day %d %s  %s" % [day, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][day], " ".join(row)])
		for pid in sample:
			var tl := life.timeline(pid, day)
			var last := 0.0
			for s in tl:
				if float(s.t0) < last - 1e-4 or float(s.t1) < float(s.t0) - 1e-4:
					bad += 1
				last = float(s.t1)
				if s.kind == "trip":
					trips += 1
					modes[s.mode] = modes.get(s.mode, 0) + 1
				if s.kind == "at" or s.kind == "out":
					whats[s.what] = whats.get(s.what, 0) + 1
	print("timelines: %.1f ms per person-day; out-of-order segments %d" % [float(Time.get_ticks_msec() - t1) / (7.0 * sample.size()), bad])
	var ks: Array = modes.keys()
	ks.sort_custom(func(x, y): return modes[x] > modes[y])
	var ms := []
	for k in ks:
		ms.append("%s %.1f%%" % [k, 100.0 * modes[k] / trips])
	print("trips %d; modes: %s" % [trips, ", ".join(ms)])
	var wk: Array = whats.keys()
	wk.sort_custom(func(x, y): return whats[x] > whats[y])
	var ws := []
	for k in wk.slice(0, 24):
		ws.append("%s %d" % [k, whats[k]])
	print("stays in a week (%d people): %s" % [sample.size(), ", ".join(ws)])
	# a few people's Tuesdays, and their [LIFE] card
	for pid in [sample[5], sample[40], sample[77]]:
		print("\n%s (%s, %d)" % [pid, life.person(pid).occupation, int(life.person(pid).age)])
		for s in life.timeline(pid, 1):
			print("   %s-%s %-5s %-10s %s %s" % [NpcLife._clock(float(s.t0)), NpcLife._clock(float(s.t1)), s.kind, s.what, life.place_words(s.uid) if s.kind != "trip" else "", s.get("mode", "")])
		print(life.card(pid, 1, 12.0))
	# routes
	var t2 := Time.get_ticks_msec()
	var rl := 0.0
	var straight := 0.0
	var nr := 0
	for pid in sample.slice(0, 200):
		var P := life.person(pid)
		if not P.has("work"):
			continue
		var r := NpcPlaces.route(P.home, NpcPlaces.unit(P.work).building)
		rl += NpcPlaces.route_length(r)
		straight += NpcPlaces.dist(life.door(P, ""), life.door(P, P.work))
		nr += 1
	print("\nroutes home->work: %d, %.1f ms each; street/straight distance %.2f" % [nr, float(Time.get_ticks_msec() - t2) / maxf(1, nr), rl / maxf(1.0, straight)])
	quit()
