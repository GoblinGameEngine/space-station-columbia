# 2. Personality disorders: dimensions, prevalence, depiction and tokens

Personality disorders matter here for two reasons. They are the **far tails** of ordinary
personality, so a population of 100,000 contains many such people. They also produce the
interpersonal patterns that drive real stories: exploitation, volatility, suspicion,
dependence, rigidity. The modern science is **dimensional**, which suits a generator: no
labels, just the extremes of traits the engine already has.

## 2.1 Three ways the field describes them
1. **The DSM-5-TR categories (Section II):** ten disorders in three clusters.
   - **A**, odd or eccentric: paranoid, schizoid, schizotypal.
   - **B**, dramatic or erratic: antisocial, borderline, histrionic, narcissistic.
   - **C**, anxious or fearful: avoidant, dependent, obsessive-compulsive.
   - The categories are familiar but overlap heavily and are unstable over time. That is why both
     manuals moved on.
2. **The DSM-5 Alternative Model (AMPD, Section III):** a dimensional-categorical hybrid
   ([APA Focus](https://psychiatryonline.org/doi/10.1176/appi.focus.11.2.189); [facet list](https://en.wikipedia.org/wiki/Alternative_DSM-5_model_for_personality_disorders)).
   - **Criterion A, level of personality functioning (LPFS)**, rated from 0 (little or no
     impairment) to 4 (extreme). It covers four areas:
     - **identity:** a stable sense of self and self-esteem, and regulating emotion;
     - **self-direction:** coherent goals and prosocial internal standards;
     - **empathy:** understanding others and the effect of one's own behaviour;
     - **intimacy:** the depth, duration and mutuality of closeness.
   - **Criterion B, five pathological trait domains with 25 facets:**
     - **Negative Affectivity:** anxiousness, emotional lability, separation insecurity, hostility,
       perseveration, submissiveness.
     - **Detachment:** withdrawal, intimacy avoidance, anhedonia, depressivity, restricted
       affectivity, suspiciousness.
     - **Antagonism:** manipulativeness, deceitfulness, grandiosity, attention seeking,
       callousness, hostility.
     - **Disinhibition:** irresponsibility, impulsivity, distractibility, risk taking, and (low)
       rigid perfectionism.
     - **Psychoticism:** unusual beliefs and experiences, eccentricity, cognitive and perceptual
       dysregulation.
   - Six named types remain: antisocial, avoidant, borderline, narcissistic,
     obsessive-compulsive and schizotypal.
3. **ICD-11 (WHO):** severity only (mild, moderate or severe personality disorder), plus optional
   **trait qualifiers**: negative affectivity, detachment, dissociality, disinhibition and
   **anankastia** (rigid perfectionism, control), and a *borderline pattern* qualifier. All the
   old categories are gone ([application of ICD-11](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6206910/)).

**For us.** The AMPD and ICD-11 domains are recognised as the maladaptive ends of the Big Five:
- Negative Affectivity ↔ high N;
- Detachment ↔ low E;
- Antagonism / Dissociality ↔ low A, and in HEXACO terms low H;
- Disinhibition ↔ low C;
- Anankastia ↔ extreme high C;
- Psychoticism ↔ an odd-beliefs variant related to O.

So we need **no new personality**. We need a **severity** value and a way to read the extremes.

## 2.2 Adjacent "dark" traits (non-clinical)
The **Dark Triad** (Paulhus & Williams 2002) is Machiavellianism, subclinical narcissism and
subclinical psychopathy: "aversive but non-pathological". Sadism was added in 2019 to make the
*Dark Tetrad* ([Dark triad](https://en.wikipedia.org/wiki/Dark_triad)). These are the everyday
schemers, braggarts and cold operators of any town. They are mostly low H with low A, with
flavours set by the facets (callousness, grandiosity, manipulativeness).

## 2.3 How common
- **Any personality disorder: about 12%** of adults in Western general populations. The
  meta-analysis covers 10 studies and 113,998 people (Volkert, Gablonski & Rabung 2018, *British
  Journal of Psychiatry*): 12.16%, 95% CI 8.0–17.0%.
- **By type:** obsessive-compulsive is the most common at 4.3%; dependent the least at 0.8%. The
  clusters each fall between 5.5% and 7.2% ([PubMed record of the global meta-analysis](https://pubmed.ncbi.nlm.nih.gov/31298170/)).
- Severe impairment is much rarer than mild.

For a generated population, most extreme-trait people are **mild** (LPFS 1). A settlement of
1,000 has a handful at LPFS 2 and perhaps one or two at LPFS 3 or above. No settlement is
"the madhouse".

## 2.4 Depicting it without stigma (a design requirement)
- **The problem.** A review of video games found **97%** portrayed mental illness in "negative,
  misleading, and problematic ways". They associated it with violence, fear, insanity and
  hopelessness, tied it to the supernatural, and offered little hope of recovery ([Gaming with Stigma, JMIR Mental Health 2019](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6707601/)).
  A 2026 scoping review agrees ([scoping review](https://kris.kl.ac.at/en/publications/a-scoping-review-about-the-portrayal-of-mental-illness-in-commerc/)).
  Some games instead use mechanics to build empathy.
- **Our rules:**
  1. **No diagnostic labels in-world or in prompts.** The engine never tells Groq "this character
     has borderline personality disorder". It passes the **behavioural tokens**: fears being left,
     mood swings fast, quick to feel slighted. Players see people, not diagnoses.
  2. **No link to violence by default.** Violence comes from situation, grievance and honor
     culture (03), as the evidence says, not from a disorder token.
  3. **Strengths go with difficulties.** A rigid perfectionist keeps the station's air plant
     running; a suspicious one notices the real saboteur. Each dimension carries an adaptive
     reading.
  4. **Change is possible.** Stress raises how visible the impairment is; support, stability and
     good relationships lower it. The severity token is a *state around a trait*, not a life
     sentence.
  5. **Help-seeking exists in the world:** a doctor, a counsellor or a friend who helps. This
     becomes a role in the roles research.

## 2.5 Tokens and generation
| token | meaning | generation |
|---|---|---|
| `D.lpfs` | level of personality functioning, 0..4 | 0 for most people. The probability rises with trait extremity: a sigmoid on the largest Mahalanobis-like distance from the population mean across N, low A, low C, low E and low H. Calibrate so about 12% are ≥1 and about 1% are ≥3. Raised by `S.stress` and early adversity (backstory), lowered by secure attachment. |
| `D.negaff` | negative affectivity, 0..1 | N, stretched in the tail: ((N − 0.7)/0.3)⁺ |
| `D.detach` | detachment | ((0.3 − E)/0.3)⁺ with attachment avoidance |
| `D.antag` | antagonism / dissociality | ((0.3 − A)/0.3)⁺ with ((0.3 − H)/0.3)⁺ |
| `D.disinhib` | disinhibition | ((0.3 − C)/0.3)⁺ with N.impulsiveness |
| `D.anank` | anankastia | ((C − 0.8)/0.2)⁺ with low O |
| `D.psych` | psychoticism, odd beliefs | a rare separate draw (about 3%), linked to O.fantasy. Isolation (solipsism syndrome, 03) may raise it temporarily. |
| `D.facets` | the 2–3 strongest AMPD facets, as behaviour words | picked from the facet list by the domain scores plus a hash |

**How they act on the story engine:**
- `D.*` scale **appraisal gains**. Antagonism lowers pity and raises gloating; negative
  affectivity amplifies distress and anger.
- They change **gossip honesty** (`K.lie`): antagonism combined with a grievance.
- They alter **tie dynamics**. Detachment slows how fast ties strengthen. Separation insecurity
  makes threats to close ties stronger.
- They pick **coping** under stress.
- All of it is scaled by `D.lpfs`: at 0 the dimension is just personality colour.
