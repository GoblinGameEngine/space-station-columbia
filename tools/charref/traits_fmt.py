#!/usr/bin/env python3
"""Write npc_traits.json in its hand-kept compact layout (one table row, one mod, one trait
field group per line), so a scripted edit doesn't balloon the file:

    python3 tools/charref/traits_fmt.py            # reformat in place
    from traits_fmt import dump; dump(data, path)  # after editing the data in Python
"""
import json
import os
import sys

PATH = os.path.join(os.path.dirname(__file__), "..", "..", "godot_project", "remake", "characters", "npc_traits.json")
HEAD = ["id", "layer", "group", "type", "range", "unit"]
LINES = [["values"], ["keys"], ["choose"], ["mods"], ["note"]]


def j(v):
    return json.dumps(v, ensure_ascii=False)


def trait(t):
    out = []
    rest = [k for k in t if k not in HEAD and not any(k in g for g in LINES)]
    out.append(", ".join("%s: %s" % (j(k), j(t[k])) for k in HEAD if k in t))
    for g in LINES:
        k = g[0]
        if k not in t:
            continue
        if k == "mods" and len(t[k]) > 1:
            out.append('"mods": [' + (",\n            ").join(j(m) for m in t[k]) + "]")
        else:
            out.append("%s: %s" % (j(k), j(t[k])))
    if rest:
        out.append(", ".join("%s: %s" % (j(k), j(t[k])) for k in rest))
    return "  {" + ",\n   ".join(out) + "}"


def table(name, tb):
    w = max(len(j(k)) for k in tb) + 1
    rows = ["   %s %s" % ((j(k) + ":").ljust(w), j(v)) for k, v in tb.items()]
    return "  %s: {\n%s\n  }" % (j(name), ",\n".join(rows))


def dumps(d):
    parts = []
    for k, v in d.items():
        if k == "tables":
            parts.append(' "tables": {\n' + ",\n".join(table(n, tb) for n, tb in v.items()) + "\n }")
        elif k == "populations":
            parts.append(' "populations": {\n' + ",\n".join("  %s: %s" % (j(n), j(p)) for n, p in v.items()) + "\n }")
        elif k == "traits":
            parts.append(' "traits": [\n' + ",\n\n".join(trait(t) for t in v) + "\n ]")
        else:
            parts.append(" %s: %s" % (j(k), j(v)))
    return "{\n" + ",\n\n".join(parts) + "\n}\n"


def dump(d, path=PATH):
    text = dumps(d)
    assert json.loads(text) == d
    with open(path, "w") as f:
        f.write(text)


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else PATH
    dump(json.load(open(p)), p)
    print("%s: %d lines" % (p, sum(1 for _ in open(p))))
