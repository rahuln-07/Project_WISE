"""
04_train_hybrid_model.py

Trains the ResNet18 + XGBoost hybrid on labeled_patches.npz (output of
02_extract_labeled_patches.py) -- real coordinates, real distinct bands,
real labels, all in one consistent dataset for the first time.

Because we now have real lat/lon per point, the train/test split is a
genuine geographic hold-out (see utils.spatial_group_split), not a proxy.

USAGE
------
python 04_train_hybrid_model.py --data ../data_pipeline/labeled_patches.npz
"""

import argparse
import os
import random

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score, accuracy_score, classification_report
import xgboost as xgb
import joblib

from model import GeoResNet
from utils import tabular_features, spatial_group_split, check_band_redundancy

SEED = 42
OUT_DIR = "saved_model"


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def pretrain_cnn(model, X, y, device, epochs=8, batch_size=32, lr=1e-4):
    model.set_embedding_mode(False)
    model.to(device)
    model.train()

    X_t = torch.tensor(X.transpose(0, 3, 1, 2), dtype=torch.float32)
    y_t = torch.tensor(y, dtype=torch.long)
    dataset = torch.utils.data.TensorDataset(X_t, y_t)
    loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

    opt = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    for epoch in range(epochs):
        total_loss, n_correct, n_total = 0.0, 0, 0
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            out = model(xb)
            loss = criterion(out, yb)
            loss.backward()
            opt.step()
            total_loss += loss.item() * xb.size(0)
            n_correct += (out.argmax(1) == yb).sum().item()
            n_total += xb.size(0)
        print(f"  epoch {epoch+1}/{epochs}  loss={total_loss/n_total:.4f}  acc={n_correct/n_total:.4f}")
    return model


def extract_embeddings(model, X, device, batch_size=64):
    model.set_embedding_mode(True)
    model.eval()
    X_t = torch.tensor(X.transpose(0, 3, 1, 2), dtype=torch.float32)
    loader = torch.utils.data.DataLoader(X_t, batch_size=batch_size, shuffle=False)
    embeddings = []
    with torch.no_grad():
        for xb in loader:
            xb = xb.to(device)
            embeddings.append(model(xb).cpu().numpy())
    return np.concatenate(embeddings, axis=0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to labeled_patches.npz")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--n_spatial_clusters", type=int, default=6,
                         help="How many geographic blocks to split your labeled points into for the hold-out test set.")
    args = parser.parse_args()

    set_seed(SEED)
    os.makedirs(OUT_DIR, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    print("\n=== Loading labeled patches ===")
    data = np.load(args.data)
    patches, labels, lats, lons = data["patches"], data["labels"], data["lats"], data["lons"]
    print(f"{len(patches)} patches, label balance: {np.bincount(labels)}")

    print("\n=== Checking band redundancy ===")
    check_band_redundancy(patches)

    print(f"\n=== Spatial split ({args.n_spatial_clusters} geographic blocks, one held out) ===")
    if len(patches) < args.n_spatial_clusters * 3:
        print(f"WARNING: only {len(patches)} labeled points for {args.n_spatial_clusters} clusters. "
              f"Results on this small a dataset should be treated as directional, not conclusive. "
              f"Get more labeled points before trusting reported metrics.")
    train_idx, test_idx, groups = spatial_group_split(lats, lons, n_clusters=args.n_spatial_clusters)
    print(f"Train: {len(train_idx)} points, Test: {len(test_idx)} points (different geographic blocks)")

    X_train, y_train = patches[train_idx], labels[train_idx]
    X_test, y_test = patches[test_idx], labels[test_idx]

    n_channels = patches.shape[-1]
    model = GeoResNet(in_channels=n_channels, num_classes=2)

    print(f"\n=== Fine-tuning CNN ({n_channels} input channels) ===")
    model = pretrain_cnn(model, X_train, y_train, device, epochs=args.epochs)

    print("\n=== Extracting embeddings ===")
    emb_train = extract_embeddings(model, X_train, device)
    emb_test = extract_embeddings(model, X_test, device)

    tab_train = tabular_features(X_train)
    tab_test = tabular_features(X_test)

    feat_train = np.concatenate([emb_train, tab_train], axis=1)
    feat_test = np.concatenate([emb_test, tab_test], axis=1)

    print("\n=== Training XGBoost ===")
    clf = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=SEED,
        eval_metric="logloss",
    )
    clf.fit(feat_train, y_train)

    probs = clf.predict_proba(feat_test)[:, 1]
    preds = clf.predict(feat_test)

    print("\n=== Held-out evaluation (real geographic split) ===")
    if len(set(y_test)) < 2:
        print("Only one class present in the held-out set -- ROC-AUC is undefined. "
              "Add more labeled points or reduce n_spatial_clusters.")
    else:
        print(f"Accuracy: {accuracy_score(y_test, preds):.4f}")
        print(f"ROC-AUC:  {roc_auc_score(y_test, probs):.4f}")
    print(classification_report(y_test, preds))

    print(f"\n=== Saving artifacts to {OUT_DIR}/ ===")
    torch.save(model.state_dict(), os.path.join(OUT_DIR, "geo_resnet.pth"))
    clf.save_model(os.path.join(OUT_DIR, "xgboost_model.json"))
    joblib.dump({"in_channels": n_channels}, os.path.join(OUT_DIR, "model_config.joblib"))
    print("Done.")


if __name__ == "__main__":
    main()
