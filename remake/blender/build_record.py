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
import gblib  # noqa: E402

GENERATORS = {}


# ------------------------------------------------------------------ the furniture recorder (remake/rooms/raw)
# Every furnishing function -- gbfurn's and shopfit's fixtures, all (p, pos, yaw, ...) -- is wrapped so a call made
# while gbhouse furnishes a room is logged on the Building: what, which room, where, facing, and the call it was part
# of (an office_set is a desk + a chair).  tools/rooms/make_rooms.py reads beds, seats and containers from it.
def _wrap(name, fn):
    def rec(p, pos, *a, **k):
        b = gblib.CURRENT
        idx = None
        if b is not None and b._room is not None:
            yaw = a[0] if a and isinstance(a[0], (int, float)) else k.get("yaw", 0.0)
            try:
                xyz = [round(float(v), 3) for v in tuple(pos)[:3]]
            except TypeError:
                xyz = None
            b.furniture.append({"item": name, "room": b._room[0], "floor": b._room[1], "pos": xyz, "yaw": round(float(yaw), 1),
                                "parent": b._furn_stack[-1] if b._furn_stack else None})
            idx = len(b.furniture) - 1
            b._furn_stack.append(idx)
        try:
            return fn(p, pos, *a, **k)
        finally:
            if idx is not None:
                b._furn_stack.pop()
    rec.__name__ = name
    rec.__wrapped__ = fn
    return rec


def _record_module(mod):
    import inspect
    for n, fn in list(vars(mod).items()):
        if not inspect.isfunction(fn) or fn.__module__ != mod.__name__ or hasattr(fn, "__wrapped__"):
            continue
        ps = list(inspect.signature(fn).parameters)
        if len(ps) >= 2 and ps[0] == "p" and ps[1] == "pos":
            setattr(mod, n, _wrap(n, fn))


def _install_recorder():
    import gbfurn
    import shopfit
    _record_module(gbfurn)
    _record_module(shopfit)
    import gbhouse
    for n in ("tv_stand", "tub", "vanity", "appliance", "base_cabinets"):
        if hasattr(gbhouse, n) and not hasattr(getattr(gbhouse, n), "__wrapped__"):
            setattr(gbhouse, n, _wrap(n, getattr(gbhouse, n)))
    if not hasattr(shopfit.fitout_for, "__wrapped__"):
        orig = shopfit.fitout_for

        def fitout_for(business_type, rnd):
            hook = orig(business_type, rnd)
            hook._kind = business_type           # (the room's fit-out, named in the raw manifest)
            return hook
        fitout_for.__wrapped__ = orig
        shopfit.fitout_for = fitout_for


_install_recorder()


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
