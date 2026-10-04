"""
VARSHA Weather Data Simulator.

Generates realistic simulated weather data for 25 Indian cities
with monsoon-season patterns (September). Data changes coherently
every 5 minutes using time-based seeding.
"""
import random
import math
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any

IST = timezone(timedelta(hours=5, minutes=30))

STATIONS = [
    {"id": "DEL", "name": "Delhi",               "state": "Delhi",              "district": "New Delhi",     "lat": 28.6139, "lon": 77.2090, "region": "north",     "basin": "Ganga Basin",                  "monsoon_weight": 0.7},
    {"id": "MUM", "name": "Mumbai",              "state": "Maharashtra",        "district": "Mumbai City",   "lat": 19.0760, "lon": 72.8777, "region": "west",      "basin": "Western Ghats Catchment",      "monsoon_weight": 0.85},
    {"id": "CHE", "name": "Chennai",             "state": "Tamil Nadu",         "district": "Chennai",       "lat": 13.0827, "lon": 80.2707, "region": "south",     "basin": "Southern Coastal / Palar",     "monsoon_weight": 0.3},
    {"id": "KOL", "name": "Kolkata",             "state": "West Bengal",        "district": "Kolkata",       "lat": 22.5726, "lon": 88.3639, "region": "east",      "basin": "Ganga-Brahmaputra Delta",      "monsoon_weight": 0.8},
    {"id": "BLR", "name": "Bengaluru",           "state": "Karnataka",          "district": "Bengaluru Urban","lat": 12.9716, "lon": 77.5946, "region": "south",    "basin": "Cauvery / Krishna Basin",      "monsoon_weight": 0.5},
    {"id": "JAI", "name": "Jaipur",              "state": "Rajasthan",          "district": "Jaipur",        "lat": 26.9124, "lon": 75.7873, "region": "north",     "basin": "Indus / Desert Catchment",     "monsoon_weight": 0.35},
    {"id": "LKO", "name": "Lucknow",             "state": "Uttar Pradesh",      "district": "Lucknow",       "lat": 26.8467, "lon": 80.9462, "region": "north",     "basin": "Ganga Basin (Gomti)",          "monsoon_weight": 0.75},
    {"id": "GHY", "name": "Guwahati",            "state": "Assam",              "district": "Kamrup Metro",  "lat": 26.1445, "lon": 91.7362, "region": "northeast", "basin": "Brahmaputra Basin",          "monsoon_weight": 0.95},
    {"id": "BPL", "name": "Bhopal",              "state": "Madhya Pradesh",     "district": "Bhopal",        "lat": 23.2599, "lon": 77.4126, "region": "central",   "basin": "Narmada / Betwa Basin",        "monsoon_weight": 0.6},
    {"id": "HYD", "name": "Hyderabad",           "state": "Telangana",          "district": "Hyderabad",     "lat": 17.3850, "lon": 78.4867, "region": "south",     "basin": "Krishna-Godavari Basin",       "monsoon_weight": 0.55},
    {"id": "PNE", "name": "Pune",                "state": "Maharashtra",        "district": "Pune",          "lat": 18.5204, "lon": 73.8567, "region": "west",      "basin": "Western Ghats Catchment",      "monsoon_weight": 0.7},
    {"id": "AMD", "name": "Ahmedabad",           "state": "Gujarat",            "district": "Ahmedabad",     "lat": 23.0225, "lon": 72.5714, "region": "west",      "basin": "Sabarmati Basin",              "monsoon_weight": 0.45},
    {"id": "PAT", "name": "Patna",               "state": "Bihar",              "district": "Patna",         "lat": 25.5941, "lon": 85.1376, "region": "east",      "basin": "Ganga Basin",                  "monsoon_weight": 0.9},
    {"id": "RAN", "name": "Ranchi",              "state": "Jharkhand",          "district": "Ranchi",        "lat": 23.3441, "lon": 85.3096, "region": "east",      "basin": "Subarnarekha / Damodar",       "monsoon_weight": 0.72},
    {"id": "DDN", "name": "Dehradun",            "state": "Uttarakhand",        "district": "Dehradun",      "lat": 30.3165, "lon": 78.0322, "region": "north",     "basin": "Himalayan Foothills (Ganga)",  "monsoon_weight": 0.8},
    {"id": "SML", "name": "Shimla",              "state": "Himachal Pradesh",   "district": "Shimla",        "lat": 31.1048, "lon": 77.1734, "region": "north",     "basin": "Himalayan Headwaters (Indus)", "monsoon_weight": 0.65},
    {"id": "TVM", "name": "Thiruvananthapuram",  "state": "Kerala",             "district": "Thiruvananthapuram","lat": 8.5241, "lon": 76.9366, "region": "south",  "basin": "Western Ghats Catchment",      "monsoon_weight": 0.6},
    {"id": "COK", "name": "Kochi",               "state": "Kerala",             "district": "Ernakulam",     "lat": 9.9312,  "lon": 76.2673, "region": "south",     "basin": "Western Ghats Catchment",      "monsoon_weight": 0.65},
    {"id": "VTZ", "name": "Visakhapatnam",       "state": "Andhra Pradesh",     "district": "Visakhapatnam", "lat": 17.6868, "lon": 83.2185, "region": "south",     "basin": "Eastern Coastal Basin",        "monsoon_weight": 0.5},
    {"id": "NAG", "name": "Nagpur",              "state": "Maharashtra",        "district": "Nagpur",        "lat": 21.1458, "lon": 79.0882, "region": "central",   "basin": "Godavari / Wainganga Basin",   "monsoon_weight": 0.6},
    {"id": "IDR", "name": "Indore",              "state": "Madhya Pradesh",     "district": "Indore",        "lat": 22.7196, "lon": 75.8577, "region": "central",   "basin": "Narmada / Chambal Basin",      "monsoon_weight": 0.55},
    {"id": "CHD", "name": "Chandigarh",          "state": "Chandigarh",         "district": "Chandigarh",    "lat": 30.7333, "lon": 76.7794, "region": "north",     "basin": "Indus Basin (Sutlej)",         "monsoon_weight": 0.6},
    {"id": "SXR", "name": "Srinagar",            "state": "Jammu & Kashmir",    "district": "Srinagar",      "lat": 34.0837, "lon": 74.7973, "region": "north",     "basin": "Jhelum / Indus Basin",         "monsoon_weight": 0.4},
    {"id": "IMF", "name": "Imphal",              "state": "Manipur",            "district": "Imphal West",   "lat": 24.8170, "lon": 93.9368, "region": "northeast", "basin": "Barak / Manipur Basin",        "monsoon_weight": 0.88},
    {"id": "SHL", "name": "Shillong",            "state": "Meghalaya",          "district": "East Khasi Hills","lat": 25.5788,"lon": 91.8933, "region": "northeast", "basin": "Brahmaputra Basin (Surma)",   "monsoon_weight": 0.92},
]


