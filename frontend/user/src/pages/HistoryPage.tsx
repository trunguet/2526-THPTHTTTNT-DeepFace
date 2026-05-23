import HistoryTable from "../components/HistoryTable";
import type { AccessLog } from "../types/log";

interface HistoryPageProps {
  logs: AccessLog[];
  isLoading: boolean;
  onRefresh: () => Promise<void>;
}

export default function HistoryPage({
  logs,
  isLoading,
  onRefresh,
}: HistoryPageProps) {
  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">History</p>
          <h2>Recent access checks</h2>
        </div>
        <button className="secondary-button" onClick={() => void onRefresh()}>
          Refresh
        </button>
      </div>
      <HistoryTable isLoading={isLoading} logs={logs} />
    </section>
  );
}
