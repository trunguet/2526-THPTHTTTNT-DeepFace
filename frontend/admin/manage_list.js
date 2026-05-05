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
    this.selectedEditId = null;
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
      const response = await fetch(`${this.apiBaseURL}/api/employees`, {
        headers: {
          Authorization: `Bearer ${this.getAuthToken()}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch employees');
      }

      this.allEmployees = await response.json();
      this.employees = [...this.allEmployees];
      this.renderTable();
    } catch (error) {
      console.error('Error fetching employees:', error);
      this.showError('Khong the tai danh sach nhan vien');
    }
  }

  renderTable() {
    if (!this.tableBody) return;

    this.tableBody.innerHTML = '';

    if (this.employees.length === 0) {
      this.tableBody.innerHTML = '<tr><td colspan="6" class="text-center">Khong co nhan vien nao</td></tr>';
      return;
    }

    this.employees.forEach((employee, index) => {
      const row = document.createElement('tr');
      const escape = window.DeepFaceAPI?.escapeHTML || ((value) => String(value ?? ''));
      row.innerHTML = `
        <td>${index + 1}</td>
        <td>${escape(employee.full_name)}</td>
        <td>${escape(employee.employee_id)}</td>
        <td>${escape(employee.email)}</td>
        <td>${escape(employee.department || 'N/A')}</td>
        <td>
          <button class="btn btn-sm btn-edit" type="button" onclick="manageModule.editEmployee(${employee.id})">Sua</button>
          <button class="btn btn-sm btn-delete" type="button" onclick="manageModule.openDeleteModal(${employee.id})">Xoa</button>
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
    const employee = this.allEmployees.find((item) => item.id === employeeId);
    if (!employee) {
      this.showError('Khong tim thay nhan vien');
      return;
    }

    this.selectedEditId = employeeId;
    this.editNameInput.value = employee.full_name || '';
    this.editCodeInput.value = employee.employee_id || '';
    this.editEmailInput.value = employee.email || '';
    this.editDepartmentInput.value = employee.department || '';
    this.openModal(this.editModal);
  }

  closeEditModal() {
    this.closeModal(this.editModal);
    this.selectedEditId = null;
    if (this.editForm) {
      this.editForm.reset();
    }
  }

  async saveEmployee(event) {
    event.preventDefault();
    if (!this.selectedEditId) return;

    const payload = {
      full_name: this.editNameInput.value.trim(),
      email: this.editEmailInput.value.trim(),
      department: this.editDepartmentInput.value,
    };

    if (!payload.full_name) {
      this.showError('Vui long nhap ho va ten');
      return;
    }

    try {
      const response = await fetch(`${this.apiBaseURL}/api/employees/${this.selectedEditId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.getAuthToken()}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('Failed to update employee');
      }

      this.closeEditModal();
      await this.fetchEmployees();
      this.showSuccess('Cap nhat nhan vien thanh cong');
    } catch (error) {
      console.error('Error updating employee:', error);
      this.showError('Khong the cap nhat nhan vien');
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
      const response = await fetch(`${this.apiBaseURL}/api/employees/${this.selectedEmployeeId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${this.getAuthToken()}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to delete employee');
      }

      this.closeDeleteModal();
      await this.fetchEmployees();
      this.showSuccess('Xoa nhan vien thanh cong');
    } catch (error) {
      console.error('Error deleting employee:', error);
      this.showError('Khong the xoa nhan vien');
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

  getAuthToken() {
    return localStorage.getItem('auth_token') || '';
  }

  showSuccess(message) {
    this.showAlert(message, 'success');
  }

  showError(message) {
    this.showAlert(message, 'error');
  }

  showAlert(message, type) {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
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
