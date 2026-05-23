import { apiRequest } from "./client";
import type { CameraRecord } from "../types/camera";

export function getDefaultActiveCamera(token: string): Promise<CameraRecord> {
  return apiRequest<CameraRecord>("/cameras/active-default", { token });
}
