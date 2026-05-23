export type CameraStatus = "active" | "inactive";

export interface Camera {
  id: number;
  name: string;
  location: string | null;
  stream_url: string | null;
  status: CameraStatus;
  created_at: string;
}

export interface CameraPayload {
  name: string;
  location?: string | null;
  stream_url?: string | null;
  status: CameraStatus;
}
