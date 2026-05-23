import { FormEvent, useEffect, useRef, useState } from "react";
import type { Employee, EmployeePayload } from "../types/employee";

interface EmployeeFormProps {
  employee?: Employee | null;
  isSaving: boolean;
  onCancelEdit: () => void;
  onSubmit: (payload: EmployeePayload, faceImage: File | null) => Promise<void>;
}

const initialForm: EmployeePayload = {
  code: "",
  name: "",
  department: "",
  status: "active",
};

export default function EmployeeForm({
  employee,
  isSaving,
  onCancelEdit,
  onSubmit,
}: EmployeeFormProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [form, setForm] = useState<EmployeePayload>(initialForm);
  const [faceImage, setFaceImage] = useState<File | null>(null);

  useEffect(() => {
    if (employee) {
      setForm({
        code: employee.code,
        name: employee.name,
        department: employee.department ?? "",
        status: employee.status,
      });
      setFaceImage(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      return;
    }

    setForm(initialForm);
    setFaceImage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, [employee]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit(
      {
        ...form,
        code: form.code.trim(),
        name: form.name.trim(),
        department: form.department?.trim() || null,
      },
      faceImage,
    );
    if (!employee) {
      setForm(initialForm);
      setFaceImage(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  return (
    <form className="panel form-panel" onSubmit={handleSubmit}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{employee ? "Edit record" : "New record"}</p>
          <h2>{employee ? employee.name : "Register employee"}</h2>
        </div>
        {employee ? (
          <button className="ghost-button" onClick={onCancelEdit} type="button">
            Cancel
          </button>
        ) : null}
      </div>

      <label>
        Employee code
        <input
          required
          maxLength={50}
          value={form.code}
          onChange={(event) => setForm({ ...form, code: event.target.value })}
        />
      </label>

      <label>
        Full name
        <input
          required
          maxLength={150}
          value={form.name}
          onChange={(event) => setForm({ ...form, name: event.target.value })}
        />
      </label>

      <label>
        Department
        <input
          maxLength={150}
          value={form.department ?? ""}
          onChange={(event) =>
            setForm({ ...form, department: event.target.value })
          }
        />
      </label>

      <label>
        Submit face photo
        <input
          ref={fileInputRef}
          accept="image/*"
          type="file"
          onChange={(event) =>
            setFaceImage(event.target.files?.[0] ?? null)
          }
        />
      </label>

      <button className="primary-button" disabled={isSaving} type="submit">
        {isSaving ? "Saving..." : employee ? "Update employee" : "Add employee"}
      </button>
    </form>
  );
}
