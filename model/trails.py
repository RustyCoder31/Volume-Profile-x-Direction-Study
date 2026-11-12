
import pandas as pd
from model.volume_profile import ProfileWalker

def crosses_value_area(level, expected):
    """True when the expected move travels across the value area to the other edge:
    P at VAL (up), b at VAH (down), D at both ends. False for P at VAH and b at VAL,
    which leave the value area, so there is no opposite level in their direction."""
    return (level == "VAL" and expected == "up") or (level == "VAH" and expected == "down")


def run_trials(day_df, touches, target_pct=0.2, stop_pct=0.2, window=60, stall=None, tier2_pct=0.3,
               block_until_tracked=False, target_rule="atr", min_target_pct=0.2, max_target_pct=0.33,
               atr_k=1.0, atr_col="atr_5m"):
    """One trial at a time. A trial starts at the OPEN of the bar after the touch bar,
    and ends at +target (pass), -stop (fail), or after `window` bars (timeout).
    Touches that happen while a trial is running are ignored.

    stall=None: a trial ends at its result (old behaviour).
    stall=30: after a PASS the trial keeps being tracked. Each new farthest point resets
    a clock, and tracking ends when `stall` bars pass with no new farthest point, when
    price comes back to the entry, or when the session ends. The score stays +target;
    max_reach and reached_tier2 are saved.
    block_until_tracked=False: the next trial may open right after the PASS while the
    old one is still tracked (trials can overlap). True: the next trial waits until
    tracking ends.
    Tier 2 line = tier2_pct percent of the entry price (0.3 percent is about 86 points
    at NQ 28,700, about 49 at 16,400), so every year is held to the same standard.
    `resolved` is the bar of the PASS/FAIL/TIMEOUT, `end` is the end of tracking.

    Distances are percents of the ENTRY price, not points: target_pct and stop_pct (0.2 means
    0.2 percent, about 58 points at NQ 29,000 and about 25 at 12,400). `target`, `target_start`
    and `move` are saved in points.

    target_rule="fixed": every trial uses `target_pct` and `stop_pct` (technique 1).
    target_rule="opposite" (technique 2): a touch that crosses the value area aims at the
    LIVE opposite level. On every bar of the trial the target is the distance from the
    ENTRY to the opposite level, read from the profile of the bars before that bar and
    clamped to min_target_pct..max_target_pct of the entry price (0.2 to 0.33 percent), so the
    target moves until it is reached. The stop stays fixed at `stop_pct`. Touches that leave the
    value area (P at VAH, b at VAL) use the fixed `target_pct` and `stop_pct`. `target_start` is the target on the first bar,
    `target` is the one in force on the last bar checked (the one that was hit on a PASS),
    and a PASS scores +target.

    target_rule="atr" (technique 3): every trial uses target = stop = atr_k times the ATR(14)
    at the touch, from the touches column named by `atr_col` ("atr_5m" by default, or "atr_15m",
    or "atr_1m"). No clamp. The 1, 5 and 15 minute ATRs are saved on every trial whatever the rule."""
    live = {}                                          # bar position -> (vah, val), built only when needed
    walker = None                                      # running volume profile, made on first use
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
        moving = target_rule == "opposite" and crosses_value_area(tc["level"], tc["expected"])
        target_start = None

        outcome, move = "TIMEOUT", None
        last = min(start + window, len(day_df)) - 1
        for j in range(start, last + 1):
            bar = day_df.iloc[j]
            if moving:
                # the target follows the live opposite level, from the profile of bars before j
                if j not in live:
                    if walker is None:
                        walker = ProfileWalker(day_df)
                    p = walker.at(j)
                    live[j] = (p.vah, p.val)
                opposite = live[j][0] if up else live[j][1]          # up trade aims at VAH, down at VAL
                dist = opposite - entry if up else entry - opposite
                target = min(max(dist, min_target), max_target)      # behind the entry clamps to the minimum
                if target_start is None:
                    target_start = target
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
                       "shape": tc["shape"], "upper_pct": tc["upper_pct"],"shape_age": tc["shape_age"],
                       "expected": tc["expected"], "entry": entry,
                       "target_start": target_start if moving else target, "target": target,
                       "atr_1m": tc["atr_1m"], "atr_5m": tc["atr_5m"], "atr_15m": tc["atr_15m"],
                       "outcome": outcome, "move": move, "approach_5": tc["approach_5"],
                       "approach_10": tc["approach_10"], "approach_15": tc["approach_15"],
                       "max_reach": max_reach, "reached_tier2": reached_tier2,
                       "resolved": resolved, "end": end})
    return pd.DataFrame(trials)