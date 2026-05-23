export interface EvaluationDataset {
  subjects: number;
  registered_subjects: number;
  impostor_subjects: number;
  images_per_subject: string;
  total_cases: number;
  scenarios: string[];
}

export interface EvaluationMetrics {
  correct: number;
  wrong: number;
  rejected: number;
  average_access_seconds: number;
}

export interface EvaluationBreakdownItem {
  scenario: string;
  cases: number;
  correct: number;
  wrong: number;
  rejected: number;
}

export interface EvaluationReport {
  updated_at: string;
  source: string;
  dataset: EvaluationDataset;
  metrics: EvaluationMetrics;
  breakdown: EvaluationBreakdownItem[];
  notes: string[];
}
