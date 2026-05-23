import { apiRequest } from "./client";
import type { AccessLog } from "../types/log";

export function listAccessLogs(token: string): Promise<AccessLog[]> {
  return apiRequest<AccessLog[]>("/logs", { token });
}
