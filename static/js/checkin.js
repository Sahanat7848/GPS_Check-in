// GPS Check-in Client-side Script (Multi-Course Aware)
document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const form = document.getElementById('checkin-form');
  const studentIdInput = document.getElementById('student_id');
  const studentNameInput = document.getElementById('student_name');
  const submitBtn = document.getElementById('submit-btn');
  const submitText = document.getElementById('submit-text');
  const submitSpinner = document.getElementById('submit-spinner');
  
  const refreshGpsBtn = document.getElementById('refresh-gps-btn');
  const gpsStatusBadge = document.getElementById('gps-status-badge');
  const gpsStatusText = document.getElementById('gps-status-text');
  const latDisplay = document.getElementById('lat-display');
  const lngDisplay = document.getElementById('lng-display');
  const accuracyDisplay = document.getElementById('accuracy-display');
  const radarCore = document.getElementById('radar-core');
  
  const feedbackCard = document.getElementById('feedback-card');
  const feedbackIcon = document.getElementById('feedback-icon');
  const feedbackTitle = document.getElementById('feedback-title');
  const feedbackDistNum = document.getElementById('feedback-distance-num');
  const feedbackDesc = document.getElementById('feedback-desc');
  const distanceHighlight = document.getElementById('distance-highlight');
  
  // State
  let currentCoordinates = null;
  let isSimulated = false;

  // Active Course Information
  const courseCode = window.CURRENT_COURSE?.course_code || 'CS101';
  const courseName = window.CURRENT_COURSE?.course_name || '';
  const targetLat = window.CURRENT_COURSE?.target_lat || 13.736717;
  const targetLng = window.CURRENT_COURSE?.target_lng || 100.533100;
  const targetRadius = window.CURRENT_COURSE?.radius_m || 100.0;

  // Initialize: request Geolocation automatically
  requestGeolocation();

  // FR-01: Request Geolocation through HTML5 Geolocation API
  function requestGeolocation() {
    isSimulated = false;
    updateGPSUI('loading', 'กำลังค้นหาสัญญาณ GPS...');
    
    if (!navigator.geolocation) {
      updateGPSUI('error', 'เบราว์เซอร์ไม่รองรับ Geolocation API');
      showFeedback('warning', 'เบราว์เซอร์ไม่รองรับ', 'เบราว์เซอร์นี้ไม่รองรับ HTML5 Geolocation API โปรดใช้ Chrome, Safari หรือ Edge');
      return;
    }

    const geoOptions = {
      enableHighAccuracy: true,
      timeout: 12000,
      maximumAge: 0
    };

    navigator.geolocation.getCurrentPosition(
      onGeoSuccess,
      onGeoError,
      geoOptions
    );
  }

  function onGeoSuccess(position) {
    const lat = position.coords.latitude;
    const lng = position.coords.longitude;
    const accuracy = position.coords.accuracy;

    currentCoordinates = { latitude: lat, longitude: lng, accuracy: accuracy };
    isSimulated = false;

    latDisplay.textContent = lat.toFixed(6);
    lngDisplay.textContent = lng.toFixed(6);
    accuracyDisplay.textContent = `ความแม่นยำ: ±${Math.round(accuracy)} เมตร`;

    updateGPSUI('active', 'ตรวจพบพิกัด GPS จริงแล้ว');
    radarCore.className = 'radar-core';
  }

  function onGeoError(error) {
    currentCoordinates = null;
    let errMsg = '';

    switch (error.code) {
      case error.PERMISSION_DENIED:
        errMsg = 'ถูกปฏิเสธสิทธิ์การเข้าถึงตำแหน่ง (User Denied)';
        showFeedback(
          'danger',
          'เบราว์เซอร์ถูกปฏิเสธสิทธิ์ GPS',
          'กรุณาเปิดการอนุญาตเข้าถึงตำแหน่ง (Location Permission) ในการตั้งค่าเบราว์เซอร์ของคุณ หรือทดสอบด้วยปุ่มจำลองพิกัดด้านล่าง'
        );
        break;
      case error.POSITION_UNAVAILABLE:
        errMsg = 'สัญญาณ GPS ขัดข้องหรือไม่พร้อมใช้งาน';
        showFeedback('danger', 'สัญญาณ GPS ขัดข้อง', 'ไม่สามารถระบุตำแหน่งของคุณได้ในขณะนี้ ตรวจสอบว่าเปิด GPS ในเครื่องแล้วหรือไม่');
        break;
      case error.TIMEOUT:
        errMsg = 'หมดเวลาการค้นหาพิกัด GPS (Timeout)';
        showFeedback('warning', 'ค้นหาพิกัดนานเกินไป', 'การดึงพิกัด GPS ใช้เวลานานเกินไป ลองกด "รีเฟรชพิกัด" ใหม่อีกครั้ง');
        break;
      default:
        errMsg = 'เกิดข้อผิดพลาดในการอ่านพิกัด';
        showFeedback('danger', 'ข้อผิดพลาด GPS', `เกิดข้อผิดพลาดรหัส ${error.code}: ${error.message}`);
    }

    latDisplay.textContent = '---';
    lngDisplay.textContent = '---';
    accuracyDisplay.textContent = 'ไม่สามารถอ่านพิกัดได้';
    updateGPSUI('error', errMsg);
  }

  function updateGPSUI(status, text) {
    gpsStatusText.textContent = text;
    gpsStatusBadge.className = 'gps-badge ' + (status === 'loading' ? 'waiting' : status);
    
    if (status === 'active') {
      submitBtn.removeAttribute('disabled');
    }
  }

  refreshGpsBtn.addEventListener('click', (e) => {
    e.preventDefault();
    requestGeolocation();
  });

  // FR-02 & FR-03: Form Submission with course_code
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const studentId = studentIdInput.value.trim();
    const studentName = studentNameInput.value.trim();

    if (!studentId) {
      showFeedback('warning', 'ข้อมูลไม่ครบถ้วน', 'กรุณากรอกรหัสนักศึกษา (Student ID)');
      studentIdInput.focus();
      return;
    }

    if (!studentName) {
      showFeedback('warning', 'ข้อมูลไม่ครบถ้วน', 'กรุณากรอกชื่อ-นามสกุล (Name)');
      studentNameInput.focus();
      return;
    }

    if (!currentCoordinates) {
      showFeedback('danger', 'ยังไม่มีพิกัด GPS', 'กรุณารอรับพิกัด GPS หรือกด "รีเฟรชพิกัด GPS" ก่อนทำการเช็กชื่อ');
      return;
    }

    // Set UI to loading
    setSubmitting(true);
    hideFeedback();

    const payload = {
      course_code: courseCode,
      student_id: studentId,
      name: studentName,
      latitude: currentCoordinates.latitude,
      longitude: currentCoordinates.longitude
    };

    try {
      const response = await fetch('/api/checkin', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      // FR-04: Immediate Feedback & Status
      if (response.status === 200) {
        if (data.status === 'SUCCESS') {
          // Success (In Range)
          radarCore.className = 'radar-core success';
          showFeedback(
            'success',
            `เช็กชื่อวิชา ${data.course_code} สำเร็จ!`,
            `บันทึกข้อมูลเวลาเรียบร้อยแล้ว คุณอยู่ห่างจากห้องเรียน ${data.distance_m} เมตร (กำหนดไม่เกิน ${data.radius_m} ม.)`,
            data.distance_m
          );
        } else {
          // Out of Range
          radarCore.className = 'radar-core danger';
          showFeedback(
            'danger',
            `อยู่นอกพื้นที่เช็กชื่อวิชา ${data.course_code}!`,
            `ระยะห่างของคุณคือ ${data.distance_m} เมตร ซึ่งเกินกว่ารัศมีที่อนุญาต (${data.radius_m} เมตร) กรุณาเข้าไปในห้องเรียนแล้วลองใหม่`,
            data.distance_m
          );
        }
      } else if (response.status === 409 && data.duplicate) {
        // FR-07: Duplicate check alert
        radarCore.className = 'radar-core';
        showFeedback(
          'warning',
          'เคยเช็กชื่อไปแล้ว (Duplicate)',
          data.message || `รหัสนักศึกษานี้ได้เช็กชื่อวิชา ${courseCode} สำเร็จไปแล้วในรอบเวลานี้`
        );
      } else {
        // Server error or validation error
        radarCore.className = 'radar-core danger';
        showFeedback('danger', 'ไม่สามารถเช็กชื่อได้', data.error || 'เกิดข้อผิดพลาดจากเซิร์ฟเวอร์');
      }
    } catch (err) {
      console.error('Fetch error:', err);
      showFeedback('danger', 'ข้อผิดพลาดการเชื่อมต่อ', 'ไม่สามารถติดต่อเซิร์ฟเวอร์ได้ โปรดตรวจสอบการเชื่อมต่ออินเทอร์เน็ต');
    } finally {
      setSubmitting(false);
    }
  });

  function setSubmitting(isSubmitting) {
    submitBtn.disabled = isSubmitting;
    if (isSubmitting) {
      submitSpinner.style.display = 'inline-block';
      submitText.textContent = 'กำลังตรวจสอบพิกัด...';
    } else {
      submitSpinner.style.display = 'none';
      submitText.textContent = `เช็กชื่อเข้าเรียนวิชา ${courseCode}`;
    }
  }

  function showFeedback(type, title, desc, distance = null) {
    feedbackCard.className = `feedback-card ${type}`;
    feedbackTitle.textContent = title;
    feedbackDesc.textContent = desc;

    if (distance !== null) {
      distanceHighlight.style.display = 'flex';
      feedbackDistNum.textContent = Number(distance).toFixed(1);
    } else {
      distanceHighlight.style.display = 'none';
    }

    if (type === 'success') {
      feedbackIcon.innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>`;
    } else if (type === 'danger') {
      feedbackIcon.innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
    } else {
      feedbackIcon.innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
    }

    feedbackCard.style.display = 'block';
    feedbackCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function hideFeedback() {
    feedbackCard.style.display = 'none';
  }

  // Preset Simulation Handlers (Relative to the course's target location)
  window.setSimulationPreset = function(type) {
    let latOffset = 0;
    let lngOffset = 0;
    let desc = '';

    switch (type) {
      case 'classroom_inside': // ~15m (SUCCESS)
        latOffset = 0.00012;
        lngOffset = 0.00008;
        desc = `จำลอง: ในห้องเรียนวิชา ${courseCode} (~15 ม.)`;
        break;
      case 'classroom_front': // ~55m (SUCCESS)
        latOffset = 0.00040;
        lngOffset = 0.00025;
        desc = `จำลอง: หน้าห้องเรียนวิชา ${courseCode} (~55 ม.)`;
        break;
      case 'building_lobby': // ~88m (SUCCESS)
        latOffset = 0.00065;
        lngOffset = 0.00050;
        desc = 'จำลอง: ล็อบบี้ตึก (~88 ม.)';
        break;
      case 'cafeteria': // ~340m (OUT OF RANGE)
        latOffset = 0.0028;
        lngOffset = 0.0015;
        desc = 'จำลอง: โรงอาหาร (~340 ม.)';
        break;
      case 'dormitory': // ~1.2km (OUT OF RANGE)
        latOffset = 0.0105;
        lngOffset = 0.0040;
        desc = 'จำลอง: หอพัก (~1.2 กม.)';
        break;
      default:
        latOffset = 0;
        lngOffset = 0;
    }

    const simLat = targetLat + latOffset;
    const simLng = targetLng + lngOffset;

    currentCoordinates = {
      latitude: simLat,
      longitude: simLng,
      accuracy: 10
    };
    isSimulated = true;

    latDisplay.textContent = simLat.toFixed(6);
    lngDisplay.textContent = simLng.toFixed(6);
    accuracyDisplay.textContent = 'โหมดจำลองพิกัด (Simulated)';

    updateGPSUI('active', desc);
    submitBtn.removeAttribute('disabled');
    hideFeedback();
  };
});
