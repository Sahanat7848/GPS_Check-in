import io
import csv
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response
from config import DATABASE_PATH
import database
import haversine

app = Flask(__name__)

# Initialize database on startup
database.init_db()

@app.route("/")
def index():
    """Client-side student check-in page."""
    config = database.get_classroom_config()
    return render_template("index.html", config=config)

@app.route("/instructor")
def instructor():
    """Instructor attendance dashboard."""
    config = database.get_classroom_config()
    return render_template("instructor.html", config=config)

@app.route("/api/config", methods=["GET", "POST"])
def classroom_config():
    """Get or update classroom target coordinates and radius."""
    if request.method == "POST":
        data = request.get_json() or {}
        try:
            target_lat = float(data.get("target_lat"))
            target_lng = float(data.get("target_lng"))
            radius_m = float(data.get("radius_m", 100.0))
            
            if not (-90 <= target_lat <= 90) or not (-180 <= target_lng <= 180):
                return jsonify({"success": False, "error": "พิกัดละติจูดหรือลองจิจูดไม่ถูกต้อง"}), 400
            if radius_m <= 0:
                return jsonify({"success": False, "error": "รัศมีต้องมากกว่า 0 เมตร"}), 400
                
            updated = database.update_classroom_config(target_lat, target_lng, radius_m)
            return jsonify({"success": True, "config": updated, "message": "อัปเดตการตั้งค่าห้องเรียนเรียบร้อยแล้ว"})
        except (ValueError, TypeError) as e:
            return jsonify({"success": False, "error": f"ข้อมูลพิกัดไม่ถูกต้อง: {str(e)}"}), 400
            
    # GET method
    return jsonify(database.get_classroom_config())

@app.route("/api/checkin", methods=["POST"])
def checkin():
    """
    FR-03: Process student check-in payload.
    FR-05: Haversine distance calculation.
    FR-06: Geofencing validation (<= radius_m).
    FR-07: Duplicate check for student_id.
    FR-08: Data persistence to SQLite.
    FR-04: Immediate feedback with distance and status.
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "ไม่พบข้อมูลที่ส่งมา (Empty Payload)"}), 400
        
    student_id = str(data.get("student_id", "")).strip()
    student_name = str(data.get("name", "") or data.get("student_name", "")).strip()
    user_lat = data.get("latitude")
    user_lng = data.get("longitude")
    
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
        
    # FR-07: Duplicate Check
    existing_success = database.check_duplicate_checkin(student_id, check_today_only=True)
    if existing_success:
        return jsonify({
            "success": False,
            "duplicate": True,
            "status": "DUPLICATE",
            "message": f"รหัสนักศึกษา {student_id} ({existing_success['student_name']}) ได้เช็กชื่อสำเร็จไปแล้วในวันนี้ เวลา {existing_success['created_at']}",
            "previous_checkin": existing_success
        }), 409
        
    # Get active classroom target coordinates & allowed radius
    cfg = database.get_classroom_config()
    target_lat = cfg["target_lat"]
    target_lng = cfg["target_lng"]
    radius_m = cfg["radius_m"]
    
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
        status=status
    )
    
    # FR-04: Immediate feedback
    if is_in_range:
        message = f"เช็กชื่อสำเร็จ! คุณอยู่ห่างจากห้องเรียน {distance_m:.1f} เมตร (อยู่ในรัศมี {radius_m:.0f} ม.)"
        return jsonify({
            "success": True,
            "record_id": record_id,
            "status": status,
            "distance_m": distance_m,
            "radius_m": radius_m,
            "student_id": student_id,
            "student_name": student_name,
            "message": message,
            "in_range": True
        }), 200
    else:
        message = f"อยู่นอกพื้นที่เช็กชื่อ! คุณอยู่ห่างจากห้องเรียน {distance_m:.1f} เมตร (เกินกำหนด {radius_m:.0f} ม.)"
        return jsonify({
            "success": False,
            "record_id": record_id,
            "status": status,
            "distance_m": distance_m,
            "radius_m": radius_m,
            "student_id": student_id,
            "student_name": student_name,
            "message": message,
            "in_range": False
        }), 200

@app.route("/api/records", methods=["GET"])
def get_records():
    """FR-09: Get checkin records with filtering & search."""
    status = request.args.get("status")
    search = request.args.get("search")
    records = database.get_all_records(status_filter=status, search_query=search)
    stats = database.get_attendance_stats()
    return jsonify({
        "success": True,
        "records": records,
        "stats": stats,
        "count": len(records)
    })

@app.route("/api/export-csv", methods=["GET"])
def export_csv():
    """
    FR-11: Export Data in CSV format with UTF-8 BOM for Thai language Excel support.
    """
    status = request.args.get("status")
    search = request.args.get("search")
    records = database.get_all_records(status_filter=status, search_query=search)
    
    output = io.StringIO()
    # Write UTF-8 BOM for Excel compatibility
    output.write("\ufeff")
    
    writer = csv.writer(output)
    writer.writerow([
        "ลำดับ",
        "รหัสนักศึกษา",
        "ชื่อ-นามสกุล",
        "ละติจูด (User Lat)",
        "ลองจิจูด (User Lng)",
        "ระยะห่าง (เมตร)",
        "สถานะภาษาอังกฤษ",
        "สถานะการเข้าเรียน",
        "วันเวลาที่บันทึก (Local Time)"
    ])
    
    for idx, r in enumerate(records, start=1):
        thai_status = "เช็กชื่อสำเร็จ (ในห้องเรียน)" if r["status"] == "SUCCESS" else "อยู่นอกพื้นที่"
        writer.writerow([
            idx,
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
    filename = f"attendance_records_{date_str}.csv"
    
    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route("/api/reset-records", methods=["POST"])
def reset_records():
    """Reset all records (useful for testing sessions)."""
    database.clear_all_records()
    return jsonify({"success": True, "message": "ล้างข้อมูลประวัติการเช็กชื่อทั้งหมดแล้ว"})

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 5001))
    print(f"Starting GPS Check-in System on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
