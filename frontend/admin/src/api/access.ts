import { apiRequest } from "./client";
import type { AccessCheckPayload, AccessCheckResponse } from "../types/access";
import type { AccessLog } from "../types/log";

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

export function listAccessLogs(token: string): Promise<AccessLog[]> {
  return apiRequest<AccessLog[]>("/logs", { token });
}
