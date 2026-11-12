import pandas as pd




cols = ["day","mode","target_type","start","level","shape","upper_pct","shape_age","expected","approach_5"]
t = pd.read_csv("Results/trials_explore_fixed.csv", usecols=cols)
t = t[(t["mode"] == "Live") & (t["target_type"] == "fixed")]
print(len(t))   # must print 2753

print("Shape\n",t["shape"].value_counts())

print("Level\n",t["level"].value_counts())

print("Approach 5\n",t["approach_5"].value_counts())


h = pd.to_datetime(t["start"], utc=True).dt.tz_convert("America/New_York").dt.hour
print(h.value_counts().sort_index())


print(pd.crosstab(t["shape"], t["level"]))


import matplotlib.pyplot as plt
plt.hist(t["upper_pct"], bins=40)
plt.axvline(40); plt.axvline(60)
plt.savefig("upper_pct_hist.png")