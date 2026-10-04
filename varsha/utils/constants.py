"""
Physical and domain-specific constants used throughout VARSHA.
"""

# Earth properties
EARTH_RADIUS_KM = 6371.0

# INSAT-3D/3DR Channel wavelengths (micrometers approx)
INSAT_CHANNELS = {
    'VIS': 0.65,
    'SWIR': 1.625,
    'MIR': 3.9,
    'WV': 6.8,
    'TIR1': 10.8,
    'TIR2': 12.0
}

# Coordinate Reference Systems
WGS84_EPSG = 4326

# Grid properties (Default fallback, should ideally be loaded from config)
DEFAULT_GRID = {
    'lat_min': 6.5,
    'lat_max': 38.0,
    'lon_min': 66.0,
    'lon_max': 100.0,
    'resolution_deg': 0.1
}

# Value for representing missing data
NODATA_VALUE = -9999.0

# Time formats
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
