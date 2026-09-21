# ระบบเช็กชื่อเข้าเรียนด้วยพิกัด GPS (GPS Check-in System)

ระบบเว็บแอปพลิเคชันสำหรับเช็กชื่อเข้าเรียนด้วยการตรวจสอบพิกัดตำแหน่งจริงของนักศึกษา (Client-side HTML5 Geolocation API + Geofencing ด้วยสูตร Haversine) ป้องกันการเช็กชื่อนอกห้องเรียนและป้องกันการกดเช็กชื่อซ้ำ พร้อมแดชบอร์ดสรุปผลและส่งออกข้อมูลเป็น CSV สำหรับผู้สอน

---

## คุณสมบัติเด่นของระบบ (Key Features)

### 1. ฝั่งผู้เรียน / ผู้ใช้งาน (Client-side Check-in)
- **FR-01 (HTML5 Geolocation API)**: ร้องขอสิทธิ์และอ่านค่า Latitude & Longitude แบบความแม่นยำสูง (High Accuracy) พร้อมคำนวณ Accuracy (เมตร)
- **FR-02 (Form Validation)**: ฟอร์มระบุรหัสนักศึกษา (Student ID) และชื่อ-นามสกุล พร้อมตรวจสอบความถูกต้องก่อนส่ง
- **FR-03 (Payload Submission)**: ส่งข้อมูลแบบ JSON ผ่าน `fetch()` POST ไปยังเซิร์ฟเวอร์
- **FR-04 (Immediate Feedback & Status)**:
  - **สำเร็จ (In Range)**: กล่องแจ้งเตือนสีเขียวเรืองแสง ระบุระยะห่างจริงจากห้องเรียน (เช่น "คุณอยู่ห่าง 35.4 เมตร")
  - **อยู่นอกพื้นที่ (Out of Range)**: กล่องแจ้งเตือนสีแดงเตือนระยะห่างจริง (เช่น "คุณอยู่นอกพื้นที่เช็กชื่อ ระยะห่าง 245.8 เมตร")
  - **Error Handling**: แจ้งเตือนชัดเจนกรณีผู้ใช้ปฏิเสธสิทธิ์ (User Denied), GPS ขัดข้อง (Position Unavailable), หรือหมดเวลา (Timeout)
- **GPS Simulation Presets**: แถบปุ่มจำลองพิกัด 1-click สำหรับทดสอบบนคอมพิวเตอร์ได้ทันที (ในห้องเรียน, หน้าตึก, โรงอาหาร, หอพัก)

### 2. ฝั่งเซิร์ฟเวอร์และฐานข้อมูล (Backend Logic)
- **FR-05 (Haversine Formula Calculation)**: คำนวณระยะทางทรงกลมระหว่างพิกัดห้องเรียนและพิกัดผู้ใช้ตามสูตรคณิตศาสตร์ Haversine Formula (หน่วยเป็นเมตร)
- **FR-06 (Geofencing Validation)**: ตรวจสอบเงื่อนไขระยะห่าง $\le 100$ เมตร (ปรับเปลี่ยนระยะได้ผ่านแดชบอร์ด)
- **FR-07 (Duplicate Check)**: ป้องกันการกดเช็กชื่อซ้ำ โดยตรวจสอบว่ารหัสนักศึกษานี้เคยเช็กชื่อสำเร็จในวันเดียวกันไปแล้วหรือไม่ (HTTP 409 Conflict)
- **FR-08 (Data Persistence)**: บันทึกข้อมูลลงฐานข้อมูล SQLite (`database.db`) ทันที

### 3. ฝั่งผู้สอน / ผู้ดูแลระบบ (Instructor Dashboard)
- **FR-09 (Summary Table)**: ตารางรายชื่อผู้เข้าเรียน เรียงตามเวลาล่าสุด แสดงรหัส, ชื่อ, ระยะห่าง, พิกัด และเวลา
- **FR-10 (Attendance Status & Live Stats)**: แถบสรุปสถิติสด (จำนวนผู้เช็กชื่อทั้งหมด, สำเร็จ, อยู่นอกพื้นที่, อัตราส่วนร้อยละ) พร้อมระบบค้นหาและกรองสถานะ
- **FR-11 (Export Data to CSV)**: ดาวน์โหลดข้อมูลเป็นไฟล์ `.csv` พร้อม **UTF-8 with BOM (`\ufeff`)** เปิดดูในโปรแกรม Microsoft Excel ภาษาไทยได้ทันที ไม่เป็นภาษาต่างดาว
- **Classroom Target Config**: ผู้สอนสามารถเปลี่ยนพิกัดห้องเรียนเป้าหมาย และปรับรัศมีอนุญาตได้ผ่านหน้าเว็บ หรือกดปุ่ม "📍 ใช้พิกัดปัจจุบันของฉัน" เพื่อตั้งค่าห้องเรียนอัตโนมัติ

---

## โครงสร้างโปรเจกต์ (Project Structure)

