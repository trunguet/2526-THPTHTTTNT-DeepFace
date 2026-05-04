/**
 * Manage Employee List Module
 * Handles display, edit, and delete operations for employee list
 */

class ManageEmployeeListModule {
  constructor() {
    this.employeeTable = document.getElementById('employee-table');
    this.tableBody = document.getElementById('employee-table-body');
    this.searchInput = document.getElementById('search-employee');
    this.deleteModal = document.getElementById('delete-modal');
    this.confirmDeleteBtn = document.getElementById('confirm-delete');
    this.cancelDeleteBtn = document.getElementById('cancel-delete');

    this.apiBaseURL = this.getApiBaseURL();
    this.employees = [];
    this.selectedEmployeeId = null;

    this.init();
  }

  init() {
    this.fetchEmployees();

    if (this.searchInput) {
      this.searchInput.addEventListener('input', (e) => this.filterEmployees(e.target.value));
    }

    if (this.confirmDeleteBtn) {
      this.confirmDeleteBtn.addEventListener('click', () => this.deleteEmployee());
    }

    if (this.cancelDeleteBtn) {
      this.cancelDeleteBtn.addEventListener('click', () => this.closeDeleteModal());
    }
  }

  getApiBaseURL() {
    return process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
  }

  /**
   * Fetch all employees from backend
   */
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

      this.employees = await response.json();
      this.renderTable();
    } catch (error) {
      console.error('Error fetching employees:', error);
      this.showError('Không thể tải danh sách nhân viên');
    }
  }

  /**
   * Render employee table
   */
  renderTable() {
    if (!this.tableBody) return;

    this.tableBody.innerHTML = '';

    if (this.employees.length === 0) {
      this.tableBody.innerHTML = '<tr><td colspan="6" class="text-center">Không có nhân viên nào</td></tr>';
      return;
    }

    this.employees.forEach((employee, index) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${index + 1}</td>
        <td>${employee.full_name}</td>
        <td>${employee.employee_id}</td>
        <td>${employee.email}</td>
        <td>${employee.department || 'N/A'}</td>
        <td>
          <button class="btn btn-sm btn-edit" onclick="manageModule.editEmployee(${employee.id})">Sửa</button>
          <button class="btn btn-sm btn-delete" onclick="manageModule.openDeleteModal(${employee.id})">Xóa</button>
        </td>
      `;
      this.tableBody.appendChild(row);
    });
  }

  /**
   * Filter employees by search term
   */
  filterEmployees(searchTerm) {
    const filtered = this.employees.filter(
      (emp) =>
        emp.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        emp.employee_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        emp.email.toLowerCase().includes(searchTerm.toLowerCase())
    );

    this.employees = filtered;
    this.renderTable();

    // If search is cleared, reload all
    if (!searchTerm.trim()) {
      this.fetchEmployees();
    }
  }

  /**
   * Edit employee (navigate to edit page or open modal)
   */
  editEmployee(employeeId) {
    window.location.href = `/admin/edit_employee.html?id=${employeeId}`;
  }

  /**
   * Open delete confirmation modal
   */
  openDeleteModal(employeeId) {
    this.selectedEmployeeId = employeeId;
    if (this.deleteModal) {
      this.deleteModal.style.display = 'block';
    }
  }

  /**
   * Close delete confirmation modal
   */
  closeDeleteModal() {
    if (this.deleteModal) {
      this.deleteModal.style.display = 'none';
    }
    this.selectedEmployeeId = null;
  }

  /**
   * Delete employee
   */
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
      this.fetchEmployees(); // Reload the list
      this.showSuccess('✓ Xóa nhân viên thành công');
    } catch (error) {
      console.error('Error deleting employee:', error);
      this.showError('❌ Không thể xóa nhân viên');
    }
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
    this.showAlert(message, 'success');
  }

  /**
   * Show error message
   */
  showError(message) {
    this.showAlert(message, 'error');
  }

  /**
   * Show alert message
   */
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

// Global instance for inline onclick handlers
let manageModule;

document.addEventListener('DOMContentLoaded', () => {
  manageModule = new ManageEmployeeListModule();
});
