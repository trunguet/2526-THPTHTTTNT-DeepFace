import type { User } from "../types/auth";
import type { AccessLog } from "../types/log";

interface ProfilePageProps {
  user: User;
  logs: AccessLog[];
  signedInAt: string | null;
}

function formatDateTime(value: string | null) {
  if (!value) {
    return "This session just started";
  }

  return new Date(value).toLocaleString();
}

function formatElapsed(value: string | null) {
  if (!value) {
    return "Just now";
  }

  const elapsedMs = Date.now() - new Date(value).getTime();
  const elapsedMinutes = Math.max(1, Math.floor(elapsedMs / 60000));

  if (elapsedMinutes < 60) {
    return `${elapsedMinutes} min active`;
  }

  const elapsedHours = Math.floor(elapsedMinutes / 60);
  const remainingMinutes = elapsedMinutes % 60;
  return `${elapsedHours}h ${remainingMinutes}m active`;
}

export default function ProfilePage({
  user,
  logs,
  signedInAt,
}: ProfilePageProps) {
  const latestLog = logs[0] ?? null;
  const grantedCount = logs.filter((log) => log.status === "granted").length;
  const deniedCount = logs.filter((log) => log.status === "denied").length;
  const errorCount = logs.filter((log) => log.status === "error").length;

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Terminal session</p>
          <h2>Gate session and access status</h2>
        </div>
      </div>

      <section className="profile-hero panel">
        <div className="profile-hero-copy">
          <p className="eyebrow">Current operator</p>
          <h3>{user.username}</h3>
          <p className="profile-note">
            This page tracks the signed-in browser session, not the identity of
            the person currently in front of the gate camera. The terminal can
            scan many different faces while staying under one operator session.
          </p>
        </div>
        <div className="profile-hero-badges">
          <span className={`status-pill ${user.role}`}>{user.role}</span>
          <strong>{formatElapsed(signedInAt)}</strong>
        </div>
      </section>

      <section className="profile-summary-grid">
        <article className="panel summary-card">
          <span>Signed in</span>
          <strong>{formatDateTime(signedInAt)}</strong>
          <p>Local session start time for this browser tab.</p>
        </article>
        <article className="panel summary-card">
          <span>Latest access</span>
          <strong>{latestLog ? latestLog.status : "No checks yet"}</strong>
          <p>
            {latestLog
              ? new Date(latestLog.created_at).toLocaleString()
              : "Run the camera once to create the first access log."}
          </p>
        </article>
        <article className="panel summary-card">
          <span>Recent camera</span>
          <strong>{latestLog?.camera_id ?? "-"}</strong>
          <p>The current access flow is using the default live gate camera.</p>
        </article>
      </section>

      <section className="profile-detail-grid">
        <div className="panel profile-grid profile-grid-expanded">
          <div>
            <span>Signed-in account</span>
            <strong>{user.username}</strong>
          </div>
          <div>
            <span>Operator role</span>
            <strong>{user.role}</strong>
          </div>
          <div>
            <span>Account created</span>
            <strong>{new Date(user.created_at).toLocaleString()}</strong>
          </div>
          <div>
            <span>Granted checks</span>
            <strong>{grantedCount}</strong>
          </div>
          <div>
            <span>Denied checks</span>
            <strong>{deniedCount}</strong>
          </div>
          <div>
            <span>Error checks</span>
            <strong>{errorCount}</strong>
          </div>
        </div>

        <aside className="panel profile-side-card">
          <p className="eyebrow">Latest result</p>
          <h3>{latestLog ? `Log #${latestLog.id}` : "No result yet"}</h3>
          <div className="profile-latest-meta">
            <span className={`status-pill ${latestLog?.status ?? "processing"}`}>
              {latestLog?.status ?? "idle"}
            </span>
            <strong>
              {latestLog?.score === null || latestLog?.score === undefined
                ? "No score available"
                : latestLog.score.toFixed(3)}
            </strong>
          </div>
          <p className="profile-note">
            {latestLog
              ? latestLog.employee_name ??
                latestLog.message ??
                latestLog.image_path ??
                "This log does not have an image path."
              : "The next successful camera scan will appear here."}
          </p>
        </aside>
      </section>
    </section>
  );
}
