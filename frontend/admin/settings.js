class AdminSettingsModule {
  constructor() {
    this.apiInput = document.getElementById('api-base-url');
    this.saveBtn = document.getElementById('save-api-url');
    this.testBtn = document.getElementById('test-api-url');
    this.resetBtn = document.getElementById('reset-api-url');
    this.status = document.getElementById('settings-status');
    this.init();
  }

  init() {
    if (this.apiInput) this.apiInput.value = DeepFaceAPI.getBaseURL();
    this.saveBtn?.addEventListener('click', () => this.save());
    this.testBtn?.addEventListener('click', () => this.test());
    this.resetBtn?.addEventListener('click', () => this.reset());
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
}

document.addEventListener('DOMContentLoaded', () => new AdminSettingsModule());
