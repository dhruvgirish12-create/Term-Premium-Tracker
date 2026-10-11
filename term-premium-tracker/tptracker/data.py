"""Data layer for the term premium tracker.

Every fetcher returns the SAME tidy frame so the rest of the code doesn't care
where the numbers came from:

    columns = ["date", "yield", "expectations", "term_premium"]
      date          business-day index (datetime64)
      yield         10y Treasury yield, in percent
      expectations  risk-neutral / expected-average-short-rate component, percent
      term_premium  yield - expectations, percent (can be negative)

Two live sources are supported:

  * "acm"  Adrian-Crump-Moench decomposition, published by the New York Fed.
           Gives fitted yield, risk-neutral yield and term premium DIRECTLY,
           so the decomposition is exact rather than inferred. This is the
           headline source.
  * "kw"   Kim-Wright, distributed on FRED as a keyless CSV (series
           THREEFYTP10). FRED gives the term premium; we take the yield from
           DGS10 and back out expectations = yield - term_premium.

And one offline source, "demo", which fabricates a plausible 20-year history so
the whole pipeline runs with no network access (useful for tests / CI / trying
it out on a plane).

Nothing here needs an API key.
"""

from __future__ import annotations

import io
import datetime as dt

import numpy as np
import pandas as pd
import requests

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
NYFED_ACM_XLS = (
    "https://www.newyorkfed.org/medialibrary/media/research/"
    "data_indicators/ACMTermPremium.xls"
)

_TIMEOUT = 30


def _fred_series(series: str) -> pd.Series:
    """Pull a single FRED series as a date-indexed float Series (keyless CSV)."""
    url = FRED_CSV.format(series=series)
    r = requests.get(url, timeout=_TIMEOUT)
    r.raise_for_status()
    frame = pd.read_csv(io.StringIO(r.text))
    # FRED CSVs are [DATE, <SERIES>]; missing obs are marked ".".
    frame.columns = ["date", "value"]
    frame["date"] = pd.to_datetime(frame["date"])
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    return frame.dropna().set_index("date")["value"]


def fetch_kw() -> pd.DataFrame:
    """Kim-Wright term premium (FRED). Expectations backed out from DGS10."""
    tp = _fred_series("THREEFYTP10").rename("term_premium")
    y = _fred_series("DGS10").rename("yield")
    df = pd.concat([y, tp], axis=1).dropna()
    df["expectations"] = df["yield"] - df["term_premium"]
    return df.reset_index()[["date", "yield", "expectations", "term_premium"]]


def fetch_acm() -> pd.DataFrame:
    """ACM decomposition (New York Fed .xls).

    The workbook's 'ACM Daily' sheet carries, for each tenor n:
        ACMY{n}    fitted yield
        ACMTP{n}   term premium
        ACMRNY{n}  risk-neutral (expectations) yield
    We take the 10-year columns. read_excel needs xlrd for the legacy .xls.
    """
    r = requests.get(NYFED_ACM_XLS, timeout=_TIMEOUT)
    r.raise_for_status()
    raw = pd.read_excel(io.BytesIO(r.content), sheet_name=0)
    raw.columns = [str(c).strip().upper() for c in raw.columns]
    date_col = "DATE" if "DATE" in raw.columns else raw.columns[0]
    out = pd.DataFrame({
        "date": pd.to_datetime(raw[date_col]),
        "yield": pd.to_numeric(raw["ACMY10"], errors="coerce"),
        "expectations": pd.to_numeric(raw["ACMRNY10"], errors="coerce"),
        "term_premium": pd.to_numeric(raw["ACMTP10"], errors="coerce"),
    }).dropna()
    # NY Fed publishes these in percent already; guard against a decimal file.
    if out["yield"].abs().median() < 1.0:
        out[["yield", "expectations", "term_premium"]] *= 100.0
    return out.sort_values("date").reset_index(drop=True)


def fetch_demo(years: int = 20, seed: int = 7) -> pd.DataFrame:
    """Synthetic but plausible history so the pipeline runs offline.

    Expectations follow a slow mean-reverting path; the term premium is a
    separate slower process that spends time negative (as it genuinely did
    across much of 2016-2021). This is FAKE DATA and the note generator stamps
    it as such — never present demo output as a real market read.
    """
    rng = np.random.default_rng(seed)
    end = pd.Timestamp.today().normalize()
    idx = pd.bdate_range(end=end, periods=years * 252)
    n = len(idx)

    def ou(mu, theta, sigma, x0):
        x = np.empty(n)
        x[0] = x0
        for i in range(1, n):
            x[i] = x[i - 1] + theta * (mu - x[i - 1]) + sigma * rng.standard_normal()
        return x

    expectations = ou(mu=2.6, theta=0.004, sigma=0.03, x0=3.2)
    term_premium = ou(mu=0.3, theta=0.0025, sigma=0.025, x0=1.4)
    yld = expectations + term_premium
    return pd.DataFrame({
        "date": idx,
        "yield": yld.round(3),
        "expectations": expectations.round(3),
        "term_premium": term_premium.round(3),
    })


def load(source: str = "acm", lookback_years: int | None = None) -> pd.DataFrame:
    """Entry point. source in {'acm', 'kw', 'demo'}."""
    source = source.lower()
    if source == "acm":
        df = fetch_acm()
    elif source == "kw":
        df = fetch_kw()
    elif source == "demo":
        df = fetch_demo()
    else:
        raise ValueError(f"unknown source {source!r} (use acm, kw or demo)")

    if lookback_years:
        cutoff = df["date"].max() - pd.DateOffset(years=lookback_years)
        df = df[df["date"] >= cutoff].reset_index(drop=True)
    return df
