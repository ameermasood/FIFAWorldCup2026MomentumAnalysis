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

    args = parser.parse_args()

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
