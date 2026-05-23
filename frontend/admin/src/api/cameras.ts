import { apiRequest } from "./client";
import type { Camera, CameraPayload } from "../types/camera";

export function listCameras(token: string): Promise<Camera[]> {
  return apiRequest<Camera[]>("/cameras", { token });
}

export function createCamera(token: string, payload: CameraPayload): Promise<Camera> {
  return apiRequest<Camera>("/cameras", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export function updateCamera(
  token: string,
  cameraId: number,
  payload: CameraPayload,
): Promise<Camera> {
  return apiRequest<Camera>(`/cameras/${cameraId}`, {
    method: "PUT",
    token,
    body: JSON.stringify(payload),
  });
}

export function deleteCamera(token: string, cameraId: number): Promise<void> {
  return apiRequest<void>(`/cameras/${cameraId}`, {
    method: "DELETE",
    token,
  });
}
