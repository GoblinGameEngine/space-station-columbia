# 7. The planning literature

## Walkable development

| author / year | work | what we take |
|---|---|---|
| Jacobs 1961 | The Death and Life of Great American Cities | mixed primary uses, short blocks, buildings of mixed ages, density; eyes on the street; sidewalks as social places (20-35 ft where busy) |
| Lynch 1960 | The Image of the City | paths, edges, districts, nodes, landmarks: legible towns |
| Gehl 1971 / 2010 | Life Between Buildings; Cities for People | the human scale: ground floors with frequent doors, edges to linger, 5 km/h architecture |
| Frank & Pivo 1994; Saelens, Sallis & Frank 2003 | Impacts of mixed use and density on driving, transit and walking; Environmental correlates of walking and cycling | density, mix and connectivity raise walking; the walkability index |
| Cervero & Kockelman 1997; Ewing & Cervero 2010 | Travel demand and the 3Ds; Travel and the Built Environment (meta-analysis, JAPA) | the D variables: density, diversity, design, destination accessibility, distance to transit; intersection density and destination access matter most for walking |
| Southworth 2005 | Designing the Walkable City (J. Urban Planning & Development) | connectivity, linkage to other modes, fine-grained land use, safety, path quality, path context |
| Speck 2012 | Walkable City | the general theory of walkability: a walk must be useful, safe, comfortable and interesting |
| Forsyth 2015 | What is a walkable place? (Urban Design International) | walkability means different things: measure what you mean |

## Urban development

| author / year | work | what we take |
|---|---|---|
| Alexander et al. 1977 | A Pattern Language | patterns from region to room: the 'network of paths and cars', 'promenade', 'small public squares' |
| Whyte 1980 | The Social Life of Small Urban Spaces | sittable space, sun, food, triangulation: what makes plazas used |
| Calthorpe 1993 | The Next American Metropolis | transit-oriented development: mixed-use within a 400-800 m walk of a stop |
| Duany & Plater-Zyberk; CNU 1996 | Charter of the New Urbanism | 5-minute walk (400 m) neighbourhoods, connected streets, buildings to the street, parking behind |
| Duany, Plater-Zyberk & Alminana 2003 | The New Civic Art; the Transect | rural-to-urban transect zones T1-T6 set street and building form by place |
| Glaeser 2011 | Triumph of the City | density and proximity as the engine of exchange |

## Suburban development

| author / year | work | what we take |
|---|---|---|
| Warner 1962 | Streetcar Suburbs | suburbs grew along the tram lines, lots within a walk of the car stop |
| Jackson 1985 | Crabgrass Frontier | the US suburb: transport, cheap land, FHA lending, and its costs |
| Fishman 1987 | Bourgeois Utopias | the suburb as an idea of the family retreat |
| Southworth & Ben-Joseph 1997 | Streets and the Shaping of Towns and Cities | how subdivision street standards (FHA 1930s, ITE) produced loops and cul-de-sacs, and wide streets |
| Duany, Plater-Zyberk & Speck 2000 | Suburban Nation | sprawl's costs; collector-street hierarchy versus the connected grid |
| Hayden 2003 | Building Suburbia | seven historical suburban landscapes, 1820-2000 |
| Dunham-Jones & Williamson 2009 | Retrofitting Suburbia | turning malls and strips into walkable centres |
| Radburn 1929; FHA 1936 | (plans and guidelines) | the cul-de-sac superblock; FHA promotes curvilinear streets and cul-de-sacs |

## Rules the generator applies

- **walk_radius_m:** 400
- **transit_walk_radius_m:** 800
- **core_block_max_m:** 121.92
- **town_block_max_m:** 182.88
- **intersection_density_target_per_km2:** 100
- **core_frontage:** "build to the back of the sidewalk; doors every 10-15 m; parking behind or in public lots"
- **town_frontage:** "front yards per the zoning district; garages behind the front wall"
- **sidewalks:** "both sides of every town street (the cities' codes); ADA clear 1.2 m minimum (PROWAG), passing space every 60 m on 1.2 m walks; cross slope 2 % max"
- **tree_lawn:** "between kerb and walk on residential streets: trees every 12 m"
- **parking_lots:** "downtown: behind the street wall, never at a corner; park-and-ride at the edge of town on a tram stop"
- **park_and_ride:** {"at": "a tram stop at the edge of each city and town, on the trunk road in", "spaces": [40, 150], "walk_to_stop_max_m": 120}
- **cul_de_sac:** "only where land allows nothing else; under 183 m; a footpath through to the next street where possible (Southworth & Ben-Joseph)"
