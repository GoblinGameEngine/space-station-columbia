#!/usr/bin/env python3
"""traffic_reports.py -- what the game's road users reported wrong with the roads (TrafficReports, user://traffic_reports.json).

    python3 tools/traffic_reports.py                 the summary: by kind, then the most-reported places
    python3 tools/traffic_reports.py KIND [N]        every report of one kind (sign_no_junction, sign_in_lane, sign_hit,
                                                     turn_too_tight, no_route, off_route, stuck, crash_static, no_parking)
    python3 tools/traffic_reports.py --town NAME     one town's
    python3 tools/traffic_reports.py --file PATH     another copy of the reports
    python3 tools/traffic_reports.py --survey [...]  the road survey's findings instead (RoadSurvey, user://road_survey.json),
                                                     summarised by kind, cause and severity, with the fix for each cause

Fill it by playing, or let the game tour its towns on its own:
    ../godot/godot4 --path . -- --selftest --quit-after-tour      (from godot_project/; ~2 min a stop)
Each report has its place (s, x): look there with `tools/where.py near S X` or `tools/gcmd.py query near S X`.
"""
import collections
import json
import os
import sys

PATH = os.path.expanduser("~/.local/share/godot/app_userdata/Space Station Columbia/traffic_reports.json")
SURVEY = os.path.expanduser("~/.local/share/godot/app_userdata/Space Station Columbia/road_survey.json")


def main(argv):
    path = PATH
    survey = "--survey" in argv
    if survey:
        argv.remove("--survey")
        path = SURVEY
    if "--file" in argv:
        i = argv.index("--file")
        path = argv[i + 1]
        del argv[i:i + 2]
    town = None
    if "--town" in argv:
        i = argv.index("--town")
        town = argv[i + 1]
        del argv[i:i + 2]
    if not os.path.exists(path):
        print("no reports yet at", path)
        return 1
    d = json.load(open(path))
    reps = d.get("reports", [])
    if town:
        reps = [r for r in reps if r.get("town") == town]
    print("%d reports (saved %s)%s" % (len(reps), d.get("saved", "?"), " in " + town if town else ""))
    if argv:
        kind = argv[0]
        n = int(argv[1]) if len(argv) > 1 else 50
        rs = sorted([r for r in reps if r["kind"] == kind], key=lambda r: -r["n"])
        for r in rs[:n]:
            print("  x%-4d s %8.1f x %8.1f  %-16s %-28s %s  [%s]" % (r["n"], r["s"], r["x"], r.get("town", ""), r.get("road", "")[:28],
                                                                  r["what"], ", ".join(r.get("by", [])[:3])))
        return 0
    kinds = collections.Counter()
    hits = collections.Counter()
    for r in reps:
        kinds[r["kind"]] += 1
        hits[r["kind"]] += r["n"]
    for k, c in kinds.most_common():
        print("  %-18s %5d places, %6d reports" % (k, c, hits[k]))
    if survey:
        print("surveyors %s, %s m driven" % (d.get("surveyors"), d.get("metres")))
        causes = collections.Counter((r["kind"], r.get("cause", ""), r.get("severity", "")) for r in reps)
        fixes = {(r["kind"], r.get("cause", "")): r.get("fix", "") for r in reps}
        print("by cause:")
        for (k, cause, sev), c in sorted(causes.items(), key=lambda kv: -kv[1]):
            print("  %5d  %-16s %-22s %-8s -> %s" % (c, k, cause, sev, fixes[(k, cause)]))
    towns = collections.Counter(r.get("town", "") for r in reps)
    print("by town:", ", ".join("%s %d" % (t or "(country)", c) for t, c in towns.most_common()))
    print("most reported:")
    for r in sorted(reps, key=lambda r: -r["n"])[:15]:
        print("  x%-4d %-16s s %8.1f x %8.1f  %-16s %s" % (r["n"], r["kind"], r["s"], r["x"], r.get("town", ""), r["what"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
