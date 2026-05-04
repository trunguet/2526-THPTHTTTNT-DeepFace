/**
 * Check History Module
 * Displays employee check-in/check-out history with filters and CSV export.
 */

class CheckHistoryModule {
  constructor() {
    this.historyTable = document.getElementById('history-table-body');
    this.dateFilter = document.getElementById('date-filter');
    this.monthFilter = document.getElementById('month-filter');
    this.refreshBtn = document.getElementById('refresh-btn');
    this.exportBtn = document.getElementById('export-btn');
    this.statsContainer = document.getElementById('stats-container');

    this.allHistory = [];
    this.visibleHistory = [];
    this.employeeId = this.getEmployeeId();

    this.init();
  }

  init() {
    if (!this.historyTable && !this.statsContainer) return;

    if (!this.employeeId) {
      this.renderEmpty('Chua co ma nhan vien. Hay dang nhap demo hoac them employee_id vao URL.');
      this.calculateStatistics();
      return;
    }

    this.fetchHistory();

    this.dateFilter?.addEventListener('change', () => this.applyFilters());
    this.monthFilter?.addEventListener('change', () => this.applyFilters());
    this.refreshBtn?.addEventListener('click', () => this.refreshData());
    this.exportBtn?.addEventListener('click', () => this.exportToCSV());

    setInterval(() => this.fetchHistory(false), 60000);
  }

  getEmployeeId() {
    const params = new URLSearchParams(window.location.search);
    return localStorage.getItem('employee_id') || params.get('employee_id');
  }

  async fetchHistory(showError = true) {
    if (!this.employeeId) return;
    this.renderLoading();

    try {
      const data = await DeepFaceAPI.get(
        `/api/employees/${encodeURIComponent(this.employeeId)}/access-history`
      );
      this.allHistory = DeepFaceAPI.normalizeList(data);
      this.applyFilters();
      this.calculateStatistics();
    } catch (error) {
      console.error('Error fetching history:', error);
      if (showError) this.renderEmpty(`Khong tai duoc lich su: ${error.message}`);
    }
  }

  renderHistory() {
    if (!this.historyTable) return;

    if (!this.visibleHistory.length) {
      this.renderEmpty('Khong co du lieu lich su phu hop');
      return;
    }

    this.historyTable.innerHTML = this.visibleHistory
      .map((record, index) => {
        const date = new Date(record.timestamp);
        const statusClass = record.status === 'allowed' ? 'status-allowed' : 'status-denied';
        const statusLabel = record.status === 'allowed' ? 'Cho phep' : 'Tu choi';
        return `
          <tr>
            <td>${index + 1}</td>
            <td>${Number.isNaN(date.getTime()) ? 'N/A' : date.toLocaleDateString('vi-VN')}</td>
            <td>${Number.isNaN(date.getTime()) ? 'N/A' : date.toLocaleTimeString('vi-VN')}</td>
            <td>${DeepFaceAPI.escapeHTML(record.access_type === 'check_out' ? 'Check-out' : 'Check-in')}</td>
            <td class="camera-location">${DeepFaceAPI.escapeHTML(record.camera_location || 'N/A')}</td>
            <td><span class="status-badge ${statusClass}">${statusLabel}</span></td>
          </tr>
        `;
      })
      .join('');
  }

  renderLoading() {
    if (!this.historyTable) return;
    this.historyTable.innerHTML =
      '<tr><td colspan="6" class="text-center">Dang tai du lieu...</td></tr>';
  }

  renderEmpty(message) {
    if (!this.historyTable) return;
    this.historyTable.innerHTML = `<tr><td colspan="6" class="text-center">${DeepFaceAPI.escapeHTML(
      message
    )}</td></tr>`;
  }

  calculateStatistics() {
    if (!this.statsContainer) return;

    const today = new Date().toDateString();
    const todayRecords = this.visibleHistory.filter(
      (record) => new Date(record.timestamp).toDateString() === today
    );
    const checkIns = this.visibleHistory.filter((record) => record.access_type !== 'check_out');
    const checkOuts = this.visibleHistory.filter((record) => record.access_type === 'check_out');

    this.statsContainer.innerHTML = `
      <div class="stat-card">
        <div class="stat-label">Hom nay</div>
        <div class="stat-value">${todayRecords.length}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Check-in</div>
        <div class="stat-value">${checkIns.length}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Check-out</div>
        <div class="stat-value">${checkOuts.length}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Tong</div>
        <div class="stat-value">${this.visibleHistory.length}</div>
      </div>
    `;
  }

  applyFilters() {
    const selectedDate = this.dateFilter?.value;
    const selectedMonth = this.monthFilter?.value;

    this.visibleHistory = this.allHistory.filter((record) => {
      const timestamp = new Date(record.timestamp);
      if (Number.isNaN(timestamp.getTime())) return false;

      if (selectedDate) {
        const selected = new Date(`${selectedDate}T00:00:00`).toDateString();
        if (timestamp.toDateString() !== selected) return false;
      }

      if (selectedMonth) {
        const [year, month] = selectedMonth.split('-').map(Number);
        if (timestamp.getFullYear() !== year || timestamp.getMonth() + 1 !== month) {
          return false;
        }
      }

      return true;
    });

    this.renderHistory();
    this.calculateStatistics();
  }

  refreshData() {
    this.fetchHistory();
    this.showNotification('Da cap nhat du lieu', 'success');
  }

  exportToCSV() {
    if (!this.visibleHistory.length) {
      this.showNotification('Khong co du lieu de xuat CSV', 'error');
      return;
    }

    const rows = [
      ['STT', 'Ngay', 'Gio', 'Loai', 'Vi tri Camera', 'Trang thai'],
      ...this.visibleHistory.map((record, index) => {
        const date = new Date(record.timestamp);
        return [
          index + 1,
          Number.isNaN(date.getTime()) ? 'N/A' : date.toLocaleDateString('vi-VN'),
          Number.isNaN(date.getTime()) ? 'N/A' : date.toLocaleTimeString('vi-VN'),
          record.access_type === 'check_out' ? 'Check-out' : 'Check-in',
          record.camera_location || 'N/A',
          record.status === 'allowed' ? 'Cho phep' : 'Tu choi',
        ];
      }),
    ];

    const csv = rows
      .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
      .join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `history_${this.employeeId}_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);

    this.showNotification('Da tai file CSV', 'success');
  }

  showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3500);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.checkHistoryModule = new CheckHistoryModule();
});
