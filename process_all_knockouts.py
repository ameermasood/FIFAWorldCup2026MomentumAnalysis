#!/usr/bin/env python3
"""Process all available knockout stage matches of the tournament."""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def main() -> None:
    calendar_path = RAW_DIR / "competition_17_season_285023_calendar.json"
    if not calendar_path.exists():
        print("Calendar file not found. Fetching using collect_match_data.py...")
        # Run a dummy collection to fetch the calendar
        subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "collect_match_data.py"), "--match-id", "400021528"],
            cwd=PROJECT_ROOT,
            capture_output=True,
        )
        if not calendar_path.exists():
            print("Error: Could not obtain calendar file.", file=sys.stderr)
            sys.exit(1)

    with open(calendar_path) as f:
        calendar = json.load(f)

    # Find all knockout matches
    knockout_matches = []
    for match in calendar.get("Results", []):
        stage_name = match.get("StageName")
        if stage_name and stage_name[0]["Description"] != "First Stage":
            # Check if both teams are resolved (i.e. not TBD)
            home = match.get("Home")
            away = match.get("Away")
            if home and away and home.get("Abbreviation") and away.get("Abbreviation"):
                knockout_matches.append({
                    "id_match": match.get("IdMatch"),
                    "home": home.get("Abbreviation"),
                    "away": away.get("Abbreviation"),
                    "stage": stage_name[0]["Description"]
                })

    print(f"Found {len(knockout_matches)} knockout matches with resolved teams.")

    success_count = 0
    fail_count = 0

    for idx, match in enumerate(knockout_matches, 1):
        match_id = str(match["id_match"])
        home = match["home"]
        away = match["away"]
        stage = match["stage"]
        
        print(f"\n[{idx}/{len(knockout_matches)}] Processing Match {match_id}: {home} vs {away} ({stage})...")
        
        # Run run_pipeline.py for this match id
        result = subprocess.run(
            [sys.executable, "run_pipeline.py", "--match-id", match_id],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            print(f"--> Success: Match {match_id} processed successfully.")
            success_count += 1
        else:
            # Check if it was because data is not yet available (e.g. 403 or 404 from FIFA API)
            print(f"--> Failed: Match {match_id} could not be processed.")
            print(f"    Error details: {result.stderr.strip() or result.stdout.strip()}")
            fail_count += 1

    print(f"\nProcessing complete!")
    print(f"Successfully processed: {success_count} matches.")
    print(f"Failed/Not available:   {fail_count} matches.")


if __name__ == "__main__":
    main()
