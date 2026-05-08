class AdminSettingsModule {
  constructor() {
    this.apiInput = document.getElementById('api-base-url');
    this.saveBtn = document.getElementById('save-api-url');
    this.testBtn = document.getElementById('test-api-url');
    this.resetBtn = document.getElementById('reset-api-url');
    this.status = document.getElementById('settings-status');

    this.unscannedRefreshBtn = document.getElementById('refresh-unscanned-today');
    this.unscannedStatus = document.getElementById('unscanned-today-status');
    this.unscannedBody = document.getElementById('unscanned-today-body');
    this.unscannedCount = document.getElementById('unscanned-today-count');
    this.unscannedDate = document.getElementById('unscanned-today-date');
    this.init();
  }

  init() {
    if (this.apiInput) this.apiInput.value = DeepFaceAPI.getBaseURL();
    this.saveBtn?.addEventListener('click', () => this.save());
    this.testBtn?.addEventListener('click', () => this.test());
    this.resetBtn?.addEventListener('click', () => this.reset());
    this.unscannedRefreshBtn?.addEventListener('click', () => this.loadUnscannedToday());
    this.loadUnscannedToday();
  }

  save() {
    const value = DeepFaceAPI.setBaseURL(this.apiInput.value);
    this.apiInput.value = value;
    this.show('Da luu cau hinh API.', 'success');
  }

  reset() {
    const value = DeepFaceAPI.setBaseURL('');
    this.apiInput.value = value;
    this.show('Da quay ve cau hinh mac dinh.', 'info');
  }

  async test() {
    this.save();
    try {
      const result = await DeepFaceAPI.health();
      this.show(`Backend san sang: ${result.status || 'ok'}`, 'success');
    } catch (error) {
      this.show(`Khong ket noi duoc backend: ${error.message}`, 'error');
    }
  }

  show(message, type) {
    if (!this.status) return;
    this.status.textContent = message;
    this.status.className = `status-message status-${type}`;
    this.status.style.display = 'block';
  }

  showUnscanned(message, type) {
    if (!this.unscannedStatus) return;
    this.unscannedStatus.textContent = message;
    this.unscannedStatus.className = `status-message status-${type}`;
    this.unscannedStatus.style.display = 'block';
  }

  hideUnscanned() {
    if (!this.unscannedStatus) return;
    this.unscannedStatus.style.display = 'none';
  }

  renderUnscanned(items) {
    if (!this.unscannedBody) return;
    const rows = (items || []).map((item, index) => {
      const name = DeepFaceAPI.escapeHTML(item.full_name || '');
      const employeeId = DeepFaceAPI.escapeHTML(item.employee_id || '');
      const department = DeepFaceAPI.escapeHTML(item.department || '');
      const email = DeepFaceAPI.escapeHTML(item.email || '');
      return `
        <tr>
          <td>${index + 1}</td>
          <td>${name}</td>
          <td>${employeeId}</td>
          <td>${department || '—'}</td>
          <td>${email || '—'}</td>
        </tr>
      `;
    });

    if (!rows.length) {
      this.unscannedBody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: #10b981; font-weight: 600">🎉 Tất cả nhân viên đã quét hôm nay</td>
        </tr>
      `;
      return;
    }

    this.unscannedBody.innerHTML = rows.join('');
  }

  async loadUnscannedToday() {
    if (!this.unscannedBody) return;
    this.hideUnscanned();
    if (this.unscannedCount) this.unscannedCount.textContent = '…';
    if (this.unscannedDate) this.unscannedDate.textContent = '…';
    this.unscannedBody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align: center; color: #a0aec0; padding: 18px 12px">
          <span style="display: inline-flex; align-items: center; gap: 10px">
            <span class="inline-spinner"></span>
            <span>Đang tải dữ liệu...</span>
          </span>
        </td>
      </tr>
    `;

    try {
      const payload = await this.withTimeout(DeepFaceAPI.get('/api/employees/unscanned-today'), 10000);
      const items = DeepFaceAPI.normalizeList(payload);

      if (this.unscannedCount) this.unscannedCount.textContent = String(payload?.count ?? items.length ?? 0);
      if (this.unscannedDate) this.unscannedDate.textContent = String(payload?.date || '--');

      this.renderUnscanned(items);
      // Make it obvious the request finished (useful when browser caches old scripts).
      this.showUnscanned('Đã cập nhật danh sách.', 'success');
      setTimeout(() => this.hideUnscanned(), 1500);
    } catch (error) {
      if (this.unscannedCount) this.unscannedCount.textContent = '--';
      if (this.unscannedDate) this.unscannedDate.textContent = '--';
      this.showUnscanned(`Không tải được danh sách: ${error.message}`, 'error');
      this.unscannedBody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: #a0aec0">Không có dữ liệu</td>
        </tr>
      `;
    }
  }

  withTimeout(promise, ms) {
    let timeoutId = null;
    const timeoutPromise = new Promise((_, reject) => {
      timeoutId = setTimeout(() => reject(new Error('Request timeout')), ms);
    });
    return Promise.race([promise, timeoutPromise])
      .then((value) => {
        clearTimeout(timeoutId);
        return value;
      })
      .catch((error) => {
        clearTimeout(timeoutId);
        throw error;
      });
  }
}

document.addEventListener('DOMContentLoaded', () => new AdminSettingsModule());
