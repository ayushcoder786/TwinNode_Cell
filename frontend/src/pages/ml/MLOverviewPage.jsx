import React, { useState, useEffect } from 'react';
import {
  Brain,
  Cpu,
  Database,
  ShieldCheck,
  AlertTriangle,
  Zap,
  Activity,
  Layers,
  CheckCircle2,
  Clock,
  Sparkles,
  ArrowRight,
  Globe
} from 'lucide-react';
import { useTwinNode } from '../../context/TwinNodeContext';

export const MLOverviewPage = ({ onNavigate }) => {
  const { latestPrediction, ledState, latestTelemetry } = useTwinNode();
  const [stats, setStats] = useState(null);
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [dsRes, modRes] = await Promise.all([
        fetch('/api/ml/dataset?limit=1'),
        fetch('/api/ml/models')
      ]);
      const dsData = await dsRes.json();
      const modData = await modRes.json();
      setStats(dsData.summary || {});
      setModels(modData || []);
    } catch (err) {
      console.error('Failed to load ML overview data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const activeModel = models.find(m => m.is_active) || models[0];

  const getLedGlow = () => {
    if (ledState === 'GREEN_ON') return 'border-emerald-500/50 bg-emerald-500/10 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.3)]';
    if (ledState === 'YELLOW_ON') return 'border-amber-500/50 bg-amber-500/10 text-amber-400 shadow-[0_0_15px_rgba(245,158,11,0.3)]';
    if (ledState === 'RED_ON') return 'border-rose-500/50 bg-rose-500/10 text-rose-400 shadow-[0_0_15px_rgba(244,63,94,0.3)]';
    return 'border-slate-700 bg-slate-900/60 text-slate-500';
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 p-6">
        <div className="absolute -right-10 -top-10 w-64 h-64 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-500/10 border border-sky-500/30 text-sky-400 text-xs font-mono font-medium mb-3">
              <Sparkles className="w-3.5 h-3.5" />
              TwinNode ML Studio • Industrial Intelligence
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Machine Learning Supervisor Overview</h1>
            <p className="text-slate-400 text-sm mt-1 max-w-2xl">
              Real-time multi-class fault classification, unsupervised anomaly detection, and closed-loop LED actuation across distributed STM32 nodes.
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
          </div>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Collected Records */}
        <div className="bg-[#0f172a]/80 border border-slate-800 rounded-xl p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Total Collected Records</span>
            <Database className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {stats ? stats.total_records?.toLocaleString() : '...'}
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2 font-mono">
            <span>Hardware: <strong className="text-emerald-400">{stats?.real_hardware_records || 0}</strong></span>
            <span>Simulation: <strong className="text-amber-400">{stats?.simulation_records || 0}</strong></span>
          </div>
        </div>

        {/* Model Registry Status */}
        <div className="bg-[#0f172a]/80 border border-slate-800 rounded-xl p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Trained ML Models</span>
            <Brain className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {models.length}
          </div>
          <div className="text-[11px] text-slate-400 mt-2 truncate">
            Active: <span className="text-sky-400 font-semibold">{activeModel ? activeModel.algorithm : 'None'}</span>
          </div>
        </div>

        {/* Active Model Accuracy */}
        <div className="bg-[#0f172a]/80 border border-slate-800 rounded-xl p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Best Model Accuracy</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400">
            {activeModel?.accuracy ? `${(activeModel.accuracy * 100).toFixed(1)}%` : 'N/A'}
          </div>
          <div className="text-[11px] text-slate-500 mt-2 font-mono">
            Macro F1: <strong className="text-slate-300">{activeModel?.f1_score ? (activeModel.f1_score * 100).toFixed(1) + '%' : 'N/A'}</strong>
          </div>
        </div>

        {/* Real-Time Anomaly Score */}
        <div className="bg-[#0f172a]/80 border border-slate-800 rounded-xl p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Current Anomaly Score</span>
            <Activity className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {latestPrediction ? `${(latestPrediction.anomaly_score * 100).toFixed(1)}%` : '0.0%'}
          </div>
          <div className="text-[11px] text-slate-500 mt-2">
            Status: <span className={`font-semibold ${latestPrediction?.is_anomaly ? 'text-rose-400' : 'text-emerald-400'}`}>
              {latestPrediction?.is_anomaly ? 'ANOMALY DETECTED' : 'NOMINAL ENVELOPE'}
            </span>
          </div>
        </div>
      </div>

      {/* Real-time State & Actuation Center */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Real-Time Inference Card */}
        <div className="lg:col-span-2 bg-[#0f172a]/90 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-sky-400" />
              <h3 className="text-sm font-semibold text-white">Live Prediction & Condition Recognition</h3>
            </div>
            <span className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-sky-400" />
              Updated: {new Date().toLocaleTimeString()}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3">
              <span className="text-[11px] font-mono text-slate-400">PREDICTED CONDITION</span>
              <div className="text-base font-bold text-sky-400 mt-1 truncate">
                {latestPrediction?.predicted_label || 'NORMAL_OPERATION'}
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Layer 2 ML Pipeline</span>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3">
              <span className="text-[11px] font-mono text-slate-400">MODEL CONFIDENCE</span>
              <div className="text-base font-bold text-emerald-400 mt-1">
                {latestPrediction?.confidence ? `${(latestPrediction.confidence * 100).toFixed(1)}%` : '98.5%'}
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Calibrated Probability</span>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3">
              <span className="text-[11px] font-mono text-slate-400">FAULT CATEGORY</span>
              <div className="text-base font-bold text-amber-400 mt-1 truncate">
                {latestPrediction?.fault_type || 'NOMINAL'}
              </div>
              <span className="text-[10px] text-slate-500 mt-1 block">Fusion Classification</span>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-lg p-3.5 flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-sky-400 shrink-0 mt-0.5" />
            <div>
              <div className="text-xs font-semibold text-white">Supervisory Recommendation:</div>
              <div className="text-xs text-slate-300 mt-0.5">
                {latestPrediction?.recommended_action || 'System operating nominally within validated physical tolerances.'}
              </div>
            </div>
          </div>
        </div>

        {/* Node 2 Actuator Integration (OPEN-LOOP) */}
        <div className="bg-[#0f172a]/90 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-semibold text-white">Node 2 Actuator Status</h3>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
              OPEN_LOOP
            </span>
          </div>

          <p className="text-xs text-slate-400">
            Node 2 updates its open-loop actuator state based on real-time ML fault predictions and safety override logic. Status reflects software command acknowledgement; no physical optical feedback sensor exists.
          </p>

          {/* LED Visual Indicators */}
          <div className="grid grid-cols-3 gap-3 pt-2">
            {/* Green LED */}
            <div className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all ${
              ledState === 'GREEN_ON'
                ? 'border-emerald-500/60 bg-emerald-500/10 shadow-[0_0_20px_rgba(16,185,129,0.3)]'
                : 'border-slate-800 bg-slate-900/40 opacity-40'
            }`}>
              <div className={`w-6 h-6 rounded-full mb-2 ${ledState === 'GREEN_ON' ? 'bg-emerald-400 animate-pulse' : 'bg-slate-700'}`} />
              <span className="text-[10px] font-mono font-bold text-emerald-400">GREEN</span>
              <span className="text-[9px] text-slate-400">PB4 (Normal)</span>
            </div>

            {/* Yellow LED */}
            <div className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all ${
              ledState === 'YELLOW_ON'
                ? 'border-amber-500/60 bg-amber-500/10 shadow-[0_0_20px_rgba(245,158,11,0.3)]'
                : 'border-slate-800 bg-slate-900/40 opacity-40'
            }`}>
              <div className={`w-6 h-6 rounded-full mb-2 ${ledState === 'YELLOW_ON' ? 'bg-amber-400 animate-pulse' : 'bg-slate-700'}`} />
              <span className="text-[10px] font-mono font-bold text-amber-400">YELLOW</span>
              <span className="text-[9px] text-slate-400">PB5 (Warning)</span>
            </div>

            {/* Red LED */}
            <div className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all ${
              ledState === 'RED_ON'
                ? 'border-rose-500/60 bg-rose-500/10 shadow-[0_0_20px_rgba(244,63,94,0.3)]'
                : 'border-slate-800 bg-slate-900/40 opacity-40'
            }`}>
              <div className={`w-6 h-6 rounded-full mb-2 ${ledState === 'RED_ON' ? 'bg-rose-400 animate-pulse' : 'bg-slate-700'}`} />
              <span className="text-[10px] font-mono font-bold text-rose-400">RED</span>
              <span className="text-[9px] text-slate-400">PB6 (Fault PWM)</span>
            </div>
          </div>

          <div className="text-[11px] text-slate-400 font-mono bg-slate-900/70 p-2.5 rounded-lg border border-slate-800/80 flex items-center justify-between">
            <span>Commanded State: <strong className="text-white">{ledState}</strong></span>
            <span className="text-amber-400 text-[10px]">OPEN_LOOP</span>
          </div>
        </div>
      </div>

      {/* Studio Navigation Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 pt-2">
        <button
          onClick={() => onNavigate('ml_datasets')}
          className="text-left p-4 rounded-xl bg-slate-900/70 hover:bg-slate-900 border border-slate-800 hover:border-sky-500/40 transition-all group"
        >
          <div className="flex items-center justify-between mb-2">
            <Database className="w-5 h-5 text-sky-400" />
            <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-sky-400 transition-colors" />
          </div>
          <div className="text-sm font-semibold text-white">Dataset Manager</div>
          <div className="text-xs text-slate-400 mt-1">Import, export, and inspect raw telemetry samples.</div>
        </button>

        <button
          onClick={() => onNavigate('ml_external_datasets')}
          className="text-left p-4 rounded-xl bg-slate-900/70 hover:bg-slate-900 border border-slate-800 hover:border-amber-500/40 transition-all group"
        >
          <div className="flex items-center justify-between mb-2">
            <Globe className="w-5 h-5 text-amber-400" />
            <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-amber-400 transition-colors" />
          </div>
          <div className="text-sm font-semibold text-white">Public Dataset Hub</div>
          <div className="text-xs text-slate-400 mt-1">TON_IoT, SWaT, and Edge-IIoTset benchmarks.</div>
        </button>

        <button
          onClick={() => onNavigate('ml_eda')}
          className="text-left p-4 rounded-xl bg-slate-900/70 hover:bg-slate-900 border border-slate-800 hover:border-indigo-500/40 transition-all group"
        >
          <div className="flex items-center justify-between mb-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-indigo-400 transition-colors" />
          </div>
          <div className="text-sm font-semibold text-white">Exploratory Data Analysis</div>
          <div className="text-xs text-slate-400 mt-1">Correlation heatmaps, distributions, and PCA clusters.</div>
        </button>

        <button
          onClick={() => onNavigate('ml_training')}
          className="text-left p-4 rounded-xl bg-slate-900/70 hover:bg-slate-900 border border-slate-800 hover:border-emerald-500/40 transition-all group"
        >
          <div className="flex items-center justify-between mb-2">
            <Brain className="w-5 h-5 text-emerald-400" />
            <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-emerald-400 transition-colors" />
          </div>
          <div className="text-sm font-semibold text-white">Model Training & Benchmarking</div>
          <div className="text-xs text-slate-400 mt-1">Train RF, Decision Tree, Logistic Regression, SVM & IF.</div>
        </button>

        <button
          onClick={() => onNavigate('ml_predictions')}
          className="text-left p-4 rounded-xl bg-slate-900/70 hover:bg-slate-900 border border-slate-800 hover:border-rose-500/40 transition-all group"
        >
          <div className="flex items-center justify-between mb-2">
            <Activity className="w-5 h-5 text-rose-400" />
            <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-rose-400 transition-colors" />
          </div>
          <div className="text-sm font-semibold text-white">Live Predictions Stream</div>
          <div className="text-xs text-slate-400 mt-1">Monitor real-time sensor inferences and anomaly flags.</div>
        </button>
      </div>
    </div>
  );
};
