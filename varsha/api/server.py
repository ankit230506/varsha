"""
VARSHA API Server.

FastAPI application serving weather predictions, alerts, station data,
model info, explainability data, and the frontend dashboard.
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from datetime import datetime
import asyncio
import json
import logging
import os
import random

from varsha.api import simulator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="VARSHA API",
    description="Vulnerability-Aware Regional Severe-weather Hazard Anticipation System",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Active WebSocket connections ----
active_connections: List[WebSocket] = []


# ======================================================================
# API ENDPOINTS
# ======================================================================

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/predict")
async def get_prediction():
    """GeoJSON FeatureCollection with all station data."""
    stations = simulator.get_all_stations()
    features = []
    for st in stations:
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [st["lon"], st["lat"]]},
            "properties": st,
        })
    alerts = simulator.get_active_alerts()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "geojson": {"type": "FeatureCollection", "features": features},
        "alerts": alerts,
        "model_version": "v1.0.0-sih",
        "processing_time_seconds": 1.2,
    }


@app.get("/alerts")
async def get_alerts():
    """Active weather alerts."""
    return simulator.get_active_alerts()


@app.get("/api/stations")
async def get_stations():
    """All stations with current conditions."""
    return simulator.get_all_stations()


@app.get("/api/station/{station_id}")
async def get_station(station_id: str):
    """Detailed station data including 24h history."""
    data = simulator.get_station_detail(station_id)
    if not data:
        raise HTTPException(404, "Station not found")
    return data


@app.get("/api/forecast/{station_id}")
async def get_forecast(station_id: str):
    """6-hour forecast for a station."""
    data = simulator.get_forecast(station_id)
    if not data:
        raise HTTPException(404, "Station not found")
    return data


@app.get("/api/model-info")
async def get_model_info():
    """Model metadata and performance metrics."""
    return simulator.get_model_info()


@app.get("/api/xai/{station_id}")
async def get_xai(station_id: str):
    """Explainability data for a station's prediction."""
    data = simulator.get_xai_data(station_id)
    if not data:
        raise HTTPException(404, "Station not found")
    return data


@app.get("/history/{date}")
async def get_history(date: str):
    """Historical prediction vs observation data."""
    return simulator.get_historical(date)


# ======================================================================
# WEBSOCKET — real-time alert push
# ======================================================================

@app.websocket("/ws/alerts")
async def alert_websocket(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"WebSocket client connected. Total: {len(active_connections)}")

    async def push_alerts():
        """Push a random alert every 45-60 seconds."""
        try:
            while True:
                await asyncio.sleep(random.uniform(45, 60))
                alert = simulator.generate_realtime_alert()
                await websocket.send_text(json.dumps(alert, default=str))
        except Exception:
            pass

    task = asyncio.create_task(push_alerts())
    try:
        while True:
            await websocket.receive_text()  # keep-alive pings from client
    except WebSocketDisconnect:
        pass
    finally:
        task.cancel()
        if websocket in active_connections:
            active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(active_connections)}")


# ======================================================================
# STATIC FILES — serve frontend
# ======================================================================

_frontend_dir = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
)

if os.path.isdir(_frontend_dir):
    # Serve index.html at root
    @app.get("/")
    async def serve_root():
        return FileResponse(os.path.join(_frontend_dir, "index.html"))

    @app.get("/favicon.ico")
    async def serve_favicon():
        fav = os.path.join(_frontend_dir, "assets", "favicon.png")
        if os.path.exists(fav):
            return FileResponse(fav)
        return FileResponse(os.path.join(_frontend_dir, "assets", "logo.png"))

    # Mount static sub-directories
    for subdir in ("css", "js", "assets"):
        d = os.path.join(_frontend_dir, subdir)
        if os.path.isdir(d):
            app.mount(f"/{subdir}", StaticFiles(directory=d), name=subdir)
else:
    logger.warning(f"Frontend directory not found: {_frontend_dir}")

    @app.get("/")
    async def serve_root_fallback():
        return {"message": "VARSHA API is running. Frontend not found."}
