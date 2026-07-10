"""Create a polished momentum chart for one processed match."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MPL_CACHE_DIR = PROJECT_ROOT / ".matplotlib-cache"
MPL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE_DIR))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnnotationBbox, DrawingArea
from matplotlib.patches import Circle, Polygon, Rectangle, RegularPolygon
import numpy as np
import pandas as pd
from scipy.interpolate import make_interp_spline


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"


INK = "#17202A"
MUTED = "#5D6D7E"
GRID = "#DDE3EA"
BREAK_GRAY = "#8A9099"
BG = "#FFFFFF"

TEAM_COLORS = {
    "ARG": "#75AADB",
    "EGY": "#CE1126",
    "MEX": "#006847",
    "ENG": "#1B365D",
    "BRA": "#009B3A",
    "NOR": "#BA0C2F",
}


def plot_signed_segments(ax, data: pd.DataFrame, home_color: str, away_color: str) -> None:
    """Draw positive and negative momentum with separate colors."""
    positive = data["momentum_smoothed"].where(data["momentum_smoothed"] >= 0)
    negative = data["momentum_smoothed"].where(data["momentum_smoothed"] < 0)

    ax.plot(
        data["minute"],
        positive,
        color=home_color,
        linewidth=4.0,
        solid_capstyle="round",
        solid_joinstyle="round",
        zorder=5,
    )
    ax.plot(
        data["minute"],
        negative,
        color=away_color,
        linewidth=4.0,
        solid_capstyle="round",
        solid_joinstyle="round",
        zorder=5,
    )


def add_football_icon(ax, minute: float, y: float) -> None:
    icon = DrawingArea(20, 20, 0, 0)
    icon.add_artist(Circle((10, 10), 8.1, facecolor=BG, edgecolor=INK, linewidth=1.2))
    icon.add_artist(RegularPolygon((10, 10), numVertices=5, radius=3.1, orientation=0.62, facecolor=INK, edgecolor=INK))
    for x, y2 in [(5.4, 6.0), (14.6, 6.0), (6.4, 14.0), (13.6, 14.0)]:
        icon.add_artist(Circle((x, y2), 1.1, facecolor=INK, edgecolor=INK, linewidth=0))
    ax.add_artist(AnnotationBbox(icon, (minute, y), frameon=False, box_alignment=(0.5, 0.5), zorder=9))


def annotate_goal(ax, minute: float, label: str, color: str, y: float) -> None:
    add_football_icon(ax, minute, y)
    text = ax.text(
        minute,
        y - 9,
        label,
        ha="center",
        va="top",
        fontsize=9,
        color=color,
        fontweight="bold",
        zorder=9,
    )
    text.set_path_effects([path_effects.withStroke(linewidth=3, foreground=BG)])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--match-id", required=True, help="FIFA match id, for example 400021528.")
    return parser.parse_args()


def localized_description(items: list[dict] | None, default: str = "") -> str:
    if not items:
        return default
    return items[0].get("Description", default)


def team_metadata(live: dict) -> tuple[dict, dict]:
    return live["HomeTeam"], live["AwayTeam"]


def chart_title(home: dict, away: dict) -> str:
    home_name = home["ShortClubName"]
    away_name = away["ShortClubName"]
    home_score = home.get("Score", 0)
    away_score = away.get("Score", 0)
    return f"{home_name} {home_score}-{away_score} {away_name}"


def chart_subtitle(live: dict) -> str:
    stage = localized_description(live.get("StageName"), "Match")
    competition = localized_description(live.get("SeasonName"), "FIFA World Cup 2026").replace("™", "")
    return f"{competition} - {stage}"


def draw_flag(fig, country_code: str, rect: list[float]) -> None:
    flag_ax = fig.add_axes(rect)
    flag_ax.set_xlim(0, 34)
    flag_ax.set_ylim(0, 22)
    flag_ax.axis("off")
    flag_ax.add_patch(Rectangle((1, 1), 32, 20, facecolor=BG, edgecolor="#D5DBE3", linewidth=0.8))

    def stripe(xy: tuple[float, float], width: float, height: float, color: str) -> None:
        flag_ax.add_patch(Rectangle(xy, width, height, facecolor=color, edgecolor="none"))

    if country_code == "MEX":
        stripe((1, 1), 10.7, 20, "#006847")
        stripe((11.7, 1), 10.6, 20, "#FFFFFF")
        stripe((22.3, 1), 10.7, 20, "#CE1126")
    elif country_code == "ENG":
        stripe((1, 1), 32, 20, "#FFFFFF")
        stripe((14.2, 1), 5.6, 20, "#C8102E")
        stripe((1, 8.2), 32, 5.6, "#C8102E")
    elif country_code == "ARG":
        stripe((1, 1), 32, 6.7, "#75AADB")
        stripe((1, 7.7), 32, 6.6, "#FFFFFF")
        stripe((1, 14.3), 32, 6.7, "#75AADB")
        flag_ax.add_patch(Circle((17, 11), 1.8, facecolor="#F6B40E", edgecolor="none"))
    elif country_code == "EGY":
        stripe((1, 1), 32, 6.7, "#000000")
        stripe((1, 7.7), 32, 6.6, "#FFFFFF")
        stripe((1, 14.3), 32, 6.7, "#CE1126")
        flag_ax.add_patch(Circle((17, 11), 1.4, facecolor="#C09300", edgecolor="none"))
    elif country_code == "BRA":
        stripe((1, 1), 32, 20, "#009B3A")
        flag_ax.add_patch(Polygon([(17, 19), (31, 11), (17, 3), (3, 11)], facecolor="#FFDF00", edgecolor="none"))
        flag_ax.add_patch(Circle((17, 11), 4.2, facecolor="#002776", edgecolor="none"))
    elif country_code == "NOR":
        stripe((1, 1), 32, 20, "#BA0C2F")
        stripe((9, 1), 6, 20, "#FFFFFF")
        stripe((1, 8), 32, 6, "#FFFFFF")
        stripe((10.5, 1), 3, 20, "#00205B")
        stripe((1, 9.5), 32, 3, "#00205B")
    else:
        stripe((1, 1), 32, 20, "#F4F6F8")
        flag_ax.add_patch(RegularPolygon((17, 11), numVertices=5, radius=5, facecolor="#9AA4B2", edgecolor="none"))


def main() -> None:
    args = parse_args()
    processed_dir = PROCESSED_DIR / f"match_{args.match_id}"
    raw_dir = RAW_DIR / f"match_{args.match_id}"
    figures_dir = FIGURES_DIR / f"match_{args.match_id}"
    figures_dir.mkdir(parents=True, exist_ok=True)

    live = json.loads((raw_dir / "live.json").read_text())
    momentum = pd.read_csv(processed_dir / "momentum_grid.csv")
    events = pd.read_csv(processed_dir / "events.csv")
    hydration = pd.read_csv(processed_dir / "hydration_breaks.csv")
    home, away = team_metadata(live)
    home_name = home["ShortClubName"]
    away_name = away["ShortClubName"]
    home_abbr = home["Abbreviation"]
    home_color = TEAM_COLORS.get(home.get("IdCountry", ""), "#1787C9")
    away_color = TEAM_COLORS.get(away.get("IdCountry", ""), "#B91C1C")

    # Interpolate momentum to high-res grid for smoother curve and fills
    x = momentum["minute"].values
    y = momentum["momentum_smoothed"].values
    x_new = np.linspace(x.min(), x.max(), len(x) * 6)  # 6x resolution (approx 0.04 min steps)
    spl = make_interp_spline(x, y, k=3)
    y_new = spl(x_new)

    # Force hydration breaks to 0.0 in high-res grid to prevent interpolation spillover
    for row in hydration.itertuples():
        mask = (x_new >= row.start_minute) & (x_new <= row.end_minute)
        y_new[mask] = 0.0

    momentum_hr = pd.DataFrame({
        "minute": x_new,
        "momentum_smoothed": y_new
    })

    plt.rcParams.update(
        {
            "figure.facecolor": BG,
            "axes.facecolor": BG,
            "savefig.facecolor": BG,
            "font.family": "DejaVu Sans",
            "axes.edgecolor": "#E8EDF2",
            "axes.linewidth": 1.1,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.labelcolor": INK,
        }
    )

    fig, ax = plt.subplots(figsize=(16, 9))
    fig.subplots_adjust(left=0.075, right=0.965, top=0.86, bottom=0.10)

    # Add a faded official FIFA World Cup 26 logo in the background centered behind the titles
    logo_path = Path(__file__).resolve().parent.parent / "data" / "fifa_logo.png"
    if logo_path.exists():
        logo_img = plt.imread(str(logo_path))
        if len(logo_img.shape) == 3:
            if logo_img.shape[2] == 3:
                alpha = np.ones((logo_img.shape[0], logo_img.shape[1], 1), dtype=logo_img.dtype)
                logo_img = np.append(logo_img, alpha, axis=2)
            if logo_img.shape[2] == 4:
                logo_img[:, :, 3] = logo_img[:, :, 3] * 0.08
            logo_ax = fig.add_axes([0.44, 0.835, 0.12, 0.13], zorder=1)
            logo_ax.axis("off")
            logo_ax.imshow(logo_img)

    ax.fill_between(
        momentum_hr["minute"],
        0,
        momentum_hr["momentum_smoothed"].clip(lower=0),
        color=home_color,
        alpha=0.13,
        zorder=1,
    )
    ax.fill_between(
        momentum_hr["minute"],
        0,
        momentum_hr["momentum_smoothed"].clip(upper=0),
        color=away_color,
        alpha=0.12,
        zorder=1,
    )
    plot_signed_segments(ax, momentum_hr, home_color, away_color)

    ax.axhline(0, color=INK, linewidth=1.2, alpha=0.88, zorder=4)

    for row in hydration.itertuples():
        ax.axvspan(row.start_minute, row.end_minute, color=BREAK_GRAY, alpha=0.18, zorder=0)
        ax.plot(
            [row.start_minute, row.end_minute],
            [0, 0],
            color=BREAK_GRAY,
            linewidth=5,
            solid_capstyle="round",
            alpha=0.75,
            zorder=7,
        )
        ax.text(
            (row.start_minute + row.end_minute) / 2,
            103,
            f"Hydration break\n{row.start_label}-{row.end_label}",
            ha="center",
            va="top",
            fontsize=10,
            color="#5C626B",
            fontweight="bold",
        )

    goals = events[events["event_type"].isin(["Goal!", "Penalty Goal", "Own Goal"])].copy().sort_values("elapsed_minute")
    previous_goal_minutes: list[tuple[float, float]] = []
    for row in goals.itertuples():
        color = home_color if row.attacking_abbr == home_abbr else away_color
        y = 92 if row.attacking_abbr == home_abbr else -82
        nearby_count = sum(abs(row.elapsed_minute - minute) <= 2 and y == goal_y for minute, goal_y in previous_goal_minutes)
        x_offset = 0.0 if nearby_count == 0 else [2.0, -2.0, 3.5, -3.5][(nearby_count - 1) % 4]
        y_offset = 0.0 if nearby_count == 0 else (8.0 * nearby_count if y < 0 else -8.0 * nearby_count)
        annotate_goal(ax, row.elapsed_minute + x_offset, f"{row.attacking_abbr} {row.match_minute_label}", color, y + y_offset)
        previous_goal_minutes.append((row.elapsed_minute, y))

        # Add faded vertical line for the goal in the scoring team's color
        ax.axvline(
            x=row.elapsed_minute,
            color=color,
            linestyle="--",
            linewidth=1.2,
            alpha=0.25,
            zorder=2,
        )

    # Draw vertical line for the first half whistle (end of Period 3)
    p3_events = events[events["period"] == 3]
    first_half_end = p3_events["elapsed_minute"].max() if not p3_events.empty else 45.0
    ax.axvline(
        x=first_half_end,
        color=MUTED,
        linestyle="-.",
        linewidth=1.2,
        alpha=0.45,
        zorder=2,
    )
    ax.text(
        first_half_end,
        -105,
        "HT",
        color=MUTED,
        fontsize=10,
        fontweight="bold",
        ha="center",
        va="bottom",
        alpha=0.6,
    )

    max_elapsed = momentum_hr["minute"].max()
    ax.set_xlim(0, max_elapsed + 1)
    ax.set_ylim(-110, 110)
    ax.set_xticks(range(0, int(max_elapsed) + 1, 10))
    ax.set_yticks([-100, -50, 0, 50, 100])
    ax.grid(visible=False)
    ax.tick_params(axis="y", length=0, labelsize=11)
    ax.tick_params(axis="x", bottom=False, labelbottom=False)
    ax.set_xlabel("")
    ax.set_ylabel("Momentum", fontsize=12, labelpad=14)

    draw_flag(fig, home.get("IdCountry", ""), [0.085, 0.74, 0.032, 0.024])
    draw_flag(fig, away.get("IdCountry", ""), [0.085, 0.14, 0.032, 0.024])

    fig.text(
        0.101,
        0.71,
        home_abbr,
        fontsize=10,
        fontweight="bold",
        color=home_color,
        ha="center",
    )
    fig.text(
        0.101,
        0.11,
        away.get("Abbreviation", ""),
        fontsize=10,
        fontweight="bold",
        color=away_color,
        ha="center",
    )

    for spine in ["top", "right", "bottom"]:
        ax.spines[spine].set_visible(False)

    fig.text(
        0.5,
        0.94,
        chart_title(home, away),
        fontsize=30,
        fontweight="bold",
        color=INK,
        ha="center",
    )
    fig.text(
        0.5,
        0.89,
        chart_subtitle(live),
        fontsize=15,
        color=MUTED,
        ha="center",
    )
    png_path = figures_dir / "momentum_chart.png"
    svg_path = figures_dir / "momentum_chart.svg"
    fig.savefig(png_path, dpi=220, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    print(png_path)
    print(svg_path)


if __name__ == "__main__":
    main()
