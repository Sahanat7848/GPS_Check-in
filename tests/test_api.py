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

    def test_courses_api_crud(self):
        # GET courses (default seeded courses)
        res = self.client.get('/api/courses')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        codes = [c['course_code'] for c in data['courses']]
        self.assertIn('CS101', codes)

        # POST create new course
        res = self.client.post('/api/courses', json={
            'course_code': 'ENG201',
            'course_name': 'English for Communication',
            'target_lat': 13.736000,
            'target_lng': 100.533000,
            'radius_m': 120.0
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['course']['course_code'], 'ENG201')

        # Test duplicate course code rejected
        res_dup = self.client.post('/api/courses', json={
            'course_code': 'ENG201',
            'course_name': 'Another Course',
            'target_lat': 13.736000,
            'target_lng': 100.533000
        })
        self.assertEqual(res_dup.status_code, 409)

    def test_checkin_in_range_success(self):
        # Target for CS101 is around 13.736717, 100.533100
        res = self.client.post('/api/checkin', json={
            'course_code': 'CS101',
            'student_id': '66010001',
            'name': 'สมชาย ทดสอบ',
            'latitude': 13.736720,
            'longitude': 100.533105
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'SUCCESS')
        self.assertEqual(data['course_code'], 'CS101')
        self.assertTrue(data['in_range'])
        self.assertLessEqual(data['distance_m'], 100.0)

    def test_checkin_duplicate_prevention_per_course(self):
        # 1. First checkin to CS101 -> SUCCESS
        res1 = self.client.post('/api/checkin', json={
            'course_code': 'CS101',
            'student_id': '66010002',
            'name': 'สมหญิง เช็กชื่อ',
            'latitude': 13.736717,
            'longitude': 100.533100
        })
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(json.loads(res1.data)['status'], 'SUCCESS')

        # 2. Duplicate checkin with same student_id to SAME course CS101 -> 409 DUPLICATE
        res2 = self.client.post('/api/checkin', json={
            'course_code': 'CS101',
            'student_id': '66010002',
            'name': 'สมหญิง เช็กชื่อ',
            'latitude': 13.736717,
            'longitude': 100.533100
        })
        self.assertEqual(res2.status_code, 409)
        data2 = json.loads(res2.data)
        self.assertFalse(data2['success'])
        self.assertTrue(data2['duplicate'])

        # 3. Check-in to a DIFFERENT course (IT202) on same day -> SUCCESS (Allowed!)
        it202_course = database.get_course('IT202', self.db_path)
        res3 = self.client.post('/api/checkin', json={
            'course_code': 'IT202',
            'student_id': '66010002',
            'name': 'สมหญิง เช็กชื่อ',
            'latitude': it202_course['target_lat'],
            'longitude': it202_course['target_lng']
        })
        self.assertEqual(res3.status_code, 200)
        data3 = json.loads(res3.data)
        self.assertTrue(data3['success'])
        self.assertEqual(data3['course_code'], 'IT202')

    def test_checkin_out_of_range(self):
        # User is far away (~4.8 km)
        res = self.client.post('/api/checkin', json={
            'course_code': 'CS101',
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

    def test_export_csv_with_course(self):
        # Insert a record
        self.client.post('/api/checkin', json={
            'course_code': 'CS101',
            'student_id': '66010088',
            'name': 'มานะ อดทน',
            'latitude': 13.736717,
            'longitude': 100.533100
        })

        # Test export all
        res = self.client.get('/api/export-csv')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data.startswith(b'\xef\xbb\xbf'))
        content = res.data.decode('utf-8')
        self.assertIn('รหัสวิชา', content)
        self.assertIn('CS101', content)
        self.assertIn('66010088', content)

        # Test export filtered by course
        res_filtered = self.client.get('/api/export-csv?course=CS101')
        self.assertEqual(res_filtered.status_code, 200)
        self.assertIn('attachment; filename=attendance_CS101_', res_filtered.headers['Content-Disposition'])

if __name__ == '__main__':
    unittest.main()
