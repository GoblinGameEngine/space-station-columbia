# Traffic flow: how much moves where, and what the street network must carry (2026-10-05)

Driver behaviour (rules, violation rates, psychology) is already in research/traffic/. This file covers the *macro*
side: generating demand, sizing roads and spacing them.

## Speed, flow and density

- **Greenshields (1935)**: speed falls linearly with density, v = v_f(1 − k/k_j).
  - Flow is q = k·v, which peaks at q_max = v_f·k_j/4 at half the jam density.
  - Past that point, more cars give *less* flow (congestion).
- **The BPR volume-delay function** (used by every four-step model): t = t₀(1 + α(V/C)^β), with α = 0.15 and
  β = 4 classically. It gives the link travel time from volume and capacity.
- **The macroscopic fundamental diagram** (Geroliminis and Daganzo, Yokohama 2008): a whole urban area has a smooth
  speed-density curve, even though single detectors scatter.
  - Accumulation in a district predicts its throughput, so a town's traffic can be simulated at district level
    without simulating every car.
- **For us**:
  - BPR on the generated network gives "how busy is this road at 8 am" cheaply, to set ambient NPC traffic density
    and stroad congestion.
  - The MFD is the far-LOD stand-in: districts outside the streaming radius carry an accumulation number, not cars.

Sources: [Fundamental diagrams (Polytechnique Montréal)](https://moodle.polymtl.ca/mod/resource/view.php?id=383455);
[Fundamental diagram handouts (TUM)](https://www.mos.ed.tum.de/fileadmin/w00ccp/tb/teaching/materials/Moreno_fundamental_diagram_handouts.pdf);
[Representing the fundamental diagram (SWOV)](https://swov.nl/en/publicatie/representing-fundamental-diagram-pursuit-mathematical-elegance-and-empirical-accuracy);
[Existence of urban-scale MFDs (Berkeley ITS)](https://its.berkeley.edu/publications/existence-urban-scale-macroscopic-fundamental-diagrams-some-experimental-findings-0);
[Analytical approximation of the MFD](https://its.berkeley.edu/publications/analytical-approximation-macroscopic-fundamental-diagram-urban-traffic).

## Demand: the four-step model

1. **Trip generation**: trips produced and attracted by each zone.
   - ITE: a single-family detached house makes about 9.4-9.6 vehicle trips a weekday (field range 9.4-12.2).
   - Apartments make about 5.4-6.7 a unit.
   - Retail and offices are rated per 1,000 sq ft.
2. **Trip distribution**: which zones pair up. Usually a **gravity model**: trips between i and j are proportional
   to Pᵢ·Aⱼ·f(travel cost), with f decaying with distance or time.
3. **Mode choice**: car, transit, walk or bike, by logit on time and cost.
4. **Assignment**: routes on the network, with BPR delays, to equilibrium.

- **For us**:
  - Our NpcLife schedules already make the trips individually (home to work to shop), which is steps 1-3 done per
    agent.
  - The four-step model is the *aggregate check*, and the way to size roads before the agents exist:
    1. Generate land use.
    2. Run a coarse gravity and assignment pass on the street graph.
    3. Promote heavily loaded links to collector or arterial width.
  - That is how real road hierarchies arise, so the hierarchy is derived, not drawn.
  - Reilly's and Huff's gravity models give shop catchments by the same rule (02).

Sources: [ITE trip generation (Concord NH code)](https://www.zoneomics.com/code/concord-NH/chapter_15);
[Tahoe trip generation](https://www.trpa.gov/wp-content/uploads/Attachment-A-Tahoe-Trip-Generation.pdf);
[Trip generation and the four-step model (TUM)](https://mediatum.ub.tum.de/node?id=1325861);
[BTS/NTL travel demand report](https://rosap.ntl.bts.gov/view/dot/19599/dot_19599_DS1.pdf).

## The road hierarchy and spacing

| Class | Function | Spacing (FHWA / regional guidance) | Notes |
|---|---|---|---|
| Interstate / freeway | through movement, no access | between towns | interchanges become nodes (edge cities, the strip) |
| Principal arterial | town to town | 1-2 mi suburban; through the core | the US highway through town = Main Street or the strip |
| Minor arterial | district to district | 1/8-1/2 mi in urban cores; 2-3 mi suburban | the section-line roads on a 1-mile grid |
| Collector | gathers local streets onto arterials | 1/4-3/4 mi | the neighbourhood unit's spine |
| Local | access to lots | the block size: 200-600 ft | grid, or loops and culs-de-sac (05) |

- **Our road standard** (research/roads/SSC_ROAD_STANDARD.md) already sets the cross-sections.
- **What this table adds**: the *spacing and connection* rules a generator needs.
  - Locals connect only to collectors (postwar) or to everything (grid).
  - Collectors connect to arterials at about 1/4-mile spacing.

Sources: [FHWA functional classification cheat sheet](https://kdot.kanecountyil.gov/KKCOM/Documents/STP/FHWA%20Guidelines%20Cheat%20Sheet%20-%20Functional%20Classification.pdf);
[FHWA FC 2012 guidance (VTrans)](https://maps.vtrans.vermont.gov/Maps/tempstor/functionalclass/FHWAFC2012AASHTOAdditional.pdf);
[Functional and context classification (UKy)](https://kp.uky.edu/knowledge-portal/articles/understanding-functional-classification-and-context-classification/);
[Met Council functional classification](https://imagine2050.metrocouncil.org/reference-materials/transportation/highway-investment-plan/roadway-functional-classification/).

## Induced demand

- **Duranton and Turner (2011)**: the elasticity of vehicle-km travelled to interstate lane-km in US metro areas is
  about 1.0 (1.03).
  - New capacity fills: from residents driving more, more commercial traffic, and in-migration.
  - Transit provision did not change VKT.
- **For us**: if the story engine widens a road, traffic rises to match within a few game years. Congestion is a
  property of a town's growth, not something a road project fixes.

Sources: [Duranton and Turner, AER 2011](https://economics.brown.edu/sites/g/files/dprerj726/files/news/Duranton_Turner_AER_2011.pdf);
[NBER working paper](https://www.nber.org/papers/w15376.pdf);
[TRID record](https://trid.trb.org/view.aspx?id=1124678);
[A counter-view (Reason)](https://reason.org/induced-demand-adding-road-capacity-and-traffic-congestion/).

## Network shape and travel

- **Connectivity**: well-connected grids (high intersection density, many 4-way junctions, few dead ends) spread
  trips over parallel streets.
- **Hierarchy**: tree-like suburban networks force every trip onto a few arterials, which become congested stroads
  even at low density. This is the main traffic difference between the 1920 grid and the 1970 subdivision.
- **Boeing**: griddedness predicts lower car ownership after controlling for density and income (05).
