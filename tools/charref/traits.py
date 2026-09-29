"""Validate the NPC characteristic file and preview the people it makes.

  python3 tools/charref/traits.py                     validate, then show 12 residents of seed 1
  python3 tools/charref/traits.py -n 40 --seed 7      more people, another world
  python3 tools/charref/traits.py --id B14823:2       one person (the same one every time)
  python3 tools/charref/traits.py --stats 5000        distributions over many people (catch soup)
  python3 tools/charref/traits.py --layers L0,L1      only some layers

Determinism: each trait draws from its own stream, hash(seed | person id | trait id), so adding
a trait never changes existing traits of existing people (procedural_npcs.md 2.3).  Expressions
are the shared subset of Python and Godot's Expression class (and/or/not, in [...], dotted dict
access, min/max/clamp/abs, iff(cond, a, b), table(), rand_normal()), so the game runs the same
strings.  NOT allowed: Python's `x if c else y` (Godot's Expression silently stops parsing at the
`if` and returns x) and chained comparisons (`a <= b <= c`); the validator rejects both."""
import argparse, collections, json, math, re, sys
from pathlib import Path

FILE = Path(__file__).resolve().parents[2] / "godot_project" / "remake" / "characters" / "npc_traits.json"
M64 = (1 << 64) - 1
CHOOSERS = {"rule", "weights", "bands", "derive", "table", "normal", "uniform", "uniform2", "dirichlet", "beta", "each", "from_lists"}
MOD_KEYS = {"if", "add", "mul", "weights", "reweight", "bias"}
TYPES = {"pick", "int", "float", "vec3", "vec4", "vec8", "color2d", "tags", "map", "rule", "text"}


def fnv1a64(s: str) -> int:
    h = 0xcbf29ce484222325
    for b in s.encode():
        h = ((h ^ b) * 0x100000001b3) & M64
    return h


class Stream:
    """splitmix64: tiny, and easy to match bit for bit in GDScript."""
    def __init__(self, seed: int):
        self.s = seed & M64

    def u64(self):
        self.s = (self.s + 0x9E3779B97F4A7C15) & M64
        z = self.s
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
        return z ^ (z >> 31)

    def rand(self):
        return (self.u64() >> 11) / float(1 << 53)

    def normal(self, mu=0.0, sd=1.0):
        u = max(self.rand(), 1e-12)
        return mu + sd * math.sqrt(-2 * math.log(u)) * math.cos(2 * math.pi * self.rand())

    def gamma(self, k):                                  # Marsaglia-Tsang, k >= 1 (boosted below 1)
        if k < 1:
            return self.gamma(k + 1) * self.rand() ** (1 / k)
        d = k - 1 / 3
        c = 1 / math.sqrt(9 * d)
        while True:
            x = self.normal()
            v = (1 + c * x) ** 3
            if v > 0 and math.log(max(self.rand(), 1e-12)) < 0.5 * x * x + d - d * v + d * math.log(v):
                return d * v

    def pick(self, weights: dict):
        tot = sum(max(0.0, float(w)) for w in weights.values())
        r = self.rand() * tot
        for k, w in weights.items():
            r -= max(0.0, float(w))
            if r < 0:
                return k
        return list(weights)[-1]


class D(dict):
    """A dict with dotted access, like a GDScript Dictionary in an Expression."""
    __getattr__ = dict.get


def clamp(x, a, b):
    return min(max(x, a), b)


