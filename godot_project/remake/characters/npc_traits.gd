extends RefCounted
class_name NpcTraits

## The character generator's trait layer: loads npc_traits.json (the extensible list of
## characteristics -- research/characters/npc_traits.md) and computes any person's traits from
## (world seed, person id, population).  A person is never stored: the same arguments give the same
## values every time (procedural_npcs.md 2).  A port of tools/charref/traits.py Person, kept
## bit-identical (remake/tools/npc_parity.gd); change one, change the other.
##
##   var db := NpcTraits.shared()
##   var v := db.person(1, "B14823:2")                      # every layer
##   var v0 := db.person(1, "B14823:2", ["L0"], "rust_belt")
##   var v1 := db.person(1, "B14823:2", [], "", {"occupation": "baker"})   # pinned traits
##
## Pinned traits (a character request's "want", or the player's saved changes) short-circuit their
## own stream; everything that depends on them is still derived from them, so a pinned baker still
## gets a baker's clothes (the Watch Dogs: Legion "any fact first" idea -- scale_survey.md 2.1).
##
## Expressions: Godot's Expression, with every number handed in as a float so `age / 17` divides
## as it does in Python.  Expression has no ternary -- `x if c else y` silently evaluates to x --
## so the file uses iff(c, x, y); traits.py's validator rejects the Python form.

const PATH := "res://remake/characters/npc_traits.json"
const KEYWORDS := ["if", "else", "and", "or", "not", "in", "true", "false", "True", "False", "null",
	"min", "max", "clamp", "abs", "iff", "table", "rand_normal", "row"]

static var _shared: NpcTraits

var data: Dictionary
var defs := {}                  # trait id -> definition
var order: Array[String] = []   # trait ids in file order
var tables: Dictionary
var populations: Dictionary
var _names_re := RegEx.create_from_string("(?<![.\\w])[A-Za-z_]\\w*")
var _strings_re := RegEx.create_from_string("'[^']*'")
var _expr_cache := {}           # expression text -> [Expression, input names]
var _mutex := Mutex.new()


static func shared() -> NpcTraits:
	if _shared == null:
		_shared = NpcTraits.new()
		_shared.load_file(PATH)
	return _shared


func load_file(path: String) -> void:
	var f := FileAccess.open(path, FileAccess.READ)
	data = JSON.parse_string(f.get_as_text())
	tables = data.get("tables", {})
	populations = data.get("populations", {})
	for t in data.traits:
		defs[t.id] = t
		order.append(t.id)


func person(world_seed: int, pid: String, layers: Array = [], population := "", pinned := {}) -> Dictionary:
	var ev := _Eval.new(self, world_seed, pid, populations.get(population, {}) if population != "" else {}, pinned)
	for tid in order:
		if layers.is_empty() or defs[tid].layer in layers:
			ev.get_trait(tid)
	return ev.v


func table(tname: String, row: String, col: String) -> Variant:
	var tb: Dictionary = tables[tname]
	return tb[row][(tb["_cols"] as Array).find(col)]


func compiled(expr: String) -> Array:
	## [Expression, input names]; the inputs are the trait ids (and `row`) the text mentions.
	_mutex.lock()
	var c: Array = _expr_cache.get(expr, [])
	if c.is_empty():
		var names := PackedStringArray()
		for m in _names_re.search_all(_strings_re.sub(expr, "''", true)):
			var n := m.get_string()
			if (n in defs or n == "row") and not n in names:
				names.append(n)
		var e := Expression.new()
		var err := e.parse(expr, names)
		if err != OK:
			push_error("NpcTraits: can't parse %s: %s" % [expr, e.get_error_text()])
		c = [e, names]
		_expr_cache[expr] = c
	_mutex.unlock()
	return c


static func py_round(x: float) -> int:
	## Python's round(): halves go to the even neighbour.
	var f := floorf(x)
	var r := x - f
	if r > 0.5 or (r == 0.5 and int(f) % 2 != 0):
		return int(f) + 1
	return int(f)


