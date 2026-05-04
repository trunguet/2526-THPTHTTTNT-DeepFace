/**
 * Manage Employee List Module
 * Handles employee listing, searching, and delete actions.
 */

class ManageEmployeeListModule {
  constructor() {
    this.tableBody = document.getElementById('employee-table-body');
    this.searchInput = document.getElementById('search-employee');
    this.deleteModal = document.getElementById('delete-modal');
    this.confirmDeleteBtn = document.getElementById('confirm-delete');
    this.cancelDeleteBtn = document.getElementById('cancel-delete');

    this.allEmployees = [];
    this.visibleEmployees = [];
    this.selectedEmployeeId = null;

    this.init();
  }

  init() {
    this.fetchEmployees();

    this.searchInput?.addEventListener('input', (event) => {
      this.filterEmployees(event.target.value);
    });

    this.confirmDeleteBtn?.addEventListener('click', () => this.deleteEmployee());
    this.cancelDeleteBtn?.addEventListener('click', () => this.closeDeleteModal());
  }

  async fetchEmployees() {
    this.renderLoading();

    try {
      const data = await DeepFaceAPI.get('/api/employees');
      this.allEmployees = DeepFaceAPI.normalizeList(data);
      this.visibleEmployees = [...this.allEmployees];
      this.renderTable();
    } catch (error) {
      console.error('Error fetching employees:', error);
      this.renderEmpty(`Khong tai duoc danh sach nhan vien: ${error.message}`);
    }
  }

  renderTable() {
    if (!this.tableBody) return;

    if (!this.visibleEmployees.length) {
      this.renderEmpty('Khong co nhan vien phu hop');
      return;
    }

    this.tableBody.innerHTML = this.visibleEmployees
      .map((employee, index) => {
        const id = employee.id || employee.employee_id;
        return `
          <tr>
            <td>${index + 1}</td>
            <td>${DeepFaceAPI.escapeHTML(employee.full_name || employee.name || 'N/A')}</td>
            <td>${DeepFaceAPI.escapeHTML(employee.employee_id || id || 'N/A')}</td>
            <td>${DeepFaceAPI.escapeHTML(employee.email || 'N/A')}</td>
            <td>${DeepFaceAPI.escapeHTML(employee.department || 'N/A')}</td>
            <td>
              <button class="btn btn-sm btn-edit" data-action="edit" data-id="${DeepFaceAPI.escapeHTML(id)}">Sua</button>
              <button class="btn btn-sm btn-delete" data-action="delete" data-id="${DeepFaceAPI.escapeHTML(id)}">Xoa</button>
            </td>
          </tr>
        `;
      })
      .join('');

    this.tableBody.querySelectorAll('button[data-action]').forEach((button) => {
      button.addEventListener('click', () => {
        const action = button.dataset.action;
        const id = button.dataset.id;
        if (action === 'edit') this.editEmployee(id);
        if (action === 'delete') this.openDeleteModal(id);
      });
    });
  }

  renderLoading() {
    if (!this.tableBody) return;
    this.tableBody.innerHTML =
      '<tr><td colspan="6" class="text-center">Dang tai du lieu...</td></tr>';
  }

  renderEmpty(message) {
    if (!this.tableBody) return;
    this.tableBody.innerHTML = `<tr><td colspan="6" class="text-center">${DeepFaceAPI.escapeHTML(
      message
    )}</td></tr>`;
  }

  filterEmployees(searchTerm) {
    const keyword = searchTerm.trim().toLowerCase();

    if (!keyword) {
      this.visibleEmployees = [...this.allEmployees];
      this.renderTable();
      return;
    }

    this.visibleEmployees = this.allEmployees.filter((employee) => {
      const searchable = [
        employee.full_name,
        employee.name,
        employee.employee_id,
        employee.email,
        employee.department,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return searchable.includes(keyword);
    });

    this.renderTable();
  }

  editEmployee(employeeId) {
    this.showAlert(
      `Chuc nang sua nhan vien ${employeeId} can backend PUT /api/employees/{id} va form edit.`,
      'info'
    );
  }

  openDeleteModal(employeeId) {
    this.selectedEmployeeId = employeeId;
    if (this.deleteModal) this.deleteModal.style.display = 'block';
  }

  closeDeleteModal() {
    if (this.deleteModal) this.deleteModal.style.display = 'none';
    this.selectedEmployeeId = null;
  }

  async deleteEmployee() {
    if (!this.selectedEmployeeId) return;

    try {
      await DeepFaceAPI.delete(`/api/employees/${encodeURIComponent(this.selectedEmployeeId)}`);
      this.closeDeleteModal();
      await this.fetchEmployees();
      this.showAlert('Da xoa nhan vien thanh cong', 'success');
    } catch (error) {
      console.error('Error deleting employee:', error);
      this.showAlert(`Khong the xoa nhan vien: ${error.message}`, 'error');
    }
  }

  showAlert(message, type) {
    const alert = document.createElement('div');
    alert.className = `notification notification-${type}`;
    alert.textContent = message;
    document.body.appendChild(alert);

    setTimeout(() => alert.remove(), 3500);
  }
}

let manageModule;

document.addEventListener('DOMContentLoaded', () => {
  manageModule = new ManageEmployeeListModule();
});
