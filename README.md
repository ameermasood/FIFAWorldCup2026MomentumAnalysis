# FIFA World Cup 2026 Match Momentum Analysis 

This project is a Python-based analysis tool that downloads public event feeds from the FIFA API to reconstruct match momentum curves for the FIFA World Cup 2026. 

By analyzing in-game event flows (such as goals, penalty decisions, saves, and card warnings), the pipeline maps out threat scores for both home and away teams. It smooths these rolling values using cubic spline interpolation to produce clean momentum graphics. Additionally, the project highlights play segments and shifts in momentum directly before and after FIFA's official hydration breaks to study the tactical impact of those interruptions.

<p align="center">
  <img src="data/fifa_logo.png" alt="FIFA World Cup 2026 Logo" width="180"/>
</p>



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

The pipeline processes match data in three key stages to determine the momentum score.

### 1. Event Threat Score (Possession Value Proxy)
Each visible timeline event is assigned a threat value ($PV$) based on its location and threat level, capped at a maximum of $0.10$:

* **Goal**: $0.10$
* **Penalty Awarded**: $0.085$
* **Attempt at Goal**: Calculated using the pitch danger level:
  $$PV = 0.035 + 0.045 \times \text{danger}$$
* **Corner**: $0.025$
* **Goal Prevention (Save)**: $0.04$
* **Foul**: Calculated using the pitch danger level:
  $$PV = 0.008 + 0.022 \times \text{danger}$$
* **Offside**: $0.01$

#### Pitch Danger Calculation
The danger level is determined by the horizontal coordinate ($x$, scaled from 0 to 100) of the event:
$$\text{danger} = 1.0 - \frac{\min(x, 100 - x)}{50}$$

---

### 2. Continuous Team Threat
To measure sustained pressure, team threats ($T$) are computed over a rolling 4-minute window using 0.25-minute steps. We take the peak threat in each 1-minute interval and weight them to discount older events:

$$T(t) = \sum_{l=0}^{3} w_l \cdot \max_{\tau \in (t - (l+1), t - l]} PV(\tau)$$

The weights are defined as:
* $w_0 = 1.00$ (last 0 to 1 minutes)
* $w_1 = 0.75$ (last 1 to 2 minutes)
* $w_2 = 0.50$ (last 2 to 3 minutes)
* $w_3 = 0.25$ (last 3 to 4 minutes)

---

### 3. Smoothed Momentum
Momentum ($M$) represents the difference between the Home and Away team threats. We normalize this difference to fit in the range $[-100, 100]$:

$$M(t) = 100 \cdot \frac{T_{\text{Home}}(t) - T_{\text{Away}}(t)}{\max_{t'} |T_{\text{Home}}(t') - T_{\text{Away}}(t')|}$$

To eliminate minor fluctuations, we apply a rolling mean filter over 9 grid points (covering 2.25 minutes). During hydration breaks, the momentum is set strictly to $0.0$ since play is stopped.

---

## How Hydration Breaks Equalize Match Momentum

Common wisdom suggests that mid-half cooling stoppages are a lifesaver for underdogs, letting exhausted players regroup and catch their breath to hold off dominant teams. However, after compiling and analyzing the momentum data across **50 hydration breaks** in **25 tournament knockout matches**, we found that these pauses act as **forced tactical timeouts** that heavily benefit the favorites. 

### The Reset and the Comeback
When play stops for 2-4 minutes, it acts as a physical and mental **circuit breaker**. It completely halts the underdog’s high-intensity emotional pressing flow, resetting the game tempo to a cold, neutral state. 

* **The Equalizer Effect**: Across all matches, the team trailing in momentum before a break managed to turn things around and gain momentum post-break **74.0% of the time**. In **52.0% of cases**, the stoppage resulted in a complete swap of the team holding the momentum lead.
* **The Favorite's Lifeline**: When the higher-ranked favorite was trailing in momentum going into a break, they used the pause to stage a comeback **72.2% of the time**. In **69.2% of those comebacks**, the favorite completely flipped the momentum lead away from the underdog. During the timeout, the favorite's coaching staff can make the adjustments necessary to reassert their superior technical class.

---

## Tactical Cases in Visuals

### 1. The Classic Comeback: Argentina vs. Egypt (Round of 16)
Egypt (red) established a clear momentum advantage over Argentina (blue) leading up to the 70th-minute mark. When the referee blew for the second hydration break (visible at the 70' to 74' gap), it completely flattened Egypt's rhythm. Argentina regrouped during the timeout, adjusted their midfield lines, registered a massive **+50.84 point shift**, and swept control of the match to secure their late-game victory.

![Argentina vs Egypt momentum chart](reports/figures/Round_of_16_Argentina_Egypt/Round_of_16_Argentina_Egypt_momentum_chart.png)

### 2. The Complete Flip: England vs. Congo DR (Round of 32)
Congo DR (red) was holding onto a strong momentum lead. The second break (68' to 71') acted as a hard circuit breaker. Post-break, England (blue) registered a **+65.24 point momentum swing**—the largest post-break shift in the tournament—completely erasing Congo DR's presence for the remainder of the match.

![England vs Congo DR momentum chart](reports/figures/Round_of_32_England_Congo_DR/Round_of_32_England_Congo_DR_momentum_chart.png)

### 3. Killing the Pressure: Canada vs. Morocco (Round of 16)
Canada (blue) had built a strong, high-pressure momentum lead in the first half. A first-half hydration break in the 24th minute halted their flow immediately. Play restarted cold, Canada's pressing intensity dropped, and Morocco (red) capitalized on the reset to claim a **+60.66 point momentum shift**.

![Canada vs Morocco momentum chart](reports/figures/Round_of_16_Canada_Morocco/Round_of_16_Canada_Morocco_momentum_chart.png)
---

## The "100% Collapse" of Extreme Dominance

Our data shows that if a team completely dominates the game right before a hydration break, they are almost guaranteed to see their control collapsed afterward. We looked at 12 instances where a team had a massive momentum lead (25 points or more) right before a stoppage. In all 12 cases, the dominant team suffered a drop in momentum (meaning the shift favored their opponent). 

The stoppage acts as a hard limit on match dominance. If a team is running away with the game, the break resets their rhythm, making it highly likely they will experience a drop in pressure.

### Visualizing the Collapse: Argentina vs. Cabo Verde (Round of 32)
Argentina (blue) held a massive momentum lead of 44.0 points. When the second hydration break (73' to 76') halted play, their control collapsed entirely. After the restart, Argentina's momentum crashed to -4.0 points, allowing Cabo Verde (red) to seize the momentum lead for the final phase of the match.

![Argentina vs Cabo Verde momentum chart](reports/figures/Round_of_32_Argentina_Cabo_Verde/Round_of_32_Argentina_Cabo_Verde_momentum_chart.png)

---

## Disclaimer & Terms of Use

* **Personal & Educational Use**: This is a personal, non-commercial sports data research project developed solely for educational and analytical purposes.
* **Non-Affiliation**: This project is not affiliated with, authorized, sponsored, or endorsed by FIFA, the FIFA World Cup, or any national football associations. 
* **Copyright**: All visualization designs, momentum metrics, and analytical code are © 2026 Amir Masoud Almasi. All rights reserved.