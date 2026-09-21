// Instructor Dashboard Logic
document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const recordsTableBody = document.getElementById('records-tbody');
  const searchInput = document.getElementById('search-input');
  const statusFilter = document.getElementById('status-filter');
  const refreshBtn = document.getElementById('refresh-btn');
  const exportCsvBtn = document.getElementById('export-csv-btn');
  const resetBtn = document.getElementById('reset-btn');
  
  // Stat counters
  const totalCountEl = document.getElementById('stat-total');
  const successCountEl = document.getElementById('stat-success');
  const outRangeCountEl = document.getElementById('stat-out-range');
  const rateEl = document.getElementById('stat-rate');
  
  // Config form elements
  const configLatInput = document.getElementById('target-lat-input');
  const configLngInput = document.getElementById('target-lng-input');
  const configRadiusInput = document.getElementById('target-radius-input');
  const saveConfigBtn = document.getElementById('save-config-btn');
  const useCurrentLocationBtn = document.getElementById('use-current-location-btn');
  const configStatusMsg = document.getElementById('config-status-msg');

  // Initial Load
  loadConfig();
  loadRecords();

  // Search and Filter Events
  let debounceTimer = null;
  searchInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      loadRecords();
    }, 300);
  });

  statusFilter.addEventListener('change', () => {
    loadRecords();
  });

  refreshBtn.addEventListener('click', () => {
    loadRecords();
  });

  // Export CSV handler (FR-11)
  exportCsvBtn.addEventListener('click', (e) => {
    e.preventDefault();
    const status = statusFilter.value;
    const search = searchInput.value.trim();
    let url = '/api/export-csv?';
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
      const status = statusFilter.value;
      const search = searchInput.value.trim();
      let url = '/api/records?';
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
          <td colspan="7" class="empty-state">
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
          <td colspan="7" class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="m4.93 4.93 14.14 14.14"/></svg>
            <div>ยังไม่มีข้อมูลการเช็กชื่อ</div>
          </td>
        </tr>
      `;
      return;
    }

    recordsTableBody.innerHTML = records.map((r, index) => {
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

      return `
        <tr>
          <td style="color: var(--text-dim); font-size: 11px;">#${r.id}</td>
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

  // Configuration management
  async function loadConfig() {
    try {
      const res = await fetch('/api/config');
      const cfg = await res.json();
      if (cfg) {
        configLatInput.value = cfg.target_lat;
        configLngInput.value = cfg.target_lng;
        configRadiusInput.value = cfg.radius_m;
      }
    } catch (err) {
      console.error('Failed to load config:', err);
    }
  }

  saveConfigBtn.addEventListener('click', async () => {
    const lat = parseFloat(configLatInput.value);
    const lng = parseFloat(configLngInput.value);
    const radius = parseFloat(configRadiusInput.value);

    if (isNaN(lat) || isNaN(lng) || isNaN(radius)) {
      showConfigMessage('danger', 'กรุณากรอกข้อมูลตัวเลขให้ถูกต้อง');
      return;
    }

    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_lat: lat, target_lng: lng, radius_m: radius })
      });
      const data = await res.json();
      if (data.success) {
        showConfigMessage('success', 'บันทึกพิกัดห้องเรียนและรัศมีเรียบร้อยแล้ว');
      } else {
        showConfigMessage('danger', data.error || 'เกิดข้อผิดพลาดในการบันทึก');
      }
    } catch (err) {
      showConfigMessage('danger', 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้');
    }
  });

  useCurrentLocationBtn.addEventListener('click', () => {
    if (!navigator.geolocation) {
      alert('เบราว์เซอร์ไม่รองรับการดึงพิกัด Geolocation');
      return;
    }

    useCurrentLocationBtn.textContent = 'กำลังดึงพิกัด...';
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        configLatInput.value = pos.coords.latitude.toFixed(6);
        configLngInput.value = pos.coords.longitude.toFixed(6);
        useCurrentLocationBtn.textContent = '📍 ใช้พิกัดปัจจุบันของฉัน';
        showConfigMessage('success', 'ดึงพิกัดปัจจุบันของคุณแล้ว อย่าลืมกด "บันทึกการตั้งค่า"');
      },
      (err) => {
        useCurrentLocationBtn.textContent = '📍 ใช้พิกัดปัจจุบันของฉัน';
        alert('ไม่สามารถดึงพิกัดได้: ' + err.message);
      },
      { enableHighAccuracy: true }
    );
  });

  function showConfigMessage(type, msg) {
    configStatusMsg.style.display = 'block';
    configStatusMsg.style.color = type === 'success' ? '#34d399' : '#fb7185';
    configStatusMsg.textContent = msg;
    setTimeout(() => {
      configStatusMsg.style.display = 'none';
    }, 4000);
  }

  function escapeHtml(string) {
    const div = document.createElement('div');
    div.textContent = string;
    return div.innerHTML;
  }
});
