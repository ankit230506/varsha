import numpy as np
from typing import Dict, Any, Optional

def _confusion_matrix_elements(y_true: np.ndarray, y_pred: np.ndarray, threshold: float = 0.5):
    """Internal helper to compute TP, FP, FN, TN."""
    pred_binary = (y_pred >= threshold).astype(bool)
    true_binary = (y_true >= threshold).astype(bool)
    
    tp = np.logical_and(pred_binary, true_binary).sum()
    fp = np.logical_and(pred_binary, ~true_binary).sum()
    fn = np.logical_and(~pred_binary, true_binary).sum()
    tn = np.logical_and(~pred_binary, ~true_binary).sum()
    
    return tp, fp, fn, tn

def critical_success_index(y_true: np.ndarray, y_pred: np.ndarray, threshold: float = 0.5) -> float:
    """CSI = TP / (TP + FP + FN). Standard meteorological skill score."""
    tp, fp, fn, _ = _confusion_matrix_elements(y_true, y_pred, threshold)
    denom = tp + fp + fn
    return float(tp / denom) if denom > 0 else 0.0

def probability_of_detection(y_true: np.ndarray, y_pred: np.ndarray, threshold: float = 0.5) -> float:
    """POD = TP / (TP + FN). Also called Hit Rate."""
    tp, _, fn, _ = _confusion_matrix_elements(y_true, y_pred, threshold)
    denom = tp + fn
    return float(tp / denom) if denom > 0 else 0.0

def false_alarm_ratio(y_true: np.ndarray, y_pred: np.ndarray, threshold: float = 0.5) -> float:
    """FAR = FP / (TP + FP). Fraction of predictions that were false alarms."""
    tp, fp, _, _ = _confusion_matrix_elements(y_true, y_pred, threshold)
    denom = tp + fp
    return float(fp / denom) if denom > 0 else 0.0

def brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """BS = mean((p - o)^2). Lower is better."""
    return float(np.mean((y_prob - y_true) ** 2))

def brier_skill_score(y_true: np.ndarray, y_prob: np.ndarray, climatology: Optional[np.ndarray] = None) -> float:
    """BSS = 1 - BS/BS_ref. Skill relative to climatology."""
    bs = brier_score(y_true, y_prob)
    if climatology is None:
        climatology = np.full_like(y_true, np.mean(y_true))
    bs_ref = brier_score(y_true, climatology)
    return float(1.0 - (bs / bs_ref)) if bs_ref > 0 else 0.0

def equitable_threat_score(y_true: np.ndarray, y_pred: np.ndarray, threshold: float = 0.5) -> float:
    """ETS = (TP - TP_random) / (TP + FP + FN - TP_random)."""
    tp, fp, fn, tn = _confusion_matrix_elements(y_true, y_pred, threshold)
    total = tp + fp + fn + tn
    if total == 0:
        return 0.0
        
    tp_random = ((tp + fn) * (tp + fp)) / total
    denom = (tp + fp + fn - tp_random)
    return float((tp - tp_random) / denom) if denom > 0 else 0.0

def compute_reliability_diagram(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> Dict[str, np.ndarray]:
    """Compute reliability diagram data (observed frequency vs predicted probability)."""
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_centers = 0.5 * (bins[:-1] + bins[1:])
    
    indices = np.digitize(y_prob, bins, right=True) - 1
    indices = np.clip(indices, 0, n_bins - 1)
    
    obs_freq = np.zeros(n_bins)
    pred_mean = np.zeros(n_bins)
    counts = np.zeros(n_bins)
    
    for i in range(n_bins):
        mask = (indices == i)
        if np.any(mask):
            obs_freq[i] = np.mean(y_true[mask])
            pred_mean[i] = np.mean(y_prob[mask])
            counts[i] = np.sum(mask)
            
    return {
        'bin_centers': bin_centers,
        'observed_frequency': obs_freq,
        'predicted_mean': pred_mean,
        'counts': counts
    }

class MetricSuite:
    """Computes all evaluation metrics for a given prediction.
    
    Returns a dict with all metrics organized by threshold and horizon.
    """
    
    def __init__(self, thresholds: list = [1.0, 10.0, 30.0]):
        self.thresholds = thresholds
        
    def evaluate(self, y_true: np.ndarray, y_prob: np.ndarray) -> Dict[str, Any]:
        """Evaluate full suite."""
        results = {}
        for thresh in self.thresholds:
            prefix = f"T{thresh}_"
            results[prefix + "CSI"] = critical_success_index(y_true, y_prob, threshold=0.5)
            results[prefix + "POD"] = probability_of_detection(y_true, y_prob, threshold=0.5)
            results[prefix + "FAR"] = false_alarm_ratio(y_true, y_prob, threshold=0.5)
            results[prefix + "ETS"] = equitable_threat_score(y_true, y_prob, threshold=0.5)
            
        results["BS"] = brier_score(y_true, y_prob)
        results["BSS"] = brier_skill_score(y_true, y_prob)
        
        return results
