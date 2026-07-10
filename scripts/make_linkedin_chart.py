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
import pandas as pd


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

MOMENTUM_PATH = PROCESSED_DIR / "argentina_egypt_400021528_momentum.csv"
EVENTS_PATH = PROCESSED_DIR / "argentina_egypt_400021528_events.csv"
HYDRATION_PATH = PROCESSED_DIR / "argentina_egypt_400021528_hydration_breaks.csv"
SUMMARY_PATH = PROCESSED_DIR / "argentina_egypt_400021528_break_summary.csv"

PNG_PATH = FIGURES_DIR / "argentina_egypt_400021528_momentum_linkedin.png"
SVG_PATH = FIGURES_DIR / "argentina_egypt_400021528_momentum_linkedin.svg"


ARG_BLUE = "#1787C9"
ARG_DARK = "#0A3D62"
EGY_RED = "#B91C1C"
EGY_DARK = "#4A0D0D"
GOLD = "#D4A017"
PURPLE = "#7C3AED"
INK = "#17202A"
MUTED = "#5D6D7E"
GRID = "#DDE3EA"
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


def annotate_goal(ax, minute: float, label: str, color: str, y: float) -> None:
    ax.scatter([minute], [y], s=72, color=color, edgecolor=BG, linewidth=1.6, zorder=8)
    text = ax.text(
        minute,
        y - 7,
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
    summary = pd.read_csv(SUMMARY_PATH)

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
    fig.subplots_adjust(left=0.075, right=0.965, top=0.80, bottom=0.17)

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
        ax.axvspan(row.start_minute, row.end_minute, color=PURPLE, alpha=0.12, zorder=0)
        ax.plot(
            [row.start_minute, row.end_minute],
            [0, 0],
            color=PURPLE,
            linewidth=5,
            solid_capstyle="round",
            alpha=0.65,
            zorder=7,
        )
        ax.text(
            (row.start_minute + row.end_minute) / 2,
            103,
            f"Hydration break\n{row.start_label}-{row.end_label}",
            ha="center",
            va="top",
            fontsize=10,
            color=PURPLE,
            fontweight="bold",
        )

    goals = events[events["event_type"] == "Goal!"].copy()
    for row in goals.itertuples():
        color = ARG_BLUE if row.attacking_abbr == "ARG" else GOLD
        y = 92 if row.attacking_abbr == "ARG" else -82
        annotate_goal(ax, row.match_minute, f"{row.attacking_abbr} {row.match_minute_label}", color, y)

    break_two = summary.loc[summary["break_number"] == 2].iloc[0]
    ax.text(
        0.985,
        0.035,
        f"70'-74' break: {break_two.before_avg_momentum:+.1f} before -> "
        f"{break_two.after_avg_momentum:+.1f} after",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=11,
        color=INK,
        bbox={"boxstyle": "round,pad=0.4,rounding_size=0.12", "fc": "#FFFFFF", "ec": "#E5EAF0"},
    )

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
        0.075,
        0.935,
        "Argentina vs Egypt, World Cup 2026 Round of 16",
        fontsize=24,
        fontweight="bold",
        color=INK,
        ha="left",
    )
    fig.text(
        0.075,
        0.895,
        "Open momentum proxy inspired by Opta: capped peak threat per team per minute, weighted over the previous four minutes",
        fontsize=13,
        color=MUTED,
        ha="left",
    )
    fig.text(
        0.075,
        0.855,
        "Key takeaway: 70'-74' hydration break precedes a sharp swing toward Argentina",
        fontsize=11.5,
        color=ARG_DARK,
        fontweight="bold",
        ha="left",
        va="center",
        bbox={"boxstyle": "round,pad=0.45,rounding_size=0.12", "fc": "#F4FAFE", "ec": "#CDEAF8"},
    )
    fig.text(
        0.075,
        0.055,
        "Positive values favor Argentina. Negative values favor Egypt. Hydration intervals are forced to zero because play is stopped. Source: FIFA public timeline data.",
        fontsize=10.5,
        color=MUTED,
        ha="left",
    )

    fig.savefig(PNG_PATH, dpi=220, bbox_inches="tight")
    fig.savefig(SVG_PATH, bbox_inches="tight")
    print(PNG_PATH)
    print(SVG_PATH)


if __name__ == "__main__":
    main()
