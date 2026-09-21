import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from config import DATABASE_PATH, DEFAULT_TARGET_LAT, DEFAULT_TARGET_LNG, DEFAULT_RADIUS_METERS

def get_db_connection(db_path: str = DATABASE_PATH) -> sqlite3.Connection:
    """Create a database connection with row factory returning dict-like objects."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = DATABASE_PATH) -> None:
    """Initialize database tables according to the required schema."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. courses table for multi-course support
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT UNIQUE NOT NULL,
                course_name TEXT NOT NULL,
                target_lat REAL NOT NULL,
                target_lng REAL NOT NULL,
                radius_m REAL NOT NULL DEFAULT 100.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. checkin_records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkin_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code TEXT NOT NULL DEFAULT 'CS101',
                student_id TEXT NOT NULL,
                student_name TEXT NOT NULL,
                user_lat REAL NOT NULL,
                user_lng REAL NOT NULL,
                distance_m REAL NOT NULL,
                status TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Check if course_code column exists in checkin_records (migration check)
        cursor.execute("PRAGMA table_info(checkin_records)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "course_code" not in columns:
            cursor.execute("ALTER TABLE checkin_records ADD COLUMN course_code TEXT NOT NULL DEFAULT 'CS101'")

        # 3. Default classroom_config table (backward compatibility)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classroom_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                target_lat REAL NOT NULL,
                target_lng REAL NOT NULL,
                radius_m REAL NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("SELECT id FROM classroom_config WHERE id = 1")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO classroom_config (id, target_lat, target_lng, radius_m)
                VALUES (1, ?, ?, ?)
            """, (DEFAULT_TARGET_LAT, DEFAULT_TARGET_LNG, DEFAULT_RADIUS_METERS))
            
        # Seed default courses if empty
        cursor.execute("SELECT COUNT(*) FROM courses")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO courses (course_code, course_name, target_lat, target_lng, radius_m)
                VALUES 
                ('CS101', 'การเขียนโปรแกรมคอมพิวเตอร์เบื้องต้น', ?, ?, 100.0),
                ('IT202', 'การพัฒนาเว็บแอปพลิเคชัน', ?, ?, 80.0)
            """, (DEFAULT_TARGET_LAT, DEFAULT_TARGET_LNG, DEFAULT_TARGET_LAT + 0.0008, DEFAULT_TARGET_LNG + 0.0005))

        conn.commit()

# --- Course CRUD Operations ---

def get_all_courses(db_path: str = DATABASE_PATH) -> List[Dict[str, Any]]:
    """Retrieve all available courses."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, course_code, course_name, target_lat, target_lng, radius_m, created_at FROM courses ORDER BY id ASC")
        return [dict(row) for row in cursor.fetchall()]

def get_course(course_code: str, db_path: str = DATABASE_PATH) -> Optional[Dict[str, Any]]:
    """Retrieve a specific course by its unique course code (case-insensitive)."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, course_code, course_name, target_lat, target_lng, radius_m, created_at
            FROM courses 
            WHERE UPPER(course_code) = UPPER(?)
        """, (course_code.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_course(
    course_code: str,
    course_name: str,
    target_lat: float,
    target_lng: float,
    radius_m: float = 100.0,
    db_path: str = DATABASE_PATH
) -> Dict[str, Any]:
    """Create a new course."""
    clean_code = course_code.strip().upper()
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO courses (course_code, course_name, target_lat, target_lng, radius_m)
            VALUES (?, ?, ?, ?, ?)
        """, (clean_code, course_name.strip(), target_lat, target_lng, radius_m))
        conn.commit()
    return get_course(clean_code, db_path)

def update_course(
    course_code: str,
    course_name: str,
    target_lat: float,
    target_lng: float,
    radius_m: float,
    db_path: str = DATABASE_PATH
) -> Optional[Dict[str, Any]]:
    """Update course details, location and radius."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE courses
            SET course_name = ?, target_lat = ?, target_lng = ?, radius_m = ?
            WHERE UPPER(course_code) = UPPER(?)
        """, (course_name.strip(), target_lat, target_lng, radius_m, course_code.strip()))
        conn.commit()
    return get_course(course_code, db_path)

def delete_course(course_code: str, db_path: str = DATABASE_PATH) -> bool:
    """Delete a course by course_code."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM courses WHERE UPPER(course_code) = UPPER(?)", (course_code.strip(),))
        conn.commit()
        return cursor.rowcount > 0

# --- Check-in Operations ---

def check_duplicate_checkin(
    student_id: str,
    course_code: str,
    check_today_only: bool = True,
    db_path: str = DATABASE_PATH
) -> Optional[Dict[str, Any]]:
    """
    FR-07: Duplicate Check - Prevent duplicate check-in.
    Checks whether this student_id has already checked in successfully today FOR THIS COURSE.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        if check_today_only:
            cursor.execute("""
                SELECT id, course_code, student_id, student_name, distance_m, status, created_at
                FROM checkin_records
                WHERE student_id = ?
                  AND UPPER(course_code) = UPPER(?)
                  AND status = 'SUCCESS'
                  AND date(created_at, 'localtime') = date('now', 'localtime')
                ORDER BY id DESC
                LIMIT 1
            """, (student_id.strip(), course_code.strip()))
        else:
            cursor.execute("""
                SELECT id, course_code, student_id, student_name, distance_m, status, created_at
                FROM checkin_records
                WHERE student_id = ?
                  AND UPPER(course_code) = UPPER(?)
                  AND status = 'SUCCESS'
                ORDER BY id DESC
                LIMIT 1
            """, (student_id.strip(), course_code.strip()))
        row = cursor.fetchone()
        return dict(row) if row else None

