from pydantic import BaseModel
from typing import List, Literal, Optional
from datetime import datetime

class Location(BaseModel):
    """Location information for an alert."""
    lat: float
    lon: float
    district: Optional[str] = None

class AlertResponse(BaseModel):
    """Weather alert response schema."""
    alert_id: str
    level: Literal["watch", "warning", "severe"]
    location: Location
    valid_from: datetime
    valid_to: datetime
    predicted_rainfall_3h: float
    extreme_rain_probability: float
    flood_susceptibility: float
    confidence: Literal["low", "moderate", "high"]
    triggers: List[str]
    recommended_action: str

class PredictionResponse(BaseModel):
    """Full prediction response schema."""
    timestamp: datetime
    geojson: dict
    alerts: List[AlertResponse]
    model_version: str
    processing_time_seconds: float
