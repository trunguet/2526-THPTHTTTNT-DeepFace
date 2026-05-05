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
    return envBaseUrl || 'http://localhost:8000';
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

    this.submitBtn.disabled = true;
    this.showMessage('Đang xử lý...', 'info');

    try {
      // Step 1: Upload image to MinIO
      const imageUrl = await this.uploadImageToMinio(imageFile, employeeId);

      // Step 2: Create employee record in database
      const employee = await this.createEmployeeRecord({
        full_name: fullName,
        employee_id: employeeId,
        email: email,
        department: department,
        image_url: imageUrl,
      });

      // Step 3: Trigger vector embedding extraction
      await this.triggerVectorExtraction(employee.id, imageUrl);

      this.showMessage('✓ Thêm nhân viên thành công!', 'success');
      this.form.reset();
      if (this.previewImage) {
        this.previewImage.style.display = 'none';
      }

      // Redirect after 2 seconds
      setTimeout(() => {
        window.location.href = '/admin/manage_list.html';
      }, 2000);
    } catch (error) {
      console.error('Error:', error);
      this.showMessage(`❌ Lỗi: ${error.message}`, 'error');
    } finally {
      this.submitBtn.disabled = false;
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

      const response = await fetch(`${this.apiBaseURL}/api/employees/upload-image`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to upload image to MinIO');
      }

      const data = await response.json();
      return data.image_url || data.url;
    } catch (error) {
      throw new Error(`Image upload failed: ${error.message}`);
    }
  }

  /**
   * Create employee record in database
   */
  async createEmployeeRecord(employeeData) {
    try {
      const response = await fetch(`${this.apiBaseURL}/api/employees`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.getAuthToken()}`,
        },
        body: JSON.stringify(employeeData),
      });

      if (!response.ok) {
        throw new Error('Failed to create employee record');
      }

      return await response.json();
    } catch (error) {
      throw new Error(`Employee creation failed: ${error.message}`);
    }
  }

  /**
   * Trigger vector embedding extraction and Qdrant indexing
   */
  async triggerVectorExtraction(employeeId, imageUrl) {
    try {
      const response = await fetch(`${this.apiBaseURL}/api/employees/${employeeId}/extract-embedding`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.getAuthToken()}`,
        },
        body: JSON.stringify({ image_url: imageUrl }),
      });

      if (!response.ok) {
        throw new Error('Failed to extract embedding');
      }

      return await response.json();
    } catch (error) {
      console.warn(`Embedding extraction warning: ${error.message}`);
      // Non-critical error, continue
    }
  }

  /**
   * Get authentication token from localStorage
   */
  getAuthToken() {
    return localStorage.getItem('auth_token') || '';
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
