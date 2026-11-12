from model.loader import load_all, load_day_data, skip_reason
import pandas as pd
from model.triggers import find_touches
from null_model import both_races, walk
import numpy as np


def build_big_table(df, days):
    tables = []
    for day in days:
        day_df = load_day_data(day, df)
        if skip_reason(day, day_df):
            continue
        touches = find_touches(day_df)
        table = both_races(day_df, touches)
        table["day"] = day
        tables.append(table)
    return pd.concat(tables, ignore_index=True)


def walk_all_days(big, directions):
    all_trials = []
    for day, part in big.groupby("day"):
        all_trials.append(walk(part, directions[part.index]))
    return pd.concat(all_trials, ignore_index=True)

def pass_rate(trials):
    counts = trials["result"].value_counts()
    p, f = counts.get("PASS", 0), counts.get("FAIL", 0)
    return p / (p + f)



def luck_rates(big, n=1000):
    rates = []
    for _ in range(n):
        shuffled = np.random.permutation(big["expected"].values)
        rates.append(pass_rate(walk_all_days(big, shuffled)))
    return rates


if __name__ == "__main__":
    df = load_all("data\\NQ 2022-2026")
    days = pd.bdate_range("2022-01-03", "2023-12-31").strftime("%Y-%m-%d")
    big = build_big_table(df, days)
    big.to_pickle("Results\\null_big_table_explore.pkl")

    real = walk_all_days(big, big["expected"].values)
    print("real:", len(real), real["result"].value_counts().to_dict(), round(pass_rate(real), 4))
    real_rate = pass_rate(real)

    rates = luck_rates(big, 1000)
    low, high = np.percentile(rates, [2.5, 97.5])

    print("real:", round(real_rate, 3))
    print("luck band:", round(low, 3), "to", round(high, 3), "from", len(rates), "runs")
    if real_rate > high:
        print("real is ABOVE the band")
    elif real_rate < low:
        print("real is BELOW the band")
    else:
        print("real is INSIDE the band")

