import { useEffect, useState } from "react";
import type { Employee } from "../types/employee";

interface EmployeeTableProps {
  employees: Employee[];
  isLoading: boolean;
  onEdit: (employee: Employee) => void;
  onDelete: (employeeId: number) => Promise<void>;
}

const PAGE_SIZE = 5;

export default function EmployeeTable({
  employees,
  isLoading,
  onEdit,
  onDelete,
}: EmployeeTableProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const pageCount = Math.max(1, Math.ceil(employees.length / PAGE_SIZE));
  const normalizedPage = Math.min(currentPage, pageCount);
  const pageStart = (normalizedPage - 1) * PAGE_SIZE;
  const visibleEmployees = employees.slice(pageStart, pageStart + PAGE_SIZE);

  useEffect(() => {
    setCurrentPage(1);
  }, [employees]);

  if (isLoading) {
    return <div className="panel state-panel">Loading employees...</div>;
  }

  if (employees.length === 0) {
    return <div className="panel state-panel">No employees yet.</div>;
  }

  function confirmDelete(employee: Employee) {
    const confirmed = window.confirm(
      `Are you sure you want to delete ${employee.name}?`,
    );
    if (confirmed) {
      void onDelete(employee.id);
    }
  }

  return (
    <div className="panel table-panel">
      <table>
        <thead>
          <tr>
            <th>Code</th>
            <th>Name</th>
            <th>Department</th>
            <th>Embedding</th>
            <th className="actions-header">Actions</th>
          </tr>
        </thead>
        <tbody>
          {visibleEmployees.map((employee) => (
            <tr key={employee.id}>
              <td>{employee.code}</td>
              <td>{employee.name}</td>
              <td>{employee.department ?? "-"}</td>
              <td>
                <span className={`status-pill ${employee.embedding_status}`}>
                  {employee.embedding_status}
                </span>
                {employee.embedding_error ? (
                  <p className="cell-note">{employee.embedding_error}</p>
                ) : null}
              </td>
              <td className="actions-cell">
                <div className="row-actions">
                  <button className="small-button" onClick={() => onEdit(employee)}>
                    Edit
                  </button>
                  <button
                    className="danger-button"
                    onClick={() => confirmDelete(employee)}
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="pagination-bar">
        <span>
          Showing {pageStart + 1}-{Math.min(pageStart + PAGE_SIZE, employees.length)} of{" "}
          {employees.length}
        </span>
        <div className="pagination-actions">
          <button
            className="secondary-button compact-button"
            disabled={normalizedPage === 1}
            onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
            type="button"
          >
            Previous
          </button>
          <strong>
            {normalizedPage} / {pageCount}
          </strong>
          <button
            className="secondary-button compact-button"
            disabled={normalizedPage === pageCount}
            onClick={() => setCurrentPage((page) => Math.min(pageCount, page + 1))}
            type="button"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
