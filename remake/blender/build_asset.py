"""build_asset.py -- build one catalogued asset from its analysed Grok references.

  flatpak run org.blender.Blender -b --factory-startup --python <abs build_asset.py> -- <id> <analysis.json> <out.glb> [render_prefix]

Dispatch by family (tools/assets/catalog.py): transit -> kit.transit (interiors from Grok's views);
hull with seats -> kit.cabin (an interior extrapolated from the exterior); other hulls -> kit.hull; frame -> remake/blender/assets/<id>.py (a build(an, out, render)
function).
"""
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

argv = sys.argv[sys.argv.index("--") + 1:]
aid, analysis, out = argv[0], argv[1], argv[2]
render = argv[3] if len(argv) > 3 else None
family = argv[4] if len(argv) > 4 else "hull"
an = json.load(open(analysis))

if family == "frame":
    if os.path.exists(os.path.join(HERE, "assets", aid + ".py")):
        mod = importlib.import_module("assets." + aid)
        mod.build(an, out, render)
    else:
        from kit import cutout
        cutout.build(an, out, render)
elif family == "transit":
    from kit import transit
    transit.build(an, out, render)
elif an.get("seats", 0) > 0:
    from kit import cabin                     # an extrapolated interior (no Grok interior views)
    cabin.build(an, out, render)
else:
    from kit import hull
    hull.build(an, out, render)
