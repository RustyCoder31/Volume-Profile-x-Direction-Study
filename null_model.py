import pandas as pd
from model.loader import load_all, load_day_data, skip_reason
from model.triggers import find_touches



def race(day_df, touch_time, up, target_pct=0.2, stop_pct=0.2, window=60):

    entry = day_df.iloc[touch_time]["Open"]

    target, stop = entry * target_pct / 100, entry * stop_pct / 100     # percent of the entry price

    outcome, move = "TIMEOUT", None
    last = min(touch_time + window, len(day_df)) - 1
    for j in range(touch_time, last + 1):
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

    return outcome , last


def both_races(day_df, touches):

    rows=[]
    for _, tc in touches.iterrows():
            if pd.isna(tc["expected"]):
                continue                                   # BOTH bars have no direction                                # a trial is still running
            start = day_df.index.get_loc(tc["time"]) + 1
            if start >= len(day_df):
                continue
            touch_time = start

            for up in [True, False]:
                outcome , last_bar  = race(day_df, touch_time, up)
                if up:
                    up_results = outcome
                    last_up = last_bar
                else:
                    down_results = outcome   
                    last_down = last_bar

            if tc["expected"] == "up":
                real_result = up_results
            else:
                real_result = down_results

            rows.append({"start": day_df.index[start], "entry_time":touch_time, "level": tc["level"],
                       "shape": tc["shape"], "up_result": up_results, "last_up": last_up, "down_result": down_results, "last_down": last_down,
                       "expected": tc["expected"],
                       "real result": real_result,})   
    
    return pd.DataFrame(rows)

def walk(table, directions):
    trials = []
    last = None
    for (_, row), d in zip(table.iterrows(), directions):
        if last is not None and row["entry_time"] <= last + 1:
            continue                                  # a trial is still running
        if d == "up":
            result, last = row["up_result"], row["last_up"]
        else:
            result, last = row["down_result"], row["last_down"]
        trials.append({"start": row["start"], "level": row["level"],
                       "shape": row["shape"], "direction": d, "result": result})
    return pd.DataFrame(trials)


   

if __name__ == "__main__":
    df = load_all("data\\raw data NQ.csv")
    all_trials = []
    for day in pd.bdate_range("2026-10-26", "2026-11-03").strftime("%Y-%m-%d"):
        day_df = load_day_data(day, df)
        if skip_reason(day, day_df):
            continue
        touches = find_touches(day_df)
        table = both_races(day_df, touches)
        all_trials.append(walk(table, table["expected"]))
    all_trials = pd.concat(all_trials)
    print(len(all_trials))
    print(all_trials["result"].value_counts())