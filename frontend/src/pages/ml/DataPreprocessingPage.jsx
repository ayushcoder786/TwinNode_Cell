import React, { useState, useEffect } from 'react';
import {
  Sliders,
  CheckCircle,
  AlertTriangle,
  Layers,
  ArrowRight,
  RefreshCw,
  Sparkles,
  TrendingUp,
  Cpu,
  BarChart2
} from 'lucide-react';

export const DataPreprocessingPage = () => {
  const [edaData, setEdaData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedScaler, setSelectedScaler] = useState('StandardScaler');
  const [rollingWindow, setRollingWindow] = useState(5);
  const [selectedFeatures, setSelectedFeatures] = useState([
    'rolling_temp_mean',
    'rolling_temp_std',
    'temp_rate_of_change',
    'rolling_dist_mean',
    'dist_rate_of_change',
    'target_temp_dev',
    'target_dist_dev',
    'latency_mean',
    'packet_loss_rate',
    'sensor_stability_score',
    'response_delay',
    'led_mismatch'
  ]);

  const fetchEDA = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/ml/eda/summary');
      const data = await res.json();
      setEdaData(data);
    } catch (err) {
      console.error('Failed to load preprocessing EDA:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEDA();
  }, []);

  const toggleFeature = (name) => {
    setSelectedFeatures(prev =>
      prev.includes(name) ? prev.filter(f => f !== name) : [...prev, name]
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-indigo-400" />
            <h1 className="text-xl font-bold text-white tracking-tight">Data Preprocessing & Pipeline Architecture</h1>
          </div>
          <p className="text-slate-400 text-xs mt-1">
            Data cleaning, duplicate elimination, outlier detection, and scikit-learn feature pipeline configuration.
          </p>
        </div>

        <button
          onClick={fetchEDA}
          className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-1.5 transition-all"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-400' : ''}`} />
          Re-Analyze
        </button>
      </div>

      {/* Cleaning & Audit Metrics */}
      {edaData && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
            <span className="text-xs font-mono text-slate-400">DUPLICATE PACKETS</span>
            <div className="text-2xl font-bold font-mono text-white mt-1">
              {edaData.duplicate_records || 0}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Filtered automatically during chronological ingestion.</p>
          </div>

          <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
            <span className="text-xs font-mono text-slate-400">OUTLIERS IDENTIFIED (IQR 1.5)</span>
            <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
              {edaData.outliers?.total_outliers || 0}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Detected across physical thermal and acoustic readings.</p>
          </div>

          <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
            <span className="text-xs font-mono text-slate-400">CHRONOLOGICAL SPLIT STRATEGY</span>
            <div className="text-base font-bold font-mono text-emerald-400 mt-2">
              SESSION-AWARE (80/20)
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Prevents time-series autocorrelation leakage.</p>
          </div>
        </div>
      )}

      {/* Pipeline Config & Feature Engineering */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Feature Engineering Selection */}
        <div className="lg:col-span-2 bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-sky-400" />
              <h3 className="text-sm font-semibold text-white">Derived Physical & Communication Features</h3>
            </div>
            <span className="text-xs font-mono text-sky-400 font-semibold">
              {selectedFeatures.length} Selected
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {[
              { id: 'rolling_temp_mean', label: 'Rolling Temp Mean', desc: 'Moving thermal average' },
              { id: 'rolling_temp_std', label: 'Rolling Temp Std Dev', desc: 'Thermal mass stability / jitter' },
              { id: 'temp_rate_of_change', label: 'Temp Rate of Change (dT/dt)', desc: 'Dynamic heating / cooling velocity' },
              { id: 'rolling_dist_mean', label: 'Rolling Dist Mean', desc: 'Moving distance average' },
              { id: 'dist_rate_of_change', label: 'Dist Rate of Change (dD/dt)', desc: 'Kinematic tracking velocity' },
              { id: 'target_temp_dev', label: 'Target Temp Deviation', desc: 'Absolute offset |T_act - T_set|' },
              { id: 'target_dist_dev', label: 'Target Dist Deviation', desc: 'Absolute offset |D_act - D_set|' },
              { id: 'latency_mean', label: 'UART Latency Mean', desc: 'Inter-node bus timing latency' },
              { id: 'packet_loss_rate', label: 'Packet Loss Rate', desc: 'Serial packet drop percentage' },
              { id: 'sensor_stability_score', label: 'Sensor Stability Score', desc: 'Composite variance rating (0-100%)' },
              { id: 'response_delay', label: 'Response Delay (ms)', desc: 'Node 2 processing cycle latency' },
              { id: 'led_mismatch', label: 'LED Command Mismatch (Open-Loop)', desc: 'Actuator command vs UART ack discrepancy' }
            ].map(f => {
              const isChecked = selectedFeatures.includes(f.id);
              return (
                <div
                  key={f.id}
                  onClick={() => toggleFeature(f.id)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    isChecked
                      ? 'bg-sky-500/10 border-sky-500/40 text-white'
                      : 'bg-slate-900/50 border-slate-800 text-slate-400 opacity-60 hover:opacity-100'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-semibold">{f.label}</span>
                    <span className={`w-3.5 h-3.5 rounded flex items-center justify-center border text-[9px] ${
                      isChecked ? 'bg-sky-500 border-sky-400 text-slate-950 font-bold' : 'border-slate-700'
                    }`}>
                      {isChecked ? '✓' : ''}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">{f.desc}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Transformer & Scaler Configuration */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-5">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="text-sm font-semibold text-white">Pipeline Preprocessing Parameters</h3>
            <p className="text-xs text-slate-400 mt-0.5">Parameters applied exclusively to training set.</p>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-300 block mb-2">Numerical Feature Scaler</label>
            <div className="space-y-2">
              {[
                { id: 'StandardScaler', name: 'StandardScaler (Z-Score)', desc: 'Zero mean, unit variance (Recommended for SVM & Logistic)' },
                { id: 'RobustScaler', name: 'RobustScaler (IQR)', desc: 'Robust against extreme outliers & sensor spikes' },
                { id: 'MinMaxScaler', name: 'MinMaxScaler (0 to 1)', desc: 'Bounded range preservation' }
              ].map(s => (
                <div
                  key={s.id}
                  onClick={() => setSelectedScaler(s.id)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    selectedScaler === s.id
                      ? 'bg-indigo-500/15 border-indigo-500/40 text-white'
                      : 'bg-slate-900/50 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <div className="text-xs font-semibold">{s.name}</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">{s.desc}</div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-300 block mb-1">
              Rolling Window Size: <span className="text-sky-400 font-mono font-bold">{rollingWindow} Samples</span>
            </label>
            <input
              type="range"
              min="3"
              max="15"
              value={rollingWindow}
              onChange={(e) => setRollingWindow(Number(e.target.value))}
              className="w-full accent-sky-500"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono mt-1">
              <span>3 (High reactivity)</span>
              <span>15 (Maximum smoothing)</span>
            </div>
          </div>

          <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 text-[11px] text-slate-400 space-y-1">
            <div className="font-semibold text-slate-200">Data Leakage Prevention:</div>
            <div>• Fit-transform executed strictly inside Scikit-learn Pipeline on chronologically partitioned training batches.</div>
          </div>
        </div>
      </div>
    </div>
  );
};
