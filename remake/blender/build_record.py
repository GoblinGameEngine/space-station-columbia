"""
build_record.py -- build catalog records into game glbs.

  flatpak run org.blender.Blender -b --factory-startup --python <abs>/build_record.py -- ID [ID ...]

Each record (remake/catalog/<ID>.json) is dispatched on its kind to a generator in gen/, and
written to godot_project/remake/buildings/<ID>.glb (+ .mats.json).  One Blender process can build
many records (each Building starts from factory settings).  Failures are reported per ID and
don't stop the batch.
"""
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "gen"))
sys.path.insert(0, HERE)

import common  # noqa: E402

GENERATORS = {}


def generator(kind):
    if kind not in GENERATORS:
        if kind in ("house", "farmhouse", "cottage", "beachhouse", "bungalow", "shingle", "singlehouse", "rowhouse"):
            import house
            GENERATORS[kind] = house.build
        elif kind in ("store", "restaurant", "bait", "market"):
            import store
            GENERATORS[kind] = store.build
        elif kind in ("civic", "school", "church"):
            import institution
            GENERATORS[kind] = institution.build
        elif kind in ("industrial", "tower", "bigbox", "strip", "vacant"):
            import works
            GENERATORS[kind] = works.build
        elif kind == "townhouse":
            import townhouse
            GENERATORS[kind] = townhouse.build
        elif kind == "farm":
            import farm
            GENERATORS[kind] = farm.build
        elif kind in ("hotel", "condo", "motel", "arcade", "stand", "kiosk", "bait", "pavilion", "bandstand", "lifeguard",
                      "lighthouse", "ride", "monument", "stack", "cannery", "fishhouse", "icehouse", "shed", "boatyard",
                      "warehouse"):
            import coastal
            GENERATORS[kind] = coastal.build
        elif kind == "crossing":
            import bridges
            GENERATORS[kind] = bridges.build
        else:
            raise NotImplementedError(f"no generator for kind '{kind}' yet")
    return GENERATORS[kind]


def kind_of(rec):
    rid = rec["id"]
    if rid.startswith("FARM-"):
        part = rid.rsplit("-", 1)[-1]
        return {"house": "farmhouse"}.get(part, "farm")
    if rid.split("-")[0] in ("MAJOR", "SMALL", "CULVERT", "RAIL"):
        return "crossing"
    return rec.get("kind", "house")


def main(ids):
    ok, bad = [], []
    for rid in ids:
        try:
            rec = common.load_record(rid)
            b = generator(kind_of(rec))(rec)
            b.finish(common.out_path(rid))
            ok.append(rid)
        except Exception:
            traceback.print_exc()
            print(f"FAILED {rid}")
            bad.append(rid)
    print(f"BUILT {len(ok)}  FAILED {len(bad)}: {' '.join(bad)}")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    main(argv)
