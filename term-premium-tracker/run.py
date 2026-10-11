#!/usr/bin/env python3
"""US 10-year Treasury term premium tracker.

Decomposes the 10y yield into an expectations component and a term premium,
tracks where the term premium sits in its own history, attributes recent yield
moves to each driver, and writes a monthly note with the numbers filled in and
the judgement left blank.

Examples
--------
    python run.py                         # ACM (NY Fed), full history
    python run.py --source kw             # Kim-Wright (FRED), keyless
    python run.py --demo                  # offline synthetic data, no network
    python run.py --lookback-years 10 --author "Your Name"
"""
import argparse
import pathlib

from tptracker import data, charts, note, decompose


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", choices=["acm", "kw", "demo"], default="acm",
                   help="acm = NY Fed Adrian-Crump-Moench (default); "
                        "kw = Kim-Wright via FRED; demo = offline synthetic")
    p.add_argument("--demo", action="store_true",
                   help="shortcut for --source demo")
    p.add_argument("--lookback-years", type=int, default=None,
                   help="trim history to the last N years")
    p.add_argument("--rolling-window", type=int, default=60,
                   help="trading-day window for the rolling driver chart")
    p.add_argument("--author", default="analyst",
                   help="name stamped on the generated note")
    p.add_argument("--out", default=".", help="output directory root")
    args = p.parse_args()

    source = "demo" if args.demo else args.source
    root = pathlib.Path(args.out)
    charts_dir = root / "charts"
    notes_dir = root / "notes"

    print(f"Loading {source.upper()} data ...")
    df = data.load(source, lookback_years=args.lookback_years)
    print(f"  {len(df):,} observations, {df['date'].min().date()} "
          f"to {df['date'].max().date()}")

    latest = decompose.latest(df)
    print(f"  10y {latest['yield']:.2f}%  =  "
          f"expectations {latest['expectations']:.2f}%  +  "
          f"term premium {latest['term_premium']:.2f}%")

    print("Building charts ...")
    for path in charts.build_all(df, charts_dir, args.rolling_window):
        print(f"  {path}")

    print("Writing note ...")
    note_path = note.build_note(df, source, args.author, notes_dir,
                                is_demo=(source == "demo"))
    print(f"  {note_path}")
    print("Done.")


if __name__ == "__main__":
    main()
