import numpy as np, pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score

F = pd.read_csv("Results\\step3_features.csv")
F["shape_age"] = np.log1p(F["shape_age"])
cols = ["upper_pct", "shape_age", "minutes", "atr_pct"]
a = F[F["day"] < "2023"]
b = F[F["day"] >= "2023"]
sc = StandardScaler().fit(a[cols])
A = sc.transform(a[cols])
B = sc.transform(b[cols])

rng = np.random.default_rng(0)
print("k  sil2022  null_mean  null_hi  sil2023own  ARI")
for k in range(2, 7):
    ka = KMeans(k, n_init=10, random_state=0).fit(A)
    s_a = silhouette_score(A, ka.labels_)
    nulls = []
    for _ in range(100):
        N = rng.multivariate_normal(A.mean(0), np.cov(A.T), size=len(A))
        nulls.append(silhouette_score(N, KMeans(k, n_init=3, random_state=0).fit(N).labels_))
    kb = KMeans(k, n_init=10, random_state=0).fit(B)
    s_b = silhouette_score(B, kb.labels_)
    ari = adjusted_rand_score(kb.labels_, ka.predict(B))
    print(k, round(s_a, 3), round(np.mean(nulls), 3), round(np.percentile(nulls, 97.5), 3), round(s_b, 3), round(ari, 3))