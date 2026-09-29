extends SceneTree

## Parity test: the game's trait generator (NpcTraits) against the Python tool (traits.py), which
## must produce identical people -- the tools preview what the game makes.
##   python3 tools/charref/traits.py -n 2000 --dump /tmp/p.json [--pop rust_belt] [--layers L0,L1]
##   ../godot/godot4 --headless --path godot_project --script res://remake/tools/npc_parity.gd -- /tmp/p.json
## Prints the mismatches (first 20) and a count; numbers compare to 1e-9.

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	var ref: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var db := NpcTraits.new()
	db.load_file(NpcTraits.PATH)
	var layers: Array = ref.layers if ref.layers != null else []
	var pop: String = ref.pop if ref.pop != null else ""
	var bad := 0
	var shown := 0
	var t0 := Time.get_ticks_usec()
	for p in ref.people:
		var mine := db.person(int(ref.seed), p.id, layers, pop)
		for k in p.v:
			if not _same(p.v[k], mine.get(k)):
				bad += 1
				if shown < 20:
					shown += 1
					print("%s %s: python %s  godot %s" % [p.id, k, p.v[k], mine.get(k)])
	var us := (Time.get_ticks_usec() - t0) / float(ref.people.size())
	print("parity: %d people, %d mismatched values; %.0f us per person in GDScript" % [ref.people.size(), bad, us])
	quit(1 if bad else 0)


func _same(a: Variant, b: Variant) -> bool:
	if typeof(a) in [TYPE_INT, TYPE_FLOAT] and typeof(b) in [TYPE_INT, TYPE_FLOAT]:
		return absf(float(a) - float(b)) <= 1e-9 * maxf(1.0, absf(float(a)))
	if typeof(a) == TYPE_ARRAY and typeof(b) == TYPE_ARRAY:
		if a.size() != b.size():
			return false
		for i in a.size():
			if not _same(a[i], b[i]):
				return false
		return true
	if typeof(a) == TYPE_DICTIONARY and typeof(b) == TYPE_DICTIONARY:
		if a.size() != b.size():
			return false
		for k in a:
			if not b.has(k) or not _same(a[k], b[k]):
				return false
		return true
	return a == b
