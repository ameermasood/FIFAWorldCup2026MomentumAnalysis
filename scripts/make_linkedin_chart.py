"""Create a polished LinkedIn-ready momentum chart."""

from __future__ import annotations

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
from matplotlib.offsetbox import AnnotationBbox, DrawingArea
from matplotlib.patches import Circle, RegularPolygon
import pandas as pd


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

MOMENTUM_PATH = PROCESSED_DIR / "argentina_egypt_400021528_momentum.csv"
EVENTS_PATH = PROCESSED_DIR / "argentina_egypt_400021528_events.csv"
HYDRATION_PATH = PROCESSED_DIR / "argentina_egypt_400021528_hydration_breaks.csv"

PNG_PATH = FIGURES_DIR / "argentina_egypt_400021528_momentum_linkedin.png"
SVG_PATH = FIGURES_DIR / "argentina_egypt_400021528_momentum_linkedin.svg"
PROXY_PNG_PATH = FIGURES_DIR / "argentina_egypt_400021528_momentum_proxy.png"


ARG_BLUE = "#1787C9"
EGY_RED = "#B91C1C"
GOLD = "#D4A017"
INK = "#17202A"
MUTED = "#5D6D7E"
GRID = "#DDE3EA"
BREAK_GRAY = "#8A9099"
BG = "#FFFFFF"


def plot_signed_segments(ax, data: pd.DataFrame) -> None:
    """Draw positive and negative momentum with separate colors."""
    positive = data["momentum_smoothed"].where(data["momentum_smoothed"] >= 0)
    negative = data["momentum_smoothed"].where(data["momentum_smoothed"] < 0)

    ax.plot(
        data["minute"],
        positive,
        color=ARG_BLUE,
        linewidth=4.0,
        solid_capstyle="round",
        solid_joinstyle="round",
        zorder=5,
    )
    ax.plot(
        data["minute"],
        negative,
        color=EGY_RED,
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


def main() -> None:
    momentum = pd.read_csv(MOMENTUM_PATH)
    events = pd.read_csv(EVENTS_PATH)
    hydration = pd.read_csv(HYDRATION_PATH)

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
    fig.subplots_adjust(left=0.075, right=0.965, top=0.84, bottom=0.13)

    ax.fill_between(
        momentum["minute"],
        0,
        momentum["momentum_smoothed"].clip(lower=0),
        color=ARG_BLUE,
        alpha=0.13,
        zorder=1,
    )
    ax.fill_between(
        momentum["minute"],
        0,
        momentum["momentum_smoothed"].clip(upper=0),
        color=EGY_RED,
        alpha=0.12,
        zorder=1,
    )
    plot_signed_segments(ax, momentum)

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

    goals = events[events["event_type"] == "Goal!"].copy()
    for row in goals.itertuples():
        color = ARG_BLUE if row.attacking_abbr == "ARG" else GOLD
        y = 92 if row.attacking_abbr == "ARG" else -82
        annotate_goal(ax, row.match_minute, f"{row.attacking_abbr} {row.match_minute_label}", color, y)

    ax.set_xlim(0, 102)
    ax.set_ylim(-110, 110)
    ax.set_xticks(range(0, 101, 10))
    ax.set_yticks([-100, -50, 0, 50, 100])
    ax.grid(axis="y", color=GRID, linewidth=1.0)
    ax.grid(axis="x", visible=False)
    ax.tick_params(axis="both", length=0, labelsize=11)
    ax.set_xlabel("Match minute", fontsize=12, labelpad=14)
    ax.set_ylabel("Momentum proxy", fontsize=12, labelpad=14)

    ax.text(0.01, 0.965, "Argentina pressure", transform=ax.transAxes, color=ARG_BLUE, fontsize=12, fontweight="bold")
    ax.text(0.01, 0.035, "Egypt pressure", transform=ax.transAxes, color=EGY_RED, fontsize=12, fontweight="bold")

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    fig.text(
        0.5,
        0.935,
        "Argentina vs Egypt, World Cup 2026 Round of 16",
        fontsize=24,
        fontweight="bold",
        color=INK,
        ha="center",
    )
    fig.savefig(PNG_PATH, dpi=220, bbox_inches="tight")
    fig.savefig(SVG_PATH, bbox_inches="tight")
    fig.savefig(PROXY_PNG_PATH, dpi=200, bbox_inches="tight")
    print(PNG_PATH)
    print(SVG_PATH)
    print(PROXY_PNG_PATH)


if __name__ == "__main__":
    main()
