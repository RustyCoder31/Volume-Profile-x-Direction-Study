"""Run every day, every variant, every target type, and save the TRIALS to one CSV.

usage:  python run_all.py <data file> <first day> <last day> <out csv>
e.g.    python run_all.py "raw data NQ.csv" 2026-10-26 2026-11-03 trials_test.csv

Modes:   Live = triggers.py + trails.py (levels and shape re-read every bar)
         C    = frozen.py + frozen_trails.py, freeze="levels" (VAH/VAL frozen at 09:30, shape live)
         D    = frozen.py + frozen_trails.py, freeze="both"   (levels and shape frozen at 09:30)
Targets: fixed (technique 1), opposite (technique 2), atr_5m and atr_15m (technique 3, k=1)
That is 3 x 4 = 12 runs per day. Every trial row gets three extra columns: day, mode, target_type.
Besides the trials CSV it writes <out stem>_daily.csv (trials and total points per day, mode, target type)
and prints total points per mode and target type at the end.

Days that fail the session check (loader.skip_reason) are not run. They are listed in
<out csv stem>_skipped.csv with the reason. A day that raises an error is listed there too
(reason starts with "error:") and the final line says how many, so nothing is dropped quietly."""
import sys
import time
import warnings

import pandas as pd

warnings.filterwarnings("ignore")
from model.loader import load_all, load_day_data, skip_reason
from model.triggers import find_touches
from model.trails import run_trials
from model_frozen.frozen import find_touches_frozen
from model_frozen.frozen_trails import run_trials_frozen

TARGETS = [("fixed", "fixed", {}),
           ("opposite", "opposite", {}),
           ("atr_5m", "atr", {"atr_col": "atr_5m"}),
           ("atr_15m", "atr", {"atr_col": "atr_15m"})]          # (label, target_rule, extra settings)


def run_day(day, day_df, stall=30):
    """All 12 runs for one day. Returns one DataFrame of trials."""
    parts = []
    touches = {"Live": find_touches(day_df),
               "C": find_touches_frozen(day_df, "levels"),
               "D": find_touches_frozen(day_df, "both")}
    for mode, tc in touches.items():
        run = run_trials if mode == "Live" else run_trials_frozen
        for label, rule, kw in TARGETS:
            tr = run(day_df, tc, stall=stall, target_rule=rule, **kw)
            tr.insert(0, "target_type", label)
            tr.insert(0, "mode", mode)
            tr.insert(0, "day", day)
            parts.append(tr)
    return pd.concat(parts, ignore_index=True)


def main(path, first, last, out):
    t0 = time.time()
    df = load_all(path)
    days = pd.bdate_range(first, last)                            # Monday to Friday; holidays fail skip_reason
    results, skipped = [], []
    for n, d in enumerate(days, 1):
        day = d.strftime("%Y-%m-%d")
        try:
            day_df = load_day_data(day, df)
            why = skip_reason(day, day_df)
            if why:
                skipped.append((day, why))
                continue
            results.append(run_day(day, day_df))
        except Exception as e:                                    # keep going, but never hide it
            skipped.append((day, f"error: {type(e).__name__}: {e}"))
            print("ERROR on", day, type(e).__name__, e)
        if n % 50 == 0:
            print(f"{n}/{len(days)} days, {time.time() - t0:.0f}s", flush=True)

    trials = pd.concat(results, ignore_index=True) if results else pd.DataFrame()
    trials.to_csv(out, index=False)
    skip_path = out.rsplit(".", 1)[0] + "_skipped.csv"
    pd.DataFrame(skipped, columns=["day", "reason"]).to_csv(skip_path, index=False)

    errors = sum(1 for _, r in skipped if r.startswith("error:"))
    print(f"days asked {len(days)}, run {len(results)}, skipped {len(skipped) - errors}, errors {errors}")
    print(f"trials {len(trials)} -> {out}   skipped list -> {skip_path}   ({time.time() - t0:.0f}s)")
    if len(trials):
        print(trials.groupby(["mode", "target_type"])["outcome"].value_counts().unstack(fill_value=0))
        print_points(trials)
        daily_path = out.rsplit(".", 1)[0] + "_daily.csv"
        daily = trials.groupby(["day", "mode", "target_type"]).agg(trials=("outcome", "size"), points=("move", "sum"))
        daily.round(2).to_csv(daily_path)                            # one row per day, mode, target type
        print(f"daily totals -> {daily_path}")


def print_points(trials):
    """Immediate difference: trials and total points per mode and target type, then points per day by mode.
    Points = sum of `move` over PASS, FAIL and TIMEOUT (AMBIGUOUS has no move, counts as 0).
    Compare modes inside one target type; points across target types are not the same size."""
    g = trials.groupby(["mode", "target_type"])
    table = g.agg(trials=("outcome", "size"), points=("move", "sum"), avg=("move", "mean"))
    table["pass_rate_%"] = g["outcome"].apply(lambda x: 100 * (x == "PASS").sum() / max(1, x.isin(["PASS", "FAIL"]).sum()))
    print("\ntotal points per mode and target type (days run: %d)" % trials["day"].nunique())
    print(table.round(1).to_string())
    if trials["day"].nunique() <= 40:                              # per-day view only for short runs
        per_day = trials.groupby(["day", "mode"])["move"].sum().unstack("mode")
        print("\npoints per day by mode (all 4 target types added)")
        print(per_day.round(1).to_string())


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])
