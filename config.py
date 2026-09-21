"""
Configuration settings for the GPS Check-in System.
"""
import os

# Default classroom target location (e.g. Bangkok / University Campus)
# Lat: 13.736717, Lng: 100.533100 (Chulalongkorn University area as sensible default)
DEFAULT_TARGET_LAT = float(os.getenv("TARGET_LAT", 13.736717))
DEFAULT_TARGET_LNG = float(os.getenv("TARGET_LNG", 100.533100))

# Allowed geofence radius in meters (FR-06: <= 100m)
DEFAULT_RADIUS_METERS = float(os.getenv("RADIUS_METERS", 100.0))

# Database file location
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")
