"""
VARSHA Configuration Module.

Provides configuration loading, validation, and typed access.
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field

class GridConfig(BaseModel):
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    resolution: float

class SatelliteConfig(BaseModel):
    channels: List[str]
    cadence_minutes: int
    history_steps: int

class ReanalysisConfig(BaseModel):
    source: str
    variables: List[str]
    resolution: float

class QPEConfig(BaseModel):
    training_source: str
    inference_source: str

class DEMConfig(BaseModel):
    source: str
    resolution_m: int
    features: List[str]

class PathsConfig(BaseModel):
    raw_data: str
    processed_data: str
    models: str
    outputs: str

class DataConfig(BaseModel):
    grid: GridConfig
    satellite: SatelliteConfig
    reanalysis: ReanalysisConfig
    qpe: QPEConfig
    dem: DEMConfig
    paths: PathsConfig

class ProjectConfig(BaseModel):
    name: str
    version: str

class VarshaConfig(BaseModel):
    project: ProjectConfig
    data: DataConfig
    # Add other sections (model, training, evaluation, alerts, deployment) as needed.
    # We will keep it flexible for now by allowing extra fields or defining full schemas later.
    model_config = {"extra": "allow"}

_GLOBAL_CONFIG: Optional[VarshaConfig] = None

def load_config(config_path: Optional[str] = None) -> VarshaConfig:
    """
    Load configuration from a YAML file.

    Args:
        config_path: Path to the YAML config file. If None, uses default_config.yaml.

    Returns:
        VarshaConfig object.
    """
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "default_config.yaml")

    with open(config_path, "r", encoding="utf-8") as f:
        config_dict = yaml.safe_load(f)

    return VarshaConfig(**config_dict)

def get_config() -> VarshaConfig:
    """
    Get the global configuration instance, loading it if necessary.
    """
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = load_config()
    return _GLOBAL_CONFIG
