"""Build event, hydration, momentum, and break-summary CSVs."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

GRID_STEP = 0.25
RECENCY_WEIGHTS = {0: 1.00, 1: 0.75, 2: 0.50, 3: 0.25}
MAX_PROXY_VALUE = 0.1
BEFORE_AFTER_WINDOW = 5.0


def localized_description(items: list[dict] | None, default: str = "") -> str:
    if not items:
        return default
    return items[0].get("Description", default)


def event_text(event: dict) -> str:
    return " ".join(description.get("Description", "") for description in event.get("EventDescription", []))


def parse_match_minute(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).replace("'", "")
    if "+" in text:
        base, added = text.split("+", 1)
        return float(base) + float(added)
    try:
        return float(text)
    except ValueError:
        return None


def danger_from_location(x: object) -> float:
    if pd.isna(x):
        return 0.0
    return max(0.0, min(1.0, 1.0 - min(float(x), 100.0 - float(x)) / 50.0))


def build_team_lookup(live: dict) -> dict:
    home_team = live["HomeTeam"]
    away_team = live["AwayTeam"]
    return {
        home_team["IdTeam"]: {
            "side": "home",
            "name": home_team["ShortClubName"],
            "abbr": home_team["Abbreviation"],
            "sign": 1,
        },
        away_team["IdTeam"]: {
            "side": "away",
            "name": away_team["ShortClubName"],
            "abbr": away_team["Abbreviation"],
            "sign": -1,
        },
    }


def opponent_team_id(team_lookup: dict, team_id: str | None) -> str | None:
    ids = list(team_lookup)
    if team_id == ids[0]:
        return ids[1]
    if team_id == ids[1]:
        return ids[0]
    return None


def flatten_events(timeline: dict, team_lookup: dict) -> pd.DataFrame:
    rows = []
    for event in timeline.get("Event", []):
        team = team_lookup.get(event.get("IdTeam"), {})
        rows.append(
            {
                "event_id": event.get("EventId"),
                "timestamp": event.get("Timestamp"),
                "match_minute_label": event.get("MatchMinute"),
                "match_minute": parse_match_minute(event.get("MatchMinute")),
                "period": event.get("Period"),
                "type_id": event.get("Type"),
                "event_type": localized_description(event.get("TypeLocalized"), "Unknown"),
                "description": event_text(event),
                "team_id": event.get("IdTeam"),
                "team": team.get("name"),
                "team_abbr": team.get("abbr"),
                "side": team.get("side"),
                "x": event.get("PositionX"),
                "y": event.get("PositionY"),
                "goal_x": event.get("GoalGatePositionX"),
                "goal_y": event.get("GoalGatePositionY"),
                "home_goals": event.get("HomeGoals"),
                "away_goals": event.get("AwayGoals"),
            }
        )
    return pd.DataFrame(rows).sort_values(["match_minute", "timestamp", "event_id"], na_position="last")


def extract_hydration(events: pd.DataFrame) -> pd.DataFrame:
    intervals = []
    open_break = None

    for _, event in events.iterrows():
        text = f"{event['event_type']} {event['description']}".lower()
        if event["event_type"] == "Delay" and "hydration break" in text:
            open_break = event
        elif open_break is not None and event["event_type"] == "Resume":
            intervals.append(
                {
                    "start_minute": open_break["match_minute"],
                    "start_label": open_break["match_minute_label"],
                    "start_timestamp": open_break["timestamp"],
                    "end_minute": event["match_minute"],
                    "end_label": event["match_minute_label"],
                    "end_timestamp": event["timestamp"],
                    "period": open_break["period"],
                }
            )
            open_break = None

    return pd.DataFrame(intervals)


def score_events(events: pd.DataFrame, team_lookup: dict) -> pd.DataFrame:
    def score_event(row: pd.Series) -> pd.Series:
        event_type = row["event_type"]
        team_id = row["team_id"]
        danger = danger_from_location(row["x"])

        attacking_team_id = team_id
        score = 0.0
        reason = "annotation/no threat"

        if event_type == "Goal!":
            score = 0.10
            reason = "goal"
        elif event_type == "Penalty Awarded":
            score = 0.085
            reason = "penalty awarded"
        elif event_type == "Attempt at Goal":
            score = 0.035 + 0.045 * danger
            reason = "shot weighted by location"
        elif event_type == "Corner":
            score = 0.025
            reason = "corner pressure"
        elif event_type == "Goal Prevention":
            attacking_team_id = opponent_team_id(team_lookup, team_id)
            score = 0.04
            reason = "save/goal prevention credited to opponent attack"
        elif event_type == "Foul":
            attacking_team_id = opponent_team_id(team_lookup, team_id)
            score = 0.008 + 0.022 * danger
            reason = "foul credited to opponent, boosted near goal"
        elif event_type == "Offside":
            score = 0.01
            reason = "attacking offside"

        attacking_team = team_lookup.get(attacking_team_id, {})
        score = min(MAX_PROXY_VALUE, score)

        return pd.Series(
            {
                "attacking_team_id": attacking_team_id,
                "attacking_team": attacking_team.get("name"),
                "attacking_abbr": attacking_team.get("abbr"),
                "proxy_value": score,
                "signed_proxy_value": score * attacking_team.get("sign", 0),
                "location_danger": danger,
                "score_reason": reason,
            }
        )

    return pd.concat([events, events.apply(score_event, axis=1)], axis=1)


def is_hydration_minute(minute: float, hydration: pd.DataFrame) -> bool:
    return any(interval.start_minute <= minute <= interval.end_minute for interval in hydration.itertuples())


def build_momentum_grid(events: pd.DataFrame, hydration: pd.DataFrame, live: dict) -> pd.DataFrame:
    max_minute = math.ceil(events["match_minute"].dropna().max())
    home_abbr = live["HomeTeam"]["Abbreviation"]
    away_abbr = live["AwayTeam"]["Abbreviation"]

    scored_events = events[(events["proxy_value"] > 0) & events["match_minute"].notna()].copy()
    scored_events["minute_bucket"] = scored_events["match_minute"].astype(int)
    minute_team_peaks = scored_events.groupby(["minute_bucket", "attacking_abbr"], as_index=False)["proxy_value"].max()
    peak_lookup = {
        (int(row.minute_bucket), row.attacking_abbr): float(row.proxy_value)
        for row in minute_team_peaks.itertuples()
    }

    def recent_team_value(minute: float, abbr: str) -> float:
        minute_bucket = int(math.floor(minute))
        return sum(
            peak_lookup.get((minute_bucket - lag, abbr), 0.0) * weight
            for lag, weight in RECENCY_WEIGHTS.items()
        )

    grid = pd.DataFrame({"minute": [round(i * GRID_STEP, 2) for i in range(int(max_minute / GRID_STEP) + 1)]})
    grid["home_recent_value"] = grid["minute"].apply(lambda minute: recent_team_value(minute, home_abbr))
    grid["away_recent_value"] = grid["minute"].apply(lambda minute: recent_team_value(minute, away_abbr))
    grid["raw_momentum"] = grid["home_recent_value"] - grid["away_recent_value"]

    break_mask = grid["minute"].apply(lambda minute: is_hydration_minute(minute, hydration))
    grid.loc[break_mask, ["home_recent_value", "away_recent_value", "raw_momentum"]] = 0.0

    max_abs = grid["raw_momentum"].abs().max()
    grid["momentum"] = 100 * grid["raw_momentum"] / max_abs if max_abs else 0.0
    grid["momentum_smoothed"] = grid["momentum"].rolling(window=5, center=True, min_periods=1).mean()
    grid.loc[break_mask, "momentum_smoothed"] = 0.0
    grid["is_hydration_break"] = break_mask

    return grid


def build_per_minute_output(grid: pd.DataFrame, hydration: pd.DataFrame) -> pd.DataFrame:
    per_minute = (
        grid.assign(minute_int=grid["minute"].astype(int))
        .groupby("minute_int", as_index=False)
        .agg(
            momentum=("momentum", "mean"),
            momentum_smoothed=("momentum_smoothed", "mean"),
            home_recent_value=("home_recent_value", "mean"),
            away_recent_value=("away_recent_value", "mean"),
            is_hydration_break=("is_hydration_break", "max"),
        )
        .rename(columns={"minute_int": "minute"})
    )

    for interval in hydration.itertuples():
        mask = per_minute["minute"].between(math.floor(interval.start_minute), math.ceil(interval.end_minute))
        per_minute.loc[mask, ["momentum", "momentum_smoothed", "home_recent_value", "away_recent_value"]] = 0.0
        per_minute.loc[mask, "is_hydration_break"] = True

    return per_minute


def build_break_summary(grid: pd.DataFrame, hydration: pd.DataFrame, live: dict) -> pd.DataFrame:
    home_name = live["HomeTeam"]["ShortClubName"]
    away_name = live["AwayTeam"]["ShortClubName"]
    rows = []
    for index, interval in hydration.iterrows():
        before = grid[
            (grid["minute"] >= interval["start_minute"] - BEFORE_AFTER_WINDOW)
            & (grid["minute"] < interval["start_minute"])
        ]
        after = grid[
            (grid["minute"] > interval["end_minute"])
            & (grid["minute"] <= interval["end_minute"] + BEFORE_AFTER_WINDOW)
        ]
        before_avg = before["momentum_smoothed"].mean()
        after_avg = after["momentum_smoothed"].mean()
        rows.append(
            {
                "break_number": index + 1,
                "interval": f"{interval['start_label']} to {interval['end_label']}",
                "before_avg_momentum": before_avg,
                "after_avg_momentum": after_avg,
                "delta_after_minus_before": after_avg - before_avg,
                "before_leader": home_name if before_avg > 0 else away_name,
                "after_leader": home_name if after_avg > 0 else away_name,
            }
        )
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--match-id", required=True, help="FIFA match id, for example 400021528.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_dir = RAW_DIR / f"match_{args.match_id}"
    processed_dir = PROCESSED_DIR / f"match_{args.match_id}"
    processed_dir.mkdir(parents=True, exist_ok=True)

    timeline = json.loads((raw_dir / "timeline.json").read_text())
    live = json.loads((raw_dir / "live.json").read_text())

    team_lookup = build_team_lookup(live)
    events = score_events(flatten_events(timeline, team_lookup), team_lookup)
    hydration = extract_hydration(events)
    momentum = build_momentum_grid(events, hydration, live)
    per_minute = build_per_minute_output(momentum, hydration)
    break_summary = build_break_summary(momentum, hydration, live)

    events_path = processed_dir / "events.csv"
    hydration_path = processed_dir / "hydration_breaks.csv"
    momentum_path = processed_dir / "momentum_grid.csv"
    per_minute_path = processed_dir / "momentum_per_minute.csv"
    break_summary_path = processed_dir / "break_summary.csv"

    events.to_csv(events_path, index=False)
    hydration.to_csv(hydration_path, index=False)
    momentum.to_csv(momentum_path, index=False)
    per_minute.to_csv(per_minute_path, index=False)
    break_summary.to_csv(break_summary_path, index=False)

    print(events_path)
    print(hydration_path)
    print(momentum_path)
    print(per_minute_path)
    print(break_summary_path)


if __name__ == "__main__":
    main()
