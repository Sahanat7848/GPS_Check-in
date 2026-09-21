import math

# Earth's mean radius in meters
EARTH_RADIUS_METERS = 6371000.0

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth's surface
    using the Haversine formula.
    
    Parameters:
        lat1 (float): Latitude of point 1 (in degrees)
        lon1 (float): Longitude of point 1 (in degrees)
        lat2 (float): Latitude of point 2 (in degrees)
        lon2 (float): Longitude of point 2 (in degrees)
        
    Returns:
        float: Distance between the two points in meters (rounded to 2 decimal places)
    """
    # Convert latitude and longitude from degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    # Ensure numerical stability for floating point errors
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    
    distance = EARTH_RADIUS_METERS * c
    return round(distance, 2)

def is_within_geofence(distance_m: float, radius_m: float = 100.0) -> bool:
    """
    Check if a distance is within the allowed geofence radius.
    
    Parameters:
        distance_m (float): Distance in meters
        radius_m (float): Maximum allowed radius in meters (default 100m)
        
    Returns:
        bool: True if distance <= radius_m, False otherwise
    """
    return distance_m <= radius_m