class Person:
    def __init__(self, data, seed, pid, layers=None, population=None):
        self.data, self.seed, self.pid = data, seed, pid
        self.pop = data.get("populations", {}).get(population, {}) if population else {}
        self.tables = data["tables"]
        self.defs = {t["id"]: t for t in data["traits"]}
        self.v = {}
        self.layers = layers
        for t in data["traits"]:
            if layers is None or t["layer"] in layers:
                self.get(t["id"])

    def table(self, name, row, col):
        tb = self.tables[name]
        return tb[row][tb["_cols"].index(col)]

    def env(self, rng, extra=None):
        e = {"min": min, "max": max, "clamp": clamp, "abs": abs, "iff": lambda c, a, b: a if c else b, "table": self.table,
             "rand_normal": rng.normal}
        e.update({k: (D(v) if isinstance(v, dict) else v) for k, v in self.v.items()})
        e.update(extra or {})
        return e

    def ev(self, expr, rng, extra=None):
        if not isinstance(expr, str):
            return expr
        names = set(re.findall(r"(?<![.\w])[A-Za-z_]\w*", re.sub(r"'[^']*'", "", expr))) - {"if", "else", "and", "or", "not", "in", "row", "True", "False", "iff"}
        for n in names:                                   # pull in dependencies on demand
            if n in self.defs and n not in self.v:
                self.get(n)
        try:
            return eval(expr, {"__builtins__": {}}, self.env(rng, extra))
        except Exception as ex:
            raise ValueError(f"{self.pid}: expression {expr!r}: {ex}")

    def get(self, tid):
        if tid in self.v:
            return self.v[tid]
        t = self.defs[tid]
        for dep in t.get("depends_on", []):
            if dep in self.defs:
                self.get(dep)
        rng = Stream(fnv1a64(f"{self.seed}|{self.pid}|{tid}"))
        ch = dict(self.pop.get("override", {}).get(tid, t["choose"]))
        adds, muls, bias = [], [], None
        for m in t.get("mods", []):                       # conditions first: they may reshape the chooser
            if "if" in m and not self.ev(m["if"], rng):
                continue
            if "weights" in m:                              # replaces the table
                ch["weights"] = dict(m["weights"])
            if "reweight" in m:                             # changes some entries of it
                ch["weights"] = {**ch.get("weights", {}), **m["reweight"]}
            if "bias" in m:
                bias = [a + b for a, b in zip(bias or [0] * len(m["bias"]), m["bias"])]
            if "add" in m:
                adds.append(m["add"])
            if "mul" in m:
                muls.append(m["mul"])
        val = self.choose(t, ch, rng, bias)
        for a in adds:
            val = self.apply(val, a, rng, lambda x, y: x + y)
        for m in muls:
            val = self.apply(val, m, rng, lambda x, y: x * y)
        if isinstance(val, float) and "range" in t:
            val = clamp(val, *t["range"])
        if t["type"] == "int" and isinstance(val, float):
            val = int(round(val))
        self.v[tid] = val
        return val

    def apply(self, val, op, rng, f):
        if isinstance(op, dict):                          # per key of a map
            return {k: (f(x, self.ev(op[k], rng)) if k in op else x) for k, x in val.items()}
        o = self.ev(op, rng)
        if isinstance(val, list):
            return [f(x, o[i] if isinstance(o, list) else o) for i, x in enumerate(val)]
        return f(val, o)

    def choose(self, t, ch, rng, bias):
        n = {"vec3": 3, "vec4": 4, "vec8": 8}.get(t["type"])
        if "rule" in ch:                                   # computed by game code (named rule), not here
            return f"(rule {ch['rule']})"
        if "derive" in ch:
            return self.ev(ch["derive"], rng)
        if "table" in ch:
            tb = self.tables[ch["table"]]
            cols = tb["_cols"]
            w = {}
            for k, row in tb.items():
                if k.startswith("_"):
                    continue
                r = D(zip(cols, row))
                if self.ev(ch.get("where", "True"), rng, {"row": r}):
                    mul = self.pop.get("table_mul", {}).get(ch["table"], {})
                    w[k] = r[ch.get("weight_col", "weight")] * mul.get(k, 1.0) * \
                        math.prod(m for key, m in mul.items() if ":" in key and r.get(key.split(":")[0]) == key.split(":")[1])
            return rng.pick(w) if w else None
        if "bands" in ch:
            b = ch["bands"][int(rng.pick({i: b[2] for i, b in enumerate(ch["bands"])}))]
            return b[0] + int(rng.rand() * (b[1] - b[0] + 1))
        if "weights" in ch:
            k = rng.pick(ch["weights"])
            return int(k) if t["type"] == "int" else k
        if "normal" in ch:
            mu, sd = ch["normal"]
            if t["type"] == "map":
                return {k: clamp(rng.normal(mu, sd), *ch.get("clamp", (-1e9, 1e9))) for k in t["keys"]}
            if n:
                return [clamp(rng.normal(mu, sd), *ch.get("clamp", (-1e9, 1e9))) for _ in range(n)]
            return clamp(rng.normal(mu, sd), *ch.get("clamp", (-1e9, 1e9)))     # the draw is clamped, then mods apply
        if "uniform" in ch:
            a, b = ch["uniform"]
            return a + (b - a) * rng.rand()
        if "uniform2" in ch:
            (a, b), (c, d) = ch["uniform2"]
            x = rng.rand() ** ch.get("bias_x", 1.0)
            return [a + (b - a) * x, c + (d - c) * rng.rand()]
        if "dirichlet" in ch:
            al = [a + (bias[i] if bias else 0) for i, a in enumerate(ch["dirichlet"])]
            g = [rng.gamma(a) for a in al]
            return [x / sum(g) for x in g]
        if "beta" in ch:
            a, b = ch["beta"]
            x, y = rng.gamma(a), rng.gamma(b)
            return x / (x + y)
        if "each" in ch:
            return [k for k, p in ch["each"].items() if rng.rand() < float(self.ev(p, rng))]
        if "from_lists" in ch:
            return "(lists: literary phase)"
        raise ValueError(f"trait {t['id']}: no chooser")


