"""
Geospatial utility functions for VARSHA.
"""
import numpy as np
import xarray as xr
from typing import Tuple, List, Union
import pyproj
from scipy.interpolate import griddata

def create_latlon_grid(
    lat_min: float, lat_max: float, 
    lon_min: float, lon_max: float, 
    resolution: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Creates a 2D latitude-longitude grid.
    
    Args:
        lat_min: Minimum latitude.
        lat_max: Maximum latitude.
        lon_min: Minimum longitude.
        lon_max: Maximum longitude.
        resolution: Grid resolution in degrees.
        
    Returns:
        Tuple of (lat_grid, lon_grid) as 2D numpy arrays.
    """
    lats = np.arange(lat_min, lat_max + resolution, resolution)
    lons = np.arange(lon_min, lon_max + resolution, resolution)
    
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    return lat_grid, lon_grid

def reproject_dataset(
    ds: xr.Dataset, 
    target_crs: str = "EPSG:4326"
) -> xr.Dataset:
    """
    Reprojects an xarray Dataset to a target CRS using rioxarray.
    
    Args:
        ds: Input xarray Dataset.
        target_crs: Target coordinate reference system.
        
    Returns:
        Reprojected xarray Dataset.
    """
    if not hasattr(ds, "rio"):
        raise ValueError("xarray Dataset must have 'rio' accessor (import rioxarray).")
        
    # Example logic, assumes the dataset is properly formatted for rioxarray
    # It requires spatial dims usually as 'y' and 'x' or 'lat' and 'lon'
    ds_reproj = ds.rio.reproject(target_crs)
    return ds_reproj

def interpolate_to_grid(
    points: np.ndarray, 
    values: np.ndarray, 
    target_grid_lat: np.ndarray, 
    target_grid_lon: np.ndarray, 
    method: str = "linear"
) -> np.ndarray:
    """
    Interpolates unstructured point data to a regular grid.
    
    Args:
        points: (N, 2) array of point coordinates (lon, lat).
        values: (N,) array of values at points.
        target_grid_lat: 2D array of target latitudes.
        target_grid_lon: 2D array of target longitudes.
        method: Interpolation method ('linear', 'nearest', 'cubic').
        
    Returns:
        2D array of interpolated values.
    """
    grid_points = (target_grid_lon, target_grid_lat)
    interpolated = griddata(points, values, grid_points, method=method)
    return interpolated
