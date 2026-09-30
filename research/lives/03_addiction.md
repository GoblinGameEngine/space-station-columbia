# 3. Addiction

Some people suffer addiction, and of many kinds. It is one of the most specific things a character
can carry into a conversation, and one of the easiest to get wrong. This file covers the
prevalences, the model, and how the game should portray it.

## The traits
| trait | what |
|---|---|
| `addictions` | Tags, drawn independently: nicotine, alcohol, caffeine, social_media, cannabis, shopping, food, gambling, work, opioids, sedatives, gaming, stimulants. |
| `addiction_stage` | For anyone with at least one: **at risk** 30, **active** 35, **recovering** 28, **relapsed** 7. |
| `addiction_severity` | 0–1, beta(2, 3), in the DSM-5 spirit of mild, moderate and severe. Zero when there are none. |

**Risk modifiers**, each kind with its own mix:
- impulsive distress: `(0.6 + 0.8·N) × (1.4 − 0.8·C)`, from high neuroticism and low
  conscientiousness. It applies to alcohol, nicotine, cannabis, opioids, stimulants, gambling and
  shopping. Sedatives, social media and food use neuroticism alone; gaming uses low
  conscientiousness alone; work addiction rises with *high* conscientiousness;
- sex: men more for alcohol, gambling and gaming; women more for shopping, social media and
  sedatives;
- age: social media and gaming peak in the teens and twenties, gambling and cannabis under 30,
  sedatives over 50;
- occupation and body:
  - alcohol: bartenders, waiters, cooks, fishers and dock workers drink more;
  - nicotine: builders, dock workers, fishers, factory hands, farmhands and drivers smoke more;
  - opioids: the same manual trades plus mechanics, and anyone with a mobility aid (×2.5): injury
    and pain;
  - stimulants: drivers, hotel workers, nurses and bartenders (long, odd hours);
  - caffeine: nurses, doctors, drivers, police, editors and hotel workers;
  - gambling: somewhat more on low wages.

## Prevalence, generated vs sources (adults, any stage)
| kind | generated | source / target |
|---|---|---|
| nicotine | 18.9% | Current use of any tobacco ≈ 18–20% (NSDUH/NHIS; approximate) |
| alcohol | 11.7% | Alcohol use disorder ≈ 10% past year (NSDUH 2023, approximate); men about twice women (NESARC 2004–05: 10.5% vs 5.1%) |
| caffeine | 10.0% | Caffeine dependence; not a DSM disorder. Used for everyday colour. |
| social media | 7.1% | Problematic social media use: 24% worldwide, 14% in individualist countries (Cheng et al. 2021). Kept low for adults; **teens 27%**. |
| cannabis | 6.2% | Cannabis use disorder ≈ 7% (NSDUH 2023, approximate) |
| shopping | 3.6% | Compulsive buying 1.8–8.1%, mostly women (Black 2007) |
| food | 3.1% | Food addiction ≈ 2.8% lifetime (US estimates) |
| gambling | 2.9% | Problem gambling 2.3% plus pathological 0.6% (Welte et al. 2008) |
| work | 2.7% | Workaholism estimates vary widely; kept modest |
| opioids | 2.5% | Opioid use disorder ≈ 2% (NSDUH 2023, approximate) |
| sedatives | 1.8% | Misuse of tranquilisers and sedatives |
| gaming | 1.7% | Gaming disorder 3.3% overall (8.5% men, 3.5% women), adolescents 6.6% (meta-analyses around the ICD-11 recognition, 2018); **teens 6%** |
| stimulants | 1.0% | Stimulant use disorder ≈ 1% |
| any substance (excluding nicotine and caffeine) | 21.0% | Substance use disorder ≈ 17% (NSDUH 2023, approximate) |

The NSDUH figures are from recall and marked approximate: the SAMHSA report pages returned 404
during this research. Verify them before the numbers are quoted anywhere public.

## Where addiction meets places
The building-types registry links places to addictions (`addictions` on each type):
- bars and liquor stores: alcohol;
- gas stations, newsstands and variety stores: nicotine, and gambling (lottery tickets);
- the arcade: gaming and gambling;
- cafés: caffeine;
- clothing stores: shopping;
- the pharmacy: opioids and sedatives.

In a day's plan, a person whose addiction matches a place's goes there **three times as often**.
The alcoholic is a regular at the bar; the gambler buys scratch cards at the gas station. That
gives the story engine witnesses and patterns to find.

## How to portray it (for the game bible and the prompt)
- **Person first.** Someone with an addiction is a whole person: a bartender, a mother, a man who
  fixes boats. The prompt card lists addictions under "private struggles" and tells the model to
  **never name them unless trust is high**. People hide these things; the player should learn them
  the way one learns about a neighbour.
- **Stages matter more than labels.** A recovering alcoholic who turns down a drink is a story; an
  active one who asks to borrow money is another. The stage drives behaviour, not the substance.
- **No jokes at the expense of the addicted, and no moralising.** This is Ghibli-toned: sympathy,
  consequences, the chance of recovery. Recovery (28%) is common, and it should be visible.
- **Behavioural addictions are ordinary.** Social media, shopping and work addictions are how most
  players will recognise themselves. They're good for gentle comedy and for quiet arcs.
