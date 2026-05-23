import { useEffect, useMemo, useState } from "react";
import { getEvaluationReport } from "../api/evaluation";
import type { EvaluationReport } from "../types/evaluation";
import type { User } from "../types/user";

interface SettingsPageProps {
  camerasCount: number;
  employeesCount: number;
  logsCount: number;
  token: string;
  user: User;
}

interface HealthSnapshot {
  status: "loading" | "ok" | "error";
  environment: string;
  database: string;
  redis: string;
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export default function SettingsPage({
  camerasCount,
  employeesCount,
  logsCount,
  token,
  user,
}: SettingsPageProps) {
  const [health, setHealth] = useState<HealthSnapshot>({
    status: "loading",
    environment: import.meta.env.MODE ?? "dev",
    database: "unknown",
    redis: "unknown",
  });
  const [evaluationReport, setEvaluationReport] = useState<EvaluationReport | null>(null);
  const [evaluationError, setEvaluationError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadHealth() {
      try {
        const response = await fetch(`${apiBaseUrl}/health`, {
          signal: controller.signal,
        });
        const body = (await response.json()) as Partial<HealthSnapshot> & {
          environment?: string;
          database?: string;
          redis?: string;
          status?: string;
        };
        setHealth({
          status: response.ok ? "ok" : "error",
          environment: body.environment ?? (import.meta.env.MODE ?? "dev"),
          database: body.database ?? "unknown",
          redis: body.redis ?? "unknown",
        });
      } catch (_error) {
        if (!controller.signal.aborted) {
          setHealth({
            status: "error",
            environment: import.meta.env.MODE ?? "dev",
            database: "unknown",
            redis: "unknown",
          });
        }
      }
    }

    void loadHealth();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadEvaluationReport() {
      try {
        const report = await getEvaluationReport(token);
        if (isMounted) {
          setEvaluationReport(report);
          setEvaluationError(null);
        }
      } catch (error) {
        if (isMounted) {
          setEvaluationReport(null);
          setEvaluationError(error instanceof Error ? error.message : "Cannot load evaluation report");
        }
      }
    }

    void loadEvaluationReport();
    return () => {
      isMounted = false;
    };
  }, [token]);

  const serviceItems = useMemo(
    () => [
      {
        label: "Backend API",
        value: health.status === "loading" ? "Checking..." : health.status === "ok" ? "Healthy" : "Unavailable",
        tone: health.status === "loading" ? "pending" : health.status === "ok" ? "success" : "error",
      },
      {
        label: "PostgreSQL",
        value: health.database === "ok" ? "Connected" : health.database === "unknown" ? "Checking..." : "Issue detected",
        tone: health.database === "ok" ? "success" : health.database === "unknown" ? "pending" : "error",
      },
      {
        label: "Redis queue",
        value: health.redis === "ok" ? "Connected" : health.redis === "unknown" ? "Checking..." : "Issue detected",
        tone: health.redis === "ok" ? "success" : health.redis === "unknown" ? "pending" : "error",
      },
      {
        label: "Worker / MinIO / Qdrant",
        value: "Coming later",
        tone: "none",
      },
    ],
    [health],
  );

  const configItems = [
    { label: "API base URL", value: apiBaseUrl },
    { label: "Environment", value: health.environment },
    { label: "Detector backend", value: "mtcnn" },
    { label: "Embedding model", value: "Facenet512" },
    { label: "Match threshold", value: "0.70" },
  ];

  const ruleItems = [
    "One person only in each frame.",
    "Multiple faces are rejected immediately.",
    "Realtime access checks run every 2 seconds.",
    "Access is granted only when the best score passes the current threshold.",
  ];

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Configuration</p>
          <h2>System settings</h2>
        </div>
      </div>

      <div className="settings-sections">
        <div className="panel settings-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Session</p>
              <h2>Admin session</h2>
            </div>
            <span className={`status-pill ${user.role}`}>{user.role}</span>
          </div>
          <div className="settings-grid">
            <div>
              <span>Signed in as</span>
              <strong>{user.username}</strong>
            </div>
            <div>
              <span>Role</span>
              <strong>{user.role}</strong>
            </div>
            <div>
              <span>Created</span>
              <strong>{new Date(user.created_at).toLocaleString()}</strong>
            </div>
          </div>
        </div>

        <div className="panel settings-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Runtime</p>
              <h2>Current configuration</h2>
            </div>
          </div>
          <div className="settings-grid">
            {configItems.map((item) => (
              <div key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        </div>

        <div className="panel settings-card evaluation-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Accuracy</p>
              <h2>Internal evaluation report</h2>
            </div>
            {evaluationReport ? (
              <span className="status-pill success">
                {Math.round((evaluationReport.metrics.correct / evaluationReport.dataset.total_cases) * 100)}% correct
              </span>
            ) : (
              <span className={`status-pill ${evaluationError ? "error" : "pending"}`}>
                {evaluationError ? "Unavailable" : "Loading"}
              </span>
            )}
          </div>

          {evaluationReport ? (
            <>
              <div className="evaluation-summary">
                <div>
                  <span>Subjects</span>
                  <strong>{evaluationReport.dataset.subjects}</strong>
                  <small>{evaluationReport.dataset.images_per_subject} images/person</small>
                </div>
                <div>
                  <span>Total cases</span>
                  <strong>{evaluationReport.dataset.total_cases}</strong>
                  <small>{evaluationReport.dataset.scenarios.join(", ")}</small>
                </div>
                <div>
                  <span>Average access</span>
                  <strong>{evaluationReport.metrics.average_access_seconds.toFixed(1)}s</strong>
                  <small>{evaluationReport.source}</small>
                </div>
              </div>

              <div className="evaluation-metrics">
                <div>
                  <span>Correct</span>
                  <strong>{evaluationReport.metrics.correct}</strong>
                </div>
                <div>
                  <span>Wrong</span>
                  <strong>{evaluationReport.metrics.wrong}</strong>
                </div>
                <div>
                  <span>Rejected</span>
                  <strong>{evaluationReport.metrics.rejected}</strong>
                </div>
              </div>

              <div className="evaluation-breakdown">
                {evaluationReport.breakdown.map((item) => (
                  <div className="evaluation-row" key={item.scenario}>
                    <strong>{item.scenario}</strong>
                    <span>{item.correct}/{item.cases} correct</span>
                    <span>{item.wrong} wrong</span>
                    <span>{item.rejected} rejected</span>
                  </div>
                ))}
              </div>

              <ul className="settings-rules compact-rules">
                {evaluationReport.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </>
          ) : (
            <div className="alert error">{evaluationError ?? "Loading evaluation report..."}</div>
          )}
        </div>

        <div className="panel settings-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Health</p>
              <h2>Service status</h2>
            </div>
          </div>
          <div className="settings-list">
            {serviceItems.map((item) => (
              <div className="settings-row" key={item.label}>
                <div>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </div>
                <span className={`status-pill ${item.tone}`}>{item.value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="panel settings-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Overview</p>
              <h2>Operational snapshot</h2>
            </div>
          </div>
          <div className="settings-grid">
            <div>
              <span>Employees</span>
              <strong>{employeesCount}</strong>
            </div>
            <div>
              <span>Access logs</span>
              <strong>{logsCount}</strong>
            </div>
            <div>
              <span>Cameras in dataset</span>
              <strong>{camerasCount}</strong>
            </div>
          </div>
        </div>

        <div className="panel settings-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Rules</p>
              <h2>Access policy</h2>
            </div>
          </div>
          <ul className="settings-rules">
            {ruleItems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
