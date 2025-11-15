# agent/geo_utils.py
from haversine import haversine

# return distance in kilometers between two (lat, lon) tuples
def distance_km(loc1: tuple, loc2: tuple) -> float:
    """
    loc1, loc2: (lat, lon)
    """
    try:
        return haversine(loc1, loc2)
    except Exception:
        return float("inf")

def geo_decay_weight(distance_km: float, scale_km: float = 1500.0) -> float:
    """
    Exponential decay weight: 1 at 0 km, decays as distance increases.
    scale_km ~ controls decay rate; tune it later.
    """
    import math
    if distance_km is None or distance_km == float("inf"):
        return 0.0
    return math.exp(-distance_km / scale_km)