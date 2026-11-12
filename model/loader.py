import pandas as pd
import streamlit as st

@st.cache_data
def load_all(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()

    df['time'] = pd.to_datetime(df['time']).dt.tz_localize('UTC').dt.tz_convert('America/New_York')

    return df


def session_window(day):
    d = pd.Timestamp(day)                                    # plain date, no time zone yet
    start = (d - pd.Timedelta(days=1)).replace(hour=18).tz_localize('America/New_York')
    end = d.replace(hour=16).tz_localize('America/New_York')
    return start, end


def skip_reason(day, day_df):
    # returns None if the day is a good session, else a short reason
    start, end = session_window(day)
    if len(day_df) == 0:
        return "no data"
    if day_df.index[0] != start:
        return "late start (first bar " + str(day_df.index[0]) + ")"
    if day_df.index[-1] != end:
        return "early end (last bar " + str(day_df.index[-1]) + ")"

    full = pd.date_range(start, end, freq='min')       # every minute that should exist
    missing = full.difference(day_df.index)            # the ones that are not in the data
    if len(missing) > 5:
        return "too many missing (" + str(len(missing)) + ")"

    d = pd.Timestamp(day)
    zone_start = d.replace(hour=9, minute=30).tz_localize('America/New_York')
    zone_end = d.replace(hour=13).tz_localize('America/New_York')
    if ((missing >= zone_start) & (missing <= zone_end)).any():
        return "hole in trial zone"
    return None


def load_day_data(day, df):
    start, end = session_window(day)


    day_df = df[(df['time'] >= start) & (df['time'] <= end)].copy()

    day_df.set_index('time', inplace=True)
    day_df.index.name = 'Date'  

    day_df = day_df.rename(columns={
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    })

    return day_df