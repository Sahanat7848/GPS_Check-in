import io
import csv
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, redirect, url_for
from config import DATABASE_PATH
import database
import haversine

app = Flask(__name__)

# Initialize database on startup
database.init_db()

@app.route("/")
def index():
    """Client-side student check-in page for default or selected course."""
    course_code = request.args.get("course")
    all_courses = database.get_all_courses()
    
    selected_course = None
    if course_code:
        selected_course = database.get_course(course_code)
        
    if not selected_course and all_courses:
        selected_course = all_courses[0]
        
    return render_template("index.html", course=selected_course, all_courses=all_courses)

@app.route("/c/<course_code>")
def course_checkin(course_code):
    """
    Dedicated check-in URL for a specific course (e.g. /c/CS101).
    Students open this exact link to check into that course.
    """
    course = database.get_course(course_code)
    all_courses = database.get_all_courses()
    
    if not course:
        # Fallback to index if course not found
        return redirect(url_for("index"))
        
    return render_template("index.html", course=course, all_courses=all_courses)

@app.route("/instructor")
def instructor():
    """Instructor attendance dashboard with multi-course management."""
    all_courses = database.get_all_courses()
    default_config = database.get_classroom_config()
    return render_template("instructor.html", courses=all_courses, config=default_config)

# --- Course Management API ---

@app.route("/api/courses", methods=["GET", "POST"])
def api_courses():
    """List or create courses."""
    if request.method == "POST":
        data = request.get_json() or {}
        course_code = str(data.get("course_code", "")).strip().upper()
        course_name = str(data.get("course_name", "")).strip()
        target_lat = data.get("target_lat")
        target_lng = data.get("target_lng")
        radius_m = data.get("radius_m", 100.0)
        
        if not course_code:
            return jsonify({"success": False, "error": "กรุณากรอกรหัสวิชา (Course Code)"}), 400
        if not course_name:
            return jsonify({"success": False, "error": "กรุณากรอกชื่อรายวิชา (Course Name)"}), 400
            
        try:
            target_lat = float(target_lat)
            target_lng = float(target_lng)
            radius_m = float(radius_m)
            if not (-90 <= target_lat <= 90) or not (-180 <= target_lng <= 180):
                return jsonify({"success": False, "error": "พิกัดละติจูด/ลองจิจูดไม่ถูกต้อง"}), 400
            if radius_m <= 0:
                return jsonify({"success": False, "error": "รัศมีต้องมากกว่า 0 เมตร"}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "รูปแบบตัวเลขพิกัดหรือรัศมีไม่ถูกต้อง"}), 400
            
        existing = database.get_course(course_code)
        if existing:
            return jsonify({"success": False, "error": f"รหัสวิชา {course_code} มีอยู่ในระบบแล้ว"}), 409
            
        created = database.create_course(course_code, course_name, target_lat, target_lng, radius_m)
        return jsonify({"success": True, "course": created, "message": f"เพิ่มรายวิชา {course_code} เรียบร้อยแล้ว"})
        
    # GET method
    return jsonify({"success": True, "courses": database.get_all_courses()})

@app.route("/api/courses/<course_code>", methods=["GET", "PUT", "POST", "DELETE"])
def api_single_course(course_code):
    """Retrieve, update, or delete a specific course."""
    if request.method == "DELETE":
        success = database.delete_course(course_code)
        return jsonify({"success": success, "message": f"ลบรายวิชา {course_code} แล้ว" if success else "ไม่พบรายวิชา"})
        
    if request.method in ("PUT", "POST"):
        data = request.get_json() or {}
        course_name = str(data.get("course_name", "")).strip()
        target_lat = data.get("target_lat")
        target_lng = data.get("target_lng")
        radius_m = data.get("radius_m", 100.0)
        
        try:
            target_lat = float(target_lat)
            target_lng = float(target_lng)
            radius_m = float(radius_m)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "พิกัดหรือรัศมีไม่ถูกต้อง"}), 400
            
        updated = database.update_course(course_code, course_name, target_lat, target_lng, radius_m)
        if updated:
            return jsonify({"success": True, "course": updated, "message": "อัปเดตข้อมูลรายวิชาเรียบร้อยแล้ว"})
        return jsonify({"success": False, "error": "ไม่พบรายวิชาที่ต้องการแก้ไข"}), 404
        
    # GET
    course = database.get_course(course_code)
    if course:
        return jsonify({"success": True, "course": course})
    return jsonify({"success": False, "error": "ไม่พบรายวิชา"}), 404

