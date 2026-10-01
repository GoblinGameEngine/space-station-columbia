# 1. Ohio's rules of the road, as the game's drivers apply them

Source: the Ohio Revised Code, Chapter 4511, read at codes.ohio.gov (2026-10-01). The BMV's
*Digest of Ohio Motor Vehicle Laws* (HSY 7607) summarises this chapter. Its old download links
(publicsafety.ohio.gov, bmv.ohio.gov) now return 404, so the statute itself is the source.

**The design rule (the user, 2026-10-01): drivers react to what is on the road.** The game bakes
no per-road behaviour. A driver obeys the signs, markings and signals it can see, and the other
road users around it. To change a street's speed limit, change its sign. To change a traffic
pattern, change its markings and signs. The left column below says what the driver perceives;
the right column says what it does.

| ORC | Rule (paraphrased; statute wording where it matters) | Perceived from | Driver behaviour |
|---|---|---|---|
| 4511.21(A) | No faster than "reasonable or proper"; able to stop "within the assured clear distance ahead". | the road ahead, the vehicle ahead | Car-following keeps a stopping gap. Speed drops for curves seen ahead. |
| 4511.21(B) | Prima-facie limits: 20 mph in school zones (when posted); **25 mph in a municipal corporation**; 35 mph on state routes and through highways in towns outside business districts; **15 mph in alleys**; **55 mph outside municipal corporations**; 60–70 on rural divided roads and freeways. | speed-limit signs; the "town" sign at the town limit; a narrow roadway | The last speed sign passed sets the limit. Passing a town sign into a town sets 25 mph (40 km/h); passing one out of town sets 55 mph (90 km/h), until another speed sign says otherwise. A roadway under 4 m wide reads as an alley: 15 mph. |
| 4511.25 | Drive on the right half of a roadway of sufficient width; slower traffic keeps right. | the road | The lane 1.8 m right of the centre line. |
| 4511.27 / .29 / .30 | Overtake on the left only with a clear view; not within 100 ft of an intersection or rail crossing. | the oncoming traffic seen; junctions ahead | Overtake a slow vehicle only when nothing is coming within the sight distance and no junction lies within 30 m. |
| 4511.31 | No-passing zones are marked by signs or markings; obey them. **Exception:** you may pass a vehicle below half the limit if you can do so without speeding and have the sight distance. | the centre-line markings: double yellow = no passing, dashed = passing allowed | Passes only where the centre line is dashed, or under the half-speed exception. Crossing a double yellow otherwise is a violation. |
| 4511.28 | Pass on the **right** only (1) a vehicle making or about to make a left turn, or (2) on a roadway with "unobstructed pavement of sufficient width for two or more lines of vehicles" in your direction; **never by driving off the roadway**. | the vehicle ahead is stopped to turn left; the roadway width | Legal: passing a left-turner on a road wide enough (≥ 10 m) without leaving the pavement. Anything else, such as passing on the shoulder or a narrow street, is a violation. |
| 4511.34 | Don't follow "more closely than is reasonable and prudent". | the vehicle ahead | The driver's time headway; below about 1 s counts as tailgating. |
| 4511.36 / .39 | Turn from the proper position; signal turns. | the route | (Turn-signal lamps are not modelled yet.) |
| 4511.41 | At an intersection with no control, when two arrive at about the same time, **the driver on the left yields to the driver on the right**. | the junction's geometry and the vehicles approaching it | At an unsigned junction, yields to a vehicle approaching from the right that will arrive within 3 s. |
| 4511.42 | Turning left: yield to oncoming traffic within the intersection or "so close … as to constitute an immediate hazard". | oncoming vehicles | Before a left turn, waits while an oncoming vehicle is within 5 s of the junction. |
| 4511.43(A) | At a **stop sign**: stop at the marked stop line, or if none before the crosswalk, or where the cross road can be seen; then yield to anything in the intersection or approaching closely enough to be an immediate hazard. | the stop sign facing the driver; the stop bar painted near it | Stops at the bar (or at the sign), stays stopped at least 1 s, then waits for a clear junction. At all-way stops it goes in arrival order. A rolling stop is the violation. |
| 4511.43(B) | At a **yield sign**: slow, stop if needed for safety, yield. | the yield sign | Slows to 15 km/h; stops only when a conflicting vehicle is close. |
| 4511.44 | Entering from a private drive or any place other than a roadway: yield to all traffic. | leaving a parking place | Pulls out only into a gap. |
| 4511.45 | Public safety vehicles with lights and siren: pull to the right edge, stop, wait until they pass. Streetcars stop clear of the intersection. | an emergency vehicle's lights and siren | (Hook in place; the game has no emergency runs yet.) |
| 4511.46 | Yield to pedestrians in a crosswalk on your half of the road, or close on the other half; don't pass a car stopped for a pedestrian. | people on the roadway ahead | Stops for a person on the road in its path within 12 m. Failing to yield is a violation. |
| 4511.13 | Signals: green go (left turns yield); steady yellow: clear or stop; red: stop at the line. | the signal heads (road_furniture `signals`), read by direction | Stops at red; on yellow, stops if it can. Running the yellow or red is a violation. |
| 4511.62 | Rail crossings: stop 15–50 ft from the nearest rail when a train is approaching, plainly visible and in hazardous proximity. | crossbuck signs; the train | Stops 5–15 m short of the crossing while a train is within 400 m. |
| 4511.68 | No parking within 20 ft of a crosswalk, 30 ft of a stop sign, or 10 ft of a hydrant; not on a crosswalk or sidewalk. | — | Parking places (NpcTraffic) keep clear of signs and junctions. |

**Streetcars (trams):** 4511.21, .34, .41, .42 and .46 name "streetcar" and "trackless trolley"
explicitly. Our road trams therefore obey the same signs and right-of-way rules as cars. Their
operators are professionals and never break them (see 04).

**Units.** Ohio posts limits in mph. The game's road standard (research/roads) posts km/h signs
that are the metric versions of the same limits: 40 km/h ≈ 25 mph, 60 ≈ 35, 70 ≈ 45,
90 ≈ 55. Drivers read whatever the sign says. Switching the signage to mph means changing
`LIMIT` in tools/road_furniture.py and the sign art; drivers would follow without any code
change.
