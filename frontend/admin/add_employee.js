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

  /**
   * Handle image preview when file is selected
   */
  handleImageChange(event) {
    const file = event.target.files[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        this.showMessage('File tai len phai la anh khuon mat', 'error');
        this.imageInput.value = '';
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        this.showMessage('Anh khong duoc vuot qua 5MB', 'error');
        this.imageInput.value = '';
        return;
      }

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

    const fullName = document.getElementById('employee-name')?.value.trim();
    const employeeId = document.getElementById('employee-id')?.value.trim();
    const imageFile = this.imageInput?.files[0];
    const email = document.getElementById('employee-email')?.value.trim();
    const department = document.getElementById('employee-department')?.value.trim();

    if (!fullName || !employeeId || !imageFile || !email) {
      this.showMessage('Vui lòng điền đầy đủ thông tin', 'error');
      return;
    }

    this.submitBtn.disabled = true;
    this.showMessage('Đang xử lý...', 'info');

    try {
      // Step 1: Upload image to MinIO
      const uploadResult = await this.uploadImageToMinio(imageFile, employeeId);

      // Step 2: Create employee record in database
      const employee = await this.createEmployeeRecord({
        full_name: fullName,
        employee_id: employeeId,
        email: email,
        department: department,
        image_url: uploadResult.image_url,
        image_object_key: uploadResult.object_key,
      });

      // Step 3: Trigger vector embedding extraction
      await this.triggerVectorExtraction(employee.id, uploadResult.image_url);

      this.showMessage('✓ Thêm nhân viên thành công!', 'success');
      this.form.reset();
      if (this.previewImage) {
        this.previewImage.style.display = 'none';
      }

      // Redirect after 2 seconds
      setTimeout(() => {
        window.location.href = './manage_list.html';
      }, 1200);
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

      const data = await DeepFaceAPI.post('/api/employees/upload-image', formData);
      return {
        image_url: data.image_url || data.url,
        object_key: data.object_key,
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
      return await DeepFaceAPI.post('/api/employees', employeeData);
    } catch (error) {
      throw new Error(`Employee creation failed: ${error.message}`);
    }
  }

  /**
   * Trigger vector embedding extraction and Qdrant indexing
   */
  async triggerVectorExtraction(employeeId, imageUrl) {
    try {
      return await DeepFaceAPI.post(
        `/api/employees/${encodeURIComponent(employeeId)}/extract-embedding`,
        { image_url: imageUrl }
      );
    } catch (error) {
      console.warn(`Embedding extraction warning: ${error.message}`);
      // Non-critical error, continue
    }
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
