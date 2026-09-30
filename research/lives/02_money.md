# 2. Money

People have different amounts of money for different reasons. The generator now carries money as
amounts, not a band, and records **why**.

## The traits (`npc_traits.json`)
| trait | layer | how |
|---|---|---|
| `wage` | L0 | The occupation's median wage (the occupations table's new `wage` column, from BLS OEWS 2024 medians, approximate) × a lognormal spread (σ 0.3) × an age curve (under 25: 0.75; 25–34: 0.95; 35–54: 1.1). Retirees get a pension-like 24k; unemployed people about 9k in benefits. |
| `money_style` | L2 | From personality: **saver** (high C), **careful**, **spender** (low C), **generous** (high A), **tight** (low A), **anxious** (high N). |
| `savings` | L2 | wage × (0.15 + years working / 30) × style × a wide lognormal (median well below the mean, like real wealth). |
| `debt` | L2 | wage × a lognormal, ×2 for spenders, ×0.4 for savers, small before 22. |
| `debts` | L2 | Tags: mortgage, student_loans, medical, credit_card, car_loan, payday_loan, gambling, family_loan, child_support. Each is likelier where it belongs: a mortgage at 28–65; gambling debt with a gambling addiction; student loans at 22–45, more for degree professions (teacher, nurse, doctor, lawyer...); medical debt with a mobility aid or over 60; credit cards for spenders; payday loans on low wages. |
| `money_reasons` | L2 | Tags: inherited, windfall, two_jobs, laid_off, pension, benefits, family_money, owns_business, sends_money_home, supports_parent, medical_bills, gambling_losses, divorce, raising_kids_alone, frugal. **This is the dialogue hook**: not "has $3,000" but "got laid off from the cannery, sends money home to her mother". |
| `finances` | L2 | The band dialogue uses: **dependent** (under 18), **wealthy** (net > 400k), **comfortable**, **getting by**, **struggling**, **in debt** (debt above a year's wage). |

## Calibration (`tools/charref/life_stats.py`, 5,000 people)
| measure | generated | target |
|---|---|---|
| at least okay financially (wealthy + comfortable + getting by) | **70%** | 72% (Fed SHED 2023) |
| savings under $400 | 22% | 37% couldn't cover a $400 expense with cash or its equivalent (SHED 2023: 63% could) |
| median wage of earners | $40.7k | BLS median weekly earnings ≈ $59k/yr full-time. The game's towns lean to service, food and retail jobs, as small coastal towns do. |
| finances bands | getting by 45%, struggling 25%, comfortable 19%, wealthy 6%, in debt 5% | — |

The $400 figure is low because SHED counts people who *would* borrow or sell something even when
they hold savings. The engine's figure is simply the share whose savings are under $400.

Sources: Federal Reserve, *Economic Well-Being of U.S. Households in 2023* (SHED, May 2024); US
Census, *Income in the United States: 2023* (median household income $80,610); BLS OEWS May 2024.

## For dialogue
- `finances` goes on the `[LIFE]` card. The amounts don't: people talk about money in bands and
  reasons, not balances.
- `money_reasons` and `debts` are **backstory hooks** for the story engine:
  - `laid_off` + `struggling` casts well in "hard times" or "a helping hand";
  - `gambling_losses` + `gambling` debts in a "secret" or a "downfall";
  - `inherited` + `wealthy` in "the rich relation".
- `money_style` shapes behaviour: generous people tip and lend; tight people haggle; anxious people
  worry aloud.
