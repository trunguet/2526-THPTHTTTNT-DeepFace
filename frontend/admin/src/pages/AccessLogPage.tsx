import { useEffect, useState } from "react";
import { listAccessLogs } from "../api/access";
import LogTable from "../components/LogTable";
import type { AccessLog } from "../types/log";

interface AccessLogPageProps {
  token: string;
  onLogsChange: (logs: AccessLog[]) => void;
}

export default function AccessLogPage({ token, onLogsChange }: AccessLogPageProps) {
  const [logs, setLogs] = useState<AccessLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadLogs() {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listAccessLogs(token);
      setLogs(data);
      onLogsChange(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cannot load logs");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadLogs();
  }, [token]);

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Audit</p>
          <h2>Access logs</h2>
        </div>
        <button className="secondary-button" onClick={() => void loadLogs()}>
          Refresh
        </button>
      </div>

      {error ? <div className="alert error">{error}</div> : null}
      <LogTable isLoading={isLoading} logs={logs} />
    </section>
  );
}
