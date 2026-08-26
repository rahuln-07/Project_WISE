"""
utils.py

Two things that weren't possible with your old data, now that real
coordinates exist:

  - tabular_features(): per-band mean/std, feeding XGBoost alongside the
    CNN embeddings (same idea as before).
  - spatial_group_split(): a REAL geographic hold-out. Clusters points by
    lat/lon into spatial blocks, then holds out whole blocks for testing.
    This replaces the "hold out whole batch files" proxy from the previous
    version -- that was a workaround for not having coordinates at all;
    now that we do, this is an actual spatial split, and gives you an
    honest read on how the model generalizes to unseen ground rather than
    an inflated number from spatially-leaked random splits.
"""

import numpy as np
from sklearn.cluster import KMeans
from sklearn.model_selection import GroupShuffleSplit


def tabular_features(patches):
    means = patches.mean(axis=(1, 2))
    stds = patches.std(axis=(1, 2))
    return np.concatenate([means, stds], axis=1)


def spatial_group_split(lats, lons, n_clusters=6, test_size=0.2, random_state=42):
    """
    Clusters points geographically, then does a group-aware split so that
    an entire spatial cluster is held out for testing -- not just
    individual points, which could sit meters from a training point.

    Returns: train_idx, test_idx (integer arrays into the original data)
    """
    coords = np.stack([lats, lons], axis=1)
    n_clusters = min(n_clusters, len(coords))  # can't have more clusters than points
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    groups = kmeans.fit_predict(coords)

    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(splitter.split(coords, groups=groups))
    return train_idx, test_idx, groups


def check_band_redundancy(patches, verbose=True):
    """Sanity check worth keeping even on fresh data -- catches accidental
    band duplication early instead of discovering it after training."""
    n_bands = patches.shape[-1]
    band_means = patches.mean(axis=(1, 2))
    corr = np.corrcoef(band_means.T)
    off_diag = corr[~np.eye(n_bands, dtype=bool)]
    max_corr = off_diag.max()
    if verbose:
        print("\nBand cross-correlation matrix (per-patch means):")
        print(np.round(corr, 4))
    if max_corr > 0.999:
        print(
            "\n*** WARNING: bands are near-perfectly correlated "
            f"(max off-diagonal correlation = {max_corr:.6f}). Check "
            "01_gee_export.py's band stack before trusting this run. ***\n"
        )
    return corr