# --- Student Check-in API ---

@app.route("/api/checkin", methods=["POST"])
def checkin():
    """
    FR-03: Process student check-in payload with Course awareness.
    FR-05: Haversine distance calculation using the course's target location.
    FR-06: Geofencing validation (<= course.radius_m).
    FR-07: Duplicate check for (student_id, course_code).
    FR-08: Data persistence to SQLite.
    FR-04: Immediate feedback with distance, status, and course details.
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "ไม่พบข้อมูลที่ส่งมา (Empty Payload)"}), 400
        
    student_id = str(data.get("student_id", "")).strip()
    student_name = str(data.get("name", "") or data.get("student_name", "")).strip()
    course_code = str(data.get("course_code", "")).strip().upper()
    user_lat = data.get("latitude")
    user_lng = data.get("longitude")
    
    # Fallback to first course if course_code is not specified
    if not course_code:
        courses = database.get_all_courses()
        course_code = courses[0]["course_code"] if courses else "CS101"
        
    course = database.get_course(course_code)
    if not course:
        return jsonify({"success": False, "error": f"ไม่พบรายวิชา {course_code} ในระบบ"}), 404
        
    # Validation (FR-02)
    if not student_id:
        return jsonify({"success": False, "error": "กรุณากรอกรหัสนักศึกษา (Student ID)"}), 400
    if not student_name:
        return jsonify({"success": False, "error": "กรุณากรอกชื่อ-นามสกุล (Name)"}), 400
    if user_lat is None or user_lng is None:
        return jsonify({"success": False, "error": "ไม่พบพิกัด GPS กรุณาเปิดสิทธิ์ Geolocation"}), 400
        
    try:
        user_lat = float(user_lat)
        user_lng = float(user_lng)
        if not (-90.0 <= user_lat <= 90.0) or not (-180.0 <= user_lng <= 180.0):
            return jsonify({"success": False, "error": "พิกัดละติจูดหรือลองจิจูดอยู่นอกช่วงที่ถูกต้อง"}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "รูปแบบพิกัดละติจูด/ลองจิจูดไม่ถูกต้อง"}), 400
        
    # FR-07: Duplicate Check per Course & Student
    existing_success = database.check_duplicate_checkin(student_id, course_code, check_today_only=True)
    if existing_success:
        return jsonify({
            "success": False,
            "duplicate": True,
            "status": "DUPLICATE",
            "course_code": course_code,
            "course_name": course["course_name"],
            "message": f"รหัสนักศึกษา {student_id} ({existing_success['student_name']}) ได้เช็กชื่อวิชา {course_code} สำเร็จไปแล้วในวันนี้ เวลา {existing_success['created_at']}",
            "previous_checkin": existing_success
        }), 409
        
    target_lat = course["target_lat"]
    target_lng = course["target_lng"]
    radius_m = course["radius_m"]
    
    # FR-05: Haversine Calculation
    distance_m = haversine.calculate_distance(user_lat, user_lng, target_lat, target_lng)
    
    # FR-06: Geofencing validation
    is_in_range = haversine.is_within_geofence(distance_m, radius_m)
    status = "SUCCESS" if is_in_range else "OUT_OF_RANGE"
    
    # FR-08: Data persistence
    record_id = database.insert_checkin_record(
        student_id=student_id,
        student_name=student_name,
        user_lat=user_lat,
        user_lng=user_lng,
        distance_m=distance_m,
        status=status,
        course_code=course_code
    )
    
    # FR-04: Immediate feedback
    if is_in_range:
        message = f"เช็กชื่อวิชา {course_code} สำเร็จ! คุณอยู่ห่างจากห้องเรียน {distance_m:.1f} เมตร (อยู่ในรัศมี {radius_m:.0f} ม.)"
        return jsonify({
            "success": True,
            "record_id": record_id,
            "status": status,
            "course_code": course_code,
            "course_name": course["course_name"],
            "distance_m": distance_m,
            "radius_m": radius_m,
            "student_id": student_id,
            "student_name": student_name,
            "message": message,
            "in_range": True
        }), 200
    else:
        message = f"อยู่นอกพื้นที่เช็กชื่อวิชา {course_code}! คุณอยู่ห่างจากห้องเรียน {distance_m:.1f} เมตร (เกินกำหนด {radius_m:.0f} ม.)"
        return jsonify({
            "success": False,
            "record_id": record_id,
            "status": status,
            "course_code": course_code,
            "course_name": course["course_name"],
            "distance_m": distance_m,
            "radius_m": radius_m,
            "student_id": student_id,
            "student_name": student_name,
            "message": message,
            "in_range": False
        }), 200

# --- Dashboard & CSV APIs ---

@app.route("/api/records", methods=["GET"])
def get_records():
    """FR-09: Get checkin records with course, status & search filtering."""
    course = request.args.get("course")
    status = request.args.get("status")
    search = request.args.get("search")
    
    records = database.get_all_records(course_code=course, status_filter=status, search_query=search)
    stats = database.get_attendance_stats(course_code=course)
    return jsonify({
        "success": True,
        "records": records,
        "stats": stats,
        "count": len(records),
        "course": course
    })

@app.route("/api/export-csv", methods=["GET"])
def export_csv():
    """
    FR-11: Export attendance records in CSV format with UTF-8 BOM, including Course info.
    """
    course = request.args.get("course")
    status = request.args.get("status")
    search = request.args.get("search")
    
    records = database.get_all_records(course_code=course, status_filter=status, search_query=search)
    
    output = io.StringIO()
    output.write("\ufeff")  # UTF-8 BOM for Thai language Excel support
    
    writer = csv.writer(output)
    writer.writerow([
        "ลำดับ",
        "รหัสวิชา",
        "ชื่อรายวิชา",
        "รหัสนักศึกษา",
        "ชื่อ-นามสกุล",
        "ละติจูด (User Lat)",
        "ลองจิจูด (User Lng)",
        "ระยะห่าง (เมตร)",
        "สถานะ",
        "ผลการเข้าเรียน",
        "วันเวลาที่บันทึก (Local Time)"
    ])
    
    for idx, r in enumerate(records, start=1):
        thai_status = "เช็กชื่อสำเร็จ (ในห้องเรียน)" if r["status"] == "SUCCESS" else "อยู่นอกพื้นที่"
        writer.writerow([
            idx,
            r.get("course_code", "-"),
            r.get("course_name") or "-",
            r["student_id"],
            r["student_name"],
            f"{r['user_lat']:.6f}",
            f"{r['user_lng']:.6f}",
            f"{r['distance_m']:.2f}",
            r["status"],
            thai_status,
            r.get("created_at_local", r["created_at"])
        ])
        
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    course_tag = f"_{course.upper()}" if course else "_ALL"
    filename = f"attendance{course_tag}_{date_str}.csv"
    
    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route("/api/config", methods=["GET", "POST"])
def classroom_config():
    """Backward-compatible classroom config endpoint."""
    if request.method == "POST":
        data = request.get_json() or {}
        try:
            target_lat = float(data.get("target_lat"))
            target_lng = float(data.get("target_lng"))
            radius_m = float(data.get("radius_m", 100.0))
            updated = database.update_classroom_config(target_lat, target_lng, radius_m)
            return jsonify({"success": True, "config": updated, "message": "อัปเดตเรียบร้อยแล้ว"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400
    return jsonify(database.get_classroom_config())

@app.route("/api/reset-records", methods=["POST"])
def reset_records():
    """Reset all records."""
    database.clear_all_records()
    return jsonify({"success": True, "message": "ล้างข้อมูลประวัติการเช็กชื่อทั้งหมดแล้ว"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    print(f"Starting GPS Check-in System on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
