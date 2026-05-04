/**
 * View Logs Module
 * Handles access logs, filters, and stranger alerts.
 */

class ViewLogsModule {
  constructor() {
    this.logsTable = document.getElementById('logs-table-body');
    this.alertsSection = document.getElementById('alerts-section');
    this.filterDateFrom = document.getElementById('filter-date-from');
    this.filterDateTo = document.getElementById('filter-date-to');
    this.filterTypeSelect = document.getElementById('filter-type');
    this.refreshBtn = document.getElementById('refresh-btn');

    this.allLogs = [];
    this.visibleLogs = [];
    this.alerts = [];

    this.init();
  }

  init() {
    this.refreshData(false);

    this.refreshBtn?.addEventListener('click', () => this.refreshData(true));
    [this.filterDateFrom, this.filterDateTo, this.filterTypeSelect].forEach((element) => {
      element?.addEventListener('change', () => this.applyFilters());
    });

    setInterval(() => this.refreshData(false), 30000);
  }

  async fetchLogs() {
    const data = await DeepFaceAPI.get('/api/access-logs');
    this.allLogs = DeepFaceAPI.normalizeList(data);
    this.visibleLogs = [...this.allLogs];
    this.applyFilters();
  }

  async fetchAlerts() {
    const data = await DeepFaceAPI.get('/api/access-logs/alerts');
    this.alerts = DeepFaceAPI.normalizeList(data);
    this.renderAlerts();
  }

  renderLogs() {
    if (!this.logsTable) return;

    if (!this.visibleLogs.length) {
      this.logsTable.innerHTML =
        '<tr><td colspan="7" class="text-center">Khong co nhat ky phu hop</td></tr>';
      return;
    }

    this.logsTable.innerHTML = this.visibleLogs
      .map((log, index) => {
        const status = log.status || 'unknown';
        const statusLabel = status === 'allowed' ? 'Cho phep' : status === 'denied' ? 'Tu choi' : status;
        return `
          <tr class="${status === 'denied' ? 'row-denied' : ''}">
            <td>${index + 1}</td>
            <td>${DeepFaceAPI.escapeHTML(log.employee_name || 'N/A')}</td>
            <td>${DeepFaceAPI.escapeHTML(log.employee_id || 'N/A')}</td>
            <td>${DeepFaceAPI.escapeHTML(log.camera_location || 'N/A')}</td>
            <td>${DeepFaceAPI.escapeHTML(DeepFaceAPI.formatDateTime(log.timestamp))}</td>
            <td><span class="status-badge status-${DeepFaceAPI.escapeHTML(status)}">${DeepFaceAPI.escapeHTML(statusLabel)}</span></td>
            <td><button class="btn btn-sm btn-view" data-id="${DeepFaceAPI.escapeHTML(log.id || index)}">Chi tiet</button></td>
          </tr>
        `;
      })
      .join('');

    this.logsTable.querySelectorAll('button[data-id]').forEach((button) => {
      button.addEventListener('click', () => this.viewDetails(button.dataset.id));
    });
  }

  renderAlerts() {
    if (!this.alertsSection) return;

    if (!this.alerts.length) {
      this.alertsSection.innerHTML =
        '<p class="no-alerts">Khong co canh bao nguoi la</p>';
      return;
    }

    this.alertsSection.innerHTML = this.alerts
      .map((alert) => {
        const confidence = Number(alert.confidence ?? 0);
        const imageHTML = alert.image_url
          ? `<img src="${DeepFaceAPI.escapeHTML(alert.image_url)}" alt="Alert" class="alert-image">`
          : '';
        return `
          <div class="alert-card alert-stranger">
            <div class="alert-header">
              <h4>Phat hien nguoi la</h4>
              <span class="alert-time">${DeepFaceAPI.escapeHTML(DeepFaceAPI.formatDateTime(alert.timestamp))}</span>
            </div>
            <div class="alert-body">
              <p><strong>Vi tri camera:</strong> ${DeepFaceAPI.escapeHTML(alert.camera_location || 'N/A')}</p>
              <p><strong>Do tin cay:</strong> ${(confidence * 100).toFixed(2)}%</p>
              ${imageHTML}
            </div>
            <div class="alert-actions">
              <button class="btn btn-sm btn-primary" data-view="${DeepFaceAPI.escapeHTML(alert.id)}">Xem chi tiet</button>
              <button class="btn btn-sm btn-secondary" data-dismiss="${DeepFaceAPI.escapeHTML(alert.id)}">Da xu ly</button>
            </div>
          </div>
        `;
      })
      .join('');

    this.alertsSection.querySelectorAll('button[data-view]').forEach((button) => {
      button.addEventListener('click', () => this.viewAlertDetails(button.dataset.view));
    });
    this.alertsSection.querySelectorAll('button[data-dismiss]').forEach((button) => {
      button.addEventListener('click', () => this.dismissAlert(button.dataset.dismiss));
    });
  }

  applyFilters() {
    const dateFrom = this.filterDateFrom?.value;
    const dateTo = this.filterDateTo?.value;
    const type = this.filterTypeSelect?.value;

    this.visibleLogs = this.allLogs.filter((log) => {
      const timestamp = new Date(log.timestamp);
      if (dateFrom && timestamp < new Date(`${dateFrom}T00:00:00`)) return false;
      if (dateTo && timestamp > new Date(`${dateTo}T23:59:59`)) return false;
      if (type && type !== 'all' && log.status !== type) return false;
      return true;
    });

    this.renderLogs();
  }

  viewDetails(logId) {
    this.showNotification(`Log ${logId}: can bo sung modal chi tiet khi backend tra snapshot/image.`, 'info');
  }

  viewAlertDetails(alertId) {
    this.showNotification(`Alert ${alertId}: can bo sung modal chi tiet khi backend tra snapshot/image.`, 'info');
  }

  async dismissAlert(alertId) {
    try {
      await DeepFaceAPI.post(`/api/access-logs/alerts/${encodeURIComponent(alertId)}/dismiss`);
      await this.fetchAlerts();
      this.showNotification('Da xu ly canh bao', 'success');
    } catch (error) {
      console.error('Error dismissing alert:', error);
      this.showNotification(`Khong the xu ly canh bao: ${error.message}`, 'error');
    }
  }

  async refreshData(showToast) {
    try {
      await Promise.all([this.fetchLogs(), this.fetchAlerts()]);
      if (showToast) this.showNotification('Da cap nhat du lieu', 'success');
    } catch (error) {
      console.error('Error refreshing logs:', error);
      if (this.logsTable) {
        this.logsTable.innerHTML = `<tr><td colspan="7" class="text-center">Khong tai duoc nhat ky: ${DeepFaceAPI.escapeHTML(
          error.message
        )}</td></tr>`;
      }
      if (this.alertsSection) {
        this.alertsSection.innerHTML = '<p class="no-alerts">Khong tai duoc canh bao</p>';
      }
      if (showToast) this.showNotification(`Khong cap nhat duoc: ${error.message}`, 'error');
    }
  }

  showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3500);
  }
}

let logsModule;

document.addEventListener('DOMContentLoaded', () => {
  logsModule = new ViewLogsModule();
});
