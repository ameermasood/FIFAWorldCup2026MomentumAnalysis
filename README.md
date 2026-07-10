# World Cup Match Momentum & Hydration Breaks

This project is a Python-based analysis tool that downloads public event feeds from the FIFA API to reconstruct match momentum curves for the FIFA World Cup 2026. 

By analyzing in-game event flows (such as goals, penalty decisions, saves, and card warnings), the pipeline maps out threat scores for both home and away teams. It smooths these rolling values using cubic spline interpolation to produce clean momentum graphics. Additionally, the project highlights play segments and shifts in momentum directly before and after FIFA's official hydration breaks to study the tactical impact of those interruptions.


## How to Run

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Process All Knockout Stage Matches
Harvest and render charts for all available tournament knockout stage matches:
```bash
python3 main.py --all-knockouts
```
*Note: Unplayed/future matches are detected and skipped automatically without crashing.*

### Process a Single Match
Run the complete collection, calculation, and charting steps for a specific match:

**By Match ID:**
```bash
python3 main.py --match-id 400021528
```

**By Team Abbreviation:**
```bash
python3 main.py --teams ARG EGY
```

---

## Directory Structure & Outputs

- **Raw API Payloads**: `data/raw/match_{match_id}/` (stores `live.json`, `timeline.json`, and `calendar.json`)
- **Cached Flags**: `data/flags/` (caches flags fetched from FlagCDN)
- **Processed Datasets**: `data/processed/{Stage}_{Home}_{Away}/`
  - `{Stage}_{Home}_{Away}_events.csv` (scored events)
  - `{Stage}_{Home}_{Away}_momentum_grid.csv` (interpolated momentum time-series)
  - `{Stage}_{Home}_{Away}_hydration_breaks.csv` (resolved hydration intervals)
  - `{Stage}_{Home}_{Away}_break_summary.csv` (average momentum before/after breaks)
- **Visualizations**: `reports/figures/{Stage}_{Home}_{Away}/`
  - `{Stage}_{Home}_{Away}_momentum_chart.png` (polished graphic)
  - `{Stage}_{Home}_{Away}_momentum_chart.svg` (vector format)

---

## Calculation Methodology

1. **Possession Value Proxy ($PV$):**
   Events are mapped to a threat score capped at $0.10$:
   - **Goal**: $0.10$
   - **Penalty Awarded**: $0.085$
   - **Attempt at Goal**: $0.035 + 0.045 \times \text{danger}$ (where $\text{danger} = 1.0 - \frac{\min(x, 100-x)}{50}$ and $x$ is the horizontal pitch coordinate)
   - **Corner**: $0.025$
   - **Goal Prevention (Save)**: $0.04$
   - **Foul**: $0.008 + 0.022 \times \text{danger}$
   - **Offside**: $0.01$

2. **Continuous Team Threat ($T_{team}$):**
   Computed over a rolling 4-minute window:
   $$T_{team}(t) = \sum_{l=0}^{3} w_l \cdot \max_{\tau \in (t - (l+1), t - l]} PV_{team}(\tau)$$
   Weights ($w_0 = 1.0$, $w_1 = 0.75$, $w_2 = 0.5$, $w_3 = 0.25$) discount older threats.

3. **Momentum ($M_{smoothed}$):**
   Difference between home and away threats scaled to range $[-100, 100]$:
   $$M(t) = 100 \cdot \frac{T_{Home}(t) - T_{Away}(t)}{\max_{t'} |T_{Home}(t') - T_{Away}(t')|}$$
   Smoothed using a centered moving average over 5 grid points. Forced to $0.0$ during hydration breaks.

---

## Example Visualizations

### Argentina vs Egypt (Round of 16)
![Argentina vs Egypt momentum chart](reports/figures/Round_of_16_Argentina_Egypt/Round_of_16_Argentina_Egypt_momentum_chart.png)

### Mexico vs England (Round of 16)
![Mexico vs England momentum chart](reports/figures/Round_of_16_Mexico_England/Round_of_16_Mexico_England_momentum_chart.png)

### Brazil vs Norway (Round of 16)
![Brazil vs Norway momentum chart](reports/figures/Round_of_16_Brazil_Norway/Round_of_16_Brazil_Norway_momentum_chart.png)