def validate(data):
    errs = []
    ids = [t.get("id") for t in data.get("traits", [])]
    for d in {i for i in ids if ids.count(i) > 1}:
        errs.append(f"duplicate trait id {d}")
    idset = set(ids)
    layer = {t["id"]: t.get("layer") for t in data["traits"]}
    order = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}
    for t in data["traits"]:
        tid = t.get("id", "?")
        for k in ("id", "layer", "group", "type", "choose"):
            if k not in t:
                errs.append(f"{tid}: missing {k}")
        if t.get("type") not in TYPES:
            errs.append(f"{tid}: unknown type {t.get('type')}")
        if t.get("layer") not in order:
            errs.append(f"{tid}: unknown layer {t.get('layer')}")
        if not CHOOSERS & set(t.get("choose", {})):
            errs.append(f"{tid}: choose has none of {sorted(CHOOSERS)}")
        if "table" in t.get("choose", {}) and t["choose"]["table"] not in data["tables"]:
            errs.append(f"{tid}: no table {t['choose']['table']}")
        for m in t.get("mods", []):
            if set(m) - MOD_KEYS:
                errs.append(f"{tid}: mod keys {sorted(set(m) - MOD_KEYS)}")
        for dep in t.get("depends_on", []):
            if dep not in idset and dep not in ("household",):
                errs.append(f"{tid}: depends on unknown {dep}")
            elif dep in layer and order.get(layer[dep], 0) > order.get(t.get("layer"), 0):
                errs.append(f"{tid} ({t['layer']}) depends on {dep} ({layer[dep]}): a layer may only depend on lower layers")
        if "affects" not in t:
            errs.append(f"{tid}: say what it affects")
    for pname, pop in data.get("populations", {}).items():
        if pname.startswith("_"):
            continue
        for tid in pop.get("override", {}):
            if tid not in idset:
                errs.append(f"population {pname}: override of unknown trait {tid}")
        for tb, mul in pop.get("table_mul", {}).items():
            rowsd = data["tables"].get(tb)
            if rowsd is None:
                errs.append(f"population {pname}: no table {tb}")
                continue
            for key in mul:
                if ":" in key:
                    col, val = key.split(":", 1)
                    if col not in rowsd["_cols"]:
                        errs.append(f"population {pname}: table {tb} has no column {col}")
                elif key not in rowsd:
                    errs.append(f"population {pname}: table {tb} has no row {key}")
    def exprs(x):
        if isinstance(x, str):
            yield x
        elif isinstance(x, dict):
            for k, y in x.items():
                if k not in ("id", "layer", "group", "type", "note", "unit", "values", "keys", "affects", "depends_on", "inherit", "rule", "table", "weight_col"):
                    yield from exprs(y)
        elif isinstance(x, list):
            for y in x:
                yield from exprs(y)
    for t in data["traits"]:
        for e in exprs({k: t[k] for k in ("choose", "mods") if k in t}):
            if re.search(r"\bif\b|\belse\b", e):
                errs.append(f"{t['id']}: `x if c else y` in {e!r}: Godot's Expression can't parse it; use iff(c, x, y)")
            if re.search(r"(<=?|>=?|==|!=)\s*(?:(?!\band\b|\bor\b)[\w.+\-*/ ])+?\s*(<=?|>=?|==|!=)", re.sub(r"'[^']*'", "''", e)):
                errs.append(f"{t['id']}: chained comparison in {e!r}: write a <= b and b <= c")
    # cycles
    deps = {t["id"]: [d for d in t.get("depends_on", []) if d in idset] for t in data["traits"]}
    state = {}

    def visit(n, path):
        if state.get(n) == 1:
            errs.append("dependency cycle: " + " -> ".join(path + [n]))
            return
        if state.get(n) == 2:
            return
        state[n] = 1
        for d in deps[n]:
            visit(d, path + [n])
        state[n] = 2
    for n in deps:
        visit(n, [])
    return errs


