import streamlit as st
import altair as alt
import plotly.graph_objects as go
import pandas as pd
from model.loader import load_day_data, load_all, skip_reason
from model.volume_profile import volume_profile
from model.profile_shape import profile_shape
from plotly.subplots import make_subplots
from model.triggers import find_touches
from model.trails import run_trials
from model_frozen.frozen_trails import run_trials_frozen
from model_frozen.frozen import find_touches_frozen

df = load_all("raw data NQ.csv")

day_df = load_day_data("2026-10-30", df)
# touches = find_touches(day_df) 

touches = find_touches_frozen(day_df, freeze="both")  # freeze="live", "levels", or "both"
# trials = run_trials(day_df, touches, stall=30)
trials = run_trials_frozen(day_df, touches, stall=30, target_rule="opposite")

st.header("Intraday Candlestick Chart")

if "t" not in st.session_state:
    st.session_state.t = 931

def step(n):
    st.session_state.t = min(max(st.session_state.t + n, 1), len(day_df))

c1, c2, c3 = st.columns(3)
c1.button("Prev", on_click=step, args=(-1,))
c2.button("Next", on_click=step, args=(1,))
c3.button("Go to 09:30", on_click=lambda: st.session_state.update(t=931))

t = st.slider("Bar", 1, len(day_df), key="t")

shown = day_df.iloc[:t]
st.caption(f"{shown.index[-1]:%a %d %b %H:%M} New York, bar {t} of {len(day_df)}")

vp_df, poc, vah, val = volume_profile(day_df, t)
shape, upper_pct = profile_shape(vp_df)
touches_at_t = touches[touches["time"] <= shown.index[-1]]

go_fig = make_subplots(rows=1, cols=2, shared_yaxes=True,
                       column_widths=[0.9, 0.1], horizontal_spacing=0.01)

go_fig.add_trace(go.Candlestick(x=shown.index,
                open=shown['Open'],
                high=shown['High'],
                low=shown['Low'],
                close=shown['Close']), row=1, col=1)
go_fig.update_layout(title='Intraday Candlestick Chart' ,xaxis_title='Time', yaxis_title='Price', xaxis_rangeslider_visible=False, showlegend=False)
go_fig.update_xaxes(range=[day_df.index[0], day_df.index[-1]], row=1, col=1)
go_fig.add_hline(y = vah, line_dash="solid", line_color="green", annotation_text=f"VAH {vah}", annotation_position="top right")
go_fig.add_hline(y = val, line_dash="solid", line_color="red", annotation_text=f"VAL {val}", annotation_position="bottom right")
go_fig.add_hline(y = poc, line_dash="solid", line_color="blue", annotation_text=f"POC {poc}", annotation_position="top right")

colors = ["orange" if val <= p <= vah else "lightgray" for p in vp_df.index]
go_fig.add_trace(go.Bar(x=vp_df.values, y=vp_df.index, orientation="h",
                        marker_color=colors, marker_line_width=0, width=0.25),
                 row=1, col=2)
go_fig.add_annotation(x=0.02, y=0.98, xref="paper", yref="paper", xanchor="left", text=f"Profile Shape: {shape}, {upper_pct:.1f}%", showarrow=False, font=dict(size=12))

# vah_hits = touches_at_t[touches_at_t["level"] == "VAH"]
# val_hits = touches_at_t[touches_at_t["level"] == "VAL"]

# go_fig.add_trace(go.Scatter(x=vah_hits["time"], y=vah_hits["level_price"], mode="markers",
#                             marker=dict(symbol="triangle-up", color="green", size=9)),
#                  row=1, col=1)
# go_fig.add_trace(go.Scatter(x=val_hits["time"], y=val_hits["level_price"], mode="markers",
#                             marker=dict(symbol="triangle-down", color="red", size=9)),
#                  row=1, col=1)

now = shown.index[-1]
started = trials[trials["start"] <= now].copy()
started["status"] = started["outcome"].where(started["resolved"] <= now, "RUNNING")
started.loc[started["status"] == "RUNNING", ["move", "resolved"]] = None
started.loc[started["end"] > now, ["max_reach", "reached_tier2", "end"]] = None   # still tracking

status_colors = {"PASS": "green", "FAIL": "red", "RUNNING": "orange",
                 "TIMEOUT": "gray", "AMBIGUOUS": "purple"}
go_fig.add_trace(go.Scatter(x=started["start"], y=started["entry"], mode="markers",
                            marker=dict(symbol="diamond", size=11,
                                        color=[status_colors[s] for s in started["status"]],
                                        line=dict(width=1, color="black")),
                            hovertext=started["shape"] + " " + started["upper_pct"].astype(str) + "%"),
                 row=1, col=1)

st.plotly_chart(go_fig, use_container_width=True)

st.dataframe(started[["start", "level", "shape", "upper_pct", "expected", "shape_age", "entry", 
                      "status", "move", "approach_5", "approach_10", "approach_15",
                      "max_reach", "reached_tier2", "resolved", "end"]])