def insert_checkin_record(
    student_id: str,
    student_name: str,
    user_lat: float,
    user_lng: float,
    distance_m: float,
    status: str,
    course_code: str = "CS101",
    db_path: str = DATABASE_PATH
) -> int:
    """FR-08: Data Persistence - Save checkin record into SQLite immediately."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO checkin_records (
                course_code, student_id, student_name, user_lat, user_lng, distance_m, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (course_code.strip().upper(), student_id.strip(), student_name.strip(), user_lat, user_lng, distance_m, status))
        conn.commit()
        return cursor.lastrowid

def get_all_records(
    course_code: Optional[str] = None,
    status_filter: Optional[str] = None,
    search_query: Optional[str] = None,
    db_path: str = DATABASE_PATH
) -> List[Dict[str, Any]]:
    """
    FR-09: Summary Table - Fetch records sorted by created_at descending (newest first).
    Supports filtering by course_code, status, and search query.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        query = """
            SELECT r.id, r.course_code, c.course_name, r.student_id, r.student_name,
                   r.user_lat, r.user_lng, r.distance_m, r.status,
                   datetime(r.created_at, 'localtime') as created_at_local,
                   r.created_at
            FROM checkin_records r
            LEFT JOIN courses c ON UPPER(r.course_code) = UPPER(c.course_code)
            WHERE 1=1
        """
        params = []
        
        if course_code:
            query += " AND UPPER(r.course_code) = UPPER(?)"
            params.append(course_code.strip())
            
        if status_filter and status_filter.upper() in ("SUCCESS", "OUT_OF_RANGE"):
            query += " AND r.status = ?"
            params.append(status_filter.upper())
            
        if search_query:
            term = f"%{search_query.strip()}%"
            query += " AND (r.student_id LIKE ? OR r.student_name LIKE ?)"
            params.extend([term, term])
            
        query += " ORDER BY r.id DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_attendance_stats(course_code: Optional[str] = None, db_path: str = DATABASE_PATH) -> Dict[str, Any]:
    """Calculate summary statistics for instructor dashboard, optionally filtered by course."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        where_clause = ""
        params = []
        if course_code:
            where_clause = " WHERE UPPER(course_code) = UPPER(?)"
            params.append(course_code.strip())

        cursor.execute(f"SELECT COUNT(*) FROM checkin_records{where_clause}", params)
        total_attempts = cursor.fetchone()[0]
        
        succ_clause = " WHERE status = 'SUCCESS'"
        if course_code:
            succ_clause += " AND UPPER(course_code) = UPPER(?)"
        cursor.execute(f"SELECT COUNT(*) FROM checkin_records{succ_clause}", params)
        total_success = cursor.fetchone()[0]
        
        out_clause = " WHERE status = 'OUT_OF_RANGE'"
        if course_code:
            out_clause += " AND UPPER(course_code) = UPPER(?)"
        cursor.execute(f"SELECT COUNT(*) FROM checkin_records{out_clause}", params)
        total_out_of_range = cursor.fetchone()[0]
        
        dist_clause = " WHERE status = 'SUCCESS'"
        if course_code:
            dist_clause += " AND UPPER(course_code) = UPPER(?)"
        cursor.execute(f"SELECT COUNT(DISTINCT student_id) FROM checkin_records{dist_clause}", params)
        unique_students = cursor.fetchone()[0]
        
        success_rate = 0.0
        if total_attempts > 0:
            success_rate = round((total_success / total_attempts) * 100, 1)
            
        return {
            "total_attempts": total_attempts,
            "total_success": total_success,
            "total_out_of_range": total_out_of_range,
            "unique_students": unique_students,
            "success_rate": success_rate
        }

def clear_all_records(db_path: str = DATABASE_PATH) -> None:
    """Clear all records for testing and reset purposes."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM checkin_records")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'checkin_records'")
        conn.commit()

# Backward compatibility config functions
def get_classroom_config(db_path: str = DATABASE_PATH) -> Dict[str, Any]:
    courses = get_all_courses(db_path)
    if courses:
        first = courses[0]
        return {
            "target_lat": first["target_lat"],
            "target_lng": first["target_lng"],
            "radius_m": first["radius_m"],
            "course_code": first["course_code"],
            "course_name": first["course_name"]
        }
    return {
        "target_lat": DEFAULT_TARGET_LAT,
        "target_lng": DEFAULT_TARGET_LNG,
        "radius_m": DEFAULT_RADIUS_METERS,
        "course_code": "DEFAULT",
        "course_name": "ทั่วไป"
    }

def update_classroom_config(lat: float, lng: float, radius: float, db_path: str = DATABASE_PATH) -> Dict[str, Any]:
    courses = get_all_courses(db_path)
    if courses:
        update_course(courses[0]["course_code"], courses[0]["course_name"], lat, lng, radius, db_path)
    return get_classroom_config(db_path)
