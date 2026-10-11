"""The four charts. All saved as PNGs into an output directory.

Deliberately plain matplotlib — no seaborn, no styling dependencies — so it
runs anywhere and you can read exactly what every line does.
"""

from __future__ import annotations

import pathlib

import matplotlib
matplotlib.use("Agg")  # headless: write files, never open a window
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from . import decompose

_YIELD = "#1f3a5f"
_EXP = "#4c8fbf"
_TP = "#c9702a"


def _finish(ax, fig, path):
    ax.grid(True, alpha=0.25, linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def chart_decomposition(df, outdir: pathlib.Path) -> pathlib.Path:
    """10y yield as expectations + term premium, stacked through time."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.stackplot(df["date"], df["expectations"], df["term_premium"],
                 labels=["Expectations (risk-neutral)", "Term premium"],
                 colors=[_EXP, _TP], alpha=0.85)
    ax.plot(df["date"], df["yield"], color=_YIELD, lw=1.4, label="10y yield")
    ax.axhline(0, color="black", lw=0.6)
    ax.set_title("US 10y yield decomposed: expectations + term premium")
    ax.set_ylabel("percent")
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    ax.xaxis.set_major_locator(mdates.YearLocator(base=2))
    p = outdir / "01_decomposition.png"
    _finish(ax, fig, p)
    return p


def chart_term_premium_history(df, pctl: dict, outdir: pathlib.Path) -> pathlib.Path:
    """Term premium over time with current level and percentile annotated."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df["date"], df["term_premium"], color=_TP, lw=1.2)
    ax.axhline(0, color="black", lw=0.6)
    ax.axhline(pctl["mean"], color=_TP, ls="--", lw=0.8, alpha=0.7,
               label=f"mean {pctl['mean']:.2f}%")
    cur = pctl["current"]
    ax.scatter([df["date"].iloc[-1]], [cur], color=_YIELD, zorder=5)
    ax.annotate(f"  now: {cur:.2f}%  ({pctl['percentile']:.0f}th pctile)",
                xy=(df["date"].iloc[-1], cur), color=_YIELD,
                fontsize=9, va="center", fontweight="bold")
    ax.set_title("10y term premium — history and current standing")
    ax.set_ylabel("percent")
    ax.legend(loc="upper right", fontsize=8)
    ax.xaxis.set_major_locator(mdates.YearLocator(base=2))
    p = outdir / "02_term_premium_history.png"
    _finish(ax, fig, p)
    return p


def chart_attribution(attr, outdir: pathlib.Path) -> pathlib.Path:
    """Change in yield split into expectations vs term premium, per window."""
    fig, ax = plt.subplots(figsize=(9, 5))
    x = range(len(attr))
    ax.bar([i - 0.2 for i in x], attr["d_expectations_bp"], width=0.4,
           color=_EXP, label="Δ expectations")
    ax.bar([i + 0.2 for i in x], attr["d_term_premium_bp"], width=0.4,
           color=_TP, label="Δ term premium")
    ax.plot(list(x), attr["d_yield_bp"], "o-", color=_YIELD, lw=1.2,
            label="Δ yield (total)")
    ax.axhline(0, color="black", lw=0.6)
    ax.set_xticks(list(x))
    ax.set_xticklabels(attr["window"])
    ax.set_title("What moved the 10y: expectations vs term premium")
    ax.set_ylabel("basis points")
    ax.legend(fontsize=8)
    p = outdir / "03_attribution.png"
    _finish(ax, fig, p)
    return p


def chart_rolling_driver(roll, outdir: pathlib.Path, window_days: int) -> pathlib.Path:
    """Rolling contribution of each driver to the long end."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(roll["date"], roll["d_expectations_bp"], color=_EXP, lw=1.0,
            label="Δ expectations")
    ax.plot(roll["date"], roll["d_term_premium_bp"], color=_TP, lw=1.0,
            label="Δ term premium")
    ax.axhline(0, color="black", lw=0.6)
    ax.set_title(f"Rolling {window_days}-day driver of the 10y yield")
    ax.set_ylabel("basis points")
    ax.legend(fontsize=8)
    ax.xaxis.set_major_locator(mdates.YearLocator(base=2))
    p = outdir / "04_rolling_driver.png"
    _finish(ax, fig, p)
    return p


def build_all(df, outdir: pathlib.Path, window_days: int = 60) -> list[pathlib.Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    pctl = decompose.percentile(df, "term_premium")
    attr = decompose.attribution(df)
    roll = decompose.rolling_driver(df, window_days)
    return [
        chart_decomposition(df, outdir),
        chart_term_premium_history(df, pctl, outdir),
        chart_attribution(attr, outdir),
        chart_rolling_driver(roll, outdir, window_days),
    ]
