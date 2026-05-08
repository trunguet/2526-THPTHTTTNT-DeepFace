/**
 * Check History Module
 * Allows employees to quickly check their check-in/check-out history
 */

class CheckHistoryModule {
  constructor() {
    this.historyTable = document.getElementById('history-table-body');
    this.dateFilter = document.getElementById('date-filter');
    this.monthFilter = document.getElementById('month-filter');
    this.refreshBtn = document.getElementById('refresh-btn');
    this.exportBtn = document.getElementById('export-btn');
    this.statsContainer = document.getElementById('stats-container');

    this.apiBaseURL = this.getApiBaseURL();
    this.history = [];
    this.employeeId = this.getEmployeeId();

    this.init();
  }

  init() {
    if (!this.employeeId) {
      this.showError('❌ Không thể xác định mã nhân viên');
      return;
    }

    this.fetchHistory();

    if (this.dateFilter) {
      this.dateFilter.addEventListener('change', () => this.filterByDate());
    }

    if (this.monthFilter) {
      this.monthFilter.addEventListener('change', () => this.filterByMonth());
    }

    if (this.refreshBtn) {
      this.refreshBtn.addEventListener('click', () => this.refreshData());
    }

    if (this.exportBtn) {
      this.exportBtn.addEventListener('click', () => this.exportToCSV());
    }

    // Auto-refresh every 60 seconds
    setInterval(() => this.fetchHistory(), 60000);
  }

  getApiBaseURL() {
    const envBaseUrl =
      typeof process !== 'undefined' &&
      process.env &&
      process.env.REACT_APP_API_BASE_URL
        ? process.env.REACT_APP_API_BASE_URL
        : null;
    return envBaseUrl || window.DeepFaceAPI?.getBaseURL?.() || 'http://localhost:18000';
  }

  /**
   * Get current employee ID from localStorage or URL
   */
  getEmployeeId() {
    // Try to get from localStorage
    let employeeId = localStorage.getItem('employee_id');

    // Or from URL query parameter
    if (!employeeId) {
      const params = new URLSearchParams(window.location.search);
      employeeId = params.get('employee_id');
    }

    return employeeId;
  }

  /**
   * Fetch access history for current employee
   */
  async fetchHistory() {
    try {
      const response = await fetch(
        `${this.apiBaseURL}/api/employees/${this.employeeId}/access-history`,
        {
          headers: {
            Authorization: `Bearer ${this.getAuthToken()}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch history');
      }

      this.history = await response.json();
      this.renderHistory();
      this.calculateStatistics();
    } catch (error) {
      console.error('Error fetching history:', error);
      this.showError('Không thể tải lịch sử truy cập');
    }
  }

  /**
   * Render history table
   */
  renderHistory() {
    if (!this.historyTable) return;

    this.historyTable.innerHTML = '';

    if (this.history.length === 0) {
      this.historyTable.innerHTML =
        '<tr><td colspan="5" class="text-center">Không có dữ liệu lịch sử</td></tr>';
      return;
    }

    this.history.forEach((record, index) => {
      const date = new Date(record.timestamp).toLocaleDateString('vi-VN');
      const time = new Date(record.timestamp).toLocaleTimeString('vi-VN');
      const type = record.access_type === 'check_in' ? '📍 Check-in' : '📤 Check-out';
      const statusClass = record.status === 'allowed' ? 'status-allowed' : 'status-denied';

      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${index + 1}</td>
        <td>${record.employee_code || this.employeeId}</td>
        <td>${date}</td>
        <td>${time}</td>
        <td>${type}</td>
        <td class="camera-location">${record.camera_location || 'N/A'}</td>
        <td><span class="status-badge ${statusClass}">${record.status === 'allowed' ? '✓ Cho phép' : '✗ Từ chối'}</span></td>
      `;
      this.historyTable.appendChild(row);
    });
  }

  /**
   * Calculate and display statistics
   */
  calculateStatistics() {
    if (!this.statsContainer) return;

    const today = new Date().toDateString();
    const todayRecords = this.history.filter((r) => new Date(r.timestamp).toDateString() === today);

    const checkIns = this.history.filter((r) => r.access_type === 'check_in');
    const checkOuts = this.history.filter((r) => r.access_type === 'check_out');

    const statsHTML = `
      <div class="stat-card">
        <div class="stat-label">Hôm nay</div>
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
        <div class="stat-label">Tổng</div>
        <div class="stat-value">${this.history.length}</div>
      </div>
    `;

    this.statsContainer.innerHTML = statsHTML;
  }

  /**
   * Filter history by specific date
   */
  filterByDate() {
    const selectedDate = this.dateFilter?.value;
    if (!selectedDate) {
      this.fetchHistory();
      return;
    }

    const selected = new Date(selectedDate).toDateString();
    const filtered = this.history.filter((r) => new Date(r.timestamp).toDateString() === selected);

    this.history = filtered;
    this.renderHistory();
  }

  /**
   * Filter history by month
   */
  filterByMonth() {
    const selectedMonth = this.monthFilter?.value;
    if (!selectedMonth) {
      this.fetchHistory();
      return;
    }

    const [year, month] = selectedMonth.split('-');
    const filtered = this.history.filter((r) => {
      const date = new Date(r.timestamp);
      return date.getFullYear() === parseInt(year) && date.getMonth() + 1 === parseInt(month);
    });

    this.history = filtered;
    this.renderHistory();
  }

  /**
   * Refresh data
   */
  refreshData() {
    this.fetchHistory();
    this.showSuccess('✓ Đã cập nhật dữ liệu');
  }

  /**
   * Export history to CSV
   */
  exportToCSV() {
    if (this.history.length === 0) {
      this.showError('❌ Không có dữ liệu để xuất');
      return;
    }

    let csv = 'STT,Mã Nhân Viên,Ngày,Giờ,Loại,Vị trí Camera,Trạng thái\n';

    this.history.forEach((record, index) => {
      const date = new Date(record.timestamp).toLocaleDateString('vi-VN');
      const time = new Date(record.timestamp).toLocaleTimeString('vi-VN');
      const type = record.access_type === 'check_in' ? 'Check-in' : 'Check-out';
      const status = record.status === 'allowed' ? 'Cho phép' : 'Từ chối';
      const employeeCode = record.employee_code || this.employeeId;

      csv += `${index + 1},"${employeeCode}","${date}","${time}","${type}","${record.camera_location || 'N/A'}","${status}"\n`;
    });

    // Create blob and download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `history_${this.employeeId}_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);

    this.showSuccess('✓ Đã tải xuống file CSV');
  }

  /**
   * Get authentication token
   */
  getAuthToken() {
    return localStorage.getItem('auth_token') || '';
  }

  /**
   * Show success message
   */
  showSuccess(message) {
    this.showNotification(message, 'success');
  }

  /**
   * Show error message
   */
  showError(message) {
    this.showNotification(message, 'error');
  }

  /**
   * Show notification
   */
  showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 15px 20px;
      border-radius: 5px;
      z-index: 1000;
      animation: slideIn 0.3s ease-out;
      background-color: ${type === 'success' ? '#10b981' : '#ef4444'};
      color: white;
    `;
    document.body.appendChild(notification);

    setTimeout(() => {
      notification.remove();
    }, 3000);
  }
}

// Initialize module when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.checkHistoryModule = new CheckHistoryModule();
});
