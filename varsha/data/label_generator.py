import logging
from typing import Dict, Union, Tuple
import numpy as np
import torch

logger = logging.getLogger(__name__)

class LabelGenerator:
    """Generates training labels from IMERG and satellite data.
    
    Rainfall labels: binary threshold exceedance from IMERG
    Convective labels: CTT-based deep convection detection from INSAT
    Flood labels: weak supervision from rainfall + terrain heuristics
    """

    def __init__(self, thresholds: Tuple[float, ...] = (1.0, 10.0, 30.0)):
        """Initialize the Label Generator.
        
        Args:
            thresholds: Rainfall thresholds in mm/hr for binary targets.
        """
        self.thresholds = thresholds

    def generate_rainfall_labels(self, qpe_sequence: np.ndarray) -> Dict[str, np.ndarray]:
        """Generate binary multi-threshold labels from future QPE sequence.
        
        Args:
            qpe_sequence (np.ndarray): Shape (T_future, H, W) of future rainfall mm/hr.
            
        Returns:
            Dict[str, np.ndarray]: Binary masks for each threshold.
        """
        labels = {}
        for thresh in self.thresholds:
            key = f"rainfall_{int(thresh)}mm"
            labels[key] = (qpe_sequence >= thresh).astype(np.float32)
            
        # Accumulated extremes over 3h windows
        if qpe_sequence.shape[0] >= 6:
            # Assumes hourly data
            acc_3h_1 = np.sum(qpe_sequence[:3], axis=0)
            acc_3h_2 = np.sum(qpe_sequence[3:6], axis=0)
            acc_combined = np.stack([acc_3h_1, acc_3h_2], axis=0)
            labels["extreme_50mm_3h"] = (acc_combined >= 50.0).astype(np.float32)
            
        labels["rainfall_amount"] = qpe_sequence.astype(np.float32)
        return labels

    def generate_convective_labels(self, tir_sequence: np.ndarray) -> np.ndarray:
        """Generate deep convection labels based on Cloud Top Temperature (CTT).
        
        Deep convection is typically indicated by very cold TIR brightness temperatures
        (e.g., < 230K or < 210K for intense convection).
        
        Args:
            tir_sequence (np.ndarray): Thermal IR sequence (T_future, H, W).
            
        Returns:
            np.ndarray: Binary mask of convective regions.
        """
        CONVECTIVE_THRESHOLD = 230.0 # Kelvin
        return (tir_sequence <= CONVECTIVE_THRESHOLD).astype(np.float32)

    def generate_weak_flood_labels(
        self,
        rainfall_acc: np.ndarray,
        hand_features: np.ndarray,
        twi_features: np.ndarray
    ) -> np.ndarray:
        """Generate weak flood labels based on heavy rain and susceptible terrain.
        
        Args:
            rainfall_acc (np.ndarray): Accumulated rainfall.
            hand_features (np.ndarray): Height Above Nearest Drainage.
            twi_features (np.ndarray): Topographic Wetness Index.
            
        Returns:
            np.ndarray: Susceptibility/flood occurrence probability (0-1).
        """
        # Heuristic: High rainfall + Low HAND + High TWI -> High Flood Risk
        risk_score = (rainfall_acc / 50.0) * (twi_features / 15.0) / (hand_features + 1.0)
        risk_prob = np.clip(risk_score, 0, 1)
        return (risk_prob > 0.7).astype(np.float32)
