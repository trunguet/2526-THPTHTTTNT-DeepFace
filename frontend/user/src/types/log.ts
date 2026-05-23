import type { AccessLogStatus } from "./access";

export interface AccessLog {
  id: number;
  employee_id: number | null;
  employee_name: string | null;
  camera_id: number | null;
  status: AccessLogStatus;
  score: number | null;
  image_path: string | null;
  message: string | null;
  created_at: string;
}
