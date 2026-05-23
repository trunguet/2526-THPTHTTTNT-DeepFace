export interface CameraRecord {
  id: number;
  name: string;
  location: string | null;
  stream_url: string | null;
  status: "active" | "inactive";
  created_at: string;
}
