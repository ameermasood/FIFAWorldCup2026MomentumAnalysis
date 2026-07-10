# World Cup Momentum Breaks

Script-first mini project to approximate World Cup 2026 match momentum from public FIFA event data and study hydration breaks.

Current first case study:

- Match: Argentina 3-2 Egypt
- Competition: FIFA World Cup 2026
- Stage: Round of 16
- FIFA match id: `400021528`

The pipeline collects FIFA public calendar, live, and timeline JSON for the match, builds an open momentum proxy, and exports polished charts for sharing.

## Reproduce

Run the full local workflow from the repo root:

```bash
python3 scripts/collect_match_data.py --match-id 400021528
python3 scripts/build_match_momentum.py --match-id 400021528
python3 scripts/make_momentum_chart.py --match-id 400021528
```

The collection script reuses existing raw JSON files when they are present and fetches from FIFA only when a raw payload is missing.
Repeat the three commands with another `--match-id` to generate the same outputs for another match.

Current selected matches:

| Match ID | Match | Stage |
| --- | --- | --- |
| `400021531` | Mexico 2-3 England | Round of 16 |
| `400021528` | Argentina 3-2 Egypt | Round of 16 |
| `400021532` | Brazil 1-2 Norway | Round of 16 |

## Current Outputs

The momentum script builds an Opta-inspired open proxy:

- Assign a capped `0.0` to `0.1` public-event value to visible FIFA timeline events.
- Keep each team's maximum event value per minute instead of summing every event.
- Weight the last four minutes most heavily.
- Force hydration-break intervals to zero because play is stopped.

- [Event table](data/processed/match_400021528/events.csv)
- [Momentum curve data](data/processed/match_400021528/momentum_grid.csv)
- [Per-minute momentum values](data/processed/match_400021528/momentum_per_minute.csv)
- [Hydration break intervals](data/processed/match_400021528/hydration_breaks.csv)
- [Before/after break summary](data/processed/match_400021528/break_summary.csv)
- [Momentum chart PNG](reports/figures/match_400021528/momentum_chart.png)
- [Momentum chart SVG](reports/figures/match_400021528/momentum_chart.svg)

![Argentina vs Egypt momentum chart](reports/figures/match_400021528/momentum_chart.png)

Additional generated charts:

- [Mexico vs England](reports/figures/match_400021531/momentum_chart.png)
- [Brazil vs Norway](reports/figures/match_400021532/momentum_chart.png)

Early descriptive result from the revised proxy:

| Break | Interval | Avg. momentum before | Avg. momentum after | Shift |
| --- | --- | ---: | ---: | ---: |
| 1 | 23' to 26' | 22.41 | 41.38 | +18.96 |
| 2 | 70' to 74' | -10.04 | 42.04 | +52.07 |

Positive values favor Argentina; negative values favor Egypt.
