export type AccessLogStatus = "processing" | "granted" | "denied" | "error";

export interface AccessLog {
  id: number;
  employee_id: number | null;
  camera_id: number | null;
  status: AccessLogStatus;
  score: number | null;
  image_path: string | null;
  created_at: string;
}
