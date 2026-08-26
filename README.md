# Anantapur Well-Siting — Full Rebuild

This is a clean rebuild. Nothing here depends on the old
`Anantapur_wellsiting_batch_*.tfrecord` files or `solve1.ipynb`'s training
data. What's kept is the **architecture** you asked for — ResNet18 CNN
feature extractor + XGBoost classifier — unchanged.

## What's different from before

| | Old data | This rebuild |
|---|---|---|
| Bands | 6 channels, but all statistically identical (correlation matrix = all 1.0) | 6 real, physically distinct bands (Slope, TWI, distance-to-stream, LULC, rainfall, NDVI) |
| Coordinates | None at all | Every patch has a real lat/lon, derived from the GeoTIFF's own geotransform |
| Labels | ~2000 patches, source/provenance unknown | You supply real, sourced ground-truth points (CSV of lat/lon/label) |
| Train/test split | Random shuffle (or a batch-file proxy in the previous iteration) — spatially leaky | Real geographic block hold-out, since coordinates now exist |
| Architecture | ResNet18 + XGBoost hybrid | Same, unchanged |

## Pipeline, in order

```
data_pipeline/01_gee_export.py            AOI → 6-band GeoTIFF (Earth Engine)
        │
        ├──► data_pipeline/02_extract_labeled_patches.py   (+ your labels.csv) → labeled_patches.npz
        │            │
        │            ▼
        │    training/04_train_hybrid_model.py  → saved_model/ (real spatial split)
        │
        └──► data_pipeline/03_tile_deploy_grid.py           → deploy_grid.npz
                     │
                     ▼
             training/05_run_inference.py (uses saved_model/) → suitability.geojson
                     │
                     ▼
             backend/app.py  → serves it
                     │
                     ▼
             frontend/index.html  → renders it on the map
```

## Step-by-step

### 1. Export the AOI imagery
```bash
cd data_pipeline
pip install -r requirements.txt
earthengine authenticate
# edit AOI_BBOX in 01_gee_export.py first
python 01_gee_export.py
```
Wait for the export task (https://code.earthengine.google.com/tasks), then download the GeoTIFF from Drive to `data_pipeline/raw/aoi_export.tif`.

### 2. Get real labeled points and extract their patches
You need a CSV of known well outcomes with coordinates — see `labels_template.csv` for the format (`lat,lon,label`, where `label` is 1 for a known suitable/productive site and 0 for unsuitable/dry). Sources to check: Andhra Pradesh groundwater department records, CGWB (Central Ground Water Board) well data, or your own field survey.

```bash
python 02_extract_labeled_patches.py --labels labels.csv --tif raw/aoi_export.tif --out labeled_patches.npz
```

Points that fall outside your AOI bounding box or too close to its edge get skipped and printed — check that output.

### 3. Build the full-coverage grid (for the map)
```bash
python 03_tile_deploy_grid.py
```

### 4. Train
```bash
cd ../training
pip install -r requirements.txt
python 04_train_hybrid_model.py --data ../data_pipeline/labeled_patches.npz
```
This holds out a real geographic cluster of your labeled points for testing — not a random shuffle. **How many labeled points you need**: the more the better, but treat anything under ~50-100 points as directional rather than a trustworthy accuracy estimate — the script will warn you if your dataset is thin relative to the number of spatial clusters requested.

### 5. Run inference over the full AOI
```bash
python 05_run_inference.py --grid ../data_pipeline/deploy_grid.npz --model_dir saved_model --out ../backend/suitability.geojson
```

### 6. Serve it
```bash
cd ../backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

### 7. View it
Edit `frontend/index.html`: set your real Google Maps API key and `AOI_CENTER`, then open the file in a browser. It fetches from `http://localhost:8000/api/suitability`.

**On a different maps provider (Mapbox/Leaflet)?** Say so — only `frontend/index.html` changes, nothing upstream does.

## The one thing that still depends on you

Steps 4 onward are only as good as the labeled points you feed into step 2. This pipeline is now internally consistent — real bands, real coordinates, real architecture — but "internally consistent" and "predictively accurate" are different claims. The accuracy number step 4 prints is honest *given your labels*; if the labels are sparse, clustered, or biased toward easy cases, the model will reflect that. Worth getting as many well-documented points as you reasonably can before trusting the output for anything beyond a demo.
