import React, { useState, useEffect } from 'react';
import { useTwinNode } from '../context/TwinNodeContext';
import {
  BarChart3,
  TrendingUp,
  Clock,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Sliders,
  Filter
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';

export const AnalyticsPage = () => {
  const { activeTestId, telemetryHistory } = useTwinNode();
  const [historyList, setHistoryList] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(activeTestId);
  const [sessionData, setSessionData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/test/history');
      const data = await res.json();
      setHistoryList(data);
      if (data.length > 0 && !selectedSessionId) {
        setSelectedSessionId(data[0].test_id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchTelemetry = async (testId) => {
    if (!testId) return;
    setIsLoading(true);
    try {
      const res = await fetch(`/api/test/${testId}/telemetry?limit=150`);
      const data = await res.json();
      setSessionData(data.map(d => ({
        ...d,
        time: d.timestamp ? new Date(d.timestamp).toLocaleTimeString([], { hour12: false }) : '',
        temp_error: Math.abs(d.actual_temp - d.target_temp),
        dist_error: Math.abs(d.actual_dist - d.target_dist),
        motor_error: Math.abs(d.actual_motor_speed - d.target_motor_speed)
      })));
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  useEffect(() => {
    if (selectedSessionId) {
      fetchTelemetry(selectedSessionId);
    }
  }, [selectedSessionId]);

  // Use live data if sessionData is empty
  const activeDataset = sessionData.length > 0 ? sessionData : telemetryHistory.map(d => ({
    ...d,
    temp_error: Math.abs(d.actual_temp - d.target_temp),
    dist_error: Math.abs(d.actual_dist - d.target_dist),
    motor_error: Math.abs(d.actual_motor - d.target_motor)
  }));

  // Metric aggregates
  const totalSamples = activeDataset.length;
  const avgLatency = totalSamples > 0
    ? (activeDataset.reduce((acc, d) => acc + (d.comm_latency_ms || d.latency || 0), 0) / totalSamples).toFixed(1)
    : '0.0';
  const avgTempError = totalSamples > 0
    ? (activeDataset.reduce((acc, d) => acc + (d.temp_error || 0), 0) / totalSamples).toFixed(2)
    : '0.00';
  const avgDistError = totalSamples > 0
    ? (activeDataset.reduce((acc, d) => acc + (d.dist_error || 0), 0) / totalSamples).toFixed(2)
    : '0.00';

  return (
    <div className="space-y-6">
      {/* Session Filter Bar */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <BarChart3 className="w-5 h-5 text-sky-400" />
            <h2 className="text-base font-bold text-white font-mono">Performance & Setpoint Tracking Analytics</h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Statistical deviation analysis, response rise time distribution, and plant reliability metrics.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <label className="text-xs font-mono text-slate-400">SELECT SESSION:</label>
          <select
            value={selectedSessionId || ''}
            onChange={(e) => setSelectedSessionId(Number(e.target.value))}
            className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
          >
            {historyList.length === 0 ? (
              <option value={activeTestId}>Active Live Session (#{activeTestId})</option>
            ) : (
              historyList.map(h => (
                <option key={h.test_id} value={h.test_id}>
                  #{h.test_id} - {h.name} ({h.status})
                </option>
              ))
            )}
          </select>
          <button
            onClick={() => fetchTelemetry(selectedSessionId)}
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Aggregate KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 font-mono text-xs">
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
          <span className="text-slate-500 block text-[10px]">ANALYZED SAMPLES</span>
          <span className="text-2xl font-bold text-white">{totalSamples}</span>
          <span className="text-[11px] text-slate-400 block mt-1">100ms Epoch Intervals</span>
        </div>
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
          <span className="text-slate-500 block text-[10px]">MEAN TEMPERATURE ERROR</span>
          <span className="text-2xl font-bold text-rose-400">{avgTempError} °C</span>
          <span className="text-[11px] text-emerald-400 block mt-1">&lt; 3.0°C Tolerance Band</span>
        </div>
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
          <span className="text-slate-500 block text-[10px]">MEAN DISTANCE ERROR</span>
          <span className="text-2xl font-bold text-cyan-400">{avgDistError} cm</span>
          <span className="text-[11px] text-emerald-400 block mt-1">&lt; 4.0cm Tolerance Band</span>
        </div>
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
          <span className="text-slate-500 block text-[10px]">AVG BUS LATENCY</span>
          <span className="text-2xl font-bold text-amber-400">{avgLatency} ms</span>
          <span className="text-[11px] text-slate-400 block mt-1">UART Ring Buffer</span>
        </div>
      </div>

      {/* Analytics Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tracking Error (Variance) Chart */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Absolute Setpoint Tracking Error</h3>
              <p className="text-xs text-slate-400">Deviation from target |Actual - Target| over time</p>
            </div>
            <span className="text-xs font-mono text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
              RESIDUAL ERROR
            </span>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={activeDataset} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                <Line type="monotone" dataKey="temp_error" stroke="#f43f5e" name="Temp Error (°C)" strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="dist_error" stroke="#0ea5e9" name="Dist Error (cm)" strokeWidth={2} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Bus Round-Trip Latency Chart */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Inter-Node Packet Round-Trip Delay</h3>
              <p className="text-xs text-slate-400">Time elapsed between setpoint command and telemetry receipt (ms)</p>
            </div>
            <span className="text-xs font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
              COMM LATENCY
            </span>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={activeDataset} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                <Line type="monotone" dataKey="comm_latency_ms" stroke="#f59e0b" name="Latency (ms)" strokeWidth={2} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
