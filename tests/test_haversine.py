import unittest
import math
from haversine import calculate_distance, is_within_geofence

class TestHaversine(unittest.TestCase):
    def test_same_coordinate_zero_distance(self):
        lat, lon = 13.736717, 100.533100
        dist = calculate_distance(lat, lon, lat, lon)
        self.assertEqual(dist, 0.0)

    def test_known_short_distance(self):
        # Point 1: 13.736717, 100.533100
        # Point 2: 13.736717 + ~0.00045 degrees lat (approx 50 meters north)
        p1 = (13.736717, 100.533100)
        p2 = (13.737167, 100.533100)
        dist = calculate_distance(p1[0], p1[1], p2[0], p2[1])
        # ~50.04 meters
        self.assertAlmostEqual(dist, 50.04, delta=0.5)

    def test_geofence_in_range(self):
        self.assertTrue(is_within_geofence(0.0, 100.0))
        self.assertTrue(is_within_geofence(50.5, 100.0))
        self.assertTrue(is_within_geofence(100.0, 100.0))

    def test_geofence_out_of_range(self):
        self.assertFalse(is_within_geofence(100.01, 100.0))
        self.assertFalse(is_within_geofence(250.0, 100.0))
        self.assertFalse(is_within_geofence(1500.0, 100.0))

if __name__ == '__main__':
    unittest.main()
