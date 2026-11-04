"""Static charts (matplotlib, light theme).

A state tile-grid map stands in for a choropleth: every state gets the same
area, so small expensive states (DC, Hawaii, New Jersey) are as visible as
large ones, and no shapefile is needed.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
NEUTRAL = "#ecebe7"

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK_2,
        "axes.titlecolor": INK,
        "axes.titleweight": "bold",
        "axes.titlesize": 13,
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": INK_2,
        "ytick.color": INK_2,
        "font.size": 10,
        "savefig.dpi": 160,
        "savefig.bbox": "tight",
    }
)

# Diverging: cheaper than average (blue) <- neutral at 100 -> pricier (orange)
DIVERGING = LinearSegmentedColormap.from_list("rpp", [BLUE, NEUTRAL, ORANGE])

STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
    "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}

# (row, col) on an 8 x 11 grid, laid out to resemble the map
TILE_GRID = {
    "AK": (0, 0), "ME": (0, 10),
    "VT": (1, 9), "NH": (1, 10),
    "WA": (2, 0), "ID": (2, 1), "MT": (2, 2), "ND": (2, 3), "MN": (2, 4), "IL": (2, 5),
    "WI": (2, 6), "MI": (2, 7), "NY": (2, 8), "RI": (2, 9), "MA": (2, 10),
    "OR": (3, 0), "NV": (3, 1), "WY": (3, 2), "SD": (3, 3), "IA": (3, 4), "IN": (3, 5),
    "OH": (3, 6), "PA": (3, 7), "NJ": (3, 8), "CT": (3, 9),
    "CA": (4, 0), "UT": (4, 1), "CO": (4, 2), "NE": (4, 3), "MO": (4, 4), "KY": (4, 5),
    "WV": (4, 6), "VA": (4, 7), "MD": (4, 8), "DE": (4, 9),
    "AZ": (5, 1), "NM": (5, 2), "KS": (5, 3), "AR": (5, 4), "TN": (5, 5), "NC": (5, 6),
    "SC": (5, 7), "DC": (5, 8),
    "OK": (6, 3), "LA": (6, 4), "MS": (6, 5), "AL": (6, 6), "GA": (6, 7),
    "HI": (7, 0), "TX": (7, 3), "FL": (7, 8),
}


def _finish(fig, path: Path) -> None:
    fig.savefig(path)
    plt.close(fig)


def purchasing_power_bar(pp: pd.DataFrame, base: int, end: int, path: Path) -> None:
    df = pp.iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    colors = [INK_2 if c == "All items" else BLUE for c in df["category"]]
    ax.barh(df["category"], df["cents_per_base_dollar"], color=colors, height=0.6)
    for y, v in enumerate(df["cents_per_base_dollar"]):
        ax.text(v + 1, y, f"{v:.0f}¢", va="center", color=INK)
    ax.axvline(100, color=INK_2, linewidth=1, linestyle=":")
    ax.text(100, len(df) - 0.4, f" \\$1 in {base}", color=INK_2, fontsize=9, va="bottom")
    ax.set_xlim(0, 112)
    ax.set_xlabel(f"What \\$1 of {base} spending buys in {end} (cents)")
    ax.set_title(f"How far a {base} dollar goes in {end}")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    _finish(fig, path)


def yoy_line(yoy: pd.DataFrame, target: float, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    ax.plot(yoy["year"], yoy["yoy_pct"], color=BLUE, linewidth=2, marker="o", markersize=5)
    ax.axhline(target, color=INK_2, linewidth=1, linestyle="--")
    ax.text(yoy["year"].max(), target - 0.15, f"Fed target {target:g}%", color=INK_2, fontsize=9,
            ha="right", va="top")
    peak = yoy.loc[yoy["yoy_pct"].idxmax()]
    ax.annotate(f"{peak['yoy_pct']:.1f}% in {int(peak['year'])}", (peak["year"], peak["yoy_pct"]),
                xytext=(8, 0), textcoords="offset points", color=INK, va="center")
    ax.set_ylabel("Change in annual average CPI (%)")
    ax.set_title("U.S. inflation, all items, year over year")
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_ylim(bottom=0)
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    _finish(fig, path)


def rpp_tile_map(summary: pd.DataFrame, year: int, path: Path) -> None:
    values = summary.set_index("state")[f"rpp_{year}"]
    lo, hi = values.min(), values.max()
    span = max(100 - lo, hi - 100)
    norm = TwoSlopeNorm(vmin=100 - span, vcenter=100, vmax=100 + span)

    fig, ax = plt.subplots(figsize=(9, 6.2))
    for state, abbr in STATE_ABBR.items():
        if state not in values or abbr not in TILE_GRID:
            continue
        r, c = TILE_GRID[abbr]
        v = values[state]
        ax.add_patch(plt.Rectangle((c, -r), 0.92, 0.92, color=DIVERGING(norm(v))))
        ax.text(c + 0.46, -r + 0.6, abbr, ha="center", va="center", fontsize=9,
                color=INK, fontweight="bold")
        ax.text(c + 0.46, -r + 0.28, f"{v:.0f}", ha="center", va="center", fontsize=8, color=INK)
    ax.set_xlim(-0.2, 11.2)
    ax.set_ylim(-7.2, 1.1)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"Cost of living by state, {year} (U.S. average = 100)")
    sm = plt.cm.ScalarMappable(norm=norm, cmap=DIVERGING)
    cb = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.04, pad=0.02, aspect=40)
    cb.set_label("Regional Price Parity: below 100 is cheaper than average, above is pricier",
                 color=INK_2)
    cb.outline.set_visible(False)
    _finish(fig, path)


def rpp_extremes_bar(summary: pd.DataFrame, year: int, path: Path, n: int = 5) -> None:
    col = f"rpp_{year}"
    df = pd.concat([summary.head(n), summary.tail(n)]).sort_values(col)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    colors = [ORANGE if v > 100 else BLUE for v in df[col]]
    ax.barh(df["state"], df[col] - 100, left=100, color=colors, height=0.6)
    for y, (v, d) in enumerate(zip(df[col], df["value_of_100_usd"])):
        off = 0.6 if v > 100 else -0.6
        ax.text(v + off, y, f"{v:.1f}  (\\$100 buys \\${d:.0f})", va="center",
                ha="left" if v > 100 else "right", color=INK_2, fontsize=9)
    ax.axvline(100, color=INK, linewidth=1)
    lo, hi = df[col].min(), df[col].max()
    ax.set_xlim(lo - 24, hi + 18)
    ax.set_title(f"Most and least expensive states, {year}")
    ax.set_xlabel("Regional Price Parity (U.S. = 100)")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    _finish(fig, path)
