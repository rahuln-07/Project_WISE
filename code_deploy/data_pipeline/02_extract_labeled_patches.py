"""
02_extract_labeled_patches.py

This is the file that replaces your old Anantapur_wellsiting_batch_*.tfrecord
data entirely. Instead of unlabeled/uncoordinated historical batches, you
provide a CSV of real, known points -- e.g. existing borewell records with
a success/failure outcome, sourced from the AP groundwater department,
CGWB (Central Ground Water Board), or your own field survey.

For each point, this script cuts a 65x65 patch out of the GeoTIFF exported
by 01_gee_export.py, centered on that point's real location. The result is
one dataset where every patch has a REAL coordinate AND a REAL label AND
REAL distinct bands -- the three things your original data never had
together.

INPUT CSV FORMAT (see labels_template.csv):
    lat,lon,label
    14.6710,77.5920,1
    14.6802,77.6011,0
    ...
    label: 1 = suitable / known productive well site, 0 = unsuitable / dry or failed

USAGE
------
python 02_extract_labeled_patches.py \
    --labels labels.csv \
    --tif raw/aoi_export.tif \
    --out labeled_patches.npz
"""

import argparse
import csv
import os

import numpy as np
import rasterio
from rasterio.windows import Window

PATCH = 65


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", required=True, help="CSV with lat,lon,label columns")
    parser.add_argument("--tif", default=os.path.join("raw", "aoi_export.tif"))
    parser.add_argument("--out", default="labeled_patches.npz")
    args = parser.parse_args()

    if not os.path.exists(args.tif):
        raise FileNotFoundError(f"Expected GeoTIFF at {args.tif}. Run 01_gee_export.py first.")

    points = []
    with open(args.labels) as f:
        reader = csv.DictReader(f)
        for row in reader:
            points.append((float(row["lat"]), float(row["lon"]), int(row["label"])))

    print(f"Loaded {len(points)} labeled points from {args.labels}")

    patches, labels, lats, lons = [], [], [], []
    skipped = 0

    with rasterio.open(args.tif) as src:
        n_bands = src.count
        if n_bands != 6:
            print(f"WARNING: GeoTIFF has {n_bands} bands, expected 6. Check 01_gee_export.py.")

        for lat, lon, label in points:
            row, col = src.index(lon, lat)
            row_start = row - PATCH // 2
            col_start = col - PATCH // 2

            if row_start < 0 or col_start < 0 or \
               row_start + PATCH > src.height or col_start + PATCH > src.width:
                print(f"  Skipping ({lat}, {lon}) -- patch would fall outside raster bounds")
                skipped += 1
                continue

            window = Window(col_start, row_start, PATCH, PATCH)
            patch = src.read(window=window)  # (bands, H, W)
            patch = np.transpose(patch, (1, 2, 0))  # -> (H, W, bands)

            if np.isnan(patch).any():
                print(f"  Skipping ({lat}, {lon}) -- patch contains no-data pixels")
                skipped += 1
                continue

            patches.append(patch.astype(np.float32))
            labels.append(label)
            lats.append(lat)
            lons.append(lon)

    if not patches:
        raise RuntimeError("No valid patches extracted. Check that your CSV points fall inside the AOI_BBOX used in 01_gee_export.py.")

    patches = np.stack(patches)
    labels = np.array(labels, dtype=np.int64)
    lats = np.array(lats, dtype=np.float32)
    lons = np.array(lons, dtype=np.float32)

    print(f"\nExtracted {len(patches)} patches ({skipped} skipped)")
    print(f"Label balance: {np.bincount(labels)}")

    np.savez_compressed(args.out, patches=patches, labels=labels, lats=lats, lons=lons)
    print(f"Saved to {args.out}")


if __name__ == "__main__":
    main()
