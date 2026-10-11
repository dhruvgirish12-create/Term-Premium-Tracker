"""Analytics on top of the tidy frame from data.load().

The single idea the whole tracker rests on:

    10y yield  =  expectations  +  term premium

so any *change* in the 10y yield is, exactly,

    d(yield)  =  d(expectations)  +  d(term premium)

That decomposition of the CHANGE is the interesting bit: it tells you whether a
sell-off in the long end was the market repricing the path of policy rates
(expectations) or repricing the compensation for holding duration (term
premium). Two very different stories that a headline yield number hides.
"""

from __future__ import annotations

import pandas as pd

WINDOWS = {"1m": 21, "3m": 63, "6m": 126, "12m": 252}  # trading days


def latest(df: pd.DataFrame) -> dict:
    """Most recent observation as a plain dict."""
    row = df.iloc[-1]
    return {
        "date": row["date"].date().isoformat(),
        "yield": float(row["yield"]),
        "expectations": float(row["expectations"]),
        "term_premium": float(row["term_premium"]),
    }


def percentile(df: pd.DataFrame, column: str = "term_premium",
               lookback_years: int | None = None) -> dict:
    """Where the current value of `column` sits in its own history."""
    s = df.set_index("date")[column]
    if lookback_years:
        s = s[s.index >= s.index.max() - pd.DateOffset(years=lookback_years)]
    current = float(s.iloc[-1])
    pct = float((s < current).mean() * 100)
    return {
        "column": column,
        "current": current,
        "percentile": round(pct, 1),
        "min": float(s.min()),
        "max": float(s.max()),
        "mean": float(s.mean()),
        "n_obs": int(s.shape[0]),
    }


def attribution(df: pd.DataFrame) -> pd.DataFrame:
    """Decompose the yield change over each window into its two drivers.

    Returns one row per window with the change in yield, expectations and term
    premium (in basis points), plus the term premium's share of the move.
    """
    df = df.sort_values("date").reset_index(drop=True)
    rows = []
    for name, k in WINDOWS.items():
        if len(df) <= k:
            continue
        now, then = df.iloc[-1], df.iloc[-1 - k]
        d_yield = (now["yield"] - then["yield"]) * 100
        d_exp = (now["expectations"] - then["expectations"]) * 100
        d_tp = (now["term_premium"] - then["term_premium"]) * 100
        share = (d_tp / d_yield * 100) if abs(d_yield) > 1e-9 else float("nan")
        rows.append({
            "window": name,
            "d_yield_bp": round(d_yield, 1),
            "d_expectations_bp": round(d_exp, 1),
            "d_term_premium_bp": round(d_tp, 1),
            "tp_share_pct": round(share, 1),
        })
    return pd.DataFrame(rows)


def rolling_driver(df: pd.DataFrame, window_days: int = 60) -> pd.DataFrame:
    """Rolling contribution of each component to the change in the long end.

    Over a trailing `window_days` window at every date, how many bp of the
    yield move came from expectations vs term premium. Lets you see regimes
    where one driver dominates.
    """
    df = df.sort_values("date").set_index("date")
    d_exp = (df["expectations"] - df["expectations"].shift(window_days)) * 100
    d_tp = (df["term_premium"] - df["term_premium"].shift(window_days)) * 100
    out = pd.DataFrame({
        "d_expectations_bp": d_exp,
        "d_term_premium_bp": d_tp,
    }).dropna()
    return out.reset_index()
