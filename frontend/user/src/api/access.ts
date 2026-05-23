import { apiRequest } from "./client";
import type {
  AccessCheckPayload,
  AccessCheckResponse,
  ImageUploadResponse,
} from "../types/access";

export function checkAccess(
  token: string,
  payload: AccessCheckPayload,
): Promise<AccessCheckResponse> {
  return apiRequest<AccessCheckResponse>("/access/check", {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}

export function uploadAccessSnapshot(
  token: string,
  file: File,
): Promise<ImageUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiRequest<ImageUploadResponse>("/access/snapshots", {
    method: "POST",
    token,
    body: formData,
  });
}

export function checkAccessImage(
  token: string,
  cameraId: number,
  file: File,
): Promise<AccessCheckResponse> {
  const formData = new FormData();
  formData.append("camera_id", String(cameraId));
  formData.append("file", file);
  return apiRequest<AccessCheckResponse>("/access/check-image", {
    method: "POST",
    token,
    body: formData,
  });
}
