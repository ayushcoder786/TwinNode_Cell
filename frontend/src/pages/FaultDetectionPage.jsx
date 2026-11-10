import React, { useState, useEffect } from 'react';
import { useTwinNode } from '../context/TwinNodeContext';
import {
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
  HelpCircle,
  Zap,
  Sliders,
  AlertOctagon,
  FileQuestion,
  ExternalLink
} from 'lucide-react';

export const FaultDetectionPage = () => {
  const {
    activeFaults,
    faultHistory,
    acknowledgeFault,
    resetFaults,
    injectSimulationFault
  } = useTwinNode();

  const [injections, setInjections] = useState({
    disconnect_lm35: false,
    disconnect_ultrasonic: false,
    temp_out_of_range: false,
    dist_out_of_range: false,
    motor_stall: false,
    servo_stall: false,
    comm_drop: false,
    latency_spike: false,
    reverse_motor: false
  });

  const [eqStatus, setEqStatus] = useState(null);

  const fetchEqStatus = async () => {
    try {
      const res = await fetch('/api/eq15_09/status');
      const data = await res.json();
      setEqStatus(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchEqStatus();
  }, []);

  const handleToggleInjection = async (key) => {
    const newState = !injections[key];
    setInjections(prev => ({ ...prev, [key]: newState }));
    await injectSimulationFault(key, newState);
  };

  const handleClearInjections = async () => {
    const cleared = Object.keys(injections).reduce((acc, k) => ({ ...acc, [k]: false }), {});
    setInjections(cleared);
    for (const k of Object.keys(cleared)) {
      await injectSimulationFault(k, false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-rose-400" />
            <h2 className="text-base font-bold text-white font-mono">Special Condition & Fault Detection Supervisor</h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time rule engine evaluating setpoint deviation, actuator failure, sensor validity, and communication integrity.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={resetFaults}
            className="flex items-center space-x-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-bold uppercase border border-slate-700 transition"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Reset All Faults</span>
          </button>
        </div>
      </div>

      {/* Special Condition: EQ-15-09 Dedicated Status Banner */}
      <div className="bg-slate-900/90 border-2 border-amber-500/40 rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <FileQuestion className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-sm font-bold text-white font-mono">CONDITION EQ-15-09: RESERVED ENGINEERING RULE</h3>
                <span className="text-[10px] font-mono font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded">
                  STATUS: PENDING CONFIRMATION
                </span>
              </div>
              <p className="text-xs text-slate-400">Configured via backend/config/eq15_09_condition.json</p>
            </div>
          </div>
          <span className="text-xs font-mono text-slate-400">NON-BLOCKING STUB</span>
        </div>

        <div className="bg-[#090d16] p-3.5 rounded-lg border border-slate-800 text-xs space-y-2">
          <p className="text-slate-300">
            <strong>System Notice:</strong> The exact physical criteria, trigger thresholds, and actuation sequence for engineering condition <strong>EQ-15-09</strong> have not yet been supplied by the engineering authority.
          </p>
          <p className="text-slate-400">
            Per system requirements, this detection rule is isolated in a dedicated configuration file and detector module without inventing physical criteria. The rest of the TwinNode distributed sensing and actuation supervisor remains fully operational.
          </p>
          <div className="flex items-center space-x-4 pt-1 font-mono text-[11px] text-slate-400">
            <span>Enabled: <strong className="text-amber-400">{eqStatus?.enabled ? 'TRUE' : 'FALSE (Pending confirmation)'}</strong></span>
            <span>Channel: <strong className="text-slate-300">{eqStatus?.parameters?.monitoring_channel || 'RESERVED_CUSTOM_SENSING'}</strong></span>
            <span>Action on Trigger: <strong className="text-slate-300">{eqStatus?.action_on_trigger?.severity || 'WARNING'}</strong></span>
          </div>
        </div>
      </div>

      {/* Active Faults Live Table */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            <h3 className="text-sm font-semibold text-white">Active Plant Alarms ({activeFaults.length})</h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">Auto-evaluated at 10Hz</span>
        </div>

        {activeFaults.length === 0 ? (
          <div className="flex items-center justify-center p-8 bg-slate-900/50 rounded-lg border border-slate-800/80 text-slate-400 space-x-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span className="text-sm">No active alarms. Distributed nodes operating within normal parameters.</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Severity</th>
                  <th className="py-2.5 px-3">Fault ID</th>
                  <th className="py-2.5 px-3">Title & Description</th>
                  <th className="py-2.5 px-3">Recommended Engineering Action</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Acknowledge</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {activeFaults.map((f, idx) => (
                  <tr key={idx} className="hover:bg-slate-900/40">
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 rounded font-bold text-[10px] uppercase ${
                        f.severity === 'CRITICAL' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40' :
                        f.severity === 'WARNING' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40' :
                        'bg-sky-500/20 text-sky-400'
                      }`}>
                        {f.severity}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-white font-semibold">{f.fault_code}</td>
                    <td className="py-2.5 px-3 font-sans">
                      <strong className="block text-white text-xs">{f.title}</strong>
                      <span className="text-slate-400 text-[11px]">{f.description}</span>
                    </td>
                    <td className="py-2.5 px-3 text-amber-300/90 font-sans">{f.recommended_action}</td>
                    <td className="py-2.5 px-3">
                      <span className={`text-[10px] font-bold ${f.is_acknowledged ? 'text-emerald-400' : 'text-rose-400 animate-pulse'}`}>
                        {f.is_acknowledged ? 'ACKNOWLEDGED' : 'UNACKNOWLEDGED'}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {!f.is_acknowledged && (
                        <button
                          onClick={() => acknowledgeFault(f.fault_code)}
                          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-[11px] font-sans border border-slate-700 transition"
                        >
                          Ack
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Interactive Simulation Fault Injector Panel */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <Zap className="w-5 h-5 text-sky-400" />
            <div>
              <h3 className="text-sm font-semibold text-white">Interactive Simulation Fault Injector</h3>
              <p className="text-xs text-slate-400">Trigger physical and communication failures to validate supervisor engine response.</p>
            </div>
          </div>
          <button
            onClick={handleClearInjections}
            className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs border border-slate-700 font-mono transition"
          >
            Clear All Injections
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {/* Inject Sensor Disconnects */}
          <div className="bg-slate-900/70 p-3.5 rounded-lg border border-slate-800 space-y-2">
            <span className="text-xs font-bold text-white block">Sensor Failure Injections</span>
            <div className="space-y-1.5">
              <button
                onClick={() => handleToggleInjection('disconnect_lm35')}
                className={`w-full py-1.5 px-3 rounded text-xs font-mono text-left flex justify-between items-center transition ${
                  injections.disconnect_lm35 ? 'bg-rose-600 text-white font-bold' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                <span>Disconnect LM35 (0V)</span>
                <span>{injections.disconnect_lm35 ? 'ACTIVE' : 'OFF'}</span>
              </button>
              <button
                onClick={() => handleToggleInjection('disconnect_ultrasonic')}
                className={`w-full py-1.5 px-3 rounded text-xs font-mono text-left flex justify-between items-center transition ${
                  injections.disconnect_ultrasonic ? 'bg-rose-600 text-white font-bold' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                <span>Disconnect Ultrasonic Echo</span>
                <span>{injections.disconnect_ultrasonic ? 'ACTIVE' : 'OFF'}</span>
              </button>
            </div>
          </div>

          {/* Inject Out-of-Range */}
          <div className="bg-slate-900/70 p-3.5 rounded-lg border border-slate-800 space-y-2">
            <span className="text-xs font-bold text-white block">Physical Out-of-Range</span>
            <div className="space-y-1.5">
              <button
                onClick={() => handleToggleInjection('temp_out_of_range')}
                className={`w-full py-1.5 px-3 rounded text-xs font-mono text-left flex justify-between items-center transition ${
                  injections.temp_out_of_range ? 'bg-rose-600 text-white font-bold' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                <span>Temp Runaway (115°C)</span>
                <span>{injections.temp_out_of_range ? 'ACTIVE' : 'OFF'}</span>
              </button>
              <button
                onClick={() => handleToggleInjection('dist_out_of_range')}
                className={`w-full py-1.5 px-3 rounded text-xs font-mono text-left flex justify-between items-center transition ${
                  injections.dist_out_of_range ? 'bg-rose-600 text-white font-bold' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                <span>Distance Exceeded (480cm)</span>
                <span>{injections.dist_out_of_range ? 'ACTIVE' : 'OFF'}</span>
              </button>
            </div>
          </div>

          {/* Inject Actuator & Comm Failures */}
          <div className="bg-slate-900/70 p-3.5 rounded-lg border border-slate-800 space-y-2">
            <span className="text-xs font-bold text-white block">Actuator & Bus Injections</span>
            <div className="space-y-1.5">
              <button
                onClick={() => handleToggleInjection('motor_stall')}
                className={`w-full py-1.5 px-3 rounded text-xs font-mono text-left flex justify-between items-center transition ${
                  injections.motor_stall ? 'bg-rose-600 text-white font-bold' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                <span>DC Motor Stall (0 RPM)</span>
                <span>{injections.motor_stall ? 'ACTIVE' : 'OFF'}</span>
              </button>
              <button
                onClick={() => handleToggleInjection('comm_drop')}
                className={`w-full py-1.5 px-3 rounded text-xs font-mono text-left flex justify-between items-center transition ${
                  injections.comm_drop ? 'bg-rose-600 text-white font-bold' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                <span>Inter-Node UART Loss</span>
                <span>{injections.comm_drop ? 'ACTIVE' : 'OFF'}</span>
              </button>
              <button
                onClick={() => handleToggleInjection('reverse_motor')}
                className={`w-full py-1.5 px-3 rounded text-xs font-mono text-left flex justify-between items-center transition ${
                  injections.reverse_motor ? 'bg-rose-600 text-white font-bold' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                <span>Inverted Motor Polarity</span>
                <span>{injections.reverse_motor ? 'ACTIVE' : 'OFF'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