```
GPS_Check-in/
├── app.py                     # Flask Main Application & REST API
├── database.py                # SQLite Database CRUD & Duplicate check
├── haversine.py               # Haversine distance formula calculation
├── config.py                  # ค่าพิกัดห้องเรียนเริ่มต้น และ Database path
├── requirements.txt           # Python dependencies (Flask)
├── static/
│   ├── css/
│   │   ├── style.css          # สไตล์หลัก Mobile-First, Glassmorphism & Animations
│   │   └── instructor.css     # สไตล์แดชบอร์ดอาจารย์ และตารางข้อมูล
│   └── js/
│       ├── checkin.js         # Geolocation API, form handling & feedback UI
│       └── instructor.js      # ดึงข้อมูลแดชบอร์ด, ค้นหา/กรอง, ปรับค่าพิกัด และส่งออก CSV
├── templates/
│   ├── index.html             # หน้าเว็บเช็กชื่อนักศึกษา (Mobile-First)
│   └── instructor.html        # หน้าเว็บแดชบอร์ดผู้สอน
├── tests/
│   ├── test_haversine.py      # Unit tests สูตร Haversine
│   └── test_api.py            # Integration tests API และกรณีต่างๆ
└── README.md
```

---

## การติดตั้งและรันระบบ (Installation & Running)

### 1. ติดตั้ง Virtual Environment และ Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. เริ่มต้นรันเซิร์ฟเวอร์
```bash
python3 app.py
```
- หน้าเช็กชื่อนักศึกษา: [http://127.0.0.1:5001/](http://127.0.0.1:5001/)
- หน้าแดชบอร์ดผู้สอน: [http://127.0.0.1:5001/instructor](http://127.0.0.1:5001/instructor)

---

## คู่มือการทดสอบระบบ (Testing Guide)

### วิธีที่ 1: รัน Automated Tests
ทดสอบครอบคลุมทั้งสูตรคณิตศาสตร์ Haversine, Geofence, Duplicate Check, Validations, และ CSV Export:
```bash
./venv/bin/python -m unittest discover -s tests -p "test_*.py" -v
```

### วิธีที่ 2: ทดสอบด้วยปุ่มจำลองพิกัดบนหน้าเว็บ (Built-in Quick Presets)
เปิดหน้าเว็บ [http://127.0.0.1:5001/](http://127.0.0.1:5001/) แล้วเลื่อนลงมาที่แถบ **"ทดสอบพิกัดจำลอง (Test GPS Presets)"**:
- คลิก **"ในห้องเรียน (~15 ม.)"** -> กรอกชื่อ -> กดเช็กชื่อ -> ผลลัพธ์ **สำเร็จ (In Range)**
- คลิก **"โรงอาหาร (~340 ม.)"** -> กรอกชื่อ -> กดเช็กชื่อ -> ผลลัพธ์ **อยู่นอกพื้นที่ (Out of Range)**
- ลองกรอกรหัสนักศึกษาเดิมที่เคยเช็กชื่อผ่านไปแล้ว -> ผลลัพธ์ **เคยเช็กชื่อไปแล้ว (Duplicate)**

### วิธีที่ 3: ทดสอบจำลองพิกัดด้วย Chrome DevTools Sensors
1. เปิด Google Chrome แล้วไปที่ `http://127.0.0.1:5001/`
2. กด `F12` หรือคลิกขวาเลือก **Inspect (ตรวจสอบ)**
3. กดปุ่ม `Esc` เพื่อเปิดแผงด้านล่าง -> คลิกไอคอนเมนูสามจุดข้างซ้ายของ Console -> เลือก **Sensors**
4. ในส่วน **Location**:
   - เลือก **Other...** แล้วใส่พิกัดทดสอบ:
     - **ในห้องเรียน**: Latitude `13.736717`, Longitude `100.533100`
     - **นอกรัศมี**: Latitude `13.740000`, Longitude `100.533100`
5. กดปุ่ม **"รีเฟรชพิกัด GPS"** บนหน้าเว็บเพื่ออ่านค่าจาก DevTools Sensors

### วิธีที่ 4: ทดสอบผ่านสมาร์ตโฟนจริงในเครือข่าย Wi-Fi (NFR-01: HTTPS / Tunneling)
เนื่องจาก Geolocation API ของเบราว์เซอร์มือถือต้องทำงานบน HTTPS เมื่อไม่ได้เปิดบน `localhost` สามารถเปิดผ่าน Tunneling ได้ง่ายๆ เช่น:

#### ใช้ Cloudflare Tunnel (ฟรีและไม่ต้องสมัครสมาชิก):
```bash
npx untun@latest tunnel http://localhost:5001
# หรือใช้ cloudflared
cloudflared tunnel --url http://localhost:5001
```
#### หรือใช้ ngrok:
```bash
ngrok http 5001
```
นำลิงก์ HTTPS ที่ได้ไปเปิดบน Safari (iOS) หรือ Chrome (Android) ในมือถือได้ทันที
