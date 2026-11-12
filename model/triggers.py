from model.volume_profile import ProfileWalker
from model.profile_shape import shape_from_pct, shape_labels, shape_age
from model.atr import atr_table, atr_before
import pandas as pd


def touch(bar, vah, val):
    """Which level this bar traded through, or None. Uses the wick, not the close."""
    hit_vah = bar["High"] >= vah >= bar["Low"]
    hit_val = bar["Low"] <= val <= bar["High"]

    if hit_vah and hit_val:
        return "BOTH"
    if hit_vah:
        return "VAH"
    if hit_val:
        return "VAL"
    return None

def expected_direction(shape, level):
    if shape == "P-shaped":
        return "up"
    if shape == "b-shaped":
        return "down"
    return "down" if level == "VAH" else "up"   # D fades at both ends

def zone_positions(day_df, start="09:30", end="11:59"):
    """Positions of the first and last TOUCH bars, found by TIME, not by counting bars.
    Counting breaks when a minute is missing before 09:30 (the session check allows up to 5).
    The session ends 16:00 on the trade day, so the last bar's date is the trade day."""
    day = day_df.index[-1].strftime("%Y-%m-%d")
    tz = "America/New_York"
    try:
        first = day_df.index.get_loc(pd.Timestamp(f"{day} {start}").tz_localize(tz))
        last = day_df.index.get_loc(pd.Timestamp(f"{day} {end}").tz_localize(tz))
    except KeyError as e:
        raise ValueError(f"{day}: the {start} or {end} bar is missing, cannot place the touch zone ({e})") from None
    return first, last


def find_touches(day_df, first=None, last=None):
    """first and last are the positions of the 09:30 and 11:59 bars, the first and last
    TOUCH bars. They are found by time (zone_positions) unless passed in. A trial enters at the
    open of the next bar, so entries run 09:31 to 12:00. Levels come from the bars BEFORE the tested bar."""
    if first is None or last is None:
        z_first, z_last = zone_positions(day_df)
        first = z_first if first is None else first
        last = z_last if last is None else last
    rows = []
    walker = ProfileWalker(day_df)                    # one running profile, shared by labels and touches
    labels = shape_labels(day_df, last, walker)
    atrs = {m: atr_table(day_df, m) for m in (1, 5, 15)}      # ATR(14) on 1, 5 and 15 minute candles
    for i in range(first, last + 1):
        bar = day_df.iloc[i]
        vp = walker.at(i)                               # bars 0 to i-1 only
        vah, val = vp.vah, vp.val
        level = touch(bar, vah, val)
        if level is None:
            continue
        pct = vp.upper_pct
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
                     "shape_age": shape_age(labels, i), "approach_5": approach_side(day_df, i, level_price, 5),
                     "approach_10": approach_side(day_df, i, level_price, 10),
                     "approach_15": approach_side(day_df, i, level_price, 15),})
    return pd.DataFrame(rows)


def approach_side(day_df, i, level_price, lookback):
    if level_price is None:
        return None                                   # BOTH touch, no single level

    closes = day_df["Close"].iloc[i - lookback : i]
    above = (closes > level_price).sum()
    below = (closes < level_price).sum()

    if above > below:
        return "above"
    if below > above:
        return "below"  
    return "at"
    
    

if __name__ == "__main__":
    import sys
    from model.loader import load_all, load_day_data
    if len(sys.argv) != 3:
        sys.exit('usage: python triggers.py <data file> <day YYYY-MM-DD>')
    day_df = load_day_data(sys.argv[2], load_all(sys.argv[1]))
    print(find_touches(day_df).to_string())
