/**
 * Manage Employee List Module
 * Handles employee display, inline edit, and delete operations.
 */

class ManageEmployeeListModule {
  constructor() {
    this.tableBody = document.getElementById('employee-table-body');
    this.searchInput = document.getElementById('search-employee');

    this.editModal = document.getElementById('edit-modal');
    this.editForm = document.getElementById('edit-employee-form');
    this.cancelEditBtn = document.getElementById('cancel-edit');
    this.editNameInput = document.getElementById('edit-employee-name');
    this.editCodeInput = document.getElementById('edit-employee-code');
    this.editEmailInput = document.getElementById('edit-employee-email');
    this.editDepartmentInput = document.getElementById('edit-employee-department');

    this.deleteModal = document.getElementById('delete-modal');
    this.confirmDeleteBtn = document.getElementById('confirm-delete');
    this.cancelDeleteBtn = document.getElementById('cancel-delete');

    this.apiBaseURL = this.getApiBaseURL();
    this.allEmployees = [];
    this.employees = [];
    this.selectedEmployeeIdForEdit = null;
    this.selectedEmployeeId = null;

    this.init();
  }

  init() {
    this.fetchEmployees();

    if (this.searchInput) {
      this.searchInput.addEventListener('input', (event) => this.filterEmployees(event.target.value));
    }

    if (this.editForm) {
      this.editForm.addEventListener('submit', (event) => this.saveEmployee(event));
    }

    if (this.cancelEditBtn) {
      this.cancelEditBtn.addEventListener('click', () => this.closeEditModal());
    }

    if (this.confirmDeleteBtn) {
      this.confirmDeleteBtn.addEventListener('click', () => this.deleteEmployee());
    }

    if (this.cancelDeleteBtn) {
      this.cancelDeleteBtn.addEventListener('click', () => this.closeDeleteModal());
    }

    [this.editModal, this.deleteModal].forEach((modal) => {
      if (modal) {
        modal.addEventListener('click', (event) => {
          if (event.target === modal) {
            this.closeModal(modal);
          }
        });
      }
    });
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

  async fetchEmployees() {
    try {
      // Sử dụng API client dùng chung để nhất quán và xử lý lỗi tốt hơn
      const employeeList = await window.DeepFaceAdmin.get('/api/employees');

      // Chuẩn hóa dữ liệu trả về từ API
      this.allEmployees = window.DeepFaceAdmin.normalizeList(employeeList);
      this.employees = [...this.allEmployees];
      this.renderTable();
    } catch (error) {
      console.error('Error fetching employees:', error);
      this.showError(`Không thể tải danh sách nhân viên: ${error.message}`);
    }
  }

  renderTable() {
    if (!this.tableBody) return;

    this.tableBody.innerHTML = '';

    if (this.employees.length === 0) {
      this.tableBody.innerHTML =
        '<tr><td colspan="6" style="text-align: center; color: #a0aec0">Không có nhân viên nào</td></tr>';
      return;
    }

    this.employees.forEach((employee, index) => {
      const row = document.createElement('tr');
      const escape = window.DeepFaceAPI?.escapeHTML || ((value) => String(value ?? ''));
      // Sửa lại để hiển thị `employee_id` (mã nghiệp vụ) thay vì `id` (mã DB)
      row.innerHTML = `
        <td>${index + 1}</td>
        <td>${escape(employee.full_name)}</td> 
        <td>${escape(employee.employee_id)}</td>
        <td>${escape(employee.email)}</td>
        <td>${escape(employee.department || 'N/A')}</td>
        <td>
          <button class="btn btn-sm btn-edit" type="button" onclick="manageModule.editEmployee('${escape(employee.employee_id)}')">Sửa</button>
          <button class="btn btn-sm btn-delete" type="button" onclick="manageModule.openDeleteModal('${escape(employee.employee_id)}')">Xóa</button>
        </td>
      `;
      this.tableBody.appendChild(row);
    });
  }

  filterEmployees(searchTerm) {
    const keyword = searchTerm.trim().toLowerCase();
    if (!keyword) {
      this.employees = [...this.allEmployees];
      this.renderTable();
      return;
    }

    this.employees = this.allEmployees.filter(
      (employee) =>
        String(employee.full_name || '').toLowerCase().includes(keyword) ||
        String(employee.employee_id || '').toLowerCase().includes(keyword) ||
        String(employee.email || '').toLowerCase().includes(keyword)
    );
    this.renderTable();
  }

  editEmployee(employeeId) {
    // Tìm nhân viên bằng mã nghiệp vụ `employee_id`
    const employee = this.allEmployees.find((item) => item.employee_id === employeeId);
    if (!employee) {
      this.showError('Không tìm thấy nhân viên.');
      return;
    }

    this.selectedEmployeeIdForEdit = employee.employee_id;
    this.editNameInput.value = employee.full_name || '';
    this.editCodeInput.value = employee.employee_id || '';
    this.editEmailInput.value = employee.email || '';
    this.editDepartmentInput.value = employee.department || '';
    this.openModal(this.editModal);
  }

  closeEditModal() {
    this.closeModal(this.editModal);
    this.selectedEmployeeIdForEdit = null;
    if (this.editForm) {
      this.editForm.reset();
    }
  }

  async saveEmployee(event) {
    event.preventDefault();
    if (!this.selectedEmployeeIdForEdit) return;

    const payload = {
      full_name: this.editNameInput.value.trim(),
      email: this.editEmailInput.value.trim(),
      department: this.editDepartmentInput.value,
    };

    if (!payload.full_name) {
      this.showError('Vui lòng nhập họ và tên.');
      return;
    }

    try {
      // Sử dụng API client để cập nhật, URL dùng mã nghiệp vụ `employee_id`
      await window.DeepFaceAdmin.put(`/api/employees/${this.selectedEmployeeIdForEdit}`, payload);

      this.closeEditModal();
      await this.fetchEmployees();
      this.showSuccess('Cập nhật nhân viên thành công!');
    } catch (error) {
      console.error('Error updating employee:', error);
      this.showError(`Không thể cập nhật nhân viên: ${error.message}`);
    }
  }
  openDeleteModal(employeeId) {
    this.selectedEmployeeId = employeeId;
    this.openModal(this.deleteModal);
  }

  closeDeleteModal() {
    this.closeModal(this.deleteModal);
    this.selectedEmployeeId = null;
  }

  async deleteEmployee() {
    if (!this.selectedEmployeeId) return;

    try {
      // Sử dụng API client để xóa, URL dùng mã nghiệp vụ `employee_id`
      await window.DeepFaceAdmin.delete(`/api/employees/${this.selectedEmployeeId}`);

      this.closeDeleteModal();
      await this.fetchEmployees();
      this.showSuccess('Xóa nhân viên thành công!');
    } catch (error) {
      console.error('Error deleting employee:', error);
      this.showError(`Không thể xóa nhân viên: ${error.message}`);
    }
  }

  openModal(modal) {
    if (modal) {
      modal.classList.add('show');
      modal.style.display = 'flex';
    }
  }

  closeModal(modal) {
    if (modal) {
      modal.classList.remove('show');
      modal.style.display = 'none';
    }
  }

  showSuccess(message) {
    this.showAlert(message, 'success');
  }

  showError(message) {
    this.showAlert(message, 'error');
  }

  showAlert(message, type) {
    const alert = document.createElement('div');
    // Tái sử dụng class `notification` từ các module khác để nhất quán
    alert.className = `notification notification-${type}`;
    alert.textContent = message;
    alert.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 15px 20px;
      border-radius: 8px;
      z-index: 1000;
      color: white;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    `;
    document.body.appendChild(alert);

    setTimeout(() => {
      alert.remove();
    }, 3000);
  }
}

let manageModule;

document.addEventListener('DOMContentLoaded', () => {
  manageModule = new ManageEmployeeListModule();
});
