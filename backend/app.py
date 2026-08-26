"""
app.py

Serves the static suitability.geojson (output of training/05_run_inference.py)
to the frontend map, plus a health check. No live inference here -- for one
fixed AOI, precomputing once offline is simpler than a live model server.

Also mounts the frontend/ directory as static files so you can access the
full application at http://localhost:8000.

USAGE
------
pip install fastapi uvicorn
uvicorn app:app --reload --port 8000
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Anantapur Well-Siting API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your real frontend origin before real deployment
    allow_methods=["GET"],
    allow_headers=["*"],
)

GEOJSON_PATH = os.path.join(os.path.dirname(__file__), "suitability.geojson")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


@app.get("/")
def root():
    """Redirect root to the frontend."""
    return RedirectResponse(url="/app/index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "geojson_present": os.path.exists(GEOJSON_PATH)}


@app.get("/api/suitability")
def get_suitability():
    if not os.path.exists(GEOJSON_PATH):
        raise HTTPException(
            status_code=404,
            detail="suitability.geojson not found. Run training/05_run_inference.py first.",
        )
    with open(GEOJSON_PATH) as f:
        import json
        data = json.load(f)
    return JSONResponse(content=data)


# Mount frontend as static files — MUST be after API routes
if os.path.isdir(FRONTEND_DIR):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
