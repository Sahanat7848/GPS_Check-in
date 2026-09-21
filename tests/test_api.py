import os
import unittest
import json
import tempfile
import database
from app import app

class TestGPSCheckInAPI(unittest.TestCase):
    def setUp(self):
        # Create a temporary database for isolation
        self.db_fd, self.db_path = tempfile.mkstemp()
        database.DATABASE_PATH = self.db_path
        database.init_db(self.db_path)
        
        # Configure app for testing
        app.config['TESTING'] = True
        self.client = app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_classroom_config_api(self):
        # GET config
        res = self.client.get('/api/config')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('target_lat', data)
        self.assertIn('target_lng', data)
        self.assertEqual(data['radius_m'], 100.0)

        # POST update config
        res = self.client.post('/api/config', json={
            'target_lat': 13.750000,
            'target_lng': 100.500000,
            'radius_m': 150.0
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['config']['radius_m'], 150.0)

    def test_checkin_in_range_success(self):
        # Target is at 13.750000, 100.500000 with radius 150m
        self.client.post('/api/config', json={
            'target_lat': 13.750000,
            'target_lng': 100.500000,
            'radius_m': 100.0
        })

        # User is only ~15 meters away
        res = self.client.post('/api/checkin', json={
            'student_id': '66010001',
            'name': 'สมชาย ทดสอบ',
            'latitude': 13.750100,
            'longitude': 100.500050
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'SUCCESS')
        self.assertTrue(data['in_range'])
        self.assertLessEqual(data['distance_m'], 100.0)
        self.assertIn('เช็กชื่อสำเร็จ', data['message'])

    def test_checkin_duplicate_prevention(self):
        # First checkin
        res1 = self.client.post('/api/checkin', json={
            'student_id': '66010002',
            'name': 'สมหญิง เช็กชื่อ',
            'latitude': 13.736717,
            'longitude': 100.533100
        })
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(json.loads(res1.data)['status'], 'SUCCESS')

        # Duplicate checkin with same student_id
        res2 = self.client.post('/api/checkin', json={
            'student_id': '66010002',
            'name': 'สมหญิง เช็กชื่อ',
            'latitude': 13.736717,
            'longitude': 100.533100
        })
        self.assertEqual(res2.status_code, 409)
        data2 = json.loads(res2.data)
        self.assertFalse(data2['success'])
        self.assertTrue(data2['duplicate'])
        self.assertEqual(data2['status'], 'DUPLICATE')
        self.assertIn('ได้เช็กชื่อสำเร็จไปแล้ว', data2['message'])

    def test_checkin_out_of_range(self):
        # User is at 13.780000 (~4.8 km away)
        res = self.client.post('/api/checkin', json={
            'student_id': '66010099',
            'name': 'สมปอง อยู่นอกพื้นที่',
            'latitude': 13.780000,
            'longitude': 100.533100
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['status'], 'OUT_OF_RANGE')
        self.assertFalse(data['in_range'])
        self.assertGreater(data['distance_m'], 100.0)
        self.assertIn('อยู่นอกพื้นที่', data['message'])

    def test_checkin_validation_errors(self):
        # Missing student_id
        res = self.client.post('/api/checkin', json={
            'name': 'ไม่มีรหัส',
            'latitude': 13.736717,
            'longitude': 100.533100
        })
        self.assertEqual(res.status_code, 400)

        # Missing name
        res = self.client.post('/api/checkin', json={
            'student_id': '66010055',
            'latitude': 13.736717,
            'longitude': 100.533100
        })
        self.assertEqual(res.status_code, 400)

        # Missing latitude / longitude
        res = self.client.post('/api/checkin', json={
            'student_id': '66010055',
            'name': 'ไม่มี GPS'
        })
        self.assertEqual(res.status_code, 400)

    def test_export_csv(self):
        # Insert a record first
        self.client.post('/api/checkin', json={
            'student_id': '66010088',
            'name': 'มานะ อดทน',
            'latitude': 13.736717,
            'longitude': 100.533100
        })

        res = self.client.get('/api/export-csv')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/csv', res.content_type)
        
        # Check UTF-8 BOM
        self.assertTrue(res.data.startswith(b'\xef\xbb\xbf'))
        content = res.data.decode('utf-8')
        self.assertIn('รหัสนักศึกษา', content)
        self.assertIn('66010088', content)
        self.assertIn('มานะ อดทน', content)

if __name__ == '__main__':
    unittest.main()
