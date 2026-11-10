import React, { useState, useEffect } from 'react';
import { useTwinNode } from '../context/TwinNodeContext';
import {
  FileText,
  Download,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  FileSpreadsheet,
  Clock,
  Printer
} from 'lucide-react';

export const TestReportsPage = () => {
  const { activeTestId } = useTwinNode();
  const [sessions, setSessions] = useState([]);
  const [selectedReportId, setSelectedReportId] = useState(activeTestId);

  const fetchSessions = async () => {
    try {
      const res = await fetch('/api/test/history');
      const data = await res.json();
      setSessions(data);
      if (data.length > 0 && !selectedReportId) {
        setSelectedReportId(data[0].test_id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleDownloadCsv = (testId) => {
    window.open(`/api/reports/export/csv/${testId}`, '_blank');
  };

  const handleDownloadPdf = (testId) => {
    window.open(`/api/reports/export/pdf/${testId}`, '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <FileText className="w-5 h-5 text-sky-400" />
            <h2 className="text-base font-bold text-white font-mono">Formal Industrial Validation Reports</h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Audit-grade execution certificates, setpoint vs actual telemetry logs, and fault event records.
          </p>
        </div>

        <button
          onClick={fetchSessions}
          className="flex items-center space-x-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-mono border border-slate-700 transition"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh Sessions</span>
        </button>
      </div>

      {/* Historical Sessions Table */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
        <h3 className="text-sm font-semibold text-white">Recorded Test Sessions Archive</h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Test ID</th>
                <th className="py-2.5 px-3">Campaign Name</th>
                <th className="py-2.5 px-3">Profile</th>
                <th className="py-2.5 px-3">Start Timestamp</th>
                <th className="py-2.5 px-3">Samples</th>
                <th className="py-2.5 px-3">Faults</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3 text-right">Export</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {sessions.length === 0 ? (
                <tr>
                  <td colSpan="8" className="py-6 text-center text-slate-500 font-sans">
                    No historic sessions logged yet. Run a test bench session to generate reports.
                  </td>
                </tr>
              ) : (
                sessions.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-900/40">
                    <td className="py-2.5 px-3 text-white font-bold">#{s.test_id}</td>
                    <td className="py-2.5 px-3 text-sky-400 font-semibold">{s.name}</td>
                    <td className="py-2.5 px-3 text-slate-300">{s.profile}</td>
                    <td className="py-2.5 px-3 text-slate-400">
                      {s.start_time ? new Date(s.start_time).toLocaleString([], { hour12: false }) : '-'}
                    </td>
                    <td className="py-2.5 px-3 text-white">{s.total_samples || 0}</td>
                    <td className="py-2.5 px-3">
                      <span className={`px-1.5 py-0.5 rounded font-bold ${
                        (s.total_faults || 0) > 0 ? 'text-rose-400 bg-rose-500/10' : 'text-emerald-400 bg-emerald-500/10'
                      }`}>
                        {s.total_faults || 0}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-800 text-slate-300">
                        {s.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right space-x-2">
                      <button
                        onClick={() => handleDownloadCsv(s.test_id)}
                        title="Download CSV raw data"
                        className="inline-flex items-center space-x-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 rounded text-[11px] font-sans transition"
                      >
                        <FileSpreadsheet className="w-3.5 h-3.5" />
                        <span>CSV</span>
                      </button>
                      <button
                        onClick={() => handleDownloadPdf(s.test_id)}
                        title="Download official PDF report"
                        className="inline-flex items-center space-x-1 px-2.5 py-1 bg-sky-600 hover:bg-sky-500 text-white rounded text-[11px] font-sans transition"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>PDF Report</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
