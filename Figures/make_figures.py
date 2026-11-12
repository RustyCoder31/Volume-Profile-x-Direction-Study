"""Paper figures for the Volume Profile x Direction study. Run from the project folder:
    .vpxdir\\Scripts\\python.exe Figures\\make_figures.py
Reads only existing result files and the price data. Writes PNG (300 dpi) and PDF to Figures.
Pass rate = PASS / (PASS + FAIL). Band = 1.96 * sqrt(p(1-p)/n) around the observed rate (normal approx)."""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, ROOT)
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from model.loader import load_all, load_day_data
from model.volume_profile import volume_profile
from model.profile_shape import profile_shape

OUT = "Figures"
INK, SOFT, BLUE, RED, GREEN = "#2E2C27", "#8A887F", "#2C6E9B", "#B5483A", "#3E7D5A"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": INK, "axes.labelcolor": INK,
                     "text.color": INK, "xtick.color": INK, "ytick.color": INK})
BREAK_EVEN = 51.4   # assumed, not measured


def save(fig, name):
    fig.savefig(f"{OUT}/{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(f"{OUT}/{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def live_fixed(path):
    t = pd.read_csv(path)
    return t[(t["mode"] == "Live") & (t["target_type"] == "fixed")].copy()


def rate(sub):
    w, l = (sub["outcome"] == "PASS").sum(), (sub["outcome"] == "FAIL").sum()
    n = w + l
    p = 100 * w / n
    return p, 196 * np.sqrt((p / 100) * (1 - p / 100) / n), n


# ---------- Figure 1: what P, D and b profiles look like (real days) ----------
days = pd.read_csv("Results/step2_days.csv")
picks = [("P-shaped", 70), ("D-shaped", 50), ("b-shaped", 30)]
df = load_all("data\\NQ 2022-2026")
fig, axes = plt.subplots(1, 3, figsize=(11, 4.4), gridspec_kw={"wspace": 0.45})
for ax, (name, target) in zip(axes, picks):
    row = days.iloc[(days["upper_pct"] - target).abs().argsort().iloc[0]]
    day = row["day"]
    day_df = load_day_data(day, df)
    cut = pd.Timestamp(day).replace(hour=9, minute=30).tz_localize("America/New_York")
    t = (day_df.index < cut).sum()
    vp, poc, vah, val = volume_profile(day_df, t)
    shape, up = profile_shape(vp)
    step = 2.0                                       # plot in 2 point rows
    agg = vp.groupby(np.floor(vp.index / step) * step).sum()
    ax.barh(agg.index, agg.values, height=step * 0.9, color=SOFT, alpha=0.55, linewidth=0)
    inva = agg[(agg.index >= val - step) & (agg.index <= vah)]
    ax.barh(inva.index, inva.values, height=step * 0.9, color=BLUE, alpha=0.85, linewidth=0)
    mid = (vp.index.max() + vp.index.min()) / 2
    ax.axhline(mid, color=INK, lw=0.8, ls=":")
    ax.axhline(poc, color=RED, lw=1.2)
    xmax = ax.get_xlim()[1]
    ax.set_xlim(0, xmax * 1.18)
    for lvl, lab in ((vah, "VAH"), (val, "VAL")):
        ax.axhline(lvl, color=GREEN, lw=1.2, ls="--")
        ax.text(xmax * 1.17, lvl, lab, va="bottom", ha="right", color=GREEN, fontsize=8)
    ax.text(xmax * 1.17, poc, "POC", va="bottom", ha="right", color=RED, fontsize=8)
    ax.set_title(f"{shape}, {day}\n{up:.0f}% of volume in upper half", fontsize=10)
    ax.set_xlabel("Volume (contracts)")
    ax.set_xticks([])
axes[0].set_ylabel("Price (NQ points)")
fig.suptitle("Overnight volume profile up to 09:30 New York, three real days", y=1.02, fontsize=11)
fig.text(0.5, -0.04, "Blue = value area (70% of volume). Dotted line = midpoint of the range. "
         "Rule: more than 60% above the midpoint is P, less than 40% is b, otherwise D.",
         ha="center", fontsize=8, color=SOFT)
save(fig, "fig1_profile_shapes")

# ---------- Figure 2: the shape number is one smooth spread ----------
feat = pd.read_csv("Results/step3_features.csv")
fig, ax = plt.subplots(figsize=(6.4, 3.8))
ax.hist(feat["upper_pct"], bins=40, color=BLUE, alpha=0.8, edgecolor="white")
for x in (40, 60):
    ax.axvline(x, color=RED, ls="--", lw=1.2)
top = ax.get_ylim()[1] * 0.97
ax.text(40, top, "b | D ", color=RED, fontsize=9, ha="right")
ax.text(60, top, " D | P", color=RED, fontsize=9)
ax.set_xlabel("Share of overnight volume above the midpoint (%)")
ax.set_ylabel("Number of touches")
ax.set_title(f"P, D and b are cut-offs on one spread, not separate groups\n(n = {len(feat):,} touches, 2022 to 2023)", fontsize=9.5)
save(fig, "fig2_upper_pct_histogram")

# ---------- Figure 3: pass rate by shape, explore and sealed 2026 ----------
ex = live_fixed("Results/trials_explore_fixed.csv")
se = live_fixed("Results/trials_sealed2026.csv")
groups = [("All", None), ("P", "P-shaped"), ("b", "b-shaped"), ("D", "D-shaped")]
fig, ax = plt.subplots(figsize=(7.2, 4))
width = 0.36
for k, (data, lab, col) in enumerate(((ex, "Explore 2022 to 2023", BLUE), (se, "Sealed 2026", RED))):
    ps, es = [], []
    for _, shp in groups:
        sub = data if shp is None else data[data["shape"] == shp]
        p, e, n = rate(sub)
        ps.append(p); es.append(e)
        print(lab, shp, round(p, 2), round(e, 2), n)
    x = np.arange(len(groups)) + (k - 0.5) * width
    ax.errorbar(x, ps, yerr=es, fmt="o", color=col, capsize=4, label=lab, lw=1.5)
ax.axhline(50, color=SOFT, lw=1)
ax.axhline(BREAK_EVEN, color=GREEN, lw=1, ls="--")
ax.text(-1.3, BREAK_EVEN + 0.25, "break even 51.4%", color=GREEN, fontsize=8, ha="left")
ax.text(-1.3, 50 - 0.9, "coin flip 50%", color=SOFT, fontsize=8, ha="left")
ax.set_xlim(-1.35, 3.6); ax.set_ylim(40, 66)
ax.set_xticks(range(len(groups))); ax.set_xticklabels([g[0] for g in groups])
ax.set_ylabel("Pass rate, PASS / (PASS + FAIL), %")
ax.set_title("Pass rate by profile shape, with 95% bands", fontsize=10)
ax.legend(frameon=False, loc="lower left", ncol=1)
save(fig, "fig3_pass_rate_by_shape")

# ---------- Figure 4: 2026 registered predictions (S1 to S7 drawn) ----------
# Values copied from the sealed run result in VP Study Log.md (11-12).
def band(p, n):
    return 196 * np.sqrt(p / 100 * (1 - p / 100) / n)


S = [("S1 all trials", 52.11, 3.26), ("S2 P-shape", 47.24, 5.75), ("S3 b-shape", 56.99, 6.98),
     ("S4 D-shape", 53.24, 4.79), ("S5 pile 1", 53.83, 5.11),
     ("S6 pile 2", 51.97, band(51.97, 279)), ("S7 pile 3", 49.80, band(49.80, 255))]
fig, ax = plt.subplots(figsize=(6.6, 4))
for i, (lab, p, e) in enumerate(S[::-1]):
    ax.errorbar(p, i, xerr=e, fmt="o", color=RED, capsize=4, lw=1.5)
ax.set_yticks(range(len(S))); ax.set_yticklabels([s[0] for s in S[::-1]])
ax.axvline(50, color=SOFT, lw=1); ax.axvline(BREAK_EVEN, color=GREEN, lw=1, ls="--")
ax.set_xlabel("Pass rate in sealed 2026 data (%)")
ax.set_title("Sealed 2026: registered predictions with 95% bands (0 of 8 supported)", fontsize=10)
ax.text(BREAK_EVEN + 0.15, -0.55, "51.4 break even", color=GREEN, fontsize=8)
ax.set_ylim(-0.8, len(S) - 0.4)
fig.text(0.5, -0.12, "S8 (D minus non-D inside pile 2, +7.78, band about plus or minus 23) is a difference, not a pass rate, so it is not drawn.\n"
         "Bands are normal approximations, not the shuffle luck bands.", ha="center", fontsize=7.5, color=SOFT)
save(fig, "fig4_sealed_2026_predictions")

# ---------- Figure 5: what the data could see (power) ----------
n = np.arange(100, 3001, 50)
mde = 2.8 * 100 * 0.5 / np.sqrt(n)          # 80% power, 5% two sided, p = 0.5, in points of pass rate
fig, ax = plt.subplots(figsize=(6.4, 3.9))
ax.plot(n, mde, color=BLUE, lw=2)
ax.axhline(1.4, color=GREEN, ls="--", lw=1.2)
ax.text(3000, 1.6, "edge needed to break even (1.4 points above 50)", color=GREEN, fontsize=8, ha="right")
for nn, lab in ((2686, "full set 2,686"), (300, "pile-sized group 300")):
    y = 2.8 * 50 / np.sqrt(nn)
    ax.plot(nn, y, "o", color=RED)
    ax.annotate(f"{lab}: {y:.1f} pts", (nn, y), xytext=(8, 8), textcoords="offset points", fontsize=8)
ax.set_xlabel("Number of trials (PASS + FAIL)")
ax.set_ylabel("Smallest edge seen with 80% power (points)")
ax.set_title("Small groups could never show a small real edge", fontsize=10)
ax.set_ylim(0, 17)
save(fig, "fig5_power_curve")
