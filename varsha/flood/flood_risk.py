import logging
from typing import Dict, Any
import numpy as np
import xgboost as xgb

logger = logging.getLogger(__name__)

class FloodRiskModule:
    """Stage 2: Flash Flood Risk Assessment.
    
    Combines ML precipitation forecasts with pre-computed DEM features
    and antecedent precipitation to estimate flash flood susceptibility.
    
    Uses XGBoost classifier trained on weakly-supervised flood labels.
    
    Features:
        - Predicted 3h/6h rainfall accumulation (from Stage 1)
        - Antecedent Precipitation Index (7-day weighted)
        - HAND (min within grid cell)
        - Slope (mean)
        - TWI (mean)
        - Flow accumulation (log)
        - Drainage density
        - Month (seasonal indicator)
    """
    
    def __init__(self, model_path: str = None):
        """Initialize the Flood Risk Module.
        
        Args:
            model_path (str, optional): Path to pre-trained XGBoost model.
        """
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            objective='binary:logistic',
            eval_metric='auc'
        )
        if model_path:
            self.model.load_model(model_path)
            logger.info(f"Loaded FloodRisk model from {model_path}")

    def prepare_features(self, data: Dict[str, np.ndarray]) -> np.ndarray:
        """Flattens 2D spatial features into a tabular format for XGBoost.
        
        Args:
            data (Dict[str, np.ndarray]): Dictionary of 2D grids (H, W).
                Expected keys: 'pred_rainfall_3h', 'api_7d', 'hand_min',
                'slope_mean', 'twi_mean', 'flow_acc', 'drainage_density', 'month'.
                
        Returns:
            np.ndarray: Feature matrix of shape (N_pixels, N_features).
        """
        feature_keys = [
            'pred_rainfall_3h', 'api_7d', 'hand_min', 'slope_mean', 
            'twi_mean', 'flow_acc', 'drainage_density', 'month'
        ]
        
        arrays = []
        for key in feature_keys:
            if key not in data:
                raise ValueError(f"Missing required feature: {key}")
            # Flatten spatial dims
            arrays.append(data[key].flatten())
            
        return np.column_stack(arrays)

    def train(self, data: Dict[str, np.ndarray], labels: np.ndarray):
        """Train the XGBoost model.
        
        Args:
            data (Dict[str, np.ndarray]): Training features.
            labels (np.ndarray): Binary target flood labels (H, W).
        """
        logger.info("Preparing features for training...")
        X = self.prepare_features(data)
        y = labels.flatten()
        
        logger.info("Training FloodRisk XGBoost model...")
        self.model.fit(X, y)
        logger.info("Training complete.")

    def predict_risk(self, data: Dict[str, np.ndarray]) -> np.ndarray:
        """Predict flash flood risk probabilities.
        
        Args:
            data (Dict[str, np.ndarray]): Inference features.
            
        Returns:
            np.ndarray: Risk probability grid (H, W).
        """
        X = self.prepare_features(data)
        probs = self.model.predict_proba(X)[:, 1]
        
        # Reshape back to grid
        H, W = data['pred_rainfall_3h'].shape
        return probs.reshape((H, W))
