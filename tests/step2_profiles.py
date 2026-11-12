import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
from model.loader import load_all, load_day_data, skip_reason
from model.volume_profile import volume_profile
from model.profile_shape import profile_shape

df = load_all("data\\NQ 2022-2026")
days = pd.bdate_range("2022-01-03", "2023-12-31").strftime("%Y-%m-%d")

NB = 100                                    # price bins per day
X, kept, upper = [], [], []
for day in days:
    day_df = load_day_data(day, df)
    if skip_reason(day, day_df):
        continue
    cut = pd.Timestamp(day).replace(hour=9, minute=30).tz_localize("America/New_York")
    t = (day_df.index < cut).sum()         # number of bars before 09:30
    vp, poc, vah, val = volume_profile(day_df, t)

    x = (vp.index - vp.index.min()) / (vp.index.max() - vp.index.min())   # price scaled to 0..1
    bins = np.minimum((x * NB).astype(int), NB - 1)
    prof = np.bincount(bins, weights=vp.values, minlength=NB)
    X.append(prof / prof.sum())            # volume as share of the day's total
    kept.append(day)
    upper.append(profile_shape(vp)[1])     # the 60/40 number, for comparing later

X = np.array(X)
print(X.shape)
np.save("Results\\step2_X.npy", X)
pd.DataFrame({"day": kept, "upper_pct": upper}).to_csv("Results\\step2_days.csv", index=False)