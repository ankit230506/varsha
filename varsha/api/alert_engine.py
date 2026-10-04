import logging
import numpy as np
from typing import List, Optional, Dict
from datetime import datetime
import uuid

# Assume these classes would be imported from schemas if used widely
# from varsha.api.schemas import AlertResponse, Location

logger = logging.getLogger(__name__)

class AlertRegion:
    """Represents a spatial cluster of alert cells."""
    def __init__(self, lat: float, lon: float, rain_prob: float, flood_risk: float):
        self.lat = lat
        self.lon = lon
        self.rain_prob = rain_prob
        self.flood_risk = flood_risk

class AlertEngine:
    """Generates weather alerts from model predictions.
    
    Alert tiers:
        WATCH:   P(rain>10mm/h) > 0.3 OR flood_risk > 0.3
        WARNING: P(rain>30mm/h) > 0.4 OR flood_risk > 0.5  
        SEVERE:  P(rain>50mm/3h) > 0.5 AND flood_risk > 0.5
    
    Thresholds are configurable and should be calibrated
    from validation data to achieve target FAR/POD.
    """
    
    def __init__(self, thresholds: Optional[Dict] = None):
        """Initialize the AlertEngine with threshold configurations.
        
        Args:
            thresholds: Optional dictionary of probability thresholds.
        """
        self.thresholds = thresholds or {
            "watch": {"rain_prob": 0.3, "flood_risk": 0.3},
            "warning": {"rain_prob": 0.4, "flood_risk": 0.5},
            "severe": {"rain_prob": 0.5, "flood_risk": 0.5}
        }
        
    def generate_alerts(
        self,
        rainfall_probs: np.ndarray,
        flood_risk: np.ndarray,
        lat_grid: np.ndarray,
        lon_grid: np.ndarray,
        timestamp: datetime,
        explanations: Optional[Dict] = None
    ) -> List[dict]:
        """Generate alerts from prediction grids.
        
        Args:
            rainfall_probs: 2D array of rainfall probabilities
            flood_risk: 2D array of flood risk probabilities
            lat_grid: 2D array of latitudes
            lon_grid: 2D array of longitudes
            timestamp: Valid timestamp for the prediction
            explanations: Optional dictionary of explanations for cells
            
        Returns:
            List of generated alerts as dictionaries
        """
        logger.info("Generating alerts from prediction grids.")
        alerts = []
        
        # Simplified logic: find cells exceeding watch thresholds
        # In practice, this would use more sophisticated clustering
        watch_threshold = self.thresholds["watch"]
        
        mask = (rainfall_probs > watch_threshold["rain_prob"]) | (flood_risk > watch_threshold["flood_risk"])
        alert_indices = np.argwhere(mask)
        
        if len(alert_indices) == 0:
            return alerts
            
        regions = self._cluster_alerts(alert_indices, rainfall_probs, flood_risk, lat_grid, lon_grid)
        
        for region in regions:
            level = self._determine_level(region.rain_prob, region.flood_risk)
            if level:
                alert = {
                    "alert_id": str(uuid.uuid4()),
                    "level": level,
                    "location": {
                        "lat": region.lat,
                        "lon": region.lon,
                        "district": self._assign_district(region.lat, region.lon)
                    },
                    "valid_from": timestamp,
                    "valid_to": timestamp, # Should add duration
                    "predicted_rainfall_3h": 0.0, # Placeholder
                    "extreme_rain_probability": region.rain_prob,
                    "flood_susceptibility": region.flood_risk,
                    "confidence": "moderate",
                    "triggers": ["High rainfall probability" if region.rain_prob > 0.5 else "High flood risk"],
                    "recommended_action": "Stay indoors and avoid flood-prone areas."
                }
                alerts.append(alert)
                
        logger.info(f"Generated {len(alerts)} alerts.")
        return alerts
    
    def _cluster_alerts(self, alert_cells: np.ndarray, rain_probs: np.ndarray, 
                        flood_risks: np.ndarray, lats: np.ndarray, lons: np.ndarray) -> List[AlertRegion]:
        """Spatially cluster adjacent alert cells into alert regions.
        
        Args:
            alert_cells: Indices of cells exceeding thresholds
            rain_probs: 2D array of rainfall probabilities
            flood_risks: 2D array of flood risks
            lats: Latitude grid
            lons: Longitude grid
            
        Returns:
            List of AlertRegion objects
        """
        # Placeholder for spatial clustering logic (e.g., DBSCAN)
        # For now, just treat each cell as a region (not recommended for production)
        regions = []
        for idx in alert_cells[:10]: # Limit to 10 for dummy implementation
            r, c = idx
            regions.append(AlertRegion(float(lats[r, c]), float(lons[r, c]), float(rain_probs[r, c]), float(flood_risks[r, c])))
        return regions
    
    def _determine_level(self, rain_prob: float, flood_risk: float) -> Optional[str]:
        """Determine alert level based on thresholds.
        
        Args:
            rain_prob: Probability of extreme rainfall
            flood_risk: Probability of flash flood
            
        Returns:
            Alert level string ('watch', 'warning', 'severe') or None
        """
        t = self.thresholds
        if rain_prob > t["severe"]["rain_prob"] and flood_risk > t["severe"]["flood_risk"]:
            return "severe"
        elif rain_prob > t["warning"]["rain_prob"] or flood_risk > t["warning"]["flood_risk"]:
            return "warning"
        elif rain_prob > t["watch"]["rain_prob"] or flood_risk > t["watch"]["flood_risk"]:
            return "watch"
        return None
    
    def _assign_district(self, lat: float, lon: float) -> Optional[str]:
        """Lookup district name for a given coordinate (using shapefile).
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            District name if found, else None
        """
        # Placeholder for geospatial lookup
        return "Unknown District"
