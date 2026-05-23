import { useEffect, useRef, useState } from "react";
import type { AccessLogStatus } from "../types/access";

interface CameraViewProps {
  cameraId: number;
  cameraName: string;
  imagePath: string;
  intervalMs: number;
  isSubmittingFrame: boolean;
  resultStatus: AccessLogStatus | null;
  onRealtimeFrame: (file: File) => Promise<void>;
}

function getScanFrameClass(
  status: AccessLogStatus | null,
  isSubmittingFrame: boolean,
  isCameraOn: boolean,
) {
  const classes = ["scan-frame"];

  if (status === "granted") {
    classes.push("granted");
  } else if (status === "denied" || status === "error") {
    classes.push("rejected");
  } else if (status === "processing" || isSubmittingFrame) {
    classes.push("processing");
  }

  if (isCameraOn) {
    classes.push("camera-on");
  }

  return classes.join(" ");
}

export default function CameraView({
  cameraId,
  cameraName,
  imagePath,
  intervalMs,
  isSubmittingFrame,
  resultStatus,
  onRealtimeFrame,
}: CameraViewProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const isSubmittingFrameRef = useRef(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [isCameraOn, setIsCameraOn] = useState(false);

  useEffect(() => {
    isSubmittingFrameRef.current = isSubmittingFrame;
  }, [isSubmittingFrame]);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    if (!isCameraOn) {
      return;
    }

    const timer = window.setInterval(async () => {
      if (isSubmittingFrameRef.current) {
        return;
      }

      const file = await createFrameFile();
      if (file) {
        await onRealtimeFrame(file);
      }
    }, intervalMs);

    return () => window.clearInterval(timer);
  }, [intervalMs, isCameraOn, onRealtimeFrame]);

  async function startCamera() {
    setCameraError(null);
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        setCameraError("This browser does not support webcam capture.");
        return;
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 640 },
          height: { ideal: 480 },
        },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsCameraOn(true);
    } catch (err) {
      setCameraError(
        err instanceof Error ? err.message : "Cannot open the webcam.",
      );
    }
  }

  function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsCameraOn(false);
  }

  async function createFrameFile() {
    const video = videoRef.current;
    if (!video || !isCameraOn) {
      setCameraError("Start the camera before capturing a frame.");
      return null;
    }

    setCameraError(null);
    const canvas = document.createElement("canvas");
    const sourceWidth = video.videoWidth || 640;
    const sourceHeight = video.videoHeight || 480;
    const maxWidth = 640;
    const scale = Math.min(1, maxWidth / sourceWidth);
    canvas.width = Math.round(sourceWidth * scale);
    canvas.height = Math.round(sourceHeight * scale);
    const context = canvas.getContext("2d");
    if (!context) {
      setCameraError("Cannot capture this frame.");
      return null;
    }

    context.translate(canvas.width, 0);
    context.scale(-1, 1);
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((resolve) => {
      canvas.toBlob(resolve, "image/jpeg", 0.88);
    });
    if (!blob) {
      setCameraError("Cannot create a snapshot image.");
      return null;
    }

    return new File([blob], `webcam-${Date.now()}.jpg`, {
      type: "image/jpeg",
    });
  }

  return (
    <section className="panel camera-view">
      <div className="camera-meta">
        <div>
          <p className="eyebrow">Live gate camera</p>
          <h3>{cameraName}</h3>
          <p className="camera-id-label">Camera ID #{cameraId}</p>
        </div>
        <span className={isCameraOn ? "status-pill processing" : "status-pill denied"}>
          {isCameraOn ? "Scanning" : "Idle"}
        </span>
      </div>
      <div className="camera-stage">
        <div className={getScanFrameClass(resultStatus, isSubmittingFrame, isCameraOn)}>
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            className={isCameraOn ? "camera-preview active" : "camera-preview"}
          />
          <span />
          <span />
          <span />
          <span />
        </div>
        <div className="camera-actions">
          {isCameraOn ? (
            <button className="primary-button camera-toggle-button" type="button" onClick={stopCamera}>
              Stop camera
            </button>
          ) : (
            <button className="primary-button camera-toggle-button" type="button" onClick={startCamera}>
              Start camera
            </button>
          )}
        </div>
        <div className={isCameraOn ? "realtime-status active" : "realtime-status"}>
          <span>{isCameraOn ? "Realtime scanning" : "Realtime idle"}</span>
          <strong>{isSubmittingFrame ? "Sending frame..." : `${intervalMs / 1000}s interval`}</strong>
        </div>
      </div>
      {cameraError ? <div className="alert error">{cameraError}</div> : null}
      <div className="snapshot-path">
        <p className="eyebrow">Snapshot path</p>
        <strong>{imagePath || "/app/storage/uploads/snapshot.jpg"}</strong>
      </div>
    </section>
  );
}
