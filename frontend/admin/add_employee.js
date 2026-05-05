/**
 * Add Employee Module
 * Handles employee registration form, image upload to MinIO, and vector extraction
 */

class AddEmployeeModule {
  constructor() {
    this.form = document.getElementById('add-employee-form');
    this.imageInput = document.getElementById('employee-image');
    this.previewImage = document.getElementById('preview-image');
    this.submitBtn = document.getElementById('submit-btn');
    this.statusMessage = document.getElementById('status-message');

    this.apiBaseURL = this.getApiBaseURL();
    this.init();
  }

  init() {
    if (this.form) {
      this.form.addEventListener('submit', (e) => this.handleSubmit(e));
      this.form.addEventListener('reset', () => this.clearPreview());
    }
    if (this.imageInput) {
      this.imageInput.addEventListener('change', (e) => this.handleImageChange(e));
    }
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
   * Handle image preview when file is selected
   */
  handleImageChange(event) {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        if (this.previewImage) {
          this.previewImage.src = e.target.result;
          this.previewImage.style.display = 'block';
        }
      };
      reader.readAsDataURL(file);
    } else {
      this.clearPreview();
    }
  }

  /**
   * Handle form submission
   */
  async handleSubmit(event) {
    event.preventDefault();

    const fullName = document.getElementById('employee-name')?.value;
    const employeeId = document.getElementById('employee-id')?.value;
    const imageFile = this.imageInput?.files[0];
    const email = document.getElementById('employee-email')?.value;
    const department = document.getElementById('employee-department')?.value;

    if (!fullName || !employeeId || !imageFile || !email) {
      this.showMessage('Vui lòng điền đầy đủ thông tin', 'error');
      return;
    }

    this.setSubmitLoading(true);
    this.showMessage('Đang xử lý...', 'info');

    try {
      // Step 1: Upload image to MinIO
      const upload = await this.uploadImageToMinio(imageFile, employeeId);

      // Step 2: Create employee record in database
      await this.createEmployeeRecord({
        full_name: fullName,
        employee_id: employeeId,
        email: email,
        department: department,
        image_url: upload.image_url,
        image_object_key: upload.image_object_key,
      });

      this.showMessage('✓ Thêm nhân viên thành công! Hệ thống đang tạo vector khuôn mặt.', 'success');
      this.form.reset();
      this.clearPreview();

      // Redirect after 2 seconds
      setTimeout(() => {
        window.location.href = './manage_list.html';
      }, 2000);
    } catch (error) {
      console.error('Error:', error);
      this.showMessage(`❌ Lỗi: ${error.message}`, 'error');
    } finally {
      this.setSubmitLoading(false);
    }
  }

  /**
   * Upload image to MinIO
   */
  async uploadImageToMinio(file, employeeId) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('employee_id', employeeId);

      const data = window.DeepFaceAPI
        ? await window.DeepFaceAPI.post('/api/employees/upload-image', formData)
        : await this.fetchJson('/api/employees/upload-image', {
            method: 'POST',
            body: formData,
          });
      return {
        image_url: data.image_url || data.url,
        image_object_key: data.image_object_key || '',
      };
    } catch (error) {
      throw new Error(`Image upload failed: ${error.message}`);
    }
  }

  /**
   * Create employee record in database
   */
  async createEmployeeRecord(employeeData) {
    try {
      return window.DeepFaceAPI
        ? await window.DeepFaceAPI.post('/api/employees', employeeData)
        : await this.fetchJson('/api/employees', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${this.getAuthToken()}`,
            },
            body: JSON.stringify(employeeData),
          });
    } catch (error) {
      throw new Error(`Employee creation failed: ${error.message}`);
    }
  }

  /**
   * Get authentication token from localStorage
   */
  getAuthToken() {
    return localStorage.getItem('auth_token') || '';
  }

  async fetchJson(path, options = {}) {
    const response = await fetch(`${this.apiBaseURL}${path}`, options);
    const contentType = response.headers.get('content-type') || '';
    const payload = contentType.includes('application/json')
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      const detail =
        typeof payload === 'object' ? payload.detail || payload.message : payload;
      throw new Error(detail || `HTTP ${response.status}`);
    }

    return payload;
  }

  setSubmitLoading(isLoading) {
    if (!this.submitBtn) return;
    this.submitBtn.disabled = isLoading;
    this.submitBtn.setAttribute('aria-busy', isLoading ? 'true' : 'false');
  }

  clearPreview() {
    if (!this.previewImage) return;
    this.previewImage.removeAttribute('src');
    this.previewImage.style.display = 'none';
  }

  /**
   * Display status message
   */
  showMessage(message, type) {
    if (this.statusMessage) {
      this.statusMessage.textContent = message;
      this.statusMessage.className = `status-message status-${type}`;
      this.statusMessage.style.display = 'block';
    }
  }
}

// Initialize module when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  new AddEmployeeModule();
});
