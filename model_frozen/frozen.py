"""Variants Live, C and D of the touch finder, kept apart from triggers.py.

freeze="live"   Live: VAH/VAL and the shape are re-read from the profile of the bars before every bar.
freeze="levels" C:    VAH/VAL are frozen at the 09:30 profile (bars through 09:29), the shape stays live.
freeze="both"   D:    VAH/VAL and the shape are all frozen at the 09:30 profile.

The frozen profile is the profile of bars[:first], so it uses no bar from 09:30 on (no lookahead).
Rows have the same columns as find_touches. Under D the shape never changes, so `shape_age` is the
number of bars since 09:30. `opposite_price` is the frozen opposite level under C and D, which is
what technique 2 aims at when the trials are run with frozen_trails.run_trials_frozen."""
import pandas as pd
from model.volume_profile import ProfileWalker
from model.profile_shape import shape_from_pct, shape_labels, shape_age
from model.atr import atr_table, atr_before
from model.triggers import touch, expected_direction, approach_side, zone_positions

FREEZES = ("live", "levels", "both")


def find_touches_frozen(day_df, freeze="levels", first=None, last=None):
    if first is None or last is None:                   # found by time, see triggers.zone_positions
        z_first, z_last = zone_positions(day_df)
        first = z_first if first is None else first
        last = z_last if last is None else last
    if freeze not in FREEZES:
        raise ValueError(f"freeze must be one of {FREEZES}, got {freeze!r}")
    rows = []
    walker = ProfileWalker(day_df)
    frozen = walker.at(first)                           # profile of bars 0 to first-1
    labels = shape_labels(day_df, last, walker)
    atrs = {m: atr_table(day_df, m) for m in (1, 5, 15)}
    for i in range(first, last + 1):
        bar = day_df.iloc[i]
        vp = walker.at(i)                               # bars 0 to i-1 only
        vah, val = (vp.vah, vp.val) if freeze == "live" else (frozen.vah, frozen.val)
        level = touch(bar, vah, val)
        if level is None:
            continue
        if freeze == "both":
            pct, age = frozen.upper_pct, i - first
        else:
            pct, age = vp.upper_pct, shape_age(labels, i)
        shape = shape_from_pct(pct)
        level_price = vah if level == "VAH" else val if level == "VAL" else None
        opposite_price = val if level == "VAH" else vah if level == "VAL" else None
        rows.append({"time": day_df.index[i], "level": level,
                     "level_price": level_price, "opposite_price": opposite_price,
                     "atr_1m": atr_before(atrs[1], day_df.index[i]),
                     "atr_5m": atr_before(atrs[5], day_df.index[i]),
                     "atr_15m": atr_before(atrs[15], day_df.index[i]),
                     "shape": shape, "upper_pct": round(pct, 1),
                     "expected": expected_direction(shape, level) if level != "BOTH" else None,
                     "shape_age": age, "approach_5": approach_side(day_df, i, level_price, 5),
                     "approach_10": approach_side(day_df, i, level_price, 10),
                     "approach_15": approach_side(day_df, i, level_price, 15)})
    return pd.DataFrame(rows)
