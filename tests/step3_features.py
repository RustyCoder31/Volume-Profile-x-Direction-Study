import pandas as pd

t = pd.read_csv("Results\\trials_explore_fixed.csv")
t = t[(t["mode"] == "Live") & (t["target_type"] == "fixed")].copy()

start = pd.to_datetime(t["start"], utc=True).dt.tz_convert("America/New_York")
t["minutes"] = start.dt.hour * 60 + start.dt.minute - 570
t["side"] = t["approach_5"].map({"above": 1, "below": -1, "at": 0})
t["atr_pct"] = t["atr_5m"] / t["entry"] * 100

F = t[["day", "upper_pct", "shape_age", "side", "minutes", "atr_pct"]]
print(F.shape)
print(F.describe().round(2))
F.to_csv("Results\\step3_features.csv", index=False)