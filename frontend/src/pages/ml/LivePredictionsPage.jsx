import React, { useState, useEffect } from 'react';
import {
  Activity,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Cpu,
  Layers,
  Sparkles,
  ShieldAlert,
  Server,
  Radio,
  Sliders,
  Filter,
  Play
} from 'lucide-react';
import { useTwinNode } from '../../context/TwinNodeContext';

export const LivePredictionsPage = () => {
  const { latestPrediction, ledState, latestTelemetry, mlPredictionHistory, hardwareStatus } = useTwinNode();
  const [history, setHistory] = useState([]);
  const [provenanceFilter, setProvenanceFilter] = useState('ALL');
  const [compatibilityData, setCompatibilityData] = useState(null);
  const [isInspecting, setIsInspecting] = useState(false);
  const [isTrainingHardware, setIsTrainingHardware] = useState(false);
  const [trainMessage, setTrainMessage] = useState(null);

  const fetchHistory = async () => {
    try {
      const endpoint = provenanceFilter === 'REAL_HARDWARE'
        ? '/api/hardware/predictions?limit=30'
        : '/api/ml/predictions?limit=30';
      const res = await fetch(endpoint);
      const data = await res.json();
      setHistory(data || []);
    } catch (err) {
      console.error('Failed to fetch prediction history:', err);
    }
  };

  const inspectCompatibility = async () => {
    setIsInspecting(true);
    try {
      const res = await fetch('/api/hardware/feature-compatibility');
      const data = await res.json();
      setCompatibilityData(data);
    } catch (err) {
      console.error('Failed to inspect compatibility:', err);
    } finally {
      setIsInspecting(false);
    }
  };

  const trainHardwareDedicatedModel = async () => {
    setIsTrainingHardware(true);
    setTrainMessage(null);
    try {
      const res = await fetch('/api/hardware/train-model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ n_samples: 5000 })
      });
      const data = await res.json();
      if (res.ok) {
        setTrainMessage(`Hardware Model Trained: ${data.model_id} (Accuracy: ${(data.metrics.accuracy * 100).toFixed(1)}%, F1: ${data.metrics.f1_macro})`);
      } else {
        setTrainMessage(`Training failed: ${data.detail || 'Unknown error'}`);
      }
    } catch (err) {
      setTrainMessage(`Error: ${err}`);
    } finally {
      setIsTrainingHardware(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    const interval = setInterval(fetchHistory, 3000);
    return () => clearInterval(interval);
  }, [provenanceFilter]);

  const getConditionColor = (cond) => {
    if (cond === 'NORMAL_OPERATION') return 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400';
    if (cond === 'SETPOINT_DEVIATION' || cond === 'COMMUNICATION_FAULT' || cond === 'WARNING') return 'bg-amber-500/15 border-amber-500/40 text-amber-400';
    return 'bg-rose-500/15 border-rose-500/40 text-rose-400';
  };

  const filteredHistory = history.filter(h => {
    if (provenanceFilter === 'ALL') return true;
    return h.data_source === provenanceFilter;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-rose-400" />
            <h1 className="text-xl font-bold text-white tracking-tight">Real-Time ML Inference & Closed-Loop Actuation</h1>
          </div>
          <p className="text-slate-400 text-xs mt-1">
            Real-time STM32 sensor telemetry inference with Layer 1 Safety arbitration and closed-loop LED command dispatch.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className={`px-3 py-1.5 rounded-lg border text-xs font-mono font-semibold flex items-center gap-2 ${
            latestTelemetry.data_source === 'REAL_HARDWARE'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
          }`}>
            <span className={`w-2 h-2 rounded-full ${latestTelemetry.data_source === 'REAL_HARDWARE' ? 'bg-emerald-400' : 'bg-amber-400'} animate-pulse`} />
            DATA SOURCE: {latestTelemetry.data_source || 'SIMULATION'}
          </span>

          <span className={`px-3 py-1.5 rounded-lg border text-xs font-mono font-semibold flex items-center gap-1.5 ${
            hardwareStatus?.is_connected
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-slate-800/60 border-slate-700 text-slate-400'
          }`}>
            <Radio className="w-3.5 h-3.5" />
            {hardwareStatus?.is_connected ? `COM3 ONLINE (${hardwareStatus.baudrate})` : 'HARDWARE OFFLINE'}
          </span>
        </div>
      </div>

      {/* Main Cockpit Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Prediction Display */}
        <div className="lg:col-span-2 bg-[#0f172a] border border-slate-800 rounded-2xl p-6 space-y-5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-sky-400" />
              <h2 className="text-sm font-semibold text-white">Active Operational Condition & ML Inference</h2>
            </div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
              <span>Model: <strong className="text-white">{latestPrediction?.model_id || 'Active Pipeline'}</strong></span>
              <span>v{latestPrediction?.model_version || '1.0.0'}</span>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-5 rounded-xl bg-slate-900/80 border border-slate-800">
            <div>
              <span className="text-[11px] font-mono text-slate-400 block mb-1">OPERATIONAL CONDITION</span>
              <div className={`text-xl sm:text-2xl font-bold tracking-tight px-3 py-1.5 rounded-lg border inline-block ${getConditionColor(latestPrediction?.predicted_label)}`}>
                {latestPrediction?.predicted_label || 'NORMAL_OPERATION'}
              </div>
            </div>

            <div className="flex items-center gap-6 text-right">
              <div>
                <span className="text-[11px] font-mono text-slate-400 block">CONFIDENCE</span>
                <span className="text-2xl font-bold font-mono text-emerald-400">
                  {latestPrediction?.confidence !== undefined ? `${(latestPrediction.confidence * 100).toFixed(1)}%` : '98.5%'}
                </span>
              </div>
              <div>
                <span className="text-[11px] font-mono text-slate-400 block">ANOMALY SCORE</span>
                <span className="text-2xl font-bold font-mono text-rose-400">
                  {latestPrediction?.anomaly_score !== undefined ? `${(latestPrediction.anomaly_score * 100).toFixed(1)}%` : '1.5%'}
                </span>
              </div>
            </div>
          </div>

          {/* Corrective Action Banner */}
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-sky-400 shrink-0 mt-0.5" />
            <div>
              <div className="text-xs font-semibold text-white">Supervisory Guidance & Suggested LED:</div>
              <div className="text-xs text-slate-300 mt-1">
                {latestPrediction?.recommended_action || 'System operating nominally within physical sensor envelope.'}
              </div>
              <div className="mt-2 text-xs font-mono flex items-center gap-2">
                <span className="text-slate-400">DISPATCHED LED COMMAND:</span>
                <strong className="text-emerald-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                  {latestPrediction?.suggested_led || 'LED:GREEN'}
                </strong>
              </div>
            </div>
          </div>

          {/* Telemetry Input Features Snapshot */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
            <div className="p-3 bg-slate-900/90 border border-slate-800 rounded-lg">
              <span className="text-[10px] font-mono text-slate-500">TEMPERATURE</span>
              <div className="text-base font-bold text-rose-400 mt-0.5">
                {latestTelemetry.actual_temp !== undefined ? `${latestTelemetry.actual_temp.toFixed(1)} °C` : '--'}
              </div>
            </div>
            <div className="p-3 bg-slate-900/90 border border-slate-800 rounded-lg">
              <span className="text-[10px] font-mono text-slate-500">HUMIDITY (DHT11)</span>
              <div className="text-base font-bold text-cyan-400 mt-0.5">
                {latestTelemetry.humidity !== undefined ? `${latestTelemetry.humidity.toFixed(1)} %` : '58.0 %'}
              </div>
            </div>
            <div className="p-3 bg-slate-900/90 border border-slate-800 rounded-lg">
              <span className="text-[10px] font-mono text-slate-500">DISTANCE (HC-SR04)</span>
              <div className="text-base font-bold text-amber-400 mt-0.5">
                {latestTelemetry.actual_dist !== undefined ? `${latestTelemetry.actual_dist.toFixed(1)} cm` : '--'}
              </div>
            </div>
            <div className="p-3 bg-slate-900/90 border border-slate-800 rounded-lg">
              <span className="text-[10px] font-mono text-slate-500">RX JITTER</span>
              <div className="text-base font-bold text-sky-400 mt-0.5">
                {latestTelemetry.comm_latency_ms || 10} ms
              </div>
            </div>
          </div>

          {/* Raw Frame string */}
          {latestTelemetry.raw_message && (
            <div className="text-xs font-mono text-slate-400 bg-slate-950 p-2.5 rounded border border-slate-800 flex items-center justify-between">
              <span>RAW SERIAL MESSAGE:</span>
              <span className="text-emerald-400 font-bold">{latestTelemetry.raw_message}</span>
            </div>
          )}
        </div>

        {/* Node 2 Actuator LED Status */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-2xl p-6 space-y-5">
          <div className="border-b border-slate-800 pb-3 flex items-start justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Cpu className="w-4 h-4 text-emerald-400" />
                Node 2 Actuator LED State
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">Closed-loop serial dispatch reflection</p>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/30">
              SOFTWARE ACK
            </span>
          </div>

          <div className="space-y-3">
            {/* Green LED */}
            <div className={`p-4 rounded-xl border flex items-center justify-between transition-all ${
              ledState === 'GREEN_ON'
                ? 'bg-emerald-500/10 border-emerald-500/50 shadow-[0_0_20px_rgba(16,185,129,0.25)]'
                : 'bg-slate-900/40 border-slate-800/80 opacity-40'
            }`}>
              <div className="flex items-center gap-3">
                <div className={`w-5 h-5 rounded-full ${ledState === 'GREEN_ON' ? 'bg-emerald-400 animate-pulse' : 'bg-slate-700'}`} />
                <div>
                  <div className="text-xs font-bold text-white">GREEN LED (PB4)</div>
                  <div className="text-[10px] text-slate-400">Normal Operation</div>
                </div>
              </div>
              <span className="text-xs font-mono font-bold text-emerald-400">{ledState === 'GREEN_ON' ? 'ACTIVE' : 'OFF'}</span>
            </div>

            {/* Yellow LED */}
            <div className={`p-4 rounded-xl border flex items-center justify-between transition-all ${
              ledState === 'YELLOW_ON'
                ? 'bg-amber-500/10 border-amber-500/50 shadow-[0_0_20px_rgba(245,158,11,0.25)]'
                : 'bg-slate-900/40 border-slate-800/80 opacity-40'
            }`}>
              <div className="flex items-center gap-3">
                <div className={`w-5 h-5 rounded-full ${ledState === 'YELLOW_ON' ? 'bg-amber-400 animate-pulse' : 'bg-slate-700'}`} />
                <div>
                  <div className="text-xs font-bold text-white">YELLOW LED (PB5)</div>
                  <div className="text-[10px] text-slate-400">Warning / Drift</div>
                </div>
              </div>
              <span className="text-xs font-mono font-bold text-amber-400">{ledState === 'YELLOW_ON' ? 'ACTIVE' : 'OFF'}</span>
            </div>

            {/* Red LED */}
            <div className={`p-4 rounded-xl border flex items-center justify-between transition-all ${
              ledState === 'RED_ON'
                ? 'bg-rose-500/10 border-rose-500/50 shadow-[0_0_20px_rgba(244,63,94,0.25)]'
                : 'bg-slate-900/40 border-slate-800/80 opacity-40'
            }`}>
              <div className="flex items-center gap-3">
                <div className={`w-5 h-5 rounded-full ${ledState === 'RED_ON' ? 'bg-rose-400 animate-pulse' : 'bg-slate-700'}`} />
                <div>
                  <div className="text-xs font-bold text-white">RED LED (PB6 PWM)</div>
                  <div className="text-[10px] text-slate-400">Fault / Out of Range</div>
                </div>
              </div>
              <span className="text-xs font-mono font-bold text-rose-400">{ledState === 'RED_ON' ? 'ACTIVE' : 'OFF'}</span>
            </div>
          </div>

          <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 text-[11px] text-slate-400 space-y-1">
            <div><strong>Feedback Verification:</strong> Status reflects commanded GPIO state. STM32 hardware lacks physical optical photodiode feedback.</div>
            <div><strong>Safety Priority:</strong> Emergency Stop unconditionally overrides ML predictions, setting <code className="text-white">LED:OFF</code>.</div>
          </div>
        </div>
      </div>

      {/* Feature Compatibility & Hardware Training Tools */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Sliders className="w-4 h-4 text-sky-400" />
              Physical STM32 Model Compatibility & Dedicated Hardware Training
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Inspect model feature requirements against single-STM32 telemetry to eliminate synthetic imputation.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={inspectCompatibility}
              disabled={isInspecting}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-mono border border-slate-700 transition"
            >
              {isInspecting ? 'Inspecting...' : 'Inspect Feature Schema'}
            </button>
            <button
              onClick={trainHardwareDedicatedModel}
              disabled={isTrainingHardware}
              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-bold font-mono transition flex items-center gap-1.5"
            >
              <Play className="w-3.5 h-3.5" />
              {isTrainingHardware ? 'Training...' : 'Train Dedicated Hardware Model'}
            </button>
          </div>
        </div>

        {trainMessage && (
          <div className="p-3 rounded bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-400 font-mono">
            {trainMessage}
          </div>
        )}

        {compatibilityData && (
          <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">
                ACTIVE MODEL: <strong className="text-white">{compatibilityData.active_model_name}</strong> ({compatibilityData.active_model_id})
              </span>
              <span className={`px-2 py-0.5 rounded font-bold ${
                compatibilityData.analysis.is_directly_compatible ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
              }`}>
                COMPATIBILITY: {compatibilityData.analysis.compatibility_score_pct}%
              </span>
            </div>

            <p className="text-xs text-slate-300">
              {compatibilityData.analysis.recommendation}
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 pt-1">
              {compatibilityData.analysis.breakdown.map((item, idx) => (
                <div key={idx} className="p-2 rounded bg-slate-900 border border-slate-800 text-[11px] font-mono">
                  <div className="font-bold text-white">{item.feature}</div>
                  <div className={`text-[10px] mt-0.5 ${
                    item.category.includes('DIRECTLY') ? 'text-emerald-400' :
                    item.category.includes('SETPOINT') ? 'text-sky-400' : 'text-amber-400'
                  }`}>
                    {item.category}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">{item.description}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Prediction History Table with Strict Provenance Filtering */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-white">Inference History & Provenance Log</h3>
            <p className="text-xs text-slate-400 mt-0.5">Showing {filteredHistory.length} records</p>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" /> PROVENANCE:
            </span>
            <div className="flex rounded-lg overflow-hidden border border-slate-700 text-xs font-mono">
              <button
                onClick={() => setProvenanceFilter('ALL')}
                className={`px-2.5 py-1 ${provenanceFilter === 'ALL' ? 'bg-sky-600 text-white' : 'bg-slate-800 text-slate-400'}`}
              >
                ALL
              </button>
              <button
                onClick={() => setProvenanceFilter('REAL_HARDWARE')}
                className={`px-2.5 py-1 ${provenanceFilter === 'REAL_HARDWARE' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-400'}`}
              >
                REAL_HARDWARE
              </button>
              <button
                onClick={() => setProvenanceFilter('SIMULATION')}
                className={`px-2.5 py-1 ${provenanceFilter === 'SIMULATION' ? 'bg-amber-600 text-white' : 'bg-slate-800 text-slate-400'}`}
              >
                SIMULATION
              </button>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto max-h-[350px]">
          <table className="w-full text-left text-xs font-mono border-collapse">
            <thead className="bg-slate-900/90 text-slate-400 sticky top-0 border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">TIMESTAMP</th>
                <th className="py-2.5 px-3">PREDICTED LABEL</th>
                <th className="py-2.5 px-3">CONFIDENCE</th>
                <th className="py-2.5 px-3">ANOMALY SCORE</th>
                <th className="py-2.5 px-3">ANOMALY?</th>
                <th className="py-2.5 px-3">DATA PROVENANCE</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {filteredHistory.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-6 text-center text-slate-500 font-sans">
                    No predictions found matching provenance filter '{provenanceFilter}'.
                  </td>
                </tr>
              ) : (
                filteredHistory.map((h) => (
                  <tr key={h.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-2 px-3 text-slate-400 text-[11px]">
                      {h.timestamp ? h.timestamp.slice(11, 19) : '--'}
                    </td>
                    <td className="py-2 px-3 font-semibold text-white">
                      {h.predicted_label}
                    </td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">
                      {h.confidence !== null && h.confidence !== undefined ? `${(h.confidence * 100).toFixed(1)}%` : '--'}
                    </td>
                    <td className="py-2 px-3 text-rose-400">
                      {h.anomaly_score !== null && h.anomaly_score !== undefined ? `${(h.anomaly_score * 100).toFixed(1)}%` : '--'}
                    </td>
                    <td className="py-2 px-3">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        h.is_anomaly ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'
                      }`}>
                        {h.is_anomaly ? 'YES' : 'NO'}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        h.data_source === 'REAL_HARDWARE' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
                      }`}>
                        {h.data_source}
                      </span>
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
