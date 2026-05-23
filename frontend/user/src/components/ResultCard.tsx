import type { AccessCheckResponse } from "../types/access";
import type { AccessLog } from "../types/log";

interface ResultCardProps {
  cameraName: string | null;
  isSubmittingFrame: boolean;
  latestLog: AccessLog | null;
  result: AccessCheckResponse | null;
}

function getResultTitle(status: string | null, message: string | null): string {
  if (!status) {
    return "Ready for attendance";
  }

  if (message?.toLowerCase().includes("multiple faces")) {
    return "Frame rejected";
  }

  if (status === "granted") {
    return "Attendance confirmed";
  }

  if (status === "denied") {
    return "Access denied";
  }

  if (status === "error") {
    return "Check failed";
  }

  return "Processing frame";
}

function getResultMessage(status: string | null, message: string | null): string {
  if (message?.toLowerCase().includes("multiple faces")) {
    return "Too many people are in the camera frame. This image was rejected and will not be accepted for attendance.";
  }

  if (status === "granted") {
    return message ?? "Attendance was confirmed successfully.";
  }

  if (status === "denied") {
    return message ?? "No matching active employee was found.";
  }

  if (status === "error") {
    return message ?? "This frame could not be processed.";
  }

  if (status === "processing") {
    return message ?? "The frame is being checked by the recognition worker.";
  }

  return "Stand centered in the frame and keep exactly one face visible.";
}

export default function ResultCard({
  cameraName,
  isSubmittingFrame,
  latestLog,
  result,
}: ResultCardProps) {
  const activeLog =
    result && latestLog?.id === result.log_id
      ? latestLog
      : result && latestLog && latestLog.id > result.log_id
        ? latestLog
        : !result
          ? latestLog
          : null;
  const status = activeLog?.status ?? result?.status ?? null;
  const message =
    activeLog?.message ??
    result?.message ??
    "Stand centered in the frame and keep exactly one face visible.";
  const displayMessage = getResultMessage(status, message);
  const employeeName = activeLog?.employee_name ?? result?.employee_name ?? null;
  const score = activeLog?.score ?? result?.score ?? null;
  const cameraLabel = cameraName ?? result?.camera_id ?? activeLog?.camera_id ?? "-";
  const cardStatus = status ?? "idle";

  return (
    <section className={`panel result-card ${cardStatus}`}>
      <span>{isSubmittingFrame ? "Scanning" : status ?? "Guide"}</span>
      <strong>{getResultTitle(status, message)}</strong>
      <p>{displayMessage}</p>
      <dl>
        <div>
          <dt>Camera</dt>
          <dd>{cameraLabel}</dd>
        </div>
        <div>
          <dt>Employee</dt>
          <dd>{employeeName ?? "-"}</dd>
        </div>
        <div>
          <dt>Score</dt>
          <dd>{score === null ? "-" : score.toFixed(3)}</dd>
        </div>
      </dl>
      {status === "granted" ? null : (
        <ul className="result-guide-list">
          <li>Keep exactly one person in the camera frame.</li>
          <li>Look straight at the camera until the status changes.</li>
        </ul>
      )}
    </section>
  );
}
