"""
01_gee_export.py

Exports a 6-band GeoTIFF over one fixed AOI in Anantapur, using real,
physically distinct bands (not derived from any of your old data at all):

  Band 1: Slope (degrees)                -- SRTM 30m DEM
  Band 2: TWI (topographic wetness)      -- SRTM slope + MERIT Hydro upstream area
  Band 3: Distance to nearest stream (m) -- MERIT Hydro flow accumulation
  Band 4: LULC class                     -- ESA WorldCover v200 (10m, resampled to 30m)
  Band 5: Mean annual rainfall (mm)      -- CHIRPS, multi-year mean
  Band 6: NDVI                           -- Sentinel-2 SR, median composite

Because it's a GeoTIFF, every pixel's lat/lon comes from the raster's own
geotransform -- no separate coordinate export needed. This file feeds BOTH
downstream scripts:
  - 02_extract_labeled_patches.py (pairs it with your real labeled points)
  - 03_tile_deploy_grid.py (tiles the whole AOI for map coverage)

HOW TO RUN
-----------
pip install earthengine-api
earthengine authenticate        (one-time browser login)
# edit AOI_BBOX below
python 01_gee_export.py

I cannot run this myself -- it needs your authenticated GEE account.
"""

import ee

# ---------------------------------------------------------------------------
# EDIT THIS: bounding box for your fixed AOI in Anantapur.
# [min_lon, min_lat, max_lon, max_lat]. Keep it small (~5-10km across) for
# a first pass -- faster exports, easier to sanity-check.
# ---------------------------------------------------------------------------
AOI_BBOX = [77.54, 14.62, 77.68, 14.76]

DRIVE_FOLDER = "anantapur_wellsiting_export"
EXPORT_NAME = "aoi_export"
SCALE_M = 30  # 65px * 30m ~= 2km per patch, matching your original patch-size intent

RAINFALL_START = "2020-01-01"
RAINFALL_END = "2025-01-01"

STREAM_THRESHOLD_KM2 = 1.0  # MERIT Hydro upstream area threshold to call a pixel "a stream"


def main():
    ee.Initialize()
    aoi = ee.Geometry.Rectangle(AOI_BBOX)

    dem = ee.Image("USGS/SRTMGL1_003").clip(aoi)
    slope = ee.Terrain.slope(dem).rename("slope")

    merit = ee.Image("MERIT/Hydro/v1_0_1").clip(aoi)
    upstream_area_km2 = merit.select("upa")

    slope_rad = slope.multiply(3.14159265).divide(180)
    tan_slope = slope_rad.tan().max(0.001)
    twi = upstream_area_km2.divide(tan_slope).log().rename("twi")

    stream_mask = upstream_area_km2.gt(STREAM_THRESHOLD_KM2)
    dist_to_stream = (
        stream_mask.fastDistanceTransform(256)
        .sqrt()
        .multiply(ee.Image.pixelArea().sqrt())
        .rename("dist_to_stream")
    )

    lulc = ee.ImageCollection("ESA/WorldCover/v200").first().clip(aoi).rename("lulc")

    rainfall = (
        ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
        .filterDate(RAINFALL_START, RAINFALL_END)
        .filterBounds(aoi)
        .sum()
        .divide(ee.Date(RAINFALL_END).difference(ee.Date(RAINFALL_START), "year"))
        .rename("rainfall")
    )

    def add_cloud_mask(img):
        qa = img.select("QA60")
        cloud_bit, cirrus_bit = 1 << 10, 1 << 11
        mask = qa.bitwiseAnd(cloud_bit).eq(0).And(qa.bitwiseAnd(cirrus_bit).eq(0))
        return img.updateMask(mask)

    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi)
        .filterDate("2024-01-01", "2024-12-31")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
        .map(add_cloud_mask)
        .median()
    )
    ndvi = s2.normalizedDifference(["B8", "B4"]).rename("ndvi")

    stacked = (
        ee.Image.cat([slope, twi, dist_to_stream, lulc, rainfall, ndvi])
        .reproject(crs="EPSG:4326", scale=SCALE_M)
        .clip(aoi)
    )

    task = ee.batch.Export.image.toDrive(
        image=stacked,
        description=EXPORT_NAME,
        folder=DRIVE_FOLDER,
        fileNamePrefix=EXPORT_NAME,
        region=aoi,
        scale=SCALE_M,
        crs="EPSG:4326",
        maxPixels=1e10,
    )
    task.start()
    print(f"Export task started: {task.id}")
    print("Check progress at https://code.earthengine.google.com/tasks")
    print(f"When done, download from Drive folder '{DRIVE_FOLDER}' "
          f"and place it at data_pipeline/raw/{EXPORT_NAME}.tif")


if __name__ == "__main__":
    main()
