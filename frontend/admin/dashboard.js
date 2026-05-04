class AdminDashboardModule {
  constructor() {
    this.checkinCount = document.getElementById('checkin-count');
    this.presentCount = document.getElementById('present-count');
    this.alertCount = document.getElementById('alert-count');
    this.activityBody = document.getElementById('activity-body');
    this.init();
  }

  async init() {
    await this.load();
  }

  async load() {
    try {
      const [employees, logs, alerts] = await Promise.all([
        DeepFaceAPI.get('/api/employees').then(DeepFaceAPI.normalizeList),
        DeepFaceAPI.get('/api/access-logs').then(DeepFaceAPI.normalizeList),
        DeepFaceAPI.get('/api/access-logs/alerts').then(DeepFaceAPI.normalizeList),
      ]);

      const today = new Date().toDateString();
      const todayLogs = logs.filter((log) => new Date(log.timestamp).toDateString() === today);
      const checkins = todayLogs.filter((log) => log.access_type !== 'check_out' && log.status === 'allowed');

      this.setText(this.checkinCount, checkins.length);
      this.setText(this.presentCount, employees.length);
      this.setText(this.alertCount, alerts.length);
      this.renderActivities(logs.slice(0, 5));
    } catch (error) {
      this.setText(this.checkinCount, '--');
      this.setText(this.presentCount, '--');
      this.setText(this.alertCount, '--');
      this.renderError(error.message);
    }
  }

  renderActivities(logs) {
    if (!this.activityBody) return;
    if (!logs.length) {
      this.activityBody.innerHTML =
        '<tr><td colspan="4" style="text-align:center;color:#a0aec0">Chua co hoat dong nao</td></tr>';
      return;
    }

    this.activityBody.innerHTML = logs
      .map((log) => {
        const status = log.status === 'allowed' ? 'Cho phep' : 'Tu choi';
        const statusClass = log.status === 'allowed' ? 'status-allowed' : 'status-denied';
        return `
          <tr>
            <td>${DeepFaceAPI.escapeHTML(DeepFaceAPI.formatDateTime(log.timestamp))}</td>
            <td>${DeepFaceAPI.escapeHTML(log.access_type || 'access')}</td>
            <td>${DeepFaceAPI.escapeHTML(log.employee_name || log.camera_location || 'N/A')}</td>
            <td><span class="status-badge ${statusClass}">${status}</span></td>
          </tr>
        `;
      })
      .join('');
  }

  renderError(message) {
    if (!this.activityBody) return;
    this.activityBody.innerHTML = `
      <tr>
        <td colspan="4" style="text-align:center;color:#fbbf24">
          Khong tai duoc dashboard: ${DeepFaceAPI.escapeHTML(message)}
        </td>
      </tr>
    `;
  }

  setText(element, value) {
    if (element) element.textContent = value;
  }
}

document.addEventListener('DOMContentLoaded', () => new AdminDashboardModule());
