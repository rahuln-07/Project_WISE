"""
03_tile_deploy_grid.py

Cuts the full AOI GeoTIFF (from 01_gee_export.py) into a grid of 65x65
patches covering the whole area, each with a real lat/lon center. This is
what gets run through the trained model to paint the full map -- separate
from 02_extract_labeled_patches.py, which only pulls patches at your known
labeled points (used for training/evaluation, not full-coverage display).

INPUT:  data_pipeline/raw/aoi_export.tif
OUTPUT: data_pipeline/deploy_grid.npz
          - patches: float32 (N, 65, 65, 6)
          - lats:    float32 (N,)
          - lons:    float32 (N,)

USAGE
------
pip install rasterio numpy
python 03_tile_deploy_grid.py
"""

import os
import numpy as np
import rasterio

RAW_TIF = "d:/3-1/SOLVE/code/data/aoi_export.tif"
OUT_NPZ = "d:/3-1/SOLVE/code/data/deploy_grid.npz"

PATCH = 65
STRIDE = 65  # non-overlapping. Lower (e.g. 32) for a denser/overlapping grid.


def main():
    if not os.path.exists(RAW_TIF):
        raise FileNotFoundError(f"Expected GeoTIFF at {RAW_TIF}. Run 01_gee_export.py first.")

    with rasterio.open(RAW_TIF) as src:
        n_bands = src.count
        height, width = src.height, src.width
        transform = src.transform

        print(f"Opened {RAW_TIF}: {width}x{height} px, {n_bands} bands, crs={src.crs}")
        if n_bands != 6:
            print(f"WARNING: expected 6 bands, found {n_bands}.")

        img = src.read()
        img = np.transpose(img, (1, 2, 0))

        patches, lats, lons = [], [], []
        for row in range(0, height - PATCH + 1, STRIDE):
            for col in range(0, width - PATCH + 1, STRIDE):
                patch = img[row:row + PATCH, col:col + PATCH, :]
                if np.isnan(patch).any():
                    continue

                center_row = row + PATCH // 2
                center_col = col + PATCH // 2
                lon, lat = rasterio.transform.xy(transform, center_row, center_col)

                patches.append(patch.astype(np.float32))
                lats.append(lat)
                lons.append(lon)

        patches = np.stack(patches)
        lats = np.array(lats, dtype=np.float32)
        lons = np.array(lons, dtype=np.float32)

        print(f"Built {len(patches)} geocoded grid cells.")
        np.savez_compressed(OUT_NPZ, patches=patches, lats=lats, lons=lons)
        print(f"Saved to {OUT_NPZ}")


if __name__ == "__main__":
    main()