def fmt(v):
    if isinstance(v, float):
        return f"{v:.2f}"
    if isinstance(v, list):
        return "[" + " ".join(fmt(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + " ".join(f"{k[:5]}={fmt(x)}" for k, x in v.items()) + "}"
    return str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=12)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--id")
    ap.add_argument("--stats", type=int)
    ap.add_argument("--layers")
    ap.add_argument("--file", default=str(FILE))
    ap.add_argument("--pop", help="settlement archetype (populations in the trait file)")
    ap.add_argument("--dump", help="write the people as JSON to this file (for the GDScript parity test)")
    a = ap.parse_args()
    data = json.loads(Path(a.file).read_text())
    errs = validate(data)
    print(f"{len(data['traits'])} traits, {len(errs)} problems")
    for e in errs:
        print("  !", e)
    if errs:
        sys.exit(1)
    layers = set(a.layers.split(",")) if a.layers else None
    if a.stats:
        c = collections.defaultdict(collections.Counter)
        num = collections.defaultdict(list)
        for i in range(a.stats):
            p = Person(data, a.seed, f"B{i // 3}:{i % 3}", layers or {"L0", "L1"}, a.pop)
            for k, v in p.v.items():
                if isinstance(v, str):
                    c[k][v] += 1
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    num[k].append(v)
                elif isinstance(v, list) and v and isinstance(v[0], str):
                    c[k].update(v)
        for k, vs in num.items():
            vs.sort()
            q = lambda f: vs[min(len(vs) - 1, int(f * len(vs)))]
            print(f"{k:14} p5 {q(.05):7.2f}  p50 {q(.5):7.2f}  p95 {q(.95):7.2f}")
        for k, cnt in c.items():
            print(f"{k:14} " + "  ".join(f"{v} {n * 100 / a.stats:.0f}%" for v, n in cnt.most_common(8)))
        return
    ids = [a.id] if a.id else [f"B{1000 + i}:{i % 3}" for i in range(a.n)]
    if a.dump:
        out = [{"id": pid, "v": Person(data, a.seed, pid, layers, a.pop).v} for pid in ids]
        Path(a.dump).write_text(json.dumps({"seed": a.seed, "pop": a.pop, "layers": sorted(layers) if layers else None, "people": out}))
        print(f"wrote {len(out)} people to {a.dump}")
        return
    for pid in ids:
        p = Person(data, a.seed, pid, layers, a.pop)
        print(f"\n{pid}: " + "  ".join(f"{k}={fmt(v)}" for k, v in p.v.items()))


if __name__ == "__main__":
    main()
