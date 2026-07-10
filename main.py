#!/usr/bin/env python3
"""Run the complete Match Momentum pipeline for a FIFA match."""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def run_command(cmd: list[str]) -> None:
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"Error: Command failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the complete World Cup 2026 match momentum pipeline."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--match-id", help="FIFA match id, e.g. 400021528.")
    group.add_argument(
        "--teams",
        nargs=2,
        metavar=("HOME", "AWAY"),
        help="Country codes to look up, e.g. --teams ARG EGY.",
    )
    group.add_argument(
        "--all-knockouts",
        action="store_true",
        help="Process all available knockout stage matches of the tournament.",
    )

    args = parser.parse_args()

    if args.all_knockouts:
        import json
        calendar_path = PROJECT_ROOT / "data" / "raw" / "competition_17_season_285023_calendar.json"
        if not calendar_path.exists():
            print("Calendar file not found. Fetching using collect_match_data.py...")
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

        knockout_matches = []
        for match in calendar.get("Results", []):
            stage_name = match.get("StageName")
            if stage_name and stage_name[0]["Description"] != "First Stage":
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
            
            result = subprocess.run(
                [sys.executable, __file__, "--match-id", match_id],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            
            if result.returncode == 0:
                print(f"--> Success: Match {match_id} processed successfully.")
                success_count += 1
            else:
                print(f"--> Failed: Match {match_id} could not be processed.")
                print(f"    Error details: {result.stderr.strip() or result.stdout.strip()}")
                fail_count += 1

        print(f"\nProcessing complete!")
        print(f"Successfully processed: {success_count} matches.")
        print(f"Failed/Not available:   {fail_count} matches.")
        sys.exit(0)

    # 1. Collection
    collect_cmd = [sys.executable, str(SCRIPTS_DIR / "collect_match_data.py")]
    if args.match_id:
        collect_cmd.extend(["--match-id", args.match_id])
    else:
        collect_cmd.extend(["--home", args.teams[0], "--away", args.teams[1]])

    # If --teams was passed, we run collection first and parse match_id from output
    if not args.match_id:
        print("Executing collection to resolve match ID...")
        result = subprocess.run(
            collect_cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            sys.exit(result.returncode)
        
        # Print captured output so user sees it
        print(result.stdout)
        
        match_id = None
        for line in result.stdout.splitlines():
            if "FIFA match id:" in line:
                match_id = line.split(":")[-1].strip()
                break
        
        if not match_id:
            print("Error: Could not identify match ID from data collection.", file=sys.stderr)
            sys.exit(1)
        print(f"Resolved match ID: {match_id}")
    else:
        run_command(collect_cmd)
        match_id = args.match_id

    # 2. Build momentum
    build_cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "build_match_momentum.py"),
        "--match-id",
        match_id,
    ]
    run_command(build_cmd)

    # 3. Create chart
    chart_cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "make_momentum_chart.py"),
        "--match-id",
        match_id,
    ]
    run_command(chart_cmd)

    import json
    live_path = PROJECT_ROOT / "data" / "raw" / f"match_{match_id}" / "live.json"
    if live_path.exists():
        live = json.loads(live_path.read_text())
        stage = live.get("StageName")[0]["Description"].replace(" ", "_") if live.get("StageName") else "Match"
        home = live["HomeTeam"]["ShortClubName"].replace(" ", "_")
        away = live["AwayTeam"]["ShortClubName"].replace(" ", "_")
        for char in ["'", "\"", "/", "\\", "?", "*", ":", "|", "<", ">"]:
            stage = stage.replace(char, "")
            home = home.replace(char, "")
            away = away.replace(char, "")
        descriptive_name = f"{stage}_{home}_{away}"
        
        print("\nPipeline run completed successfully!")
        print(f"Processed data: data/processed/{descriptive_name}/")
        print(f"Chart figure:   reports/figures/{descriptive_name}/{descriptive_name}_momentum_chart.png")
    else:
        print("\nPipeline run completed successfully!")


if __name__ == "__main__":
    main()
