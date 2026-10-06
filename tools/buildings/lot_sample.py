#!/usr/bin/env python3
"""lot_sample.py REGION [AREA_ID ...] -- measure real lots (research/buildings/LOTS.md).

For each sample area (research/buildings/regions/REGION/lot_samples.json): fetch the tax parcels (geometry, use class,
acreage; never owner names or addresses), the OSM buildings and streets (Overpass), and the USGS NAIP aerial; match
buildings to parcels and measure each lot -- width and depth (oriented to its street), area, building coverage,
front setback, least side gap, rear yard, alley, corner, outbuildings. Writes per-area lots JSON + summary to
research/buildings/regions/REGION/lots/, and a render (aerial + parcel lines + buildings) to
reference/lots/REGION/<area>.png for annotation. Data: WI parcels (public), OSM (ODbL), NAIP (public domain)."""
import json, math, os, statistics as S, sys, time, urllib.parse, urllib.request

from shapely.geometry import LineString, Polygon, box
from shapely.ops import nearest_points

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
UA = "SSC-building-research/0.1 (github.com/GoblinGameEngine)"
OVERPASS = "https://overpass-api.de/api/interpreter"
NAIP = "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer/exportImage"
STREET = {"residential", "tertiary", "secondary", "primary", "unclassified", "living_street", "trunk"}


def get(url, data=None, binary=False):
    for k in range(4):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r:
                b = r.read()
            return b if binary else json.loads(b)
        except Exception as e:
            if k == 3:
                raise
            time.sleep(5 + 10 * k)


class Local:
    """Metres east/north of the bbox's SW corner (equirectangular: fine at this size)."""
    def __init__(self, s, w):
        self.s, self.w, self.k = s, w, math.cos(math.radians(s))

    def __call__(self, lon, lat):
        return ((lon - self.w) * 111320.0 * self.k, (lat - self.s) * 110540.0)


def parcels(url, bb, P):
    s, w, n, e = bb
    q = {"geometry": "%f,%f,%f,%f" % (w, s, e, n), "geometryType": "esriGeometryEnvelope", "inSR": "4326",
         "spatialRel": "esriSpatialRelIntersects", "outSR": "4326", "f": "json", "returnGeometry": "true",
         "outFields": "PARCELID,PROPCLASS,AUXCLASS,IMPROVED,GISACRES,PLACENAME,LNDVALUE,IMPVALUE"}
    d = get(url + "?" + urllib.parse.urlencode(q))
    out = []
    for f in d.get("features", []):
        rings = f["geometry"].get("rings") or []
        if not rings:
            continue
        poly = Polygon([P(x, y) for x, y in rings[0]], [[P(x, y) for x, y in r] for r in rings[1:]])
        if poly.is_valid and poly.area > 20:
            out.append((f["attributes"], poly))
    return out


def osm(bb, P):
    s, w, n, e = bb
    q = "[out:json][timeout:120];(way[building](%f,%f,%f,%f);way[highway](%f,%f,%f,%f););out geom;" % (s, w, n, e, s, w, n, e)
    d = get(OVERPASS, data=urllib.parse.urlencode({"data": q}).encode())
    bld, streets, alleys = [], [], []
    for el in d.get("elements", []):
        pts = [P(g["lon"], g["lat"]) for g in el.get("geometry", [])]
        t = el.get("tags", {})
        if "building" in t and len(pts) >= 4:
            p = Polygon(pts)
            if p.is_valid and p.area > 6:
                bld.append((t.get("building"), p))
        elif t.get("highway") in STREET and len(pts) >= 2:
            streets.append((t.get("name", ""), LineString(pts)))
        elif t.get("highway") == "service" and len(pts) >= 2:
            (alleys if t.get("service") == "alley" else streets if False else alleys).append(LineString(pts))
    return bld, streets, alleys


