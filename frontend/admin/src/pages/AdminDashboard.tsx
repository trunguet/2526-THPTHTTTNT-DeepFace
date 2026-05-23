import type { Camera } from "../types/camera";
import type { Employee } from "../types/employee";
import type { AccessLog } from "../types/log";

interface AdminDashboardProps {
  employees: Employee[];
  cameras: Camera[];
  logs: AccessLog[];
  onRefresh: () => void;
}

export default function AdminDashboard({
  employees,
  cameras,
  logs,
  onRefresh,
}: AdminDashboardProps) {
  const grantedCount = logs.filter((log) => log.status === "granted").length;
  const processingCount = logs.filter((log) => log.status === "processing").length;

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Overview</p>
          <h2>Access control status</h2>
        </div>
        <button className="secondary-button" onClick={onRefresh} type="button">
          Refresh
        </button>
      </div>

      <div className="metric-grid">
        <article className="metric-card">
          <span>Employees</span>
          <strong>{employees.length}</strong>
        </article>
        <article className="metric-card">
          <span>Cameras</span>
          <strong>{cameras.length}</strong>
        </article>
        <article className="metric-card">
          <span>Granted logs</span>
          <strong>{grantedCount}</strong>
        </article>
        <article className="metric-card">
          <span>Processing</span>
          <strong>{processingCount}</strong>
        </article>
      </div>

      <div className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Recent activity</p>
            <h2>Latest access decisions</h2>
          </div>
        </div>
        <div className="activity-list">
          {logs.slice(0, 5).map((log) => (
            <div className="activity-item" key={log.id}>
              <span className={`status-dot ${log.status}`} />
              <div>
                <strong>Log #{log.id}</strong>
                <p>{log.image_path ?? "No image path"}</p>
              </div>
              <span>{log.status}</span>
            </div>
          ))}
          {logs.length === 0 ? <p className="muted">No activity yet.</p> : null}
        </div>
      </div>
    </section>
  );
}
