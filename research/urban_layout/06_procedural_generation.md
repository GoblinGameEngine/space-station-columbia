# Procedural city generation: the computer-graphics literature (2026-10-05)

What has been built, what each method is good at, and what fits our rules (determinism, locality, a few knobs, the
map as the authority).

| Work | Method | Good for | Fit for us |
|---|---|---|---|
| **Parish and Müller, "Procedural Modeling of Cities"** (SIGGRAPH 2001; CityEngine) | An extended L-system grows highways then streets, steered by *global goals* (pattern style: grid, radial, least-elevation; population density) and checked by *local constraints* (water, slope, snapping to nearby junctions to close loops). Lots by subdivision, buildings by grammar | Whole-city road networks from density and terrain maps | The goals and constraints split is right. Growth order makes it non-local: run it per settlement, offline |
| **Chen, Esch, Wonka, Müller, Zhang, "Interactive Procedural Street Modeling"** (SIGGRAPH 2008) | Streets are traced along a *tensor field* (grid, radial, boundary-following basis fields blended, with noise and rotation); the major and minor eigenvector lines become the streets | Street patterns that flow with shores, rivers and slopes; pattern blending between districts | Very good: the field is a closed-form function of position (local), and our map's water and terrain become its boundary fields |
| **Lipp, Scherzer, Wonka, Wimmer, "Interactive Modeling of City Layouts using Layers of Procedural Content"** (EG 2011) | Layers of procedural and manual edits merged with graph cuts; topology-preserving drag, drop and rotate | Hand edits that survive regeneration | The principle: hand-placed landmarks (the map's) as a layer the procedure respects |
| **Vanegas, Kelly, Weber, Halatsch, Aliaga, Müller, "Procedural Generation of Parcels in Urban Modeling"** (EG 2012) | Blocks split into parcels by *oriented-bounding-box* recursive split (irregular blocks) or *straight-skeleton* (frontage-preserving); style parameters for lot width, depth, frontage | Realistic lot patterns per district style | Directly usable: a block's parcels depend only on that block (local) |
| **Weber, Müller, Wonka, Gross, "Interactive Geometric Simulation of 4D Cities"** (EG 2009) | City growth over time with exact parcels, arbitrary streets, land-use values, and building envelopes, at about 1 s per step | Towns that grow and change through eras | The *time* model we want for the story engine (03), run per settlement |
| **Emilien, Bernhardt, Peytavie, Cani, Galin, "Procedural Generation of Villages on Arbitrary Terrains"** (2012) | Interest maps (sun, slope, water, roads, neighbours) seed buildings one at a time; roads connect them; walls and fields follow | Small organic settlements fitted to terrain | Our villages and resort hamlets (population_tiers under 500 to 5,000) |
| **Kelly and McCabe, "Interactive city generation methods"** (SIGGRAPH 2007), and **Kelly and McCabe's survey of procedural city techniques** | Survey and comparison: grid, L-system, agent, template methods | Choosing techniques | Background reading |
| **Galin et al., road networks on terrain** (Purdue/LIRIS) | Least-cost roads over slope, curvature, water and bridges | Roads between settlements | Our county roads and highways (already researched: research/roads) |
| **SimCity (Wright, 1989)** | Cellular automaton zoning; RCI demand loop; land value from access, parks, water, pollution, crime | Player-legible land value and growth | The land-value field; the RCI loop as a check on the mix of uses. Wright drew on Alexander |
| **StreetGen** (2018) | Street surfaces, junctions and furniture from a centreline network | Turning a graph into geometry | Our road pipeline already does this |

Sources: [Parish and Müller (SIGGRAPH history)](https://history.siggraph.org/?p=116923);
[Watson et al., Procedural urban modeling tutorial](https://peterwonka.net/Publications/pdfs/2008.CGA.Watson.ProceduralModelingTutorial.pdf);
[Purdue SIGGRAPH 2011 course: urban layouts](https://www.cs.purdue.edu/cgvlab/urban/sg_2011_course/umc_SG11_02_urban_layouts.pdf);
[Chen et al. 2008 project page](https://www2.cs.uh.edu/~chengu/Publications/streetModeling/street_modeling.html);
[Chen et al. 2008 paper](https://web.engr.oregonstate.edu/~zhange/images/street_sig08.pdf);
[Lipp et al. 2011 (TU Wien)](https://www.cg.tuwien.ac.at/research/publications/2011/lipp2011a/);
[Vanegas et al. 2012 paper](https://www.cs.purdue.edu/cgvlab/papers/aliaga/eg2012.pdf);
[OBB parcelling implementation](https://github.com/stavguo/obb-parcelling);
[Weber et al. 2009](https://diglib.eg.org/handle/10.2312/CGF.v28i2pp481-492);
[Emilien et al., villages](https://perso.liris.cnrs.fr/egalin/Articles/2012-villages.pdf);
[Kelly and McCabe (SIGGRAPH history)](https://history.siggraph.org/?p=142350);
[Galin et al., road generation](https://www.cs.purdue.edu/homes/bbenes/papers/Galin11CGF.pdf);
[StreetGen (arXiv)](https://ar5iv.labs.arxiv.org/html/1801.05741);
[Procedural modeling of urban land use (arXiv 2510.15877)](https://arxiv.org/pdf/2510.15877);
[SimCity series (mirror)](https://wikipedia.classicistranieri.com/en/articles/s/i/m/SimCity_%28series%29_b4da.html);
[Fractal nets play SimCity (arXiv)](https://arxiv.org/pdf/2002.03896);
[Purdue urban modelling publications](https://www.cs.purdue.edu/cgvlab/urban/publications.html).

## The pipeline these share

1. **Inputs (fields)**: terrain, water, protected land, density target, era or pattern style. For us these come from
   the map (map_preview / map_expanded) and the settlement's knobs.
2. **Major roads**: arterials from the inter-settlement network (already on our map), plus collectors at the
   spacing rules (04).
3. **Minor roads**: a tensor field or grid template per district, clipped by water and slope.
4. **Blocks**: the faces of the planar road graph.
5. **Parcels**: OBB or straight-skeleton split, using the district style's lot width and depth.
6. **Use and form per parcel**: from the zoning or Transect value, the bid-rent price and street integration.
   Outputs are a building *type and slot* (never a model: ssc-build-order).
7. **Time**: increments, decay, gentrification (03) over game years.
