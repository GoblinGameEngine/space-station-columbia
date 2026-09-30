extends SceneTree

## Names from the game bible on the generated households: sample families per town, the commonest
## names, and how given names change with age (generations).
##   ../godot/godot4 --headless --path . --script res://remake/tools/npc_names_test.gd


func _initialize() -> void:
	var st: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://remake/placement.json"))
	var t0 := Time.get_ticks_msec()
	var sur := {}
	var giv := {"young": {}, "mid": {}, "old": {}}
	var her := {}
	var shown := {}
	var n := 0
	for b in st.structures:
		if not NpcHouseholds.is_home(b):
			continue
		var hh := NpcHouseholds.of_building(1, b)
		var town := str(b.get("settlement")) if b.get("settlement") != null else "(country)"
		for h in hh.households:
			if int(shown.get(town, 0)) < 2 and town in ["Playa Verde", "Port Carrow", "Tamarack", "Fenwick", "Pelican Cove", "Bellhaven", "Harrow Falls"]:
				shown[town] = int(shown.get(town, 0)) + 1
				var ms := []
				for m in h.members:
					ms.append("%s %s (%s %d)" % [m.pinned.given_name, m.pinned.surname, m.role, m.pinned.age])
				print("%-13s %-12s %s" % [town, h.type, ", ".join(ms)])
		for m in hh.members:
			n += 1
			var p: Dictionary = m.pinned
			sur[p.surname] = int(sur.get(p.surname, 0)) + 1
			her[p.name_heritage] = int(her.get(p.name_heritage, 0)) + 1
			var band := "young" if int(p.age) < 25 else ("mid" if int(p.age) < 60 else "old")
			giv[band][p.given_name] = int(giv[band].get(p.given_name, 0)) + 1
	print("\n%d people named in %d ms" % [n, Time.get_ticks_msec() - t0])
	print("distinct surnames %d; top: %s" % [sur.size(), _top(sur, 20)])
	print("surname heritage: %s" % _top(her, 12))
	for band in ["young", "mid", "old"]:
		print("given (%s, %d distinct): %s" % [band, (giv[band] as Dictionary).size(), _top(giv[band], 18)])
	quit()


func _top(d: Dictionary, k: int) -> String:
	var ks: Array = d.keys()
	ks.sort_custom(func(a, b): return d[a] > d[b])
	var out := []
	for key in ks.slice(0, k):
		out.append("%s %d" % [key, d[key]])
	return ", ".join(out)