def measure(attr, lot, bld, streets, alleys):
    m = {"class": attr.get("PROPCLASS"), "aux": attr.get("AUXCLASS"), "area_m2": round(lot.area, 1)}
    if not streets:
        return m
    near = sorted(((lot.distance(g), nm, g) for nm, g in streets), key=lambda t: t[0])
    d0, name0, s0 = near[0]
    def bearing(g, at):
        t = g.project(at)
        p0, p1 = g.interpolate(max(0.0, t - 3.0)), g.interpolate(t + 3.0)
        return math.atan2(p1.y - p0.y, p1.x - p0.x) % math.pi
    b0 = bearing(s0, nearest_points(s0, lot)[0])
    m["corner"] = False                                   # (a second street, crossing the first, along another side)
    for d, nm, g in near[1:]:
        if d > d0 + 8.0:
            break
        db = abs(bearing(g, nearest_points(g, lot)[0]) - b0)
        if min(db, math.pi - db) > math.radians(45):
            m["corner"] = True
            break
    # the lot's frame: x along the street at its nearest point, y away from it
    a, b = nearest_points(s0, lot)
    seg = s0.interpolate(max(0.0, s0.project(a) - 2.0)), s0.interpolate(s0.project(a) + 2.0)
    ang = math.atan2(seg[1].y - seg[0].y, seg[1].x - seg[0].x)
    ca, sa = math.cos(-ang), math.sin(-ang)

    def rot(pt):
        x, y = pt[0] - a.x, pt[1] - a.y
        return (x * ca - y * sa, x * sa + y * ca)
    L = [rot(p) for p in lot.exterior.coords]
    side = 1.0 if S.mean(p[1] for p in L) > 0 else -1.0
    L = [(x, y * side) for x, y in L]
    xs, ys = [p[0] for p in L], [p[1] for p in L]
    m["width_m"], m["depth_m"] = round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1)
    from shapely.geometry import Polygon as _P, LineString as _L
    LP = _P(L)
    dep = max(ys) - min(ys)

    def width_at(f):                                       # (the lot's width a fraction of the way back from the street)
        y = min(ys) + f * dep
        cut = LP.intersection(_L([(min(xs) - 1, y), (max(xs) + 1, y)]))
        return cut.length
    wf, wr = width_at(0.12), width_at(0.88)
    m["front_w_m"], m["rear_w_m"] = round(wf, 1), round(wr, 1)
    m["rectangularity"] = round(lot.area / lot.minimum_rotated_rectangle.area, 2)
    m["poly"] = [[round(x, 1), round(y, 1)] for x, y in L]
    m["street_gap_m"] = round(d0, 1)                       # (centreline to the lot line: half the right of way)
    m["alley"] = any(lot.distance(al) < 6.0 and lot.distance(al) > 0.5 for al in alleys)
    mine = []
    for kind, bp in bld:
        ov = bp.intersection(lot).area
        if ov > 0.5 * bp.area:
            mine.append((bp.area, kind, bp))
    mine.sort(key=lambda t: -t[0])
    m["n_buildings"] = len(mine)
    m["coverage"] = round(sum(t[0] for t in mine) / lot.area, 3) if lot.area else 0
    if mine:
        bp = mine[0][2]
        B = [rot(p) for p in bp.exterior.coords]
        B = [(x, y * side) for x, y in B]
        bxs, bys = [p[0] for p in B], [p[1] for p in B]
        m["principal"] = {"kind": mine[0][1], "area_m2": round(mine[0][0], 1), "w_m": round(max(bxs) - min(bxs), 1),
                          "d_m": round(max(bys) - min(bys), 1)}
        m["front_setback_m"] = round(min(bys) - min(ys), 1)
        m["rear_yard_m"] = round(max(ys) - max(bys), 1)
        m["side_gaps_m"] = [round(min(bxs) - min(xs), 1), round(max(xs) - max(bxs), 1)]
        acc = []
        for ar, kind, ap in mine[1:]:
            A = [rot(p) for p in ap.exterior.coords]
            ay = S.mean(p[1] * side for p in A)
            acc.append({"kind": kind, "area_m2": round(ar, 1), "where": "rear" if ay > max(bys) else "side" if ay > min(bys) else "front"})
        m["accessory"] = acc
    m["tokens"] = lot_tokens(m)                            # (after the buildings: coverage, setback, outbuilding)
    return m


def cls(v, cuts, names):
    for c, n in zip(cuts, names):
        if v < c:
            return n
    return names[-1]


def lot_tokens(m):
    """The measured lot as tokens (research/buildings/LOTS.md, vocab.json)."""
    t = []
    w, d = m.get("width_m"), m.get("depth_m")
    if w:
        t.append("lot_w:" + cls(w, (9, 14, 22, 35, 70), ("very_narrow", "narrow", "standard", "wide", "very_wide", "acreage")))
        t.append("lot_depth:" + cls(d, (25, 40, 55, 90), ("shallow", "standard", "deep", "very_deep", "acreage")))
        fw, rw = m.get("front_w_m", w), m.get("rear_w_m", w)
        rect = m.get("rectangularity", 1)
        if fw and rw and rw > 1.6 * fw:
            shape = "pie"
        elif fw and rw and fw > 1.6 * rw:
            shape = "reverse_pie"
        elif fw and fw < 0.45 * w and rect < 0.8:
            shape = "flag"
        elif rect > 0.92:
            shape = "rect"
        else:
            shape = "irregular"
        t.append("lot_shape:" + shape)
        t.append("lot_access:" + ("alley" if m.get("alley") else "street"))
        t.append("lot_corner:" + ("yes" if m.get("corner") else "no"))
    if "coverage" in m:
        t.append("lot_coverage:" + cls(m["coverage"], (0.02, 0.12, 0.25, 0.45, 0.8), ("vacant", "sparse", "low", "medium", "high", "full")))
    if "front_setback_m" in m:
        t.append("setback:" + cls(m["front_setback_m"], (1.0, 4.5, 9, 18), ("zero", "shallow", "medium", "deep", "very_deep")))
        g = min(m.get("side_gaps_m", [0, 0]))
        t.append("side_gap:" + cls(g, (0.6, 2.5, 6), ("none", "tight", "medium", "wide")))
        t.append("rear_yard:" + cls(m.get("rear_yard_m", 0), (3, 10, 20), ("none", "small", "medium", "large")))
        acc = m.get("accessory", [])
        t.append("outbuilding:" + (acc[0]["where"] if acc else "none"))
    return t


