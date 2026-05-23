import CameraForm from "../components/CameraForm";
import type { Camera } from "../types/camera";

interface CameraPageProps {
  token: string;
  onCamerasChange: (cameras: Camera[]) => void;
}

export default function CameraPage({ token, onCamerasChange }: CameraPageProps) {
  void token;
  void onCamerasChange;

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Entry points</p>
          <h2>Camera management</h2>
        </div>
      </div>

      <div className="camera-coming-layout">
        <CameraForm />
      </div>
    </section>
  );
}
