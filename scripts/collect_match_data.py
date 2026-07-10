"""Collect FIFA public JSON payloads for one FIFA match."""

from __future__ import annotations

import argparse
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


def find_target_match(calendar: dict, home_or_away: set[str], match_id: str | None) -> dict:
    for match in calendar["Results"]:
        if match_id and str(match.get("IdMatch")) != str(match_id):
            continue
        teams = [team_summary(match, "Home"), team_summary(match, "Away")]
        abbreviations = {team["abbr"] for team in teams if team}
        if match_id or home_or_away.issubset(abbreviations):
            return {
                "match_number": match.get("MatchNumber"),
                "id_match": match.get("IdMatch"),
                "id_stage": match.get("IdStage"),
                "date": match.get("Date"),
                "stage": localized_description(match.get("StageName")),
                "home": team_summary(match, "Home"),
                "away": team_summary(match, "Away"),
            }
    target = match_id or " vs ".join(sorted(home_or_away))
    raise RuntimeError(f"Match {target} was not found in the WC26 calendar payload.")


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", default="ARG", help="One team abbreviation to search for. Default: ARG.")
    parser.add_argument("--away", default="EGY", help="The other team abbreviation to search for. Default: EGY.")
    parser.add_argument("--match-id", help="FIFA match id. If supplied, team search is skipped.")
    parser.add_argument("--competition-id", default=ID_COMPETITION, help="FIFA competition id. Default: 17.")
    parser.add_argument("--season-id", default=ID_SEASON, help="FIFA season id. Default: 285023.")
    parser.add_argument("--language", default=LANGUAGE, help="FIFA API language. Default: en.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    calendar_url = (
        f"{BASE_URL}/calendar/matches?language={args.language}"
        f"&idCompetition={args.competition_id}&idSeason={args.season_id}&count=200"
    )
    calendar_path = RAW_DIR / f"competition_{args.competition_id}_season_{args.season_id}_calendar.json"
    calendar = load_or_fetch_json(calendar_url, calendar_path)

    match = find_target_match(calendar, {args.home.upper(), args.away.upper()}, args.match_id)
    id_match = match["id_match"]
    id_stage = match["id_stage"]
    match_raw_dir = RAW_DIR / f"match_{id_match}"
    match_raw_dir.mkdir(parents=True, exist_ok=True)

    live_url = f"{BASE_URL}/live/football/{args.competition_id}/{args.season_id}/{id_stage}/{id_match}?language={args.language}"
    timeline_url = f"{BASE_URL}/timelines/{id_match}?language={args.language}"
    match_calendar_url = f"{BASE_URL}/calendar/{id_match}?language={args.language}"

    live_path = match_raw_dir / "live.json"
    timeline_path = match_raw_dir / "timeline.json"
    match_calendar_path = match_raw_dir / "calendar.json"

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
    print(f"Raw data directory: {match_raw_dir}")


if __name__ == "__main__":
    main()
