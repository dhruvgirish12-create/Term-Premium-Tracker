"""Monthly note generator.

Design principle: the tracker fills in every NUMBER and leaves every JUDGEMENT
blank. It will tell you the term premium is at the 78th percentile and that 40bp
of the last quarter's move came from term premium — it will NOT tell you what
that means for a bond allocation. That sentence is yours to write.

That split is deliberate. It keeps the analysis defensibly your own work (which
matters when a recruiter asks you to walk through a note with your name on it),
and it stops the tool from laundering a canned opinion as a market view.
"""

from __future__ import annotations

import datetime as dt
import pathlib

from . import decompose


def _arrow(bp: float) -> str:
    return "rose" if bp > 0 else "fell" if bp < 0 else "was unchanged"


def build_note(df, source: str, author: str, outdir: pathlib.Path,
               is_demo: bool = False) -> pathlib.Path:
    latest = decompose.latest(df)
    pctl = decompose.percentile(df, "term_premium")
    attr = decompose.attribution(df)

    stamp = dt.date.fromisoformat(latest["date"])
    fname = f"{stamp:%Y-%m}-long-end.md"
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / fname

    lines: list[str] = []
    a = lines.append

    a(f"# The long end — {stamp:%B %Y}")
    a("")
    if is_demo:
        a("> **DEMO DATA — NOT A REAL MARKET READ.** Regenerate with "
          "`--source acm` before using any of these numbers.")
        a("")
    a(f"*Source: {source.upper()} decomposition · as of {latest['date']} · "
      f"generated for {author}*")
    a("")

    # --- Facts (auto-filled) --------------------------------------------
    a("## Where things stand")
    a("")
    a(f"- 10y yield: **{latest['yield']:.2f}%**")
    a(f"- Expectations component: **{latest['expectations']:.2f}%**")
    a(f"- Term premium: **{latest['term_premium']:.2f}%** "
      f"— {pctl['percentile']:.0f}th percentile of its "
      f"{pctl['n_obs']:,}-observation history "
      f"(range {pctl['min']:.2f}% to {pctl['max']:.2f}%, mean {pctl['mean']:.2f}%)")
    a("")

    a("## What moved it")
    a("")
    a("| Window | Δ yield | Δ expectations | Δ term premium | TP share |")
    a("|--------|--------:|---------------:|---------------:|---------:|")
    for _, r in attr.iterrows():
        a(f"| {r['window']} | {r['d_yield_bp']:+.0f}bp "
          f"| {r['d_expectations_bp']:+.0f}bp | {r['d_term_premium_bp']:+.0f}bp "
          f"| {r['tp_share_pct']:.0f}% |")
    a("")
    if not attr.empty:
        q = attr[attr["window"] == "3m"]
        if not q.empty:
            r = q.iloc[0]
            a(f"Over the last 3 months the 10y {_arrow(r['d_yield_bp'])} "
              f"{abs(r['d_yield_bp']):.0f}bp, of which "
              f"{abs(r['d_term_premium_bp']):.0f}bp was term premium "
              f"({r['tp_share_pct']:.0f}% of the move).")
            a("")

    # --- Judgement (left blank) -----------------------------------------
    a("## Read  _(write this yourself)_")
    a("")
    a("- **What this means for a bond allocation:** _______________________")
    a("- **Expectations vs term premium — which story dominates and why:** ___")
    a("- **What would make this read wrong (the falsifier):** ________________")
    a("- **One thing to watch into next month:** ____________________________")
    a("")
    a("---")
    a("*Numbers auto-generated; interpretation intentionally left blank.*")

    path.write_text("\n".join(lines))
    return path
