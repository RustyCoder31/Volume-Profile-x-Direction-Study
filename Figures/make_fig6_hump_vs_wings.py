"""Figure 6: one hump vs two wings (step 2 of Phase 0). Run from the project folder:
    .vpxdir/Scripts/python.exe Figures/make_fig6_hump_vs_wings.py
Same recipe as tests/step2_models.py: step2_X.npy (100 buckets, summed in pairs to the 50 bucket version the log used),
PCA, first 3 components, KMeans k=2, n_init=10, random_state=0. No outcomes are used anywhere."""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

INK, SOFT, BLUE, RED = "#2E2C27", "#8A887F", "#2C6E9B", "#B5483A"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": INK, "axes.labelcolor": INK,
                     "text.color": INK, "xtick.color": INK, "ytick.color": INK})

X100 = np.load("Results/step2_X.npy")
X = X100[:, 0::2] + X100[:, 1::2]                    # 50 buckets, rows still sum to 1
assert X.shape == (487, 50)
pca = PCA(n_components=6).fit(X)
Z = pca.transform(X)[:, :3]
km = KMeans(n_clusters=2, n_init=10, random_state=0).fit(Z)
lab = km.labels_
mid = X[:, 20:30].sum(1)                              # middle 20 of 50 buckets
one_hump = int(np.argmax([mid[lab == g].mean() for g in (0, 1)]))
wings = 1 - one_hump
sizes = {g: int((lab == g).sum()) for g in (0, 1)}
print("group sizes (one hump, wings):", sizes[one_hump], sizes[wings], "expected 310, 177")
print("explained PC1, PC2, PC3:", np.round(pca.explained_variance_ratio_[:3], 3))

y = (np.arange(50) + 0.5) / 50 * 100                  # position in the day's own range, 0 = low, 100 = high
fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.6), gridspec_kw={"wspace": 0.35, "width_ratios": [1.25, 1]})

ax = axes[0]
for g, name, col in ((one_hump, f"One hump, {sizes[one_hump]} days", BLUE), (wings, f"Two wings, {sizes[wings]} days", RED)):
    sub = X[lab == g] * 100
    m = sub.mean(0)
    lo, hi = np.percentile(sub, 25, axis=0), np.percentile(sub, 75, axis=0)
    ax.fill_betweenx(y, lo, hi, color=col, alpha=0.18, linewidth=0)
    ax.plot(m, y, color=col, lw=2.2, label=name)
ax.set_xlabel("Share of the day's overnight volume per row (%)")
ax.set_ylabel("Position in the day's own range (0 = low, 100 = high)")
ax.set_title("Average profile of each group\n(line = mean, band = middle half of days)", fontsize=10)
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, fontsize=9)
ax.set_ylim(0, 100)

ax = axes[1]
ax.axvline(0, color=SOFT, lw=1)
ax.plot(pca.components_[0], y, color=INK, lw=2, label=f"PC1, {100 * pca.explained_variance_ratio_[0]:.1f}% of variance")
ax.plot(pca.components_[1], y, color=SOFT, lw=2, ls="--", label=f"PC2, {100 * pca.explained_variance_ratio_[1]:.1f}% of variance")
ax.set_xlabel("Loading")
ax.set_title("The two biggest differences between days\nPC1 = hump vs wings, PC2 = top heavy vs bottom heavy", fontsize=10)
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=1, fontsize=8.5)
ax.set_ylim(0, 100)
ax.set_yticks([])

fig.suptitle("Step 2: the biggest difference between days is hump versus wings, not P versus b", y=1.03, fontsize=11)
fig.text(0.5, -0.14, "487 days, 2022 to 2023, profile up to 09:30 New York, no outcomes used. "
         "Weak structure: silhouette 0.296 against a random cloud band up to about 0.28.",
         ha="center", fontsize=8, color=SOFT)
fig.savefig("Figures/fig6_hump_vs_wings.png", dpi=300, bbox_inches="tight")
fig.savefig("Figures/fig6_hump_vs_wings.pdf", bbox_inches="tight")
print("wrote fig6")
