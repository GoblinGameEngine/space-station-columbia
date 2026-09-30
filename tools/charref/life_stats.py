#!/usr/bin/env python3
"""Distribution check for the life traits (money, addiction, travel) against the targets in
research/lives/. python3 tools/charref/life_stats.py [n]"""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(__file__))
import traits as T

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    data = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "godot_project", "remake", "characters", "npc_traits.json")))
    ppl = []
    for i in range(n):
        p = T.Person(data, 7, "S%d:0" % i, ["L0", "L1", "L2"])
        ppl.append({k: p.get(k) for k in ("age", "sex", "occupation", "wage", "car_access", "commute_mode", "savings", "debt", "finances", "addictions", "addiction_stage", "money_style")})
    ad = [p for p in ppl if p["age"] >= 18]
    workers = [p for p in ad if p["commute_mode"] not in ("none",)]
    pct = lambda xs, f: 100.0 * sum(1 for x in xs if f(x)) / max(1, len(xs))
    print("adults %d of %d" % (len(ad), n))
    fin = collections.Counter(p["finances"] for p in ad)
    print("finances (adults): " + ", ".join("%s %.0f%%" % (k, 100 * v / len(ad)) for k, v in fin.most_common()),
          "| at least okay (wealthy+comfortable+getting_by) %.0f%% [target ~72%%]" % pct(ad, lambda p: p["finances"] in ("wealthy", "comfortable", "getting_by")))
    print("savings < $400: %.0f%% [target ~37%% couldn't cover $400 in cash]; median wage of earners $%.0f" % (
        pct(ad, lambda p: p["savings"] < 400), sorted(p["wage"] for p in ad if p["wage"] > 0)[len([p for p in ad if p["wage"] > 0]) // 2]))
    kinds = collections.Counter(k for p in ad for k in p["addictions"])
    print("addictions (adults, any stage): " + ", ".join("%s %.1f%%" % (k, 100 * v / len(ad)) for k, v in kinds.most_common()))
    subs = ("alcohol", "cannabis", "opioids", "stimulants", "sedatives")
    print("  any substance (excl. nicotine/caffeine) %.1f%% [target SUD ~17%%]; active stage share of those with any %.0f%%" % (
        pct(ad, lambda p: any(k in subs for k in p["addictions"])), pct([p for p in ad if p["addictions"]], lambda p: p["addiction_stage"] == "active")))
    teens = [p for p in ppl if 13 <= p["age"] < 20]
    print("  teens: social media %.0f%%, gaming %.0f%%" % (pct(teens, lambda p: "social_media" in p["addictions"]), pct(teens, lambda p: "gaming" in p["addictions"])))
    print("car access (adults): " + ", ".join("%s %.0f%%" % (k, 100 * v / len(ad)) for k, v in collections.Counter(p["car_access"] for p in ad).most_common()), "[target no vehicle ~8% of households]")
    cm = collections.Counter(p["commute_mode"] for p in workers)
    print("commute (adults who commute): " + ", ".join("%s %.1f%%" % (k, 100 * v / len(workers)) for k, v in cm.most_common()))

if __name__ == "__main__":
    main()