def naip(bb, path, px=1400):
    s, w, n, e = bb
    q = {"bbox": "%f,%f,%f,%f" % (w, s, e, n), "bboxSR": "4326", "imageSR": "3857", "size": "%d,%d" % (px, px),
         "format": "jpg", "f": "image"}
    with open(path, "wb") as f:
        f.write(get(NAIP + "?" + urllib.parse.urlencode(q), binary=True))


def render(bb, P, lots, bld, streets, alleys, img, out):
    from PIL import Image, ImageDraw
    s, w, n, e = bb
    W, H = P(e, n)
    im = Image.open(img).convert("RGB").resize((1400, int(1400 * H / W)))
    k = im.width / W
    dr = ImageDraw.Draw(im)
    T = lambda p: (p[0] * k, im.height - p[1] * k)                                    # noqa: E731
    for _, g in streets:
        dr.line([T(c) for c in g.coords], fill=(255, 210, 0), width=2)
    for g in alleys:
        dr.line([T(c) for c in g.coords], fill=(255, 120, 0), width=2)
    for _, bp in bld:
        dr.polygon([T(c) for c in bp.exterior.coords], outline=(255, 60, 60))
    for i, (attr, lot, m) in enumerate(lots):
        dr.polygon([T(c) for c in lot.exterior.coords], outline=(0, 255, 255))
        c = lot.representative_point()
        dr.text(T((c.x, c.y)), str(i), fill=(255, 255, 255))
    im.save(out)


def summarise(ms):
    def med(key):
        v = [m[key] for m in ms if isinstance(m.get(key), (int, float))]
        return round(S.median(v), 1) if v else None
    built = [m for m in ms if m.get("n_buildings")]
    return {"lots": len(ms), "built": len(built), "median_area_m2": med("area_m2"), "median_width_m": med("width_m"),
            "median_depth_m": med("depth_m"), "median_coverage": round(S.median([m["coverage"] for m in built]), 3) if built else None,
            "median_front_setback_m": round(S.median([m["front_setback_m"] for m in built if "front_setback_m" in m]), 1) if built else None,
            "median_rear_yard_m": round(S.median([m["rear_yard_m"] for m in built if "rear_yard_m" in m]), 1) if built else None,
            "median_least_side_gap_m": round(S.median([min(m["side_gaps_m"]) for m in built if "side_gaps_m" in m]), 1) if built else None,
            "share_alley": round(sum(1 for m in ms if m.get("alley")) / max(1, len(ms)), 2),
            "share_corner": round(sum(1 for m in ms if m.get("corner")) / max(1, len(ms)), 2),
            "share_with_accessory": round(sum(1 for m in built if m.get("accessory")) / max(1, len(built)), 2),
            "accessory_where": {w: sum(1 for m in built for a in m.get("accessory", []) if a["where"] == w) for w in ("rear", "side", "front")},
            "classes": {c: sum(1 for m in ms if m.get("class") == c) for c in sorted({str(m.get("class")) for m in ms})}}


def main():
    region = sys.argv[1] if len(sys.argv) > 1 else "great_lakes"
    want = set(sys.argv[2:])
    cfg = json.load(open(os.path.join(ROOT, "research", "buildings", "regions", region, "lot_samples.json")))
    od = os.path.join(ROOT, "research", "buildings", "regions", region, "lots")
    rd = os.path.join(ROOT, "reference", "lots", region)
    os.makedirs(od, exist_ok=True)
    os.makedirs(rd, exist_ok=True)
    for A in cfg["areas"]:
        if want and A["id"] not in want:
            continue
        bb = A["bbox"]
        P = Local(bb[0], bb[1])
        clip = box(0, 0, *P(bb[3], bb[2]))
        pl = parcels(cfg["parcels"], bb, P)
        bld, streets, alleys = osm(bb, P)
        lots = []
        for attr, lot in pl:
            if not clip.contains(lot.representative_point()):
                continue
            lots.append((attr, lot, measure(attr, lot, bld, streets, alleys)))
        summ = summarise([m for _, _, m in lots])
        summ.update({"id": A["id"], "place": A["place"], "band": A["band"], "setting": A["setting"], "bbox": bb,
                     "placenames": sorted({str(a.get("PLACENAME")) for a, _, _ in lots}), "osm_buildings": len(bld)})
        json.dump({"summary": summ, "lots": [dict(m, n=i) for i, (_, _, m) in enumerate(lots)]},
                  open(os.path.join(od, A["id"] + ".json"), "w"), indent=1)
        img = os.path.join(rd, A["id"] + "_naip.jpg")
        try:
            if not os.path.exists(img):
                naip(bb, img)
            render(bb, P, lots, bld, streets, alleys, img, os.path.join(rd, A["id"] + ".png"))
        except Exception as e:
            print("  render failed", e)
        print(json.dumps(summ))
        time.sleep(2)


if __name__ == "__main__":
    main()
