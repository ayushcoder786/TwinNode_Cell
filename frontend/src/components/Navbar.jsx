import React from 'react';
import { useTwinNode } from '../context/TwinNodeContext';
import { ShieldAlert, Radio, AlertOctagon, Cpu, Power, RefreshCw } from 'lucide-react';

export const Navbar = () => {
  const {
    isConnected,
    simulationMode,
    setSimulationMode,
    testStatus,
    activeTestId,
    activeFaults,
    emergencyStop,
    resetTest
  } = useTwinNode();

  const criticalFaults = activeFaults.filter(f => f.severity === 'CRITICAL');

  return (
    <header className="h-16 bg-[#0f172a] border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-50">
      {/* Brand & Project Identity */}
      <div className="flex items-center space-x-3">
        <div className="w-9 h-9 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
          <Cpu className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold text-white tracking-wide text-base">TWINNODE CELL</span>
            <span className="text-[10px] bg-slate-800 text-sky-400 font-mono px-2 py-0.5 rounded border border-slate-700">
              v1.0-IIoT
            </span>
          </div>
          <p className="text-xs text-slate-400">Distributed Sensing & Actuation Supervisor</p>
        </div>
      </div>

      {/* Center Operational Status */}
      <div className="flex items-center space-x-4">
        {/* Active Test Pill */}
        <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg text-xs font-mono">
          <span className="text-slate-400">SESSION:</span>
          <span className="text-white font-semibold">#{activeTestId}</span>
          <span className="text-slate-600">|</span>
          <span className={`px-2 py-0.5 rounded-full font-bold uppercase text-[11px] flex items-center gap-1.5 ${
            testStatus === 'RUNNING' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' :
            testStatus === 'PAUSED' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40' :
            testStatus === 'STOPPED' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40' :
            'bg-slate-800 text-slate-300'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${
              testStatus === 'RUNNING' ? 'bg-emerald-400 animate-pulse' :
              testStatus === 'PAUSED' ? 'bg-amber-400' :
              testStatus === 'STOPPED' ? 'bg-rose-400' :
              'bg-slate-500'
            }`} />
            {testStatus}
          </span>
        </div>

        {/* Mode Selector Toggle */}
        <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-1">
          <button
            onClick={() => setSimulationMode(true)}
            className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
              simulationMode
                ? 'bg-sky-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Simulation
          </button>
          <button
            onClick={() => setSimulationMode(false)}
            className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
              !simulationMode
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Hardware (COM)
          </button>
        </div>

        {/* Server Link Badge */}
        <div className="flex items-center space-x-1.5 text-xs font-mono text-slate-400">
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 glow-emerald' : 'bg-rose-500 glow-rose animate-ping'}`} />
          <span>{isConnected ? 'LIVE WS' : 'OFFLINE'}</span>
        </div>
      </div>

      {/* Right Controls: E-Stop & Actions */}
      <div className="flex items-center space-x-3">
        {criticalFaults.length > 0 && (
          <div className="flex items-center space-x-1.5 bg-rose-500/10 border border-rose-500/40 text-rose-400 px-3 py-1.5 rounded-lg text-xs font-medium animate-pulse">
            <ShieldAlert className="w-4 h-4" />
            <span>{criticalFaults.length} CRITICAL ALARM</span>
          </div>
        )}

        <button
          onClick={resetTest}
          title="Reset Test & Clear Faults"
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition"
        >
          <RefreshCw className="w-4 h-4" />
        </button>

        <button
          onClick={emergencyStop}
          className="flex items-center space-x-2 bg-rose-600 hover:bg-rose-500 active:scale-95 text-white px-4 py-2 rounded-lg font-bold text-xs tracking-wider uppercase border border-rose-400 glow-rose transition shadow-lg"
        >
          <AlertOctagon className="w-4 h-4" />
          <span>EMERGENCY STOP</span>
        </button>
      </div>
    </header>
  );
};
