"""Collect FIFA public JSON payloads for Argentina vs Egypt."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://api.fifa.com/api/v3"
LANGUAGE = "en"
ID_COMPETITION = "17"
ID_SEASON = "285023"

TARGET_TEAMS = {"ARG", "EGY"}
OUTPUT_PREFIX = "argentina_egypt_400021528"


def fetch_json(url: str, output_path: Path) -> dict:
    request = Request(url, headers={"User-Agent": "world-cup-momentum-breaks/0.1"})
    with urlopen(request) as response:
        payload = json.loads(response.read().decode("utf-8"))
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


def load_or_fetch_json(url: str, output_path: Path) -> dict:
    if output_path.exists():
        return json.loads(output_path.read_text())
    return fetch_json(url, output_path)


def localized_description(items: list[dict] | None, default: str = "") -> str:
    if not items:
        return default
    return items[0].get("Description", default)


def team_summary(match: dict, side: str) -> dict | None:
    team = match.get(side)
    if not team:
        return None
    return {
        "side": side,
        "id_team": team.get("IdTeam"),
        "abbr": team.get("Abbreviation"),
        "name": team.get("ShortClubName"),
        "score": team.get("Score"),
    }


def find_target_match(calendar: dict) -> dict:
    for match in calendar["Results"]:
        teams = [team_summary(match, "Home"), team_summary(match, "Away")]
        abbreviations = {team["abbr"] for team in teams if team}
        if TARGET_TEAMS.issubset(abbreviations):
            return {
                "match_number": match.get("MatchNumber"),
                "id_match": match.get("IdMatch"),
                "id_stage": match.get("IdStage"),
                "date": match.get("Date"),
                "stage": localized_description(match.get("StageName")),
                "home": team_summary(match, "Home"),
                "away": team_summary(match, "Away"),
            }
    raise RuntimeError("Argentina vs Egypt was not found in the WC26 calendar payload.")


def event_text(event: dict) -> str:
    return " ".join(description.get("Description", "") for description in event.get("EventDescription", []))


def extract_hydration_intervals(timeline: dict) -> list[dict]:
    intervals = []
    open_break = None

    for event in timeline.get("Event", []):
        label = localized_description(event.get("TypeLocalized"))
        lower_text = f"{label} {event_text(event)}".lower()

        if label == "Delay" and "hydration break" in lower_text:
            open_break = event
        elif open_break and label == "Resume":
            intervals.append(
                {
                    "start_minute": open_break.get("MatchMinute"),
                    "start_timestamp": open_break.get("Timestamp"),
                    "end_minute": event.get("MatchMinute"),
                    "end_timestamp": event.get("Timestamp"),
                    "period": open_break.get("Period"),
                    "start_event_id": open_break.get("EventId"),
                    "end_event_id": event.get("EventId"),
                }
            )
            open_break = None

    return intervals


def main() -> None:
    calendar_url = (
        f"{BASE_URL}/calendar/matches?language={LANGUAGE}"
        f"&idCompetition={ID_COMPETITION}&idSeason={ID_SEASON}&count=200"
    )
    calendar_path = RAW_DIR / "wc26_calendar_matches.json"
    calendar = load_or_fetch_json(calendar_url, calendar_path)

    match = find_target_match(calendar)
    id_match = match["id_match"]
    id_stage = match["id_stage"]

    live_url = f"{BASE_URL}/live/football/{ID_COMPETITION}/{ID_SEASON}/{id_stage}/{id_match}?language={LANGUAGE}"
    timeline_url = f"{BASE_URL}/timelines/{id_match}?language={LANGUAGE}"
    match_calendar_url = f"{BASE_URL}/calendar/{id_match}?language={LANGUAGE}"

    live_path = RAW_DIR / f"{OUTPUT_PREFIX}_live.json"
    timeline_path = RAW_DIR / f"{OUTPUT_PREFIX}_timeline.json"
    match_calendar_path = RAW_DIR / f"{OUTPUT_PREFIX}_calendar.json"

    live = load_or_fetch_json(live_url, live_path)
    timeline = load_or_fetch_json(timeline_url, timeline_path)
    load_or_fetch_json(match_calendar_url, match_calendar_path)

    event_type_counts = Counter(
        localized_description(event.get("TypeLocalized"), "Unknown") for event in timeline.get("Event", [])
    )
    hydration_intervals = extract_hydration_intervals(timeline)

    print(f"Match: {live['HomeTeam']['ShortClubName']} {live['HomeTeam']['Score']}-{live['AwayTeam']['Score']} {live['AwayTeam']['ShortClubName']}")
    print(f"Stage: {localized_description(live.get('StageName'))}")
    print(f"FIFA match id: {id_match}")
    print(f"Timeline events: {len(timeline.get('Event', []))}")
    print(f"Hydration intervals: {len(hydration_intervals)}")
    print(f"Top event types: {event_type_counts.most_common(6)}")
    print(f"Raw data directory: {RAW_DIR}")


if __name__ == "__main__":
    main()
