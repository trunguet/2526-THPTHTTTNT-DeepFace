export type AccessLogStatus = "processing" | "granted" | "denied" | "error";

export interface AccessCheckPayload {
  camera_id: number;
  image_key: string;
}

export interface AccessCheckResponse {
  log_id: number;
  job_id: string | null;
  status: AccessLogStatus;
  employee_id: number | null;
  employee_name: string | null;
  camera_id: number;
  score: number | null;
  image_key: string;
  image_path: string;
  message: string;
  created_at: string;
}

export interface ImageUploadResponse {
  object_key: string;
  bucket: string;
  content_type: string;
  size: number;
}
