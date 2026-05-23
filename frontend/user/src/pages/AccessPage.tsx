import { useEffect, useState } from "react";
import { checkAccessImage } from "../api/access";
import { getDefaultActiveCamera } from "../api/cameras";
import CameraView from "../components/CameraView";
import ResultCard from "../components/ResultCard";
import type { AccessCheckResponse, AccessLogStatus } from "../types/access";
import type { CameraRecord } from "../types/camera";
import type { AccessLog } from "../types/log";

interface AccessPageProps {
  logs: AccessLog[];
  token: string;
  onAccessQueued: () => Promise<void>;
}

export default function AccessPage({ logs, token, onAccessQueued }: AccessPageProps) {
  const [imageKey, setImageKey] = useState("");
  const [result, setResult] = useState<AccessCheckResponse | null>(null);
  const [isSubmittingFrame, setIsSubmittingFrame] = useState(false);
  const [lastRealtimeAt, setLastRealtimeAt] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [camera, setCamera] = useState<CameraRecord | null>(null);
  const [isLoadingCamera, setIsLoadingCamera] = useState(true);
  const realtimeIntervalMs = 2000;
  const latestCameraLog = camera
    ? logs.find((log) => log.camera_id === camera.id) ?? null
    : null;
  const activeCameraLog =
    result && latestCameraLog?.id === result.log_id
      ? latestCameraLog
      : result && latestCameraLog && latestCameraLog.id > result.log_id
        ? latestCameraLog
        : !result
          ? latestCameraLog
          : null;
  const cameraFrameStatus: AccessLogStatus | null =
    activeCameraLog?.status ?? result?.status ?? null;

  useEffect(() => {
    async function loadCamera() {
      setIsLoadingCamera(true);
      setError(null);
      try {
        const activeCamera = await getDefaultActiveCamera(token);
        setCamera(activeCamera);
      } catch (err) {
        setCamera(null);
        setError(
          err instanceof Error
            ? err.message
            : "No active camera is configured for this gate.",
        );
      } finally {
        setIsLoadingCamera(false);
      }
    }

    void loadCamera();
  }, [token]);

  async function handleRealtimeFrame(file: File) {
    if (isSubmittingFrame || !camera) {
      return;
    }

    setIsSubmittingFrame(true);
    setError(null);
    try {
      const response = await checkAccessImage(token, camera.id, file);
      setImageKey(response.image_key || file.name);
      setResult(response);
      setLastRealtimeAt(new Date().toLocaleTimeString());
      await onAccessQueued();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cannot check realtime frame");
    } finally {
      setIsSubmittingFrame(false);
    }
  }

  return (
    <section className="access-terminal">
      <div className="page-header access-heading">
        <div>
          <p className="eyebrow">Check access</p>
          <h2>Face verification</h2>
        </div>
        <div className="scan-summary compact">
          <span>{isLoadingCamera ? "Loading camera" : isSubmittingFrame ? "Scanning" : "Auto scan"}</span>
          <strong>
            {camera
              ? lastRealtimeAt
                ? `Last frame ${lastRealtimeAt}`
                : `${camera.name} ready`
              : "No active camera"}
          </strong>
        </div>
      </div>

      {error ? <div className="alert error">{error}</div> : null}

      <div className="access-main-grid">
        {camera ? (
          <CameraView
            cameraId={camera.id}
            cameraName={camera.name}
            intervalMs={realtimeIntervalMs}
            imagePath={imageKey}
            isSubmittingFrame={isSubmittingFrame}
            resultStatus={cameraFrameStatus}
            onRealtimeFrame={handleRealtimeFrame}
          />
        ) : (
          <section className="panel state-panel">
            No active camera is configured in admin yet.
          </section>
        )}
        <ResultCard
          cameraName={camera?.name ?? null}
          isSubmittingFrame={isSubmittingFrame}
          latestLog={latestCameraLog}
          result={result}
        />
      </div>
    </section>
  );
}
