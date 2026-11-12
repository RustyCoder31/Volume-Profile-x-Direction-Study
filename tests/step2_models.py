import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score

X = np.load("Results\\step2_X.npy")
days = pd.read_csv("Results\\step2_days.csv")
print(X.shape, np.isnan(X).sum())          # must be (487, 50) and 0

pca = PCA(n_components=6).fit(X)
print("PCA explained:", np.round(pca.explained_variance_ratio_, 3))
Z = pca.transform(X)[:, :3]                # first 3 components

for k in range(2, 7):
    km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(Z)
    gm = GaussianMixture(n_components=k, random_state=0, n_init=5).fit(Z)
    print(k, "silhouette", round(silhouette_score(Z, km.labels_), 3), "BIC", round(gm.bic(Z)))