def _time_seed() -> int:
    """Returns a seed that changes every 5 minutes."""
    return int(time.time() // 300)


def _station_rng(station_id: str, offset: int = 0) -> random.Random:
    """Create a deterministic RNG for a station + current time window."""
    rng = random.Random()
    rng.seed(hash(station_id) + _time_seed() + offset)
    return rng


def simulate_station(station: dict) -> dict:
    """Generate realistic weather data for one station."""
    rng = _station_rng(station["id"])
    w = station["monsoon_weight"]

    # Rainfall — driven by monsoon weight + randomness
    rain_base = w * rng.uniform(0.6, 1.4)
    is_active = rain_base > 0.55  # station is currently seeing rain
    is_extreme = rain_base > 0.75 and rng.random() < 0.4  # ~40% of high-weight become extreme

    if is_extreme:
        rainfall_rate = rng.uniform(25.0, 85.0)
        extreme_rain_prob = rng.uniform(0.55, 0.95)
        flood_susceptibility = rng.uniform(0.5, 0.92)
    elif is_active:
        rainfall_rate = rng.uniform(2.0, 22.0)
        extreme_rain_prob = rng.uniform(0.15, 0.45)
        flood_susceptibility = rng.uniform(0.15, 0.45)
    else:
        rainfall_rate = rng.uniform(0.0, 1.5)
        extreme_rain_prob = rng.uniform(0.02, 0.15)
        flood_susceptibility = rng.uniform(0.02, 0.2)

    # Temperature — cooler when raining
    if is_extreme:
        temperature = rng.uniform(22.0, 27.0)
    elif is_active:
        temperature = rng.uniform(24.0, 31.0)
    else:
        temperature = rng.uniform(28.0, 38.0)

    # Humidity — higher when raining
    humidity = min(100.0, rng.uniform(55.0, 75.0) + (rainfall_rate * 0.5))

    # Wind
    wind_speed = rng.uniform(5.0, 20.0) + (15.0 if is_extreme else 0.0) + (rainfall_rate * 0.3)
    wind_dir = rng.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"])

    # Pressure — lower during severe weather
    pressure = rng.uniform(1005.0, 1015.0) - (15.0 if is_extreme else 5.0 if is_active else 0.0)

    # CAPE/CIN
    cape = rng.uniform(800, 4200) if is_active else rng.uniform(200, 1200)
    cin = rng.uniform(0, 80) if is_active else rng.uniform(50, 250)

    # Cloud cover
    cloud_cover = min(100.0, rng.uniform(70, 100) if is_active else rng.uniform(10, 50))

    # Probability horizons
    rain_1h = min(1.0, extreme_rain_prob * rng.uniform(0.7, 1.1))
    rain_3h = min(1.0, extreme_rain_prob * rng.uniform(0.85, 1.25))
    rain_6h = min(1.0, extreme_rain_prob * rng.uniform(0.9, 1.4))

    return {
        "id": station["id"],
        "name": station["name"],
        "district": station["district"],
        "state": station["state"],
        "region": station["region"],
        "lat": station["lat"],
        "lon": station["lon"],
        "current_conditions": {
            "rainfall_rate": round(rainfall_rate, 1),
            "temperature": round(temperature, 1),
            "humidity": round(humidity, 1),
            "wind_speed": round(wind_speed, 1),
            "wind_dir": wind_dir,
            "pressure": round(pressure, 1),
            "cloud_cover": round(cloud_cover, 1),
            "CAPE": round(cape, 0),
            "CIN": round(cin, 0),
        },
        "probabilities": {
            "rain_1h": round(rain_1h, 2),
            "rain_3h": round(rain_3h, 2),
            "rain_6h": round(rain_6h, 2),
            "extreme_rain": round(extreme_rain_prob, 2),
            "flood_susceptibility": round(flood_susceptibility, 2),
        },
    }


def get_all_stations() -> List[dict]:
    """Get current data for all 25 stations."""
    return [simulate_station(st) for st in STATIONS]


def get_station_by_id(station_id: str) -> Optional[dict]:
    """Find station template by ID."""
    return next((st for st in STATIONS if st["id"] == station_id), None)


# ---------------------------------------------------------------------------
# Alert generation
# ---------------------------------------------------------------------------

def _determine_alert_level(extreme_prob: float, flood_risk: float) -> Optional[str]:
    if extreme_prob > 0.5 and flood_risk > 0.5:
        return "severe"
    elif extreme_prob > 0.4 or flood_risk > 0.5:
        return "warning"
    elif extreme_prob > 0.3 or flood_risk > 0.3:
        return "watch"
    return None


def get_active_alerts() -> List[dict]:
    """Generate alerts from current station data."""
    now = datetime.now(IST)
    alerts = []
    for st_data in get_all_stations():
        ep = st_data["probabilities"]["extreme_rain"]
        fr = st_data["probabilities"]["flood_susceptibility"]
        level = _determine_alert_level(ep, fr)
        if level is None:
            continue

        rng = _station_rng(st_data["id"], offset=7)
        triggers = []
        if ep > 0.4:
            triggers.append("Heavy rainfall probability exceeded threshold")
        if fr > 0.4:
            triggers.append("Flood susceptibility elevated due to terrain + moisture")
        if st_data["current_conditions"]["CAPE"] > 2500:
            triggers.append("High CAPE indicating convective instability")
        if not triggers:
            triggers.append("Combined risk indices crossed alert boundary")

        confidence = "high" if (ep > 0.7 and fr > 0.6) else "moderate" if ep > 0.4 else "low"

        if level == "severe":
            action = "EVACUATE low-lying areas immediately. Avoid river crossings. Seek shelter on higher ground."
        elif level == "warning":
            action = "Stay indoors. Prepare emergency supplies. Monitor official updates."
        else:
            action = "Be aware of changing weather. Avoid unnecessary travel."

        alerts.append({
            "alert_id": f"ALT-{st_data['id']}-{_time_seed()}",
            "level": level,
            "location": {
                "lat": st_data["lat"],
                "lon": st_data["lon"],
                "district": st_data["district"],
            },
            "station_name": st_data["name"],
            "state": st_data["state"],
            "valid_from": now.isoformat(),
            "valid_to": (now + timedelta(hours=6)).isoformat(),
            "predicted_rainfall_3h": round(st_data["current_conditions"]["rainfall_rate"] * 3, 1),
            "extreme_rain_probability": ep,
            "flood_susceptibility": fr,
            "confidence": confidence,
            "triggers": triggers,
            "recommended_action": action,
        })

    # Sort: severe first, then warning, then watch
    order = {"severe": 0, "warning": 1, "watch": 2}
    alerts.sort(key=lambda a: order.get(a["level"], 3))
    return alerts


# ---------------------------------------------------------------------------
# Station detail with 24h history
# ---------------------------------------------------------------------------

def get_station_detail(station_id: str) -> Optional[dict]:
    """Get detailed station data including 24h time series."""
    tpl = get_station_by_id(station_id)
    if tpl is None:
        return None

    current = simulate_station(tpl)
    rng = _station_rng(station_id, offset=42)

    # Generate 24-hour history (hourly)
    now = datetime.now(IST)
    base_rain = current["current_conditions"]["rainfall_rate"]
    base_temp = current["current_conditions"]["temperature"]
    base_hum = current["current_conditions"]["humidity"]

    history = []
    for i in range(24, 0, -1):
        t = now - timedelta(hours=i)
        # Gradual build-up pattern
        factor = 0.3 + 0.7 * (1 - i / 24)
        history.append({
            "timestamp": t.isoformat(),
            "rainfall": round(max(0, base_rain * factor + rng.uniform(-3, 3)), 1),
            "temperature": round(base_temp + rng.uniform(-2, 2) + (i * 0.1), 1),
            "humidity": round(max(40, min(100, base_hum - (i * 0.3) + rng.uniform(-5, 5))), 1),
        })

    current["history_24h"] = history
    return current


# ---------------------------------------------------------------------------
# 6-hour forecast
# ---------------------------------------------------------------------------

def get_forecast(station_id: str) -> Optional[dict]:
    """Generate a 6-hour forecast for a station."""
    tpl = get_station_by_id(station_id)
    if tpl is None:
        return None

    current = simulate_station(tpl)
    rng = _station_rng(station_id, offset=99)
    now = datetime.now(IST)

    base_rain = current["current_conditions"]["rainfall_rate"]
    base_prob = current["probabilities"]["extreme_rain"]
    base_temp = current["current_conditions"]["temperature"]

    forecast = []
    for i in range(1, 7):
        t = now + timedelta(hours=i)
        # Rain tends to intensify then taper
        peak_factor = 1.0 + 0.3 * math.sin(math.pi * i / 6)
        forecast.append({
            "hour": f"+{i}h",
            "timestamp": t.isoformat(),
            "predicted_rainfall": round(max(0, base_rain * peak_factor + rng.uniform(-5, 8)), 1),
            "rainfall_prob": round(max(0, min(1.0, base_prob + rng.uniform(-0.15, 0.15))), 2),
            "temperature": round(base_temp + rng.uniform(-1.5, 1.5), 1),
            "confidence_lower": round(max(0, base_rain * peak_factor * 0.6), 1),
            "confidence_upper": round(base_rain * peak_factor * 1.5 + 5, 1),
        })

    return {"station_id": station_id, "station_name": current["name"], "forecast": forecast}


# ---------------------------------------------------------------------------
# XAI / Explainability
# ---------------------------------------------------------------------------

def get_xai_data(station_id: str) -> Optional[dict]:
    """Generate explainability data for a station's prediction."""
    tpl = get_station_by_id(station_id)
    if tpl is None:
        return None

    current = simulate_station(tpl)
    rng = _station_rng(station_id, offset=200)

    # Generate attributions that sum to ~1.0
    raw = {
        "CAPE / Instability": rng.uniform(0.15, 0.40),
        "Water Vapor (WV)": rng.uniform(0.10, 0.25),
        "Thermal IR (TIR1)": rng.uniform(0.08, 0.20),
        "Shortwave IR (SWIR)": rng.uniform(0.05, 0.15),
        "DEM / Terrain Slope": rng.uniform(0.05, 0.18),
        "Wind Shear (850-200hPa)": rng.uniform(0.05, 0.15),
        "Antecedent Moisture": rng.uniform(0.03, 0.12),
    }
    total = sum(raw.values())
    attributions = {k: round(v / total, 3) for k, v in raw.items()}

    triggers = []
    if current["current_conditions"]["CAPE"] > 2500:
        triggers.append(f"CAPE = {current['current_conditions']['CAPE']:.0f} J/kg — high convective instability")
    if current["current_conditions"]["humidity"] > 85:
        triggers.append(f"Humidity = {current['current_conditions']['humidity']:.0f}% — moisture-laden atmosphere")
    if current["current_conditions"]["rainfall_rate"] > 20:
        triggers.append(f"Current rainfall = {current['current_conditions']['rainfall_rate']:.1f} mm/h — already intense")
    if current["current_conditions"]["wind_speed"] > 35:
        triggers.append("Strong low-level winds enhancing moisture convergence")
    if not triggers:
        triggers.append("Model confidence driven by satellite cloud-top cooling trend")
        triggers.append("Atmospheric reanalysis shows favourable thermodynamics")

    ep = current["probabilities"]["extreme_rain"]
    fr = current["probabilities"]["flood_susceptibility"]

    explanation = f"{'⚠️ HIGH RISK' if ep > 0.5 else 'ℹ️ MODERATE RISK' if ep > 0.3 else '✅ LOW RISK'}: "
    explanation += f"Extreme rain probability is {ep*100:.0f}% and flood susceptibility is {fr*100:.0f}%. "
    explanation += "Primary drivers: " + ", ".join(list(attributions.keys())[:3]) + "."

    return {
        "station_id": station_id,
        "station_name": current["name"],
        "channel_attributions": attributions,
        "top_triggers": triggers,
        "confidence_score": round(rng.uniform(0.65, 0.95), 2),
        "explanation_text": explanation,
    }


# ---------------------------------------------------------------------------
# Model info (static)
# ---------------------------------------------------------------------------

def get_model_info() -> dict:
    return {
        "model_name": "VarshaNet",
        "version": "v1.0.0-sih",
        "architecture": {
            "stage1": "SatelliteEncoder(ResNet-18) + AtmosphericEncoder(4-layer CNN) → Axial Attention Temporal Fusion (2 layers, 8 heads) → UNet Decoder → Multi-head Predictions",
            "stage2": "FloodRiskModule (XGBoost, 500 estimators, max_depth=8)",
        },
        "data_sources": {
            "satellite": "INSAT-3D/3DR (TIR1, TIR2, WV, SWIR) — 30-min cadence, 8 history steps",
            "reanalysis": "ERA5 (training) / NCEP GFS (inference) — CAPE, CIN, u/v 850/200, q 850/500, z500",
            "precipitation_target": "NASA IMERG Final Run V07",
            "elevation": "Copernicus GLO-30 DEM (30m) — slope, TWI, HAND, flow accumulation",
        },
        "training": {
            "optimizer": "AdamW (lr=1e-4, weight_decay=1e-5)",
            "scheduler": "Cosine Annealing",
            "epochs": 50,
            "batch_size": 4,
            "mixed_precision": True,
            "loss": "0.4×BCE + 0.4×Focal(γ=2) + 0.2×MSE",
            "train_years": "2016–2019",
            "val_years": "2020",
            "test_years": "2021–2022",
        },
        "performance": {
            "thresholds": [
                {"threshold_mm_hr": 1,  "BSS": 0.72, "PR_AUC": 0.85, "CSI": 0.68, "POD": 0.82, "FAR": 0.21, "ETS": 0.54},
                {"threshold_mm_hr": 10, "BSS": 0.61, "PR_AUC": 0.74, "CSI": 0.55, "POD": 0.71, "FAR": 0.29, "ETS": 0.43},
                {"threshold_mm_hr": 30, "BSS": 0.45, "PR_AUC": 0.58, "CSI": 0.41, "POD": 0.56, "FAR": 0.42, "ETS": 0.31},
                {"threshold_mm_hr": 50, "BSS": 0.32, "PR_AUC": 0.41, "CSI": 0.28, "POD": 0.42, "FAR": 0.51, "ETS": 0.19},
            ],
            "flood_module_auc": 0.87,
        },
        "calibration": {
            "predicted": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            "observed":  [0.12, 0.19, 0.28, 0.37, 0.46, 0.55, 0.65, 0.74, 0.83],
        },
    }


# ---------------------------------------------------------------------------
# Historical mock data
# ---------------------------------------------------------------------------

def get_historical(date_str: str) -> dict:
    """Generate mock historical prediction vs observation data."""
    rng = random.Random(hash(date_str))
    records = []
    for st in STATIONS:
        obs = round(rng.uniform(0, 50) * st["monsoon_weight"], 1)
        pred = round(obs + rng.uniform(-8, 8), 1)
        records.append({
            "station_id": st["id"],
            "station_name": st["name"],
            "state": st["state"],
            "predicted_rainfall_mm": max(0, pred),
            "observed_rainfall_mm": max(0, obs),
            "error_mm": round(pred - obs, 1),
            "alert_issued": rng.random() < 0.3,
            "alert_verified": rng.random() < 0.7,
        })
    return {"date": date_str, "records": records}


# ---------------------------------------------------------------------------
# Random real-time alert for WebSocket push
# ---------------------------------------------------------------------------

def generate_realtime_alert() -> dict:
    """Generate a single random alert for WebSocket broadcast."""
    rng = random.Random()
    st = rng.choice(STATIONS)
    level = rng.choice(["watch", "warning", "severe"])
    now = datetime.now(IST)

    return {
        "alert_id": f"RT-{uuid.uuid4().hex[:8].upper()}",
        "level": level,
        "station_name": st["name"],
        "state": st["state"],
        "location": {
            "lat": st["lat"],
            "lon": st["lon"],
            "district": st["district"],
        },
        "valid_from": now.isoformat(),
        "valid_to": (now + timedelta(hours=3)).isoformat(),
        "message": f"New {level.upper()} alert issued for {st['name']}, {st['state']}",
        "predicted_rainfall_3h": round(rng.uniform(15, 120), 1),
        "extreme_rain_probability": round(rng.uniform(0.35, 0.95), 2),
        "flood_susceptibility": round(rng.uniform(0.3, 0.9), 2),
        "confidence": rng.choice(["low", "moderate", "high"]),
        "triggers": ["Sudden precipitation spike detected by model"],
        "recommended_action": "Monitor situation closely. Follow local authority guidance.",
    }
