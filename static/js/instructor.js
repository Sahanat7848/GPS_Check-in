// Instructor Dashboard Logic (Multi-Course Support)
document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const recordsTableBody = document.getElementById('records-tbody');
  const searchInput = document.getElementById('search-input');
  const courseFilter = document.getElementById('course-filter');
  const statusFilter = document.getElementById('status-filter');
  const refreshBtn = document.getElementById('refresh-btn');
  const exportCsvBtn = document.getElementById('export-csv-btn');
  const resetBtn = document.getElementById('reset-btn');
  
  // Stat counters
  const totalCountEl = document.getElementById('stat-total');
  const successCountEl = document.getElementById('stat-success');
  const outRangeCountEl = document.getElementById('stat-out-range');
  const rateEl = document.getElementById('stat-rate');
  
  // Course Management Elements
  const courseCardsContainer = document.getElementById('course-cards-container');
  const toggleAddCourseBtn = document.getElementById('toggle-add-course-btn');
  const addCoursePanel = document.getElementById('add-course-panel');
  const submitNewCourseBtn = document.getElementById('submit-new-course-btn');
  const useMyGpsBtn = document.getElementById('use-my-gps-new-course');

  // Initial Load
  loadCourses();
  loadRecords();

  // Toggle Add Course Form
  toggleAddCourseBtn.addEventListener('click', () => {
    const isHidden = addCoursePanel.style.display === 'none' || !addCoursePanel.style.display;
    addCoursePanel.style.display = isHidden ? 'block' : 'none';
    toggleAddCourseBtn.textContent = isHidden ? '✕ ปิดฟอร์ม' : '➕ เพิ่มรายวิชาใหม่';
  });

  // Use My GPS for new course
  useMyGpsBtn.addEventListener('click', () => {
    if (!navigator.geolocation) {
      alert('เบราว์เซอร์ไม่รองรับ Geolocation');
      return;
    }
    useMyGpsBtn.textContent = 'กำลังดึงพิกัด...';
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        document.getElementById('new-course-lat').value = pos.coords.latitude.toFixed(6);
        document.getElementById('new-course-lng').value = pos.coords.longitude.toFixed(6);
        useMyGpsBtn.textContent = '📍 ใช้พิกัดปัจจุบัน';
      },
      (err) => {
        useMyGpsBtn.textContent = '📍 ใช้พิกัดปัจจุบัน';
        alert('ไม่สามารถอ่านพิกัดได้: ' + err.message);
      },
      { enableHighAccuracy: true }
    );
  });

  // Submit New Course
  submitNewCourseBtn.addEventListener('click', async () => {
    const code = document.getElementById('new-course-code').value.trim();
    const name = document.getElementById('new-course-name').value.trim();
    const lat = parseFloat(document.getElementById('new-course-lat').value);
    const lng = parseFloat(document.getElementById('new-course-lng').value);
    const radius = parseFloat(document.getElementById('new-course-radius').value);

    if (!code || !name) {
      alert('กรุณาระบุรหัสวิชาและชื่อวิชาให้ครบถ้วน');
      return;
    }
    if (isNaN(lat) || isNaN(lng) || isNaN(radius)) {
      alert('กรุณาระบุพิกัดและรัศมีเป็นตัวเลขที่ถูกต้อง');
      return;
    }

    try {
      const res = await fetch('/api/courses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          course_code: code,
          course_name: name,
          target_lat: lat,
          target_lng: lng,
          radius_m: radius
        })
      });
      const data = await res.json();
      if (data.success) {
        alert(data.message);
        document.getElementById('new-course-code').value = '';
        document.getElementById('new-course-name').value = '';
        addCoursePanel.style.display = 'none';
        toggleAddCourseBtn.textContent = '➕ เพิ่มรายวิชาใหม่';
        loadCourses();
      } else {
        alert(data.error || 'เกิดข้อผิดพลาดในการสร้างรายวิชา');
      }
    } catch (err) {
      alert('ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้');
    }
  });

  // Load and Render Course Cards
  async function loadCourses() {
    try {
      const res = await fetch('/api/courses');
      const data = await res.json();
      if (data.success) {
        renderCourseCards(data.courses);
        populateCourseFilter(data.courses);
      }
    } catch (err) {
      console.error('Failed to load courses:', err);
    }
  }

  function renderCourseCards(courses) {
    if (!courses || courses.length === 0) {
      courseCardsContainer.innerHTML = `<div style="color: var(--text-dim); padding: 12px;">ยังไม่มีรายวิชาในระบบ</div>`;
      return;
    }

    const origin = window.location.origin;

    courseCardsContainer.innerHTML = courses.map(c => {
      const checkinUrl = `${origin}/c/${c.course_code}`;
      return `
        <div class="course-card">
          <div class="course-card-top">
            <div>
              <span class="course-code-tag">${escapeHtml(c.course_code)}</span>
              <div class="course-card-name">${escapeHtml(c.course_name)}</div>
            </div>
            <button type="button" class="btn-secondary" style="height: 28px; padding: 2px 8px; font-size: 11px; color: #fb7185;" onclick="window.deleteCourse('${escapeHtml(c.course_code)}')">
              ลบ
            </button>
          </div>

          <div class="course-card-meta">
            <span>📍 พิกัดห้อง: <code>${c.target_lat.toFixed(5)}, ${c.target_lng.toFixed(5)}</code></span>
            <span>🎯 รัศมีอนุญาต: <strong>${Math.round(c.radius_m)} เมตร</strong></span>
          </div>

          <div>
            <div style="font-size: 11px; color: var(--text-dim); margin-bottom: 4px; font-weight: 600;">🔗 ลิงก์สำหรับส่งให้นักศึกษา:</div>
            <div class="course-link-box">
              <span class="course-link-text">${checkinUrl}</span>
              <button type="button" class="btn-copy" onclick="window.copyCourseLink(this, '${checkinUrl}')">
                📋 คัดลอก
              </button>
            </div>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 8px;">
            <a href="/c/${c.course_code}" target="_blank" class="nav-link" style="font-size: 11px; padding: 4px 10px;">
              🌐 เปิดหน้าเช็กชื่อ
            </a>
          </div>
        </div>
      `;
    }).join('');
  }

  function populateCourseFilter(courses) {
    const currentVal = courseFilter.value;
    courseFilter.innerHTML = `<option value="">-- ทุกรายวิชา (All Courses) --</option>`;
    courses.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.course_code;
      opt.textContent = `${c.course_code} - ${c.course_name}`;
      if (c.course_code === currentVal) opt.selected = true;
      courseFilter.appendChild(opt);
    });
  }

  // Global helper to copy link to clipboard
  window.copyCourseLink = function(btn, url) {
    navigator.clipboard.writeText(url).then(() => {
      const originalText = btn.innerHTML;
      btn.classList.add('copied');
      btn.innerHTML = 'คัดลอกแล้ว! ✅';
      setTimeout(() => {
        btn.classList.remove('copied');
        btn.innerHTML = originalText;
      }, 2000);
    }).catch(err => {
      prompt('คัดลอกลิงก์ด้านล่างนี้ได้เลยครับ:', url);
    });
  };

  // Global helper to delete course
  window.deleteCourse = async function(courseCode) {
    if (confirm(`คุณแน่ใจหรือไม่ว่าต้องการลบรายวิชา ${courseCode}?`)) {
      try {
        const res = await fetch(`/api/courses/${courseCode}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
          loadCourses();
          loadRecords();
        } else {
          alert(data.error || 'ไม่สามารถลบรายวิชาได้');
        }
      } catch (err) {
        alert('เกิดข้อผิดพลาดในการลบ');
      }
    }
  };

  // Search and Filter Events
  let debounceTimer = null;
  searchInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      loadRecords();
    }, 300);
  });

  courseFilter.addEventListener('change', () => {
    loadRecords();
  });

  statusFilter.addEventListener('change', () => {
    loadRecords();
  });

  refreshBtn.addEventListener('click', () => {
    loadRecords();
    loadCourses();
  });

  // Export CSV handler (FR-11 with Course filtering)
  exportCsvBtn.addEventListener('click', (e) => {
    e.preventDefault();
    const course = courseFilter.value;
    const status = statusFilter.value;
    const search = searchInput.value.trim();
    let url = '/api/export-csv?';
    if (course) url += `course=${encodeURIComponent(course)}&`;
    if (status) url += `status=${encodeURIComponent(status)}&`;
    if (search) url += `search=${encodeURIComponent(search)}`;
    window.location.href = url;
  });

  // Reset Records handler
  if (resetBtn) {
    resetBtn.addEventListener('click', async () => {
      if (confirm('คุณแน่ใจหรือไม่ว่าต้องการล้างข้อมูลประวัติการเช็กชื่อทั้งหมด?')) {
        try {
          const res = await fetch('/api/reset-records', { method: 'POST' });
          const data = await res.json();
          if (data.success) {
            alert('ล้างข้อมูลประวัติเรียบร้อยแล้ว');
            loadRecords();
          }
        } catch (err) {
          alert('เกิดข้อผิดพลาดในการล้างข้อมูล');
        }
      }
    });
  }

  // Load Records & Stats (FR-09, FR-10)
  async function loadRecords() {
    try {
      const course = courseFilter.value;
      const status = statusFilter.value;
      const search = searchInput.value.trim();
      let url = '/api/records?';
      if (course) url += `course=${encodeURIComponent(course)}&`;
      if (status) url += `status=${encodeURIComponent(status)}&`;
      if (search) url += `search=${encodeURIComponent(search)}`;

      const response = await fetch(url);
      const data = await response.json();

      if (data.success) {
        renderStats(data.stats);
        renderTable(data.records);
      }
    } catch (err) {
      console.error('Failed to load records:', err);
      recordsTableBody.innerHTML = `
        <tr>
          <td colspan="8" class="empty-state">
            ไม่สามารถเชื่อมต่อฐานข้อมูลได้ กรุณาลองใหม่อีกครั้ง
          </td>
        </tr>
      `;
    }
  }

  function renderStats(stats) {
    if (!stats) return;
    totalCountEl.textContent = stats.total_attempts;
    successCountEl.textContent = stats.total_success;
    outRangeCountEl.textContent = stats.total_out_of_range;
    rateEl.textContent = `${stats.success_rate}%`;
  }

  function renderTable(records) {
    if (!records || records.length === 0) {
      recordsTableBody.innerHTML = `
        <tr>
          <td colspan="8" class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="m4.93 4.93 14.14 14.14"/></svg>
            <div>ยังไม่มีข้อมูลการเช็กชื่อในรายวิชานี้</div>
          </td>
        </tr>
      `;
      return;
    }

    recordsTableBody.innerHTML = records.map((r) => {
      const isSuccess = r.status === 'SUCCESS';
      const statusBadge = isSuccess
        ? `<span class="status-badge success">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
            สำเร็จ (ในห้อง)
           </span>`
        : `<span class="status-badge out-of-range">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            อยู่นอกพื้นที่
           </span>`;

      const distTag = `<span class="distance-tag ${isSuccess ? 'success' : 'danger'}">${r.distance_m.toFixed(1)} ม.</span>`;
      const timeStr = r.created_at_local || r.created_at;
      const courseTag = `<span class="course-code-tag" style="font-size: 11px;">${escapeHtml(r.course_code || '-')}</span>`;

      return `
        <tr>
          <td style="color: var(--text-dim); font-size: 11px;">#${r.id}</td>
          <td>${courseTag}</td>
          <td><strong>${escapeHtml(r.student_id)}</strong></td>
          <td>${escapeHtml(r.student_name)}</td>
          <td>${distTag}</td>
          <td>${statusBadge}</td>
          <td style="font-family: monospace; font-size: 11px; color: var(--text-muted);">${r.user_lat.toFixed(5)}, ${r.user_lng.toFixed(5)}</td>
          <td style="font-size: 12px; color: var(--text-muted);">${escapeHtml(timeStr)}</td>
        </tr>
      `;
    }).join('');
  }

  function escapeHtml(string) {
    if (!string) return '';
    const div = document.createElement('div');
    div.textContent = string;
    return div.innerHTML;
  }
});
