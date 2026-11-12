"""Trials for variants C and D (touches from frozen.py), kept apart from trails.py.

Same race as trails.run_trials: a trial starts at the OPEN of the bar after the touch bar and ends at
+target (PASS), -stop (FAIL), after `window` bars (TIMEOUT), or AMBIGUOUS when both barriers sit inside
one 1 minute bar. After a PASS, tracking (`stall`) keeps measuring max_reach and tier 2. Distances are
percents of the ENTRY price. Same columns as trails.run_trials.

The one difference is technique 2 (target_rule="opposite"). The levels are frozen, so the target does not
follow a live profile. A crossing touch (P at VAL, b at VAH, D at both) takes its target ONCE from the
touch row's `opposite_price` (the frozen opposite level): distance from the entry to that level, clamped to
min_target_pct..max_target_pct of the entry price. `target_start` equals `target`. Leaving touches use the
fixed target_pct. The stop is always fixed. "fixed" and "atr" behave exactly as in trails.py.

If this copy and trails.py are ever changed, rerun the check that run_trials_frozen on live touches with
target_rule "fixed" or "atr" equals trails.run_trials."""
import pandas as pd
from model.trails import crosses_value_area


def run_trials_frozen(day_df, touches, target_pct=0.2, stop_pct=0.2, window=60, stall=None, tier2_pct=0.3,
                      block_until_tracked=False, target_rule="atr", min_target_pct=0.2, max_target_pct=0.33,
                      atr_k=1.0, atr_col="atr_5m"):
    trials = []
    busy_until = None
    for _, tc in touches.iterrows():
        if pd.isna(tc["expected"]):
            continue                                   # BOTH bars have no direction
        if busy_until is not None and tc["time"] <= busy_until:
            continue                                   # a trial is still running
        start = day_df.index.get_loc(tc["time"]) + 1
        if start >= len(day_df):
            continue
        entry = day_df.iloc[start]["Open"]
        up = tc["expected"] == "up"

        target, stop = entry * target_pct / 100, entry * stop_pct / 100     # percent of the entry price
        min_target, max_target = entry * min_target_pct / 100, entry * max_target_pct / 100
        if target_rule == "atr":
            if pd.isna(tc[atr_col]):
                continue                               # not enough candles for an ATR
            target = stop = atr_k * tc[atr_col]        # technique 3: same distance both ways, no clamp
        if target_rule == "opposite" and crosses_value_area(tc["level"], tc["expected"]):
            opposite = tc["opposite_price"]            # frozen level, target set once
            dist = opposite - entry if up else entry - opposite
            target = min(max(dist, min_target), max_target)

        outcome, move = "TIMEOUT", None
        last = min(start + window, len(day_df)) - 1
        for j in range(start, last + 1):
            bar = day_df.iloc[j]
            favour = bar["High"] - entry if up else entry - bar["Low"]
            adverse = entry - bar["Low"] if up else bar["High"] - entry
            if favour >= target and adverse >= stop:
                outcome, move = "AMBIGUOUS", None      # both inside one minute
            elif favour >= target:
                outcome, move = "PASS", target
            elif adverse >= stop:
                outcome, move = "FAIL", -stop
            if outcome != "TIMEOUT":
                last = j
                break
        if outcome == "TIMEOUT":
            close = day_df.iloc[last]["Close"]
            move = close - entry if up else entry - close

        resolved = day_df.index[last]
        max_reach, reached_tier2 = None, None
        if outcome == "PASS" and stall is not None:
            # the pass bar already counts as a new farthest point
            bar = day_df.iloc[last]
            farthest = bar["High"] - entry if up else entry - bar["Low"]
            last_new = last
            k = last + 1
            while k < len(day_df) and k - last_new <= stall:
                bar = day_df.iloc[k]
                last = k                                # this bar is still tracked
                if (bar["Low"] <= entry) if up else (bar["High"] >= entry):
                    break                               # price is back at the entry
                favour = bar["High"] - entry if up else entry - bar["Low"]
                if favour > farthest:
                    farthest, last_new = favour, k
                k += 1
            max_reach = farthest
            reached_tier2 = farthest >= entry * tier2_pct / 100

        end = day_df.index[last]
        busy_until = end if block_until_tracked else resolved
        trials.append({"start": day_df.index[start], "level": tc["level"],
                       "shape": tc["shape"], "upper_pct": tc["upper_pct"], "shape_age": tc["shape_age"],
                       "expected": tc["expected"], "entry": entry,
                       "target_start": target, "target": target,
                       "atr_1m": tc["atr_1m"], "atr_5m": tc["atr_5m"], "atr_15m": tc["atr_15m"],
                       "outcome": outcome, "move": move, "approach_5": tc["approach_5"],
                       "approach_10": tc["approach_10"], "approach_15": tc["approach_15"],
                       "max_reach": max_reach, "reached_tier2": reached_tier2,
                       "resolved": resolved, "end": end})
    return pd.DataFrame(trials)
