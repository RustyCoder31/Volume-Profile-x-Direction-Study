from collections import namedtuple

import numpy as np
import pandas as pd


def volume_profile(bars, t, tick=0.25, va_pct=0.70, prefer="up"):
    """bars: session bars with High, Low, Volume columns. t: number of bars shown (bars[:t])."""
    sub = bars.iloc[:t]

    lo = np.round(sub["Low"].to_numpy() / tick).astype(int)
    hi = np.round(sub["High"].to_numpy() / tick).astype(int)
    vol = sub["Volume"].to_numpy(dtype=float)

    base = lo.min()
    rows = np.zeros(hi.max() - base + 1)
    for l, h, v in zip(lo, hi, vol):
        rows[l - base : h - base + 1] += v / (h - l + 1)

    total = rows.sum()
    poc = int(np.argmax(rows))

    bot = top = poc
    enclosed = rows[poc]
    while enclosed < va_pct * total:
        below = rows[bot - 1] if bot > 0 else -1.0
        above = rows[top + 1] if top < len(rows) - 1 else -1.0
        if above > below or (above == below and prefer == "up"):
            top += 1
            enclosed += rows[top]
        else:
            bot -= 1
            enclosed += rows[bot]

    prices = (np.arange(len(rows)) + base) * tick
    return pd.Series(rows, index=prices), prices[poc], prices[top], prices[bot]

Profile = namedtuple("Profile", "poc vah val upper_pct")


class ProfileWalker:
    """The same numbers as volume_profile(bars, t), but built one bar at a time.

    volume_profile rebuilds the whole profile from bars[:t] on every call. This keeps one
    running array of volume per price row and adds each new bar over its Low..High rows with
    the same formula, in the same bar order, so every row holds exactly the same number.
    It also tracks the lowest Low and highest High so far; the rows between them are the
    profile (rows outside are still zero). POC, VAH, VAL and the upper-half share are then
    read from that slice with the same rules as volume_profile and profile_shape.

    at(t) means "the profile of bars[:t]", like volume_profile(bars, t). Asking for a later t
    only adds the new bars. Asking for an earlier t starts over, so it is always correct."""

    def __init__(self, bars, tick=0.25, va_pct=0.70, prefer="up"):
        self.tick, self.va_pct, self.prefer = tick, va_pct, prefer
        self.lo = np.round(bars["Low"].to_numpy() / tick).astype(int).tolist()
        self.hi = np.round(bars["High"].to_numpy() / tick).astype(int).tolist()
        self.vol = bars["Volume"].to_numpy(dtype=float).tolist()
        self.base = min(self.lo)                          # row 0 of the day-long array
        self.rows = np.zeros(max(self.hi) - self.base + 1)
        self._reset()

    def _reset(self):
        self.rows[:] = 0.0
        self.added = 0
        self.low_row = self.high_row = None               # lowest Low / highest High so far, in rows

    def _advance(self, t):
        if t < self.added:
            self._reset()
        rows, base = self.rows, self.base
        low_row, high_row = self.low_row, self.high_row
        for k in range(self.added, t):
            l, h = self.lo[k], self.hi[k]
            rows[l - base : h - base + 1] += self.vol[k] / (h - l + 1)
            if low_row is None or l < low_row:
                low_row = l
            if high_row is None or h > high_row:
                high_row = h
        self.added, self.low_row, self.high_row = t, low_row, high_row

    def _slice(self, t):
        self._advance(t)
        return self.rows[self.low_row - self.base : self.high_row - self.base + 1], self.low_row

    def series(self, t):
        """The same Series volume_profile(bars, t)[0] returns (row volume indexed by price)."""
        rows, first = self._slice(t)
        return pd.Series(rows.copy(), index=(np.arange(len(rows)) + first) * self.tick)

    def at(self, t):
        """Profile(poc, vah, val, upper_pct) for bars[:t]. upper_pct is the share of volume above
        the midpoint of the profile's price range, as profile_shape computes it."""
        rows, first = self._slice(t)
        prices = (np.arange(len(rows)) + first) * self.tick

        total = rows.sum()
        poc = int(np.argmax(rows))
        bot = top = poc
        enclosed = rows[poc]
        while enclosed < self.va_pct * total:
            below = rows[bot - 1] if bot > 0 else -1.0
            above = rows[top + 1] if top < len(rows) - 1 else -1.0
            if above > below or (above == below and self.prefer == "up"):
                top += 1
                enclosed += rows[top]
            else:
                bot -= 1
                enclosed += rows[bot]

        mid_point = (prices.max() + prices.min()) / 2
        upper_pct = rows[prices > mid_point].sum() / total * 100
        return Profile(prices[poc], prices[top], prices[bot], upper_pct)


# day_df = load_day_data()
# VAs = volume_profile(day_df, 1016)

# print(f"POC: {VAs[1]}, VAH: {VAs[2]}, VAL: {VAs[3]}")


if __name__ == "__main__":
    VAs = volume_profile()