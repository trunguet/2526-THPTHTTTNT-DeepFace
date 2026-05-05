/**
 * View Logs Module
 * Handles display of access logs and stranger alerts
 */

class ViewLogsModule {
  constructor() {
    this.logsTable = document.getElementById('logs-table-body');
    this.alertsSection = document.getElementById('alerts-section');
    this.filterDateFrom = document.getElementById('filter-date-from');
    this.filterDateTo = document.getElementById('filter-date-to');
    this.filterTypeSelect = document.getElementById('filter-type');
    this.refreshBtn = document.getElementById('refresh-btn');

    this.apiBaseURL = this.getApiBaseURL();
    this.logs = [];
    this.alerts = [];

    this.init();
  }

  init() {
    this.fetchLogs();
    this.fetchAlerts();

    if (this.refreshBtn) {
      this.refreshBtn.addEventListener('click', () => this.refreshData());
    }

    if (this.filterDateFrom || this.filterDateTo || this.filterTypeSelect) {
      [this.filterDateFrom, this.filterDateTo, this.filterTypeSelect].forEach((el) => {
        if (el) {
          el.addEventListener('change', () => this.applyFilters());
        }
      });
    }

    // Auto-refresh every 30 seconds
    setInterval(() => this.fetchLogs(), 30000);
  }

  getApiBaseURL() {
    const envBaseUrl =
      typeof process !== 'undefined' &&
      process.env &&
      process.env.REACT_APP_API_BASE_URL
        ? process.env.REACT_APP_API_BASE_URL
        : null;
    return envBaseUrl || 'http://localhost:8000';
  }

  /**
   * Fetch access logs from backend
   */
  async fetchLogs() {
    try {
      const response = await fetch(`${this.apiBaseURL}/api/access-logs`, {
        headers: {
          Authorization: `Bearer ${this.getAuthToken()}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }

      this.logs = await response.json();
      this.renderLogs();
    } catch (error) {
      console.error('Error fetching logs:', error);
      this.showError('Không thể tải nhật ký truy cập');
    }
  }

  /**
   * Fetch stranger alerts from backend
   */
  async fetchAlerts() {
    try {
      const response = await fetch(`${this.apiBaseURL}/api/access-logs/alerts`, {
        headers: {
          Authorization: `Bearer ${this.getAuthToken()}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch alerts');
      }

      this.alerts = await response.json();
      this.renderAlerts();
    } catch (error) {
      console.error('Error fetching alerts:', error);
    }
  }

  /**
   * Render access logs table
   */
  renderLogs() {
    if (!this.logsTable) return;

    this.logsTable.innerHTML = '';

    if (this.logs.length === 0) {
      this.logsTable.innerHTML = '<tr><td colspan="7" class="text-center">Không có nhật ký nào</td></tr>';
      return;
    }

    this.logs.forEach((log, index) => {
      const logTime = new Date(log.timestamp).toLocaleString('vi-VN');
      const rowClass = log.status === 'denied' ? 'row-denied' : '';

      const row = document.createElement('tr');
      row.className = rowClass;
      row.innerHTML = `
        <td>${index + 1}</td>
        <td>${log.employee_name || 'N/A'}</td>
        <td>${log.employee_id || 'N/A'}</td>
        <td>${log.camera_location || 'N/A'}</td>
        <td>${logTime}</td>
        <td>
          <span class="status-badge status-${log.status}">
            ${log.status === 'allowed' ? '✓ Cho phép' : '✗ Từ chối'}
          </span>
        </td>
        <td>
          <button class="btn btn-sm btn-view" onclick="logsModule.viewDetails(${log.id})">Chi tiết</button>
        </td>
      `;
      this.logsTable.appendChild(row);
    });
  }

  /**
   * Render stranger alerts
   */
  renderAlerts() {
    if (!this.alertsSection) return;

    const alertsContainer = this.alertsSection.querySelector('.alerts-container') || this.alertsSection;
    alertsContainer.innerHTML = '';

    if (this.alerts.length === 0) {
      alertsContainer.innerHTML = '<p class="no-alerts">Không có cảnh báo người lạ</p>';
      return;
    }

    this.alerts.forEach((alert) => {
      const alertTime = new Date(alert.timestamp).toLocaleString('vi-VN');
      const alertDiv = document.createElement('div');
      alertDiv.className = 'alert-card alert-stranger';
      alertDiv.innerHTML = `
        <div class="alert-header">
          <h4>⚠️ Phát hiện người lạ</h4>
          <span class="alert-time">${alertTime}</span>
        </div>
        <div class="alert-body">
          <p><strong>Vị trí camera:</strong> ${alert.camera_location || 'N/A'}</p>
          <p><strong>Độ tin cậy:</strong> ${(alert.confidence * 100).toFixed(2)}%</p>
          ${alert.image_url ? `<img src="${alert.image_url}" alt="Alert" class="alert-image">` : ''}
        </div>
        <div class="alert-actions">
          <button class="btn btn-sm btn-primary" onclick="logsModule.viewAlertDetails(${alert.id})">Xem chi tiết</button>
          <button class="btn btn-sm btn-secondary" onclick="logsModule.dismissAlert(${alert.id})">Đã xử lý</button>
        </div>
      `;
      alertsContainer.appendChild(alertDiv);
    });
  }

  /**
   * Apply filters to logs
   */
  applyFilters() {
    const dateFrom = this.filterDateFrom?.value;
    const dateTo = this.filterDateTo?.value;
    const type = this.filterTypeSelect?.value;

    let filtered = this.logs;

    if (dateFrom) {
      filtered = filtered.filter((log) => new Date(log.timestamp) >= new Date(dateFrom));
    }

    if (dateTo) {
      filtered = filtered.filter((log) => new Date(log.timestamp) <= new Date(dateTo));
    }

    if (type && type !== 'all') {
      filtered = filtered.filter((log) => log.status === type);
    }

    this.logs = filtered;
    this.renderLogs();
  }

  /**
   * View log details (can open modal or navigate to detail page)
   */
  viewDetails(logId) {
    console.log('Viewing details for log:', logId);
    // Can implement modal or navigate to detail page
  }

  /**
   * View alert details
   */
  viewAlertDetails(alertId) {
    console.log('Viewing alert details:', alertId);
  }

  /**
   * Dismiss alert
   */
  async dismissAlert(alertId) {
    try {
      const response = await fetch(`${this.apiBaseURL}/api/access-logs/alerts/${alertId}/dismiss`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${this.getAuthToken()}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to dismiss alert');
      }

      this.fetchAlerts();
      this.showSuccess('✓ Đã xử lý cảnh báo');
    } catch (error) {
      console.error('Error dismissing alert:', error);
      this.showError('❌ Không thể xử lý cảnh báo');
    }
  }

  /**
   * Refresh data
   */
  refreshData() {
    this.fetchLogs();
    this.fetchAlerts();
    this.showSuccess('✓ Đã cập nhật dữ liệu');
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
    document.body.appendChild(notification);

    setTimeout(() => {
      notification.remove();
    }, 3000);
  }
}

// Global instance
let logsModule;

document.addEventListener('DOMContentLoaded', () => {
  logsModule = new ViewLogsModule();
});
