#!/usr/bin/env python3
"""center_sample.py [AREA_ID ...] -- measure real shopping centres and industrial parks
(research/urban_layout/07_centers_and_industry.md; samples in research/urban_layout/centers_samples.json).

From OSM (Overpass: buildings, parking areas, roads, shops/amenities) and the NAIP aerial: each building's footprint,
its minimum-rectangle width and depth, its role by size (anchor / junior / inline / pad / small), the parking area and
the implied stalls per 1,000 sq ft of building, the building-to-road setback, and the tenant mix (shop= / amenity= /
craft= / office= / industrial= tags). Writes research/urban_layout/centers/<id>.json and a render to
reference/centers/<id>.png. OSM data (c) OpenStreetMap contributors, ODbL; NAIP public domain."""
import collections, json, math, os, statistics as S, sys, time, urllib.parse

from shapely.geometry import LineString, Polygon
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lot_sample as LS  # noqa: E402

ROOT = LS.ROOT
SQFT = 10.7639
STALL_M2 = 32.0                       # (a stall plus its share of aisle: 300-350 sq ft gross per space)
ROADS = {"primary", "secondary", "tertiary", "trunk", "residential", "unclassified", "motorway_link", "primary_link", "secondary_link"}


def fetch(bb, P):
    s, w, n, e = bb
    q = ("[out:json][timeout:180];(way[building](%f,%f,%f,%f);way[amenity=parking](%f,%f,%f,%f);way[highway](%f,%f,%f,%f);"
         "nwr[shop](%f,%f,%f,%f);nwr[amenity~\"restaurant|fast_food|cafe|bank|pharmacy|fuel|bar|cinema|clinic|dentist|doctors|fitness_centre|car_wash|post_office\"](%f,%f,%f,%f);"
         "nwr[office](%f,%f,%f,%f);nwr[craft](%f,%f,%f,%f);nwr[leisure=fitness_centre](%f,%f,%f,%f););out geom;") % ((s, w, n, e) * 8)
    d = LS.get(LS.OVERPASS, data=urllib.parse.urlencode({"data": q}).encode())
    bld, park, roads, tenants = [], [], [], []
    for el in d.get("elements", []):
        t = el.get("tags", {})
        geom = el.get("geometry") or ([{"lon": el["lon"], "lat": el["lat"]}] if "lon" in el else [])
        pts = [P(g["lon"], g["lat"]) for g in geom]
        for k in ("shop", "amenity", "office", "craft", "leisure"):
            if k in t and not (k == "amenity" and t[k] == "parking"):
                tenants.append("%s=%s" % (k, t[k]))
                break
        if "building" in t and len(pts) >= 4:
            p = Polygon(pts)
            if p.is_valid and p.area > 15:
                bld.append((t.get("building"), p))
        elif t.get("amenity") == "parking" and len(pts) >= 4:
            p = Polygon(pts)
            if p.is_valid:
                park.append(p)
        elif t.get("highway") in ROADS and len(pts) >= 2:
            roads.append((t.get("highway"), LineString(pts)))
    return bld, park, roads, tenants


def role(a_sqft):
    return ("anchor" if a_sqft >= 40000 else "junior" if a_sqft >= 15000 else "inline" if a_sqft >= 3000 else "pad" if a_sqft >= 1500 else "small")


def main():
    cfg = json.load(open(os.path.join(ROOT, "research", "urban_layout", "centers_samples.json")))
    want = set(sys.argv[1:])
    od = os.path.join(ROOT, "research", "urban_layout", "centers")
    rd = os.path.join(ROOT, "reference", "centers")
    os.makedirs(od, exist_ok=True)
    os.makedirs(rd, exist_ok=True)
    for A in cfg["areas"]:
        if want and A["id"] not in want:
            continue
        la, lo, h = A["c"]
        w = h / math.cos(math.radians(la))
        bb = [la - h, lo - w, la + h, lo + w]
        P = LS.Local(bb[0], bb[1])
        bld, park, roads, tenants = fetch(bb, P)
        arterials = [g for k, g in roads if k in ("primary", "secondary", "trunk", "tertiary")]
        rows = []
        for kind, p in bld:
            r = p.minimum_rotated_rectangle
            xs = list(r.exterior.coords)
            e1 = math.dist(xs[0], xs[1])
            e2 = math.dist(xs[1], xs[2])
            a = p.area * SQFT
            rows.append({"kind": kind, "area_sqft": round(a), "w_ft": round(max(e1, e2) * 3.281), "d_ft": round(min(e1, e2) * 3.281),
                         "role": role(a), "to_arterial_ft": round(min((p.distance(g) for g in arterials), default=-1) * 3.281)})
        big = [r for r in rows if r["role"] != "small"]
        gla = sum(r["area_sqft"] for r in big)
        park_sqft = sum(p.area for p in park) * SQFT
        summ = {"id": A["id"], "place": A["place"], "type": A["type"], "buildings": len(big),
                "gla_sqft": gla, "parking_sqft": round(park_sqft), "parking_to_building": round(park_sqft / gla, 2) if gla else None,
                "stalls_per_1000": round(park_sqft / SQFT / STALL_M2 / (gla / 1000), 2) if gla else None,
                "roles": dict(collections.Counter(r["role"] for r in big)),
                "median_depth_ft": {k: round(S.median([r["d_ft"] for r in big if r["role"] == k])) for k in {r["role"] for r in big}},
                "median_to_arterial_ft": {k: round(S.median([r["to_arterial_ft"] for r in big if r["role"] == k])) for k in {r["role"] for r in big}},
                "building_kinds": dict(collections.Counter(r["kind"] for r in big).most_common(8)),
                "tenants": dict(collections.Counter(tenants).most_common(40))}
        json.dump({"summary": summ, "buildings": rows}, open(os.path.join(od, A["id"] + ".json"), "w"), indent=1)
        img = os.path.join(rd, A["id"] + "_naip.jpg")
        try:
            if not os.path.exists(img):
                LS.naip(bb, img)
            LS.render(bb, P, [], bld, [("", g) for _, g in roads], [], img, os.path.join(rd, A["id"] + ".png"))
            from PIL import Image, ImageDraw
            im = Image.open(os.path.join(rd, A["id"] + ".png"))
            dr = ImageDraw.Draw(im)
            W, H = P(bb[3], bb[2])
            k = im.width / W
            for p in park:
                dr.polygon([(x * k, im.height - y * k) for x, y in p.exterior.coords], outline=(80, 160, 255))
            im.save(os.path.join(rd, A["id"] + ".png"))
        except Exception as e:
            print("  render failed", e)
        print(json.dumps(summ))
        time.sleep(3)


if __name__ == "__main__":
    main()
