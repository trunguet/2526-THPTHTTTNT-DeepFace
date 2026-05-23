import { useEffect, useState } from "react";
import {
  createEmployee,
  deleteEmployee,
  listEmployees,
  queueEmbeddingJob,
  updateEmployee,
  uploadEmployeeFaceImage,
} from "../api/employees";
import EmployeeForm from "../components/EmployeeForm";
import EmployeeTable from "../components/EmployeeTable";
import type { Employee, EmployeePayload } from "../types/employee";

interface EmployeePageProps {
  token: string;
  onEmployeesChange: (employees: Employee[]) => void;
}

type EmployeeView = "form" | "list";

export default function EmployeePage({
  token,
  onEmployeesChange,
}: EmployeePageProps) {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [employeeView, setEmployeeView] = useState<EmployeeView>("form");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const activeEmployees = employees.filter((employee) => employee.status === "active");

  async function loadEmployees() {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listEmployees(token);
      setEmployees(data);
      onEmployeesChange(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cannot load employees");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadEmployees();
  }, [token]);

  async function queueFaceImage(employeeId: number, file: File) {
    const upload = await uploadEmployeeFaceImage(token, employeeId, file);
    if (upload.job_id) {
      return `Face photo submitted and embedding job queued: ${upload.job_id}`;
    }

    const job = await queueEmbeddingJob(token, employeeId, upload.object_key);
    return `Face photo submitted and embedding job queued: ${job.job_id}`;
  }

  async function handleSubmit(payload: EmployeePayload, faceImage: File | null) {
    setIsSaving(true);
    setError(null);
    setMessage(null);
    try {
      const savedEmployee = editingEmployee
        ? await updateEmployee(token, editingEmployee.id, payload)
        : await createEmployee(token, payload);

      const imageMessage = faceImage
        ? await queueFaceImage(savedEmployee.id, faceImage)
        : null;
      setMessage(
        imageMessage ??
          (editingEmployee ? "Employee updated." : "Employee created."),
      );
      setEditingEmployee(null);
      await loadEmployees();
      setEmployeeView("list");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cannot save employee");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete(employeeId: number) {
    setError(null);
    setMessage(null);
    try {
      await deleteEmployee(token, employeeId);
      setMessage("Employee deleted.");
      await loadEmployees();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cannot delete employee");
    }
  }

  function handleEdit(employee: Employee) {
    setEditingEmployee(employee);
    setEmployeeView("form");
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">People</p>
          <h2>Employee management</h2>
        </div>
        <button className="secondary-button" onClick={() => void loadEmployees()}>
          Refresh
        </button>
      </div>

      <div className="section-tabs" aria-label="Employee management sections">
        <button
          className={employeeView === "form" ? "active" : ""}
          onClick={() => {
            setEmployeeView("form");
            setEditingEmployee(null);
          }}
          type="button"
        >
          Add employee
        </button>
        <button
          className={employeeView === "list" ? "active" : ""}
          onClick={() => setEmployeeView("list")}
          type="button"
        >
          Employee list
        </button>
      </div>

      {error ? <div className="alert error">{error}</div> : null}
      {message ? <div className="alert success">{message}</div> : null}

      {employeeView === "form" ? (
        <EmployeeForm
          employee={editingEmployee}
          isSaving={isSaving}
          onCancelEdit={() => {
            setEditingEmployee(null);
            setEmployeeView("list");
          }}
          onSubmit={handleSubmit}
        />
      ) : (
        <EmployeeTable
          employees={activeEmployees}
          isLoading={isLoading}
          onDelete={handleDelete}
          onEdit={handleEdit}
        />
      )}
    </section>
  );
}
