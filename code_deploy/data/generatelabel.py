import geopandas as gpd
import pandas as pd
import numpy as np

# 1. Load ONLY the regular wells parquet file
file_path = "d:/3-1/SOLVE/code/data/SOI_Wells.parquet"
print(f"Loading {file_path}...")
gdf = gpd.read_parquet(file_path)

# 2. Expanded AOI bounding box (roughly 15x15 km)
min_lon, min_lat, max_lon, max_lat = 77.54, 14.62, 77.68, 14.76

# 3. Filter the dataset to your new AOI
aoi_wells = gdf.cx[min_lon:max_lon, min_lat:max_lat]
print(f"Found {len(aoi_wells)} positive well locations in the expanded AOI.")

# 4. Create Positive Samples (label = 1)
positives = pd.DataFrame({
    'lat': aoi_wells.geometry.y,
    'lon': aoi_wells.geometry.x,
    'label': 1
})

# 5. Generate Negative Samples (label = 0) with a Spatial Buffer
num_negatives = len(positives) * 3

if num_negatives == 0:
    print("Warning: No wells found. Adding fallback negatives.")
    num_negatives = 50 

# Extract positive coordinates for distance checking
pos_coords = positives[['lat', 'lon']].values
neg_lats = []
neg_lons = []

# Buffer distance in degrees (0.003 degrees is roughly 330 meters)
# This prevents heavy overlap between the 640x640m image patches
min_buffer = 0.003 

print("Generating negative samples safely away from positive wells...")
while len(neg_lats) < num_negatives:
    cand_lat = np.random.uniform(min_lat, max_lat)
    cand_lon = np.random.uniform(min_lon, max_lon)
    
    # Calculate distance from the candidate to all positive wells
    if len(pos_coords) > 0:
        distances = np.sqrt((pos_coords[:, 0] - cand_lat)**2 + (pos_coords[:, 1] - cand_lon)**2)
        # Only keep the candidate if it is further than the buffer from ALL positive wells
        if np.all(distances > min_buffer):
            neg_lats.append(cand_lat)
            neg_lons.append(cand_lon)
    else:
        neg_lats.append(cand_lat)
        neg_lons.append(cand_lon)

negatives = pd.DataFrame({
    'lat': neg_lats,
    'lon': neg_lons,
    'label': 0
})

# 6. Combine, shuffle, and export directly to your data folder
labels_df = pd.concat([positives, negatives]).sample(frac=1).reset_index(drop=True)
labels_df.to_csv("d:/3-1/SOLVE/code/data/labels.csv", index=False)
print(f"Saved {len(labels_df)} total samples to labels.csv successfully!")