static func as_float(v: Variant) -> Variant:
	## Numbers into expressions as floats (Python's / semantics); containers converted inside.
	match typeof(v):
		TYPE_INT:
			return float(v)
		TYPE_ARRAY:
			var a := []
			for x in v:
				a.append(as_float(x))
			return a
		TYPE_DICTIONARY:
			var d := {}
			for k in v:
				d[k] = as_float(v[k])
			return d
	return v


class _Eval:
	## One person's evaluation: the values so far and the stream in use (for rand_normal()).
	var db: NpcTraits
	var seed: int
	var pid: String
	var pop: Dictionary
	var pinned: Dictionary
	var v := {}
	var _rng: NpcRng

	func _init(p_db: NpcTraits, p_seed: int, p_pid: String, p_pop: Dictionary, p_pinned: Dictionary) -> void:
		db = p_db
		seed = p_seed
		pid = p_pid
		pop = p_pop
		pinned = p_pinned

	# -- called from expressions --
	func table(tname: String, row: String, col: String) -> Variant:
		return NpcTraits.as_float(db.table(tname, row, col))

	func rand_normal(mu: float, sd: float) -> float:
		return _rng.normal(mu, sd)

	func iff(cond: Variant, a: Variant, b: Variant) -> Variant:
		## The expressions' conditional (Expression has no `x if c else y`: it silently stops at the
		## `if`).  Both branches are evaluated, so never put rand_normal() in one.
		return a if cond else b

	# --
	func get_trait(tid: String) -> Variant:
		if v.has(tid):
			return v[tid]
		if pinned.has(tid):
			v[tid] = pinned[tid]
			return v[tid]
		var t: Dictionary = db.defs[tid]
		for dep in t.get("depends_on", []):
			if db.defs.has(dep):
				get_trait(dep)
		var rng := NpcRng.for_trait(seed, pid, tid)
		var ch: Dictionary = (pop.get("override", {}) as Dictionary).get(tid, t.choose).duplicate()
		var adds := []
		var muls := []
		var bias: Array = []
		for m in t.get("mods", []):
			if m.has("if") and not ev(m["if"], rng):
				continue
			if m.has("weights"):                          # replaces the table
				ch["weights"] = (m.weights as Dictionary).duplicate()
			if m.has("reweight"):                         # changes some entries of it
				var w: Dictionary = (ch.get("weights", {}) as Dictionary).duplicate()
				w.merge(m.reweight, true)
				ch["weights"] = w
			if m.has("bias"):
				if bias.is_empty():
					bias.resize(m.bias.size())
					bias.fill(0.0)
				for i in m.bias.size():
					bias[i] += float(m.bias[i])
			if m.has("add"):
				adds.append(m.add)
			if m.has("mul"):
				muls.append(m.mul)
		var val: Variant = choose(t, ch, rng, bias)
		for a in adds:
			val = apply(val, a, rng, false)
		for m in muls:
			val = apply(val, m, rng, true)
		if typeof(val) == TYPE_FLOAT and t.has("range"):
			val = clampf(val, float(t.range[0]), float(t.range[1]))
		if t.type == "int" and typeof(val) == TYPE_FLOAT:
			val = NpcTraits.py_round(val)
		v[tid] = val
		return val

	func ev(expr: Variant, rng: NpcRng, extra := {}) -> Variant:
		if typeof(expr) != TYPE_STRING:
			return expr
		var c := db.compiled(expr)
		var names: PackedStringArray = c[1]
		var inputs := []
		for n in names:
			if n == "row":
				inputs.append(extra.get("row"))
			else:
				inputs.append(NpcTraits.as_float(get_trait(n)))
		_rng = rng
		var e: Expression = c[0]
		var r: Variant = e.execute(inputs, self)
		if e.has_execute_failed():
			push_error("NpcTraits %s: %s: %s" % [pid, expr, e.get_error_text()])
		return r

	func apply(val: Variant, op: Variant, rng: NpcRng, multiply: bool) -> Variant:
		if typeof(op) == TYPE_DICTIONARY:                 # per key of a map
			var out := {}
			for k in val:
				out[k] = _op(val[k], ev(op[k], rng), multiply) if op.has(k) else val[k]
			return out
		var o: Variant = ev(op, rng)
		if typeof(val) == TYPE_ARRAY:
			var out := []
			for i in val.size():
				out.append(_op(val[i], o[i] if typeof(o) == TYPE_ARRAY else o, multiply))
			return out
		return _op(val, o, multiply)

	static func _op(a: Variant, b: Variant, multiply: bool) -> Variant:
		return a * b if multiply else a + b

	func choose(t: Dictionary, ch: Dictionary, rng: NpcRng, bias: Array) -> Variant:
		var n: int = {"vec3": 3, "vec4": 4, "vec8": 8}.get(t.type, 0)
		var lo := -1e9
		var hi := 1e9
		if ch.has("clamp"):
			lo = float(ch.clamp[0])
			hi = float(ch.clamp[1])
		if ch.has("rule"):                                # game code, by name (schedule, relationships)
			return "(rule %s)" % ch.rule
		if ch.has("derive"):
			return ev(ch.derive, rng)
		if ch.has("table"):
			var tb: Dictionary = db.tables[ch.table]
			var cols: Array = tb["_cols"]
			var mul: Dictionary = (pop.get("table_mul", {}) as Dictionary).get(ch.table, {})
			var w := {}
			for k: String in tb:
				if k.begins_with("_"):
					continue
				var r := {}
				for i in cols.size():
					r[cols[i]] = tb[k][i]
				if ch.has("where") and not ev(ch.where, rng, {"row": NpcTraits.as_float(r)}):
					continue
				var col_mul := 1.0                         # (the same multiplication order as the Python tool)
				for key: String in mul:
					var cut := key.find(":")
					if cut > 0 and str(r.get(key.substr(0, cut))) == key.substr(cut + 1):
						col_mul *= float(mul[key])
				w[k] = float(r[ch.get("weight_col", "weight")]) * float(mul.get(k, 1.0)) * col_mul
			return rng.pick(w) if not w.is_empty() else null
		if ch.has("bands"):
			var bw := {}
			for i in ch.bands.size():
				bw[i] = ch.bands[i][2]
			var b: Array = ch.bands[int(rng.pick(bw))]
			return int(b[0]) + int(rng.rand() * (int(b[1]) - int(b[0]) + 1))
		if ch.has("weights"):
			var k: Variant = rng.pick(ch.weights)
			return int(k) if t.type == "int" else k
		if ch.has("normal"):
			var mu := float(ch.normal[0])
			var sd := float(ch.normal[1])
			if t.type == "map":
				var d := {}
				for key in t.keys:
					d[key] = clampf(rng.normal(mu, sd), lo, hi)
				return d
			if n > 0:
				var a := []
				for i in n:
					a.append(clampf(rng.normal(mu, sd), lo, hi))
				return a
			return clampf(rng.normal(mu, sd), lo, hi)
		if ch.has("uniform"):
			return float(ch.uniform[0]) + (float(ch.uniform[1]) - float(ch.uniform[0])) * rng.rand()
		if ch.has("uniform2"):
			var x := pow(rng.rand(), float(ch.get("bias_x", 1.0)))
			var ab: Array = ch.uniform2[0]
			var cd: Array = ch.uniform2[1]
			var first := float(ab[0]) + (float(ab[1]) - float(ab[0])) * x
			return [first, float(cd[0]) + (float(cd[1]) - float(cd[0])) * rng.rand()]
		if ch.has("dirichlet"):
			var g := []
			var tot := 0.0
			for i in ch.dirichlet.size():
				var gi := rng.gamma(float(ch.dirichlet[i]) + (float(bias[i]) if not bias.is_empty() else 0.0))
				g.append(gi)
			for gi in g:
				tot += gi
			var out := []
			for gi in g:
				out.append(gi / tot)
			return out
		if ch.has("beta"):
			var x := rng.gamma(float(ch.beta[0]))
			var y := rng.gamma(float(ch.beta[1]))
			return x / (x + y)
		if ch.has("each"):
			var tags := []
			for k in ch.each:
				var r := rng.rand()
				if r < float(ev(ch.each[k], rng)):
					tags.append(k)
			return tags
		if ch.has("from_lists"):
			return "(lists: literary phase)"
		push_error("NpcTraits: trait %s has no chooser" % t.id)
		return null
