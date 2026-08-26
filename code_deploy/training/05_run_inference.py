"""
05_run_inference.py

Loads the trained ResNet18 + XGBoost hybrid and runs it over
data_pipeline/deploy_grid.npz (the full-coverage geocoded grid from
03_tile_deploy_grid.py), producing the GeoJSON the map frontend consumes.

USAGE
------
python 05_run_inference.py \
    --grid ../data_pipeline/deploy_grid.npz \
    --model_dir saved_model \
    --out ../backend/suitability.geojson
"""

import argparse
import json
import os

import numpy as np
import torch
import xgboost as xgb
import joblib

from model import GeoResNet
from utils import tabular_features


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", required=True)
    parser.add_argument("--model_dir", default="saved_model")
    parser.add_argument("--out", default="../backend/suitability.geojson")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    data = np.load(args.grid)
    patches, lats, lons = data["patches"], data["lats"], data["lons"]
    print(f"Loaded {len(patches)} grid cells from {args.grid}")

    config = joblib.load(os.path.join(args.model_dir, "model_config.joblib"))
    n_channels = config["in_channels"]

    if patches.shape[-1] != n_channels:
        raise ValueError(
            f"Grid has {patches.shape[-1]} bands but model was trained on {n_channels}."
        )

    model = GeoResNet(in_channels=n_channels, num_classes=2)
    model.load_state_dict(torch.load(os.path.join(args.model_dir, "geo_resnet.pth"), map_location=device))
    model.to(device)
    model.set_embedding_mode(True)
    model.eval()

    X_t = torch.tensor(patches.transpose(0, 3, 1, 2), dtype=torch.float32)
    loader = torch.utils.data.DataLoader(X_t, batch_size=64, shuffle=False)
    embeddings = []
    with torch.no_grad():
        for xb in loader:
            xb = xb.to(device)
            embeddings.append(model(xb).cpu().numpy())
    embeddings = np.concatenate(embeddings, axis=0)

    tab = tabular_features(patches)
    features = np.concatenate([embeddings, tab], axis=1)

    clf = xgb.XGBClassifier()
    clf.load_model(os.path.join(args.model_dir, "xgboost_model.json"))
    probs = clf.predict_proba(features)[:, 1]

    print(f"Suitability probability range: [{probs.min():.3f}, {probs.max():.3f}], mean={probs.mean():.3f}")

    features_geojson = []
    for lat, lon, prob in zip(lats, lons, probs):
        features_geojson.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
            "properties": {"suitability_probability": round(float(prob), 4)},
        })

    geojson = {"type": "FeatureCollection", "features": features_geojson}

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(geojson, f)
    print(f"Wrote {len(features_geojson)} features to {args.out}")


if __name__ == "__main__":
    main()
