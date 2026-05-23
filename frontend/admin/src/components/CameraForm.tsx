export default function CameraForm() {
  return (
    <section className="panel form-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Camera integration</p>
          <h2>Coming later</h2>
        </div>
      </div>

      <div className="alert camera-coming-soon">
        IP camera creation is not enabled in this demo yet. The current user
        flow still uses the browser webcam, while this section will be used
        later for real RTSP or stream-based camera onboarding.
      </div>

      <label>
        Name
        <input disabled maxLength={150} placeholder="Main Gate Camera" />
      </label>

      <label>
        Location
        <input disabled maxLength={255} placeholder="Lobby" />
      </label>

      <label>
        Stream URL
        <input disabled placeholder="rtsp://camera.local/stream1" />
      </label>

      <label>
        Status
        <select disabled defaultValue="active">
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </label>

      <button className="secondary-button" disabled type="button">
        Camera onboarding coming later
      </button>
    </section>
  );
}
