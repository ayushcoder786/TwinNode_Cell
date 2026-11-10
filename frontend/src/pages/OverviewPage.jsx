import React from 'react';
import { useTwinNode } from '../context/TwinNodeContext';
import {
  Thermometer,
  Ruler,
  RotateCw,
  Compass,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Clock,
  ShieldCheck,
  ShieldAlert,
  Droplets
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';

export const OverviewPage = () => {
  const {
    latestTelemetry,
    telemetryHistory,
    currentTarget,
    activeFaults,
    testStatus,
    activeTestId,
    activeTestName,
    acknowledgeFault
  } = useTwinNode();

  // Health calculation
  const criticalCount = activeFaults.filter(f => f.severity === 'CRITICAL').length;
  const warningCount = activeFaults.filter(f => f.severity === 'WARNING').length;
  const healthScore = Math.max(0, 100 - (criticalCount * 50) - (warningCount * 15));

  return (
    <div className="space-y-6">
      {/* Prominent Data Source Banner (Distinguishes Simulated vs Physical Hardware Data) */}
      <div className={`p-3.5 rounded-xl border flex items-center justify-between font-mono text-xs ${
        latestTelemetry.is_simulated
          ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
          : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
      }`}>
        <div className="flex items-center space-x-2.5">
          <span className={`w-2.5 h-2.5 rounded-full ${
            latestTelemetry.is_simulated ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400 animate-pulse'
          }`} />
          <span>
            DATA SOURCE:{' '}
            <strong className="tracking-wide">
              {latestTelemetry.is_simulated ? 'SYNTHETIC SIMULATION ENGINE (NO HARDWARE CONNECTED)' : 'PHYSICAL HARDWARE TELEMETRY (STM32 USB COM LINK)'}
            </strong>
          </span>
        </div>
        <span className="text-[11px] opacity-80">
          {latestTelemetry.is_simulated ? 'Physics model: 100ms cycle' : 'Hardware baud: 115200 8N1'}
        </span>
      </div>

      {/* Top Banner / System Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Node 1 Card */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-slate-400 text-xs font-mono">
              <Cpu className="w-4 h-4 text-sky-400" />
              <span>NODE 1 (SETPOINT GEN)</span>
            </div>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
              latestTelemetry.node1_status === 'ONLINE' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
            }`}>
              {latestTelemetry.node1_status}
            </span>
          </div>
          <div className="mt-3">
            <div className="text-xl font-bold font-mono text-white">STM32F446RE</div>
            <p className="text-xs text-slate-400 mt-0.5">USB VCP Gateway @ 115200</p>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-800/80 flex justify-between text-[11px] text-slate-400 font-mono">
            <span>UART2: ST-LINK</span>
            <span className="text-emerald-400">ACTIVE</span>
          </div>
        </div>

        {/* Node 2 Card */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-slate-400 text-xs font-mono">
              <Cpu className="w-4 h-4 text-cyan-400" />
              <span>NODE 2 (ACTUATOR/SENS)</span>
            </div>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
              latestTelemetry.node2_status === 'ONLINE' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
            }`}>
              {latestTelemetry.node2_status}
            </span>
          </div>
          <div className="mt-3">
            <div className="text-xl font-bold font-mono text-white">STM32F446RE</div>
            <p className="text-xs text-slate-400 mt-0.5">L293D + Servo + Sensors</p>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-800/80 flex justify-between text-[11px] text-slate-400 font-mono">
            <span>INTER-NODE UART</span>
            <span className="text-sky-400">{latestTelemetry.comm_latency_ms || 0} ms</span>
          </div>
        </div>

        {/* Active Test Card */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-slate-400 text-xs font-mono">
              <Clock className="w-4 h-4 text-amber-400" />
              <span>SUPERVISOR BENCH</span>
            </div>
            <span className="text-[10px] bg-slate-800 text-slate-300 font-mono px-2 py-0.5 rounded">
              ID #{activeTestId}
            </span>
          </div>
          <div className="mt-3">
            <div className="text-xl font-bold font-mono text-white truncate">{activeTestName}</div>
            <p className="text-xs text-slate-400 mt-0.5">Status: <span className="text-white font-semibold">{testStatus}</span></p>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-800/80 flex justify-between text-[11px] text-slate-400 font-mono">
            <span>SAMPLE RATE</span>
            <span className="text-amber-400">10 Hz (100ms)</span>
          </div>
        </div>

        {/* System Health Card */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-slate-400 text-xs font-mono">
              {healthScore >= 80 ? (
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              ) : (
                <ShieldAlert className="w-4 h-4 text-rose-400" />
              )}
              <span>PLANT HEALTH</span>
            </div>
            <span className={`text-[11px] font-bold font-mono ${healthScore >= 80 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {healthScore}%
            </span>
          </div>
          <div className="mt-3">
            <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  healthScore >= 80 ? 'bg-emerald-500' : healthScore >= 50 ? 'bg-amber-500' : 'bg-rose-500'
                }`}
                style={{ width: `${healthScore}%` }}
              />
            </div>
            <p className="text-xs text-slate-400 mt-2">
              {criticalCount} Critical, {warningCount} Warning Faults
            </p>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-800/80 flex justify-between text-[11px] text-slate-400 font-mono">
            <span>ENGINE STATUS</span>
            <span className="text-emerald-400 font-semibold">SUPERVISING</span>
          </div>
        </div>
      </div>

      {/* Target vs Actual Metric Gauges */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Temperature Gauge */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-3">
            <div className="flex items-center space-x-2">
              <Thermometer className="w-4 h-4 text-rose-400" />
              <span className="font-semibold text-white">LM35 Temperature</span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">PA0 / ADC1</span>
          </div>
          <div className="flex items-baseline justify-between">
            <div>
              <div className="text-3xl font-bold font-mono text-white">
                {latestTelemetry.actual_temp !== undefined ? latestTelemetry.actual_temp.toFixed(1) : '--'}
                <span className="text-sm font-normal text-slate-400 ml-1">°C</span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5 font-mono">
                Target: {currentTarget.target_temp?.toFixed(1) || '--'} °C
              </p>
            </div>
            <div className={`text-xs font-mono px-2 py-1 rounded font-semibold ${
              Math.abs((latestTelemetry.actual_temp || 0) - (currentTarget.target_temp || 0)) <= 3.0
                ? 'bg-emerald-500/10 text-emerald-400'
                : 'bg-amber-500/10 text-amber-400'
            }`}>
              Δ {(Math.abs((latestTelemetry.actual_temp || 0) - (currentTarget.target_temp || 0))).toFixed(1)}°C
            </div>
          </div>
        </div>

        {/* Ultrasonic Distance Gauge */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-3">
            <div className="flex items-center space-x-2">
              <Ruler className="w-4 h-4 text-cyan-400" />
              <span className="font-semibold text-white">HC-SR04 Distance</span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">PB8/PB9 Level Shifted</span>
          </div>
          <div className="flex items-baseline justify-between">
            <div>
              <div className="text-3xl font-bold font-mono text-white">
                {latestTelemetry.actual_dist !== undefined ? latestTelemetry.actual_dist.toFixed(1) : '--'}
                <span className="text-sm font-normal text-slate-400 ml-1">cm</span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5 font-mono">
                Target: {currentTarget.target_dist?.toFixed(1) || '--'} cm
              </p>
            </div>
            <div className={`text-xs font-mono px-2 py-1 rounded font-semibold ${
              Math.abs((latestTelemetry.actual_dist || 0) - (currentTarget.target_dist || 0)) <= 4.0
                ? 'bg-emerald-500/10 text-emerald-400'
                : 'bg-amber-500/10 text-amber-400'
            }`}>
              Δ {(Math.abs((latestTelemetry.actual_dist || 0) - (currentTarget.target_dist || 0))).toFixed(1)}cm
            </div>
          </div>
        </div>

        {/* Relative Humidity Gauge (DHT11) */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-3">
            <div className="flex items-center space-x-2">
              <Droplets className="w-4 h-4 text-cyan-400" />
              <span className="font-semibold text-white">DHT11 Humidity</span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">GPIO Telemetry</span>
          </div>
          <div className="flex items-baseline justify-between">
            <div>
              <div className="text-3xl font-bold font-mono text-cyan-400">
                {latestTelemetry.humidity !== undefined ? latestTelemetry.humidity.toFixed(1) : '58.0'}
                <span className="text-sm font-normal text-slate-400 ml-1">%</span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5 font-mono">
                Span: 20% - 90% RH
              </p>
            </div>
            <div className="text-xs font-mono px-2 py-1 rounded bg-slate-800 text-cyan-400 font-semibold">
              {(latestTelemetry.humidity || 50) > 70 ? 'HUMID' : (latestTelemetry.humidity || 50) < 30 ? 'DRY' : 'OPTIMAL'}
            </div>
          </div>
        </div>

        {/* DC Motor Response Gauge */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-3">
            <div className="flex items-center space-x-2">
              <RotateCw className="w-4 h-4 text-amber-400" />
              <span className="font-semibold text-white">DC Motor (L293D)</span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">PB6 / PWM 1kHz</span>
          </div>
          <div className="flex items-baseline justify-between">
            <div>
              <div className="text-3xl font-bold font-mono text-white">
                {latestTelemetry.actual_motor_speed !== undefined ? latestTelemetry.actual_motor_speed : '--'}
                <span className="text-sm font-normal text-slate-400 ml-1">%</span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5 font-mono">
                Target: {currentTarget.target_motor_speed}%
              </p>
            </div>
            <div className="text-xs font-mono px-2 py-1 rounded bg-slate-800 text-sky-400 font-semibold">
              {(latestTelemetry.actual_motor_speed || 0) > 0 ? 'FORWARD (CW)' : (latestTelemetry.actual_motor_speed || 0) < 0 ? 'REVERSE (CCW)' : 'HALT'}
            </div>
          </div>
        </div>

        {/* Servo Motor Angle Gauge */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-3">
            <div className="flex items-center space-x-2">
              <Compass className="w-4 h-4 text-emerald-400" />
              <span className="font-semibold text-white">Servo Actuator</span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">TIM3_CH1 50Hz</span>
          </div>
          <div className="flex items-baseline justify-between">
            <div>
              <div className="text-3xl font-bold font-mono text-white">
                {latestTelemetry.actual_servo_angle !== undefined ? latestTelemetry.actual_servo_angle : '--'}
                <span className="text-sm font-normal text-slate-400 ml-1">°</span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5 font-mono">
                Commanded: {currentTarget.target_servo_angle}°
              </p>
            </div>
            <div className="text-xs font-mono px-2 py-1 rounded bg-slate-800 text-emerald-400 font-semibold">
              SPAN: 0° - 180°
            </div>
          </div>
        </div>
      </div>

      {/* Real-time Dynamic Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Temperature & Distance */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Environmental Sensing Telemetry</h3>
              <p className="text-xs text-slate-400">Live LM35 Temperature (°C) & HC-SR04 Distance (cm)</p>
            </div>
            <span className="text-xs font-mono text-sky-400 bg-sky-500/10 px-2 py-1 rounded border border-sky-500/20">
              REAL-TIME (35 SAMPLES)
            </span>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                <Line type="monotone" dataKey="actual_temp" stroke="#f43f5e" name="Actual Temp (°C)" strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line type="stepAfter" dataKey="target_temp" stroke="#fb7185" strokeDasharray="4 4" name="Target Temp (°C)" dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="actual_dist" stroke="#0ea5e9" name="Actual Dist (cm)" strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line type="stepAfter" dataKey="target_dist" stroke="#7dd3fc" strokeDasharray="4 4" name="Target Dist (cm)" dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Motor PWM Duty & Servo Angle */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Actuation Response Curves</h3>
              <p className="text-xs text-slate-400">DC Motor Duty Cycle (%) & Servo Position Angle (°)</p>
            </div>
            <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20">
              SYNCHRONOUS
            </span>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                <Line type="monotone" dataKey="actual_motor" stroke="#f59e0b" name="Motor Response (%)" strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line type="stepAfter" dataKey="target_motor" stroke="#fde68a" strokeDasharray="4 4" name="Target Motor (%)" dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="actual_servo" stroke="#10b981" name="Servo Measured (°)" strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line type="stepAfter" dataKey="target_servo" stroke="#a7f3d0" strokeDasharray="4 4" name="Servo Commanded (°)" dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Active Alarms & Supervisor Notifications */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-semibold text-white">Active Condition Alarms & Faults</h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {activeFaults.length} Active Alarm{activeFaults.length !== 1 ? 's' : ''}
          </span>
        </div>

        {activeFaults.length === 0 ? (
          <div className="flex items-center justify-center p-8 bg-slate-900/50 rounded-lg border border-slate-800/80 text-slate-400 space-x-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span className="text-sm">All conditions normal. Plant operating within safe engineering limits.</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Severity</th>
                  <th className="py-2.5 px-3">Condition ID</th>
                  <th className="py-2.5 px-3">Alarm Description</th>
                  <th className="py-2.5 px-3">Recommended Engineering Action</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
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
                    <td className="py-2.5 px-3 text-slate-300 font-sans">{f.description}</td>
                    <td className="py-2.5 px-3 text-amber-300/80 font-sans">{f.recommended_action}</td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => acknowledgeFault(f.fault_code)}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-[11px] font-sans border border-slate-700 transition"
                      >
                        Acknowledge
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
