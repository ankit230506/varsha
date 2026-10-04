import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# Dummy torch module typing to avoid explicit dependency here
class DummyModule:
    pass

@dataclass
class ExplanationResult:
    """Dataclass holding explanation result for a prediction."""
    channel_attributions: Dict[str, float]
    spatial_attribution_map: np.ndarray
    top_triggers: List[str]
    confidence_note: str

class VarshaExplainer:
    """Generates explanations for VARSHA predictions.
    
    Methods:
    1. Integrated Gradients: Per-channel attribution maps
       showing which satellite/atmospheric features drive the prediction.
    2. Channel Attribution: Aggregate importance per input channel
       (e.g., 'CAPE contributed 30%, WV cooling contributed 25%')
    3. XGBoost Feature Importance: For flood module.
    
    Uses Captum library for gradient-based attribution.
    """
    
    def __init__(self):
        """Initialize the Explainer."""
        logger.info("Initializing VarshaExplainer")
    
    def explain_prediction(
        self, 
        model: 'DummyModule', 
        inputs: dict,
        target_cell: Tuple[int, int],
        target_horizon: int
    ) -> ExplanationResult:
        """Generate explanation for a specific grid cell prediction.
        
        Args:
            model: PyTorch neural network model
            inputs: Dictionary of input tensors
            target_cell: (row, col) indices of the cell to explain
            target_horizon: Forecast horizon step to explain
            
        Returns:
            ExplanationResult object
        """
        logger.info(f"Generating explanation for cell {target_cell} at horizon {target_horizon}")
        # Dummy implementation
        return ExplanationResult(
            channel_attributions={"CAPE": 0.4, "TIR1": 0.3, "WV": 0.3},
            spatial_attribution_map=np.zeros((10, 10)),
            top_triggers=["High CAPE", "Rapid cloud top cooling"],
            confidence_note="High confidence based on agreement between GFS and satellite."
        )
    
    def get_channel_attribution(
        self,
        attributions: np.ndarray,
        channel_names: List[str]
    ) -> Dict[str, float]:
        """Aggregate pixel-level attributions to channel-level importance.
        
        Args:
            attributions: 3D array of attributions (C, H, W)
            channel_names: List of names for each channel
            
        Returns:
            Dictionary mapping channel name to its relative importance (summing to 1.0)
        """
        # Sum absolute attributions spatially
        channel_sums = np.abs(attributions).sum(axis=(1, 2))
        total = channel_sums.sum()
        if total > 0:
            channel_sums = channel_sums / total
            
        return {name: float(val) for name, val in zip(channel_names, channel_sums)}
    
    def format_explanation(
        self,
        channel_attr: Dict[str, float],
        atmospheric_state: Dict[str, float],
        terrain_features: Dict[str, float]
    ) -> str:
        """Format explanation as human-readable text for dashboard.
        
        Args:
            channel_attr: Channel attribution scores
            atmospheric_state: Key atmospheric variable values
            terrain_features: Key terrain/hydrological feature values
            
        Returns:
            Formatted explanation string
        """
        explanation = "⚠️ HIGH RISK because:\n"
        
        if "CAPE" in atmospheric_state and atmospheric_state["CAPE"] > 2000:
            explanation += f"  🌡️ CAPE: {atmospheric_state['CAPE']} J/kg (high instability)\n"
            
        if channel_attr.get("WV", 0) > 0.2:
            explanation += "  💧 Rapid moisture increase (past 2h)\n"
            
        if channel_attr.get("TIR", 0) > 0.2:
            explanation += "  ☁️ Cloud top cooling detected\n"
            
        if "HAND" in terrain_features and terrain_features["HAND"] < 10:
            explanation += f"  ⛰️ HAND = {terrain_features['HAND']}m (flood-prone terrain)\n"
            
        return explanation
