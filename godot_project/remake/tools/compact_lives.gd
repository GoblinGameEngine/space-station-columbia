extends SceneTree

## Packs every settlement's lives (characters/lives/<Town>.json) into the columns the game reads (<Town>.bin,
## NpcLife.compact) -- bake_lives.gd writes both; this redoes the .bin from the JSON without baking again.
##   godot4 --headless --path . --script res://remake/tools/compact_lives.gd


func _initialize() -> void:
	var dir := NpcLife.DIR
	var seed := int((JSON.parse_string(FileAccess.get_file_as_string(NpcLife.PATH)) as Dictionary).seed)
	for fn in DirAccess.get_files_at(dir):
		if not fn.ends_with(".json") or fn.begins_with("_"):
			continue
		var t0 := Time.get_ticks_msec()
		var ppl: Dictionary = (JSON.parse_string(FileAccess.get_file_as_string(dir + fn)) as Dictionary).get("people", {})
		var f := FileAccess.open(dir + fn.get_basename() + ".bin", FileAccess.WRITE)
		f.store_var(NpcLife.compact(ppl, seed))
		f.close()
		print("%s: %d people, %.1f MB, %d ms" % [fn.get_basename(), ppl.size(), FileAccess.get_file_as_bytes(dir + fn.get_basename() + ".bin").size() / 1048576.0,
			Time.get_ticks_msec() - t0])
	quit()
