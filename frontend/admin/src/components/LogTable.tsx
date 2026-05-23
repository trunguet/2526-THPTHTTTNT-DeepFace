import { useEffect, useState } from "react";
import type { AccessLog } from "../types/log";

interface LogTableProps {
  logs: AccessLog[];
  isLoading: boolean;
}

const PAGE_SIZE = 6;

export default function LogTable({ logs, isLoading }: LogTableProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const pageCount = Math.max(1, Math.ceil(logs.length / PAGE_SIZE));
  const normalizedPage = Math.min(currentPage, pageCount);
  const pageStart = (normalizedPage - 1) * PAGE_SIZE;
  const visibleLogs = logs.slice(pageStart, pageStart + PAGE_SIZE);

  useEffect(() => {
    setCurrentPage(1);
  }, [logs]);

  if (isLoading) {
    return <div className="panel state-panel">Loading access logs...</div>;
  }

  if (logs.length === 0) {
    return <div className="panel state-panel">No access logs yet.</div>;
  }

  return (
    <div className="panel table-panel">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Status</th>
            <th>Employee</th>
            <th>Camera</th>
            <th>Score</th>
            <th>Image</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {visibleLogs.map((log) => (
            <tr key={log.id}>
              <td>#{log.id}</td>
              <td>
                <span className={`status-pill ${log.status}`}>{log.status}</span>
              </td>
              <td>{log.employee_id ?? "-"}</td>
              <td>{log.camera_id ?? "-"}</td>
              <td>{log.score === null ? "-" : log.score.toFixed(3)}</td>
              <td className="path-cell">{log.image_path ?? "-"}</td>
              <td>{new Date(log.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="pagination-bar">
        <span>
          Showing {pageStart + 1}-{Math.min(pageStart + PAGE_SIZE, logs.length)} of{" "}
          {logs.length}
        </span>
        <div className="pagination-actions">
          <button
            className="secondary-button compact-button"
            disabled={normalizedPage === 1}
            onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
            type="button"
          >
            Previous
          </button>
          <strong>
            {normalizedPage} / {pageCount}
          </strong>
          <button
            className="secondary-button compact-button"
            disabled={normalizedPage === pageCount}
            onClick={() => setCurrentPage((page) => Math.min(pageCount, page + 1))}
            type="button"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
