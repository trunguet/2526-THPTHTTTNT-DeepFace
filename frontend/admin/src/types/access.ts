import type { AccessLogStatus } from "./log";

export interface AccessCheckPayload {
  camera_id: number;
  image_path: string;
}

export interface AccessCheckResponse {
  log_id: number;
  job_id: string | null;
  status: AccessLogStatus;
  employee_id: number | null;
  camera_id: number;
  score: number | null;
  image_path: string;
  message: string;
  created_at: string;
}
