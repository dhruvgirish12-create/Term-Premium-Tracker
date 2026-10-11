# US 10-Year Term Premium Tracker

Decomposes the US 10-year Treasury yield into the two things hiding inside it:

    10y yield  =  expectations  +  term premium

- **expectations** — the risk-neutral average of expected future short rates
  (what the market thinks the Fed path will be)
- **term premium** — the extra yield demanded for holding duration rather than
  rolling short bills (compensation for rate risk)

A headline yield of "10y at 4.3%" tells you nothing about *why*. This tool tells
you whether a move in the long end was the market repricing the **policy path**
or repricing the **term premium** — two very different stories with different
implications for a bond allocation.

## What it produces

Four charts (`charts/`) and one monthly note (`notes/YYYY-MM-long-end.md`):

1. **Decomposition** — the yield split into its two components through time
2. **Term-premium history** — the term premium with its current percentile marked
3. **Attribution** — the change in yield over 1m/3m/6m/12m split by driver
4. **Rolling driver** — a rolling read of which component is moving the long end

The note fills in every **number** and leaves every **judgement** blank. It will
tell you the term premium is at the 78th percentile; it will not tell you what
that means. That sentence is yours to write — which is the point if the note
carries your name.

## Data

No API key required.

| `--source` | Model | Where from |
|------------|-------|------------|
| `acm` (default) | Adrian–Crump–Moench | New York Fed `.xls` — gives fitted yield, risk-neutral yield and term premium directly, so the decomposition is exact |
| `kw` | Kim–Wright | FRED keyless CSV (`THREEFYTP10` + `DGS10`); expectations backed out as yield − term premium |
| `demo` | — | synthetic ~20y history, runs fully offline; every output is stamped DEMO |

ACM and KW are different models. They correlate closely and agree on direction;
where a point depends on the *level* rather than the *direction*, say which model
you used. If the NY Fed file location or format ever shifts, fall back to
`--source kw`.

## Run it

```bash
pip install -r requirements.txt
python run.py                          # ACM, full history
python run.py --source kw              # Kim-Wright (keyless, no xlrd needed)
python run.py --demo                   # offline, synthetic
python run.py --lookback-years 10 --author "Your Name" --out .
```

## Layout

```
run.py                 CLI
tptracker/
  data.py              fetchers (ACM / KW / demo) -> one tidy frame
  decompose.py         percentiles + attribution of yield moves
  charts.py            the four PNGs
  note.py              the monthly note (numbers in, judgement out)
```

## Method notes / caveats

- The decomposition of a *change* is exact: d(yield) = d(expectations) + d(term
  premium). No estimation error is introduced by this tool — it inherits
  whatever the underlying model (ACM or KW) assumes.
- Term premium estimates are **model-dependent**, not observed. Treat the level
  with humility; the direction and the attribution are the robust parts.
- `demo` data is fabricated for testing and is labelled as such everywhere it
  appears. Never present it as a market read.
