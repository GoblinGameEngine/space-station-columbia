# Neighbourhood change: decline, filtering, gentrification, sorting (2026-10-05)

This is the time dimension: a district is not born in its final state, and the story engine needs districts that
change.

## Filtering and the neighbourhood life cycle

- **Hoover and Vernon (1959)**, five stages:
  1. New single-family development.
  2. Transition: apartments are added and density rises.
  3. Downgrading: conversions, overcrowding, and arrival of poorer and minority households.
  4. Thinning: population loss and fewer units.
  5. Renewal: public redevelopment, replacing old housing with new apartments.
- **HUD / RERC (1975)**, a bleaker sequence: healthy, incipient decline, clearly declining, accelerating decline,
  abandoned.
- **Filtering**: housing passes down the income ladder as it ages, relative to new building.
- **Reverse filtering** (gentrification): cheap housing climbs back up.
- **Caution**: the cycle is a tendency, not a law ("avoiding the inevitability trap"). Districts stall, skip stages
  or reverse.

Sources: [Myths and realities about cycles (Shelterforce)](https://shelterforce.org/2017/01/09/myths-and-realities-about-cycles-avoiding-the-inevitability-trap/);
[Planetizen version](https://planetizen.com/node/90793);
[Filtering (academia.edu)](https://www.academia.edu/4065468/Filtering).

## Gentrification

- **Ruth Glass coined the word in 1964** for working-class districts of London "invaded by the middle class... until
  all or most of the original occupiers are displaced and the whole social character of the district is changed."
- **Neil Smith's rent gap (1979)**:
  - Gentrification happens where the gap is widest between the ground rent a site earns now (capitalised rent) and
    what it could earn under its best use (potential rent).
  - Disinvestment *creates* the gap: suburbanisation drained the inner districts, and capital returns when the gap is
    wide enough.
- **Stages** (the Urban Displacement Project's typology, from census indicators):
  - Low-income tracts move from *susceptible / not losing low-income households* to *early* (type 1: housing market
    heating; type 2: demographic change starting), then *ongoing*, then *advanced gentrification*.
  - Moderate- to high-income tracts can reach *advanced exclusion*, where low-income households can no longer get in.
- **Indicators** (all measurable per tract, so all simulable per district): the share of low-income and renter
  households, rent and home-value change against the region, and change in education, income and race.
- **What you can see on the street**:
  - Renovations of older housing stock, in the order porches, paint, then additions.
  - New cafés and boutiques in old storefronts (Jacobs's "aged buildings" put to new use).
  - Conversions of industrial loft buildings.
  - Vacant lots infilled with modern townhouses.
  - Rising rents displacing the bar, the laundromat and the hardware store.

Sources: [Gentrification (UBC wiki)](https://wiki.ubc.ca/Gentrification);
[Rent gap and gentrification (Redalyc)](https://www.redalyc.org/pdf/4028/402833928001.pdf);
[Neil Smith (academia.edu)](https://www.academia.edu/1734349/neil_smith);
[Urban Displacement Project methodology](https://www.urbandisplacement.org/wp-content/uploads/2021/08/udp_replication_project_methodology_10.16.2020-converted.pdf);
[Next City: gentrification warning map](https://nextcity.org/daily/entry/new-mapping-gentrification-warning-system-bay-area-cities-berkeley);
[Portland Central Eastside example](https://www.nextportland.com/2015/11/20/the-changing-face-of-portlands-central-eastside/).

## Segregation and sorting (Schelling)

- **The model**: agents of two kinds each want only a modest share of like neighbours (say 30 %) and move when
  unhappy. The result is near-total segregation (90 %+), which no individual wanted.
- **Tipping**: once a block passes a threshold share, the process runs on by itself and does not reverse.
- **For us**: a cheap agent rule over our NpcLife households. It produces realistic clustering by class and
  subculture without our painting it on, and it moves over game time.

Sources: [Schelling segregation explainer](https://www.codesota.com/explainers/schelling-segregation);
[Zhang, tipping and residential segregation (IZA DP 4413)](https://www.iza.org/publications/dp/4413).

## Redlining and the mortgage map -- how policy drew the lines (historical)

- **HOLC (1935-40)** graded neighbourhoods A to D (green, blue, yellow, red) for "mortgage security". Race and the
  presence of immigrants or working-class residents drove the grades.
- **The 1938 FHA Underwriting Manual** treated "incompatible racial or social groups" as an adverse influence, and
  the FHA insured the new suburbs on that basis. Levittown (1947; 17,447 homes; 50,000+ residents) barred Black
  buyers by covenant.
- **The lasting effect**: grade-D districts were starved of credit, and that disinvestment opened the rent gaps that
  later drove gentrification.
- **For us**:
  - The *mechanism* matters: credit flows by district grade, and the grade decides decay or renewal.
  - The station's own history (the bible) can supply its own grading institution and prejudices; Earth's racial
    history should not be copied in.
  - This is a tone decision for the bible: see README "Open questions".

Sources: [HOLC residential security maps (Cambridge, Social Science History)](https://resolve.cambridge.org/core/journals/social-science-history/article/residential-security-maps-and-neighborhood-appraisals/4A0B09013DBDC7B4536AA563EA869C6B);
[Pair HOLC maps with FHA maps (The Metropole)](https://themetropole.blog/2023/08/16/pair-holc-maps-with-fha-maps-to-tell-a-more-complete-story/);
[Aaronson, Hartley, Mazumder: effects of the HOLC maps](https://www.irp.wisc.edu/newsevents/workshops/2017/participants/papers/1-Aaronson-Hartley-Maxumder-SRW2017-6-19-2017.pdf);
[Housing inequality: postwar suburbs (USC Scalar)](https://scalar.usc.edu/works/housing-inequality/inequality-in-housing-post-wwii-urban-flight-and-the-creation-of-the-suburbs.29);
[Levitt estates segregation](https://simplestudy.com/gb/a-level/edexcel/history/revision-notes/391-civil-rights-and-race-relations-in-the-usa-18502009/the-changing-geography-of-civil-rights-issues/development-of-de-facto-segregation-against-black-americans-in-levitt-estates).

## What a generator takes from this

- **Each district carries state**: age, condition (0-1), price relative to the town, a tenure mix, and an investment
  grade.
- **Each game year**:
  - Condition decays with age.
  - Price follows condition, accessibility and amenity (bid-rent).
  - The rent gap is potential price minus current price; where it passes a threshold, renovation and infill
    begin (gentrification).
  - Where condition falls and the investment grade is low, conversions and vacancy begin (filtering, decline).
- **What is visible**: each state change maps to lot content (lot_contents research), storefront turnover (the
  procedural stores) and NPC moves (Schelling).
