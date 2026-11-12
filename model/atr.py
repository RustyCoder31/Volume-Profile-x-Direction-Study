import pandas as pd


def atr_table(day_df, minutes, length=14):
    """ATR(length) on `minutes`-minute candles, plain average of the last `length` true ranges.
    True range = the biggest of high-low, |high - previous close|, |low - previous close|.
    The result is indexed by the candle END time (open time + minutes), so a value is only
    available once its candle is complete."""
    if minutes == 1:
        c = day_df[["High", "Low", "Close"]]
    else:
        c = day_df.resample(f"{minutes}min").agg({"High": "max", "Low": "min", "Close": "last"}).dropna()
    prev = c["Close"].shift(1)
    tr = pd.concat([c["High"] - c["Low"], (c["High"] - prev).abs(), (c["Low"] - prev).abs()], axis=1).max(axis=1)
    atr = tr.rolling(length).mean()
    atr.index = atr.index + pd.Timedelta(minutes=minutes)
    return atr


def atr_before(atr, time):
    """The ATR of the last candle that was complete before the bar at `time` opened."""
    pos = atr.index.searchsorted(time, side="right") - 1
    return float(atr.iloc[pos]) if pos >= 0 else float("nan")
