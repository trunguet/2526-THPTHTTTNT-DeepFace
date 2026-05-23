import { apiRequest } from "./client";
import type { EvaluationReport } from "../types/evaluation";

export function getEvaluationReport(token: string) {
  return apiRequest<EvaluationReport>("/admin/evaluation-report", { token });
}
