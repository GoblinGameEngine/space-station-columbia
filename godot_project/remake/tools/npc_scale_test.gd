extends SceneTree

## Scale and distinctness (scale_survey.md 2.5): generate many people with their outfits (no
## geometry: traits + clothes choice are all that decide a look) and measure how distinguishable
## they are by what the eye actually uses in a crowd -- hair (style, colour), head covering, the top
## garment and its colour, skin, height, build, glasses (McDonnell et al. 2008/2009).
##   ../godot/godot4 --headless --path . --script res://remake/tools/npc_scale_test.gd -- 100000
## Reports: people per second, distinct looks, the largest look-alike group, and the chance that a
## crowd of 24 on screen holds two people who look the same.

func _init() -> void:
	var a := OS.get_cmdline_user_args()
	var n := int(a[0]) if a.size() > 0 else 20000
	var db := NpcTraits.shared()
	var pops := ["stable_town", "rust_belt", "exurban", "county_seat", "college_town", "lake_resort"]
	var looks := {}
	var t0 := Time.get_ticks_msec()
	for i in n:
		var pid := "S%d:%d" % [i / 3, i % 3]
		var v := db.person(5, pid, ["L0", "L1"], pops[i % pops.size()])
		var of := NpcGarments.outfit(v, 5, pid)
		var sig := NpcCharacter.signature(v, of)
		looks[sig] = looks.get(sig, 0) + 1
		if i > 0 and i % 20000 == 0:
			print("  %d people, %.0f s" % [i, (Time.get_ticks_msec() - t0) / 1000.0])
	var secs := (Time.get_ticks_msec() - t0) / 1000.0
	var sizes: Array = looks.values()
	sizes.sort()
	sizes.reverse()
	# P(two of k random people share a look) = 1 - prod over the draw of (1 - p_same), from the
	# empirical look frequencies: sum of p_i^2 is the chance two random people share a look
	var sum_p2 := 0.0
	for c in sizes:
		var p := float(c) / n
		sum_p2 += p * p
	var k := 24
	var pairs := k * (k - 1) / 2.0
	var p_twin := 1.0 - pow(1.0 - sum_p2, pairs)
	print("people %d in %.1f s (%.0f per second, traits + outfit)" % [n, secs, n / secs])
	print("distinct looks %d; largest look-alike group %d (%.3f%%); groups of one %d" % [looks.size(), sizes[0], 100.0 * sizes[0] / n, sizes.count(1)])
	print("two random people look alike: %.5f; a crowd of %d holds a look-alike pair: %.3f" % [sum_p2, k, p_twin])
	quit()
