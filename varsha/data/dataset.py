import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import numpy as np
import torch
from torch.utils.data import Dataset
import zarr

logger = logging.getLogger(__name__)

class VarshaDataset(Dataset):
    """PyTorch Dataset for VARSHA training/evaluation.
    
    Loads pre-processed satellite, atmospheric, DEM, and label tensors.
    Supports event-centered oversampling for class imbalance.
    
    Each sample contains:
        - satellite: (T, C_sat, H, W) - 8 timesteps of 6-channel satellite BT
        - atmospheric: (C_atm, H, W) - 12-channel atmospheric state
        - static: (C_dem, H, W) - 7-channel DEM features  
        - qpe_antecedent: (H, W) - 3-hour accumulated past rainfall
        - labels: dict with keys:
            - rainfall_1mm: (6, H, W) - binary, 6 horizons
            - rainfall_10mm: (6, H, W)
            - rainfall_30mm: (6, H, W)
            - extreme_50mm_3h: (2, H, W) - +3h and +6h
            - convective: (3, H, W) - +2h, +4h, +6h
            - rainfall_amount: (6, H, W) - mm/hr regression target
        - metadata: dict with timestamp, lat/lon bounds
    """

    def __init__(
        self,
        data_dir: Union[str, Path],
        split: str = 'train',
        event_indices: Optional[List[int]] = None,
        normalize: bool = True,
        stats_path: Optional[Union[str, Path]] = None,
        sequence_length: int = 8
    ) -> None:
        """Initialize the VarshaDataset.
        
        Args:
            data_dir (Union[str, Path]): Path to processed zarr/numpy datasets.
            split (str): 'train', 'val', or 'test'.
            event_indices (Optional[List[int]]): Indices for oversampling.
            normalize (bool): Whether to apply statistical normalization.
            stats_path (Optional[Union[str, Path]]): Path to normalization stats.
            sequence_length (int): Number of satellite timesteps.
        """
        self.data_dir = Path(data_dir) / split
        self.split = split
        self.sequence_length = sequence_length
        self.normalize = normalize
        
        if not self.data_dir.exists():
            logger.error(f"Data directory {self.data_dir} does not exist.")
            raise FileNotFoundError(f"Data directory {self.data_dir} not found.")

        # In a real implementation, we would open zarr groups here.
        # self.satellite_data = zarr.open(str(self.data_dir / 'satellite.zarr'), mode='r')
        # self.labels_data = zarr.open(str(self.data_dir / 'labels.zarr'), mode='r')
        
        # Mocking size for demonstration
        self.size = 100 
        
        self.indices = event_indices if event_indices is not None else list(range(self.size))
        
        self.stats = {}
        if self.normalize:
            self._load_stats(stats_path)

    def _load_stats(self, stats_path: Optional[Union[str, Path]]) -> None:
        """Load pre-computed normalization statistics."""
        if stats_path is None:
            logger.warning("Normalization is enabled but no stats_path provided. Using dummy stats.")
            self.stats = {
                'sat_mean': np.zeros((6,)),
                'sat_std': np.ones((6,))
            }
            return
        
        path = Path(stats_path)
        if path.exists():
            stats = np.load(path, allow_pickle=True).item()
            self.stats = stats
        else:
            logger.error(f"Stats file {stats_path} not found.")
            raise FileNotFoundError(f"Stats file not found: {stats_path}")

    def __len__(self) -> int:
        """Return the number of samples."""
        return len(self.indices)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        """Fetch a single sample by index."""
        actual_idx = self.indices[idx]
        
        # Mock data loading (Replace with real zarr/numpy slices)
        H, W = 128, 128
        satellite = np.random.randn(self.sequence_length, 6, H, W).astype(np.float32)
        atmospheric = np.random.randn(12, H, W).astype(np.float32)
        static = np.random.randn(7, H, W).astype(np.float32)
        qpe = np.random.rand(H, W).astype(np.float32)
        
        if self.normalize and 'sat_mean' in self.stats:
            mean = self.stats['sat_mean'].reshape((1, 6, 1, 1))
            std = self.stats['sat_std'].reshape((1, 6, 1, 1))
            satellite = (satellite - mean) / (std + 1e-8)

        labels = {
            'rainfall_1mm': torch.randint(0, 2, (6, H, W), dtype=torch.float32),
            'rainfall_10mm': torch.randint(0, 2, (6, H, W), dtype=torch.float32),
            'rainfall_30mm': torch.randint(0, 2, (6, H, W), dtype=torch.float32),
            'extreme_50mm_3h': torch.randint(0, 2, (2, H, W), dtype=torch.float32),
            'convective': torch.randint(0, 2, (3, H, W), dtype=torch.float32),
            'rainfall_amount': torch.rand((6, H, W), dtype=torch.float32) * 50.0
        }
        
        return {
            'satellite': torch.from_numpy(satellite),
            'atmospheric': torch.from_numpy(atmospheric),
            'static': torch.from_numpy(static),
            'qpe_antecedent': torch.from_numpy(qpe),
            'labels': labels,
            'metadata': {
                'timestamp': '2023-01-01T00:00:00',
                'lat_bounds': [8.0, 38.0],
                'lon_bounds': [68.0, 98.0]
            }
        }
