import logging
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass

from varsha.inference.data_fetcher import MOSDACFetcher, GFSFetcher
from varsha.api.alert_engine import AlertEngine
from varsha.xai.explainer import VarshaExplainer

logger = logging.getLogger(__name__)

@dataclass
class PredictionResult:
    """Dataclass holding the full prediction output."""
    stage1_probs: np.ndarray
    stage2_flood_risk: np.ndarray
    alerts: List[dict]
    geojson_output: dict

class InferencePipeline:
    """End-to-end inference pipeline for VARSHA.
    
    Orchestrates the full prediction workflow:
    1. Fetch latest satellite data from MOSDAC
    2. Fetch latest atmospheric analysis (GFS)
    3. Preprocess and align to model grid
    4. Run Stage 1 (atmospheric nowcasting)
    5. Apply probability calibration
    6. Run Stage 2 (flash flood risk)
    7. Generate alerts
    8. Compute XAI attributions for high-risk areas
    9. Format output as GeoJSON
    
    Args:
        model_path: Path to trained Stage 1 model checkpoint
        flood_model_path: Path to trained Stage 2 XGBoost model
        config: Configuration object
        device: GPU device for inference
    """
    
    def __init__(self, model_path: str, flood_model_path: str, config: dict, device: str = "cpu"):
        self.model_path = model_path
        self.flood_model_path = flood_model_path
        self.config = config
        self.device = device
        
        # Initialize sub-components
        self.mosdac_fetcher = MOSDACFetcher(api_key=config.get("mosdac_key", ""))
        self.gfs_fetcher = GFSFetcher()
        self.alert_engine = AlertEngine()
        self.explainer = VarshaExplainer()
        
        # In a real scenario, models would be loaded here
        logger.info(f"Initialized InferencePipeline on {device}")
    
    def run(self) -> PredictionResult:
        """Execute full inference pipeline.
        
        Returns:
            PredictionResult containing probabilities, alerts, and formatted geojson
        """
        logger.info("Starting inference pipeline run...")
        
        sat_data = self._fetch_satellite_data()
        atm_data = self._fetch_atmospheric_data()
        
        inputs = self._preprocess(sat_data, atm_data)
        
        stage1_out = self._predict_stage1(inputs)
        stage2_out = self._predict_stage2(stage1_out)
        
        alerts = self._generate_alerts({"rainfall": stage1_out, "flood": stage2_out})
        
        geojson = self._to_geojson({"rainfall": stage1_out, "flood": stage2_out}, alerts)
        
        return PredictionResult(
            stage1_probs=stage1_out["probs"],
            stage2_flood_risk=stage2_out,
            alerts=alerts,
            geojson_output=geojson
        )
    
    def _fetch_satellite_data(self) -> np.ndarray:
        """Fetch latest INSAT-3D/3DR data from MOSDAC."""
        return self.mosdac_fetcher.fetch_latest()
    
    def _fetch_atmospheric_data(self) -> np.ndarray:
        """Fetch latest GFS analysis."""
        return self.gfs_fetcher.fetch_latest()
    
    def _preprocess(self, sat_data: np.ndarray, atm_data: np.ndarray) -> dict:
        """Preprocess raw data into model input tensors.
        
        Args:
            sat_data: Raw satellite data
            atm_data: Raw atmospheric data
            
        Returns:
            Dictionary of preprocessed tensors
        """
        logger.info("Preprocessing inputs...")
        return {"satellite": sat_data, "atmospheric": atm_data}
    
    def _predict_stage1(self, inputs: dict) -> dict:
        """Run Stage 1 atmospheric nowcasting.
        
        Args:
            inputs: Preprocessed input tensors
            
        Returns:
            Dictionary containing model predictions
        """
        logger.info("Running Stage 1 prediction...")
        # Dummy probability output (grid size 64x64)
        return {"probs": np.random.rand(64, 64)}
    
    def _predict_stage2(self, stage1_output: dict) -> np.ndarray:
        """Run Stage 2 flash flood risk.
        
        Args:
            stage1_output: Outputs from Stage 1
            
        Returns:
            Array containing flood risk probabilities
        """
        logger.info("Running Stage 2 prediction...")
        # Dummy flood risk output
        return np.random.rand(64, 64)
    
    def _generate_alerts(self, predictions: dict) -> List[dict]:
        """Generate alert objects from predictions.
        
        Args:
            predictions: Dictionary with rainfall and flood predictions
            
        Returns:
            List of generated alerts
        """
        # Create dummy grid for coordinates
        lat_grid, lon_grid = np.meshgrid(np.linspace(8, 38, 64), np.linspace(68, 98, 64))
        
        # Need current datetime for valid_from
        from datetime import datetime
        now = datetime.utcnow()
        
        return self.alert_engine.generate_alerts(
            rainfall_probs=predictions["rainfall"]["probs"],
            flood_risk=predictions["flood"],
            lat_grid=lat_grid,
            lon_grid=lon_grid,
            timestamp=now
        )
    
    def _to_geojson(self, predictions: dict, alerts: List[dict]) -> dict:
        """Format predictions as GeoJSON for the dashboard.
        
        Args:
            predictions: Model predictions
            alerts: Generated alerts
            
        Returns:
            GeoJSON FeatureCollection
        """
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [77.0, 28.0]
                    },
                    "properties": {
                        "alert_count": len(alerts)
                    }
                }
            ]
        }
