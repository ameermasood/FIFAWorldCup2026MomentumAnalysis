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

## Calculation Methodology

The match momentum is computed continuously over a rolling grid (with step size $\Delta t = 0.25$ minutes) using the following mathematical formulation:

1. **Possession Value Proxy ($PV$):**
   Visible events on the timeline are mapped to a threat score capped at $0.10$:
   - **Goal**: $0.10$
   - **Penalty Awarded**: $0.085$
   - **Attempt at Goal**: $0.035 + 0.045 \times \text{danger}$ (where $\text{danger} = 1.0 - \frac{\min(x, 100-x)}{50}$ and $x$ is the horizontal coordinate of the event)
   - **Corner**: $0.025$
   - **Goal Prevention (Save)**: $0.04$ (credited to opponent's attack)
   - **Foul**: $0.008 + 0.022 \times \text{danger}$ (credited to opponent's attack)
   - **Offside**: $0.01$

2. **Continuous Team Threat ($T_{team}$):**
   For a given time $t$ on the grid, the recent threat score for team $A$ is calculated using a continuous sliding lookback window spanning the last 4 minutes:
   $$T_A(t) = \sum_{l=0}^{3} w_l \cdot \max_{\tau \in (t - (l+1), t - l]} PV_A(\tau)$$
   where the recency weights $w_l$ are:
   - $w_0 = 1.00$ (last 0 to 1 minutes)
   - $w_1 = 0.75$ (last 1 to 2 minutes)
   - $w_2 = 0.50$ (last 2 to 3 minutes)
   - $w_3 = 0.25$ (last 3 to 4 minutes)
   
   If no events occur for team $A$ in a sliding interval, the peak value for that interval is $0.0$.

3. **Raw Momentum ($M_{raw}$):**
   The difference between the home and away threats:
   $$M_{raw}(t) = T_{Home}(t) - T_{Away}(t)$$

4. **Normalized & Smoothed Momentum ($M_{smoothed}$):**
   The raw momentum is scaled relative to the maximum absolute raw momentum in the match to reside in the range $[-100, 100]$:
   $$M(t) = 100 \cdot \frac{M_{raw}(t)}{\max_{t'} |M_{raw}(t')|}$$
   We then apply a rolling mean filter with a centered window of 5 grid points (covering 1.25 minutes) to smooth out high-frequency fluctuations, yielding $M_{smoothed}(t)$. During hydration breaks, all momentum metrics are forced to $0.0$.

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
