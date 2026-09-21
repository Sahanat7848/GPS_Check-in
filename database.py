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
        
        # 1. checkin_records table as specified in FR-08 and Section 4
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkin_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                student_name TEXT NOT NULL,
                user_lat REAL NOT NULL,
                user_lng REAL NOT NULL,
                distance_m REAL NOT NULL,
                status TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. classroom_config table to persist target coordinates and geofence radius
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classroom_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                target_lat REAL NOT NULL,
                target_lng REAL NOT NULL,
                radius_m REAL NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default config if not exists
        cursor.execute("SELECT id FROM classroom_config WHERE id = 1")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO classroom_config (id, target_lat, target_lng, radius_m)
                VALUES (1, ?, ?, ?)
            """, (DEFAULT_TARGET_LAT, DEFAULT_TARGET_LNG, DEFAULT_RADIUS_METERS))
            
        conn.commit()

def get_classroom_config(db_path: str = DATABASE_PATH) -> Dict[str, Any]:
    """Retrieve the current classroom target coordinates and radius."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT target_lat, target_lng, radius_m, updated_at FROM classroom_config WHERE id = 1")
        row = cursor.fetchone()
        if row:
            return {
                "target_lat": float(row["target_lat"]),
                "target_lng": float(row["target_lng"]),
                "radius_m": float(row["radius_m"]),
                "updated_at": row["updated_at"]
            }
        return {
            "target_lat": DEFAULT_TARGET_LAT,
            "target_lng": DEFAULT_TARGET_LNG,
            "radius_m": DEFAULT_RADIUS_METERS,
            "updated_at": datetime.now().isoformat()
        }

def update_classroom_config(lat: float, lng: float, radius: float, db_path: str = DATABASE_PATH) -> Dict[str, Any]:
    """Update classroom target coordinates and geofence radius."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE classroom_config 
            SET target_lat = ?, target_lng = ?, radius_m = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (lat, lng, radius))
        conn.commit()
    return get_classroom_config(db_path)

def check_duplicate_checkin(student_id: str, check_today_only: bool = True, db_path: str = DATABASE_PATH) -> Optional[Dict[str, Any]]:
    """
    FR-07: Duplicate Check - Prevent duplicate check-in.
    Checks whether this student_id has already checked in successfully today.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        if check_today_only:
            # Check if successfully checked in on the same date (using local date)
            cursor.execute("""
                SELECT id, student_id, student_name, distance_m, status, created_at
                FROM checkin_records
                WHERE student_id = ? 
                  AND status = 'SUCCESS'
                  AND date(created_at, 'localtime') = date('now', 'localtime')
                ORDER BY id DESC
                LIMIT 1
            """, (student_id,))
        else:
            cursor.execute("""
                SELECT id, student_id, student_name, distance_m, status, created_at
                FROM checkin_records
                WHERE student_id = ? AND status = 'SUCCESS'
                ORDER BY id DESC
                LIMIT 1
            """, (student_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def insert_checkin_record(
    student_id: str,
    student_name: str,
    user_lat: float,
    user_lng: float,
    distance_m: float,
    status: str,
    db_path: str = DATABASE_PATH
) -> int:
    """FR-08: Data Persistence - Save checkin record into SQLite immediately."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO checkin_records (
                student_id, student_name, user_lat, user_lng, distance_m, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (student_id.strip(), student_name.strip(), user_lat, user_lng, distance_m, status))
        conn.commit()
        return cursor.lastrowid

def get_all_records(
    status_filter: Optional[str] = None,
    search_query: Optional[str] = None,
    db_path: str = DATABASE_PATH
) -> List[Dict[str, Any]]:
    """
    FR-09: Summary Table - Fetch records sorted by created_at descending (newest first).
    Supports optional status filtering and text search by student_id or student_name.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        query = """
            SELECT id, student_id, student_name, user_lat, user_lng, distance_m, status,
                   datetime(created_at, 'localtime') as created_at_local,
                   created_at
            FROM checkin_records
            WHERE 1=1
        """
        params = []
        
        if status_filter and status_filter.upper() in ("SUCCESS", "OUT_OF_RANGE"):
            query += " AND status = ?"
            params.append(status_filter.upper())
            
        if search_query:
            term = f"%{search_query.strip()}%"
            query += " AND (student_id LIKE ? OR student_name LIKE ?)"
            params.extend([term, term])
            
        query += " ORDER BY id DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_attendance_stats(db_path: str = DATABASE_PATH) -> Dict[str, Any]:
    """Calculate summary statistics for instructor dashboard."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM checkin_records")
        total_attempts = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM checkin_records WHERE status = 'SUCCESS'")
        total_success = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM checkin_records WHERE status = 'OUT_OF_RANGE'")
        total_out_of_range = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT student_id) FROM checkin_records WHERE status = 'SUCCESS'")
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
