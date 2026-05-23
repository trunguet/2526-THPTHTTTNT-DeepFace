export type EmployeeStatus = "active" | "inactive";
export type EmbeddingStatus = "none" | "pending" | "success" | "error";

export interface Employee {
  id: number;
  code: string;
  name: string;
  department: string | null;
  status: EmployeeStatus;
  embedding_status: EmbeddingStatus;
  embedding_error: string | null;
  created_at: string;
}

export interface EmployeePayload {
  code: string;
  name: string;
  department?: string | null;
  status: EmployeeStatus;
}

export interface EmbeddingJobResponse {
  job_id: string;
  type: string;
  employee_id: number;
  image_key: string;
  image_path: string;
  queue_name: string;
  message: string;
}

export interface ImageUploadResponse {
  object_key: string;
  bucket: string;
  content_type: string;
  size: number;
  job_id: string | null;
  type: string | null;
  employee_id: number | null;
  queue_name: string | null;
  message: string | null;
}
