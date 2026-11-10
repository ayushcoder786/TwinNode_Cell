import React from 'react';
import {
  LayoutDashboard,
  Cpu,
  Sliders,
  Activity,
  AlertTriangle,
  BarChart3,
  FileText,
  Brain,
  Database,
  Layers,
  Sparkles,
  ShieldCheck,
  Zap,
  TrendingUp,
  Globe
} from 'lucide-react';
import { useTwinNode } from '../context/TwinNodeContext';

export const Sidebar = ({ activeTab, setActiveTab }) => {
  const { activeFaults, latestTelemetry, ledState } = useTwinNode();

  const scadaItems = [
    { id: 'overview', label: 'Overview Dashboard', icon: LayoutDashboard },
    { id: 'nodes', label: 'Node Management', icon: Cpu },
    { id: 'testbench', label: 'Test Bench', icon: Sliders },
    { id: 'sensors', label: 'Sensor Monitoring', icon: Activity },
    { id: 'faults', label: 'Fault Detection', icon: AlertTriangle, badge: activeFaults.length },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'reports', label: 'Test Reports', icon: FileText }
  ];

  const mlItems = [
    { id: 'ml_overview', label: 'ML Studio Overview', icon: Brain },
    { id: 'ml_datasets', label: 'Dataset Manager', icon: Database },
    { id: 'ml_external_datasets', label: 'Public Dataset Hub', icon: Globe },
    { id: 'ml_preprocessing', label: 'Data Preprocessing', icon: Sliders },
    { id: 'ml_eda', label: 'Exploratory Analysis (EDA)', icon: TrendingUp },
    { id: 'ml_training', label: 'Model Training & Benchmark', icon: Sparkles },
    { id: 'ml_evaluation', label: 'Model Evaluation', icon: ShieldCheck },
    { id: 'ml_predictions', label: 'Live ML Predictions', icon: Zap },
    { id: 'ml_management', label: 'Model Management', icon: Layers }
  ];

  return (
    <aside className="w-64 bg-[#0c1220] border-r border-slate-800 flex flex-col justify-between p-4 select-none shrink-0 overflow-y-auto">
      <div className="space-y-6">
        {/* ML Studio Navigation */}
        <nav className="space-y-1">
          <div className="text-[10px] font-bold tracking-wider text-sky-400 uppercase px-3 mb-2 font-mono flex items-center justify-between">
            <span>Machine Learning Studio</span>
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-ping" />
          </div>
          {mlItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-sky-500/15 text-sky-300 border border-sky-500/30 font-semibold shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                }`}
              >
                <div className="flex items-center space-x-2.5 truncate">
                  <Icon className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-sky-400' : 'text-slate-400'}`} />
                  <span className="truncate">{item.label}</span>
                </div>
              </button>
            );
          })}
        </nav>

        {/* SCADA Instrument Navigation */}
        <nav className="space-y-1">
          <div className="text-[10px] font-bold tracking-wider text-slate-500 uppercase px-3 mb-2 font-mono">
            SCADA & Telemetry
          </div>
          {scadaItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-slate-800 text-white border border-slate-700 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
                }`}
              >
                <div className="flex items-center space-x-2.5 truncate">
                  <Icon className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span className="truncate">{item.label}</span>
                </div>
                {item.badge > 0 && (
                  <span className="bg-rose-500 text-white font-mono text-[9px] px-1.5 py-0.5 rounded-full font-bold">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Diagnostics Quick Footer with Node 2 Actuator LED feedback */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3 space-y-2 mt-4">
        <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
          <span>BUS LATENCY</span>
          <span className="text-white font-semibold">{latestTelemetry.comm_latency_ms || 0} ms</span>
        </div>
        <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
          <span>ACTUATOR (OPEN_LOOP)</span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
            ledState === 'GREEN_ON'
              ? 'bg-emerald-500/20 text-emerald-400'
              : ledState === 'YELLOW_ON'
              ? 'bg-amber-500/20 text-amber-400'
              : ledState === 'RED_ON'
              ? 'bg-rose-500/20 text-rose-400'
              : 'bg-slate-800 text-slate-500'
          }`}>
            {ledState || 'GREEN_ON'}
          </span>
        </div>
        <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
          <span>PROVENANCE</span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
            latestTelemetry.data_source === 'REAL_HARDWARE' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
          }`}>
            {latestTelemetry.data_source || 'SIMULATION'}
          </span>
        </div>
      </div>
    </aside>
  );
};
