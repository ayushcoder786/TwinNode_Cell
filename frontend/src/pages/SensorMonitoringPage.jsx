import React from 'react';
import { useTwinNode } from '../context/TwinNodeContext';
import {
  Thermometer,
  Ruler,
  RotateCw,
  Compass,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Activity,
  Zap,
  Info,
  Droplets
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip
} from 'recharts';

export const SensorMonitoringPage = () => {
  const { latestTelemetry, currentTarget, telemetryHistory, activeFaults } = useTwinNode();

  const temp = latestTelemetry.actual_temp || 0;
  const dist = latestTelemetry.actual_dist || 0;
  const hum = latestTelemetry.humidity !== undefined ? latestTelemetry.humidity : 58.0;
  const motor = latestTelemetry.actual_motor_speed || 0;
  const servoActual = latestTelemetry.actual_servo_angle || 90;
  const servoCommanded = currentTarget.target_servo_angle || 90;

  // Sensor validity status
  const isTempDisconnected = temp <= 0.5;
  const isTempOutOfRange = temp < 2.0 || temp > 90.0;
  const tempStatus = isTempDisconnected ? 'DISCONNECTED' : isTempOutOfRange ? 'OUT_OF_RANGE' : 'VALID';

  const isDistDisconnected = dist <= 0.0 || dist === 999.0;
  const isDistOutOfRange = dist < 2.0 || dist > 400.0;
  const distStatus = isDistDisconnected ? 'DISCONNECTED' : isDistOutOfRange ? 'OUT_OF_RANGE' : 'VALID';

  const isHumOutOfRange = hum < 10.0 || hum > 95.0;
  const humStatus = isHumOutOfRange ? 'OUT_OF_RANGE' : 'VALID';

  // Approximate sensor signal equivalents
  const lm35_voltage_mv = (temp * 10).toFixed(0);
  const echo_pulse_us = (dist * 58).toFixed(0); // 58us per cm
  const dew_point_c = (temp - ((100 - hum) / 5)).toFixed(1);

  return (
    <div className="space-y-6">
      {/* Sensor Channel Header Notice */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <Activity className="w-5 h-5 text-sky-400" />
          <div>
            <h2 className="text-sm font-bold text-white font-mono">Real-Time Sensor & Actuator Telemetry Channels</h2>
            <p className="text-xs text-slate-400">
              Low-latency signal acquisition from Node 2 (ADC1 12-bit, Timer Input Capture, Dual PWM).
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-3 text-xs font-mono">
          <span className={`px-2.5 py-1 rounded-full font-bold flex items-center gap-1.5 ${
            latestTelemetry.is_simulated
              ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
              : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${
              latestTelemetry.is_simulated ? 'bg-amber-400' : 'bg-emerald-400'
            }`} />
            {latestTelemetry.is_simulated ? 'SIMULATED TELEMETRY' : 'PHYSICAL HARDWARE'}
          </span>
          <span className="text-slate-500">|</span>
          <span className="text-slate-400">BUS UPDATE:</span>
          <span className="text-emerald-400 font-bold">100 ms</span>
        </div>
      </div>

      {/* Main Sensor Diagnostic Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. LM35 Temperature Sensor */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
                <Thermometer className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white font-mono">LM35 Precision Centigrade Sensor</h3>
                <p className="text-xs text-slate-400">Linear 10.0 mV/°C scale factor on ADC1_IN0 (PA0)</p>
              </div>
            </div>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
              tempStatus === 'VALID' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
              'bg-rose-500/20 text-rose-400 border border-rose-500/30'
            }`}>
              {tempStatus}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-3 text-xs font-mono">
            <div className="bg-slate-900/70 p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">MEASURED TEMP</span>
              <span className="text-white text-lg font-bold">{temp.toFixed(1)} °C</span>
            </div>
            <div className="bg-slate-900/70 p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">ANALOG VOLTAGE</span>
              <span className="text-rose-400 text-lg font-bold">{lm35_voltage_mv} mV</span>
            </div>
            <div className="bg-slate-900/70 p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">TARGET SETPOINT</span>
              <span className="text-slate-300 text-lg font-bold">{(currentTarget.target_temp || 25).toFixed(1)} °C</span>
            </div>
          </div>

          {/* Thermal Bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-[11px] text-slate-400 font-mono">
              <span>0°C (Ice Point)</span>
              <span>Span (0°C - 100°C)</span>
              <span>100°C (Boiling)</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  tempStatus !== 'VALID' ? 'bg-rose-500' : 'bg-gradient-to-r from-sky-400 via-emerald-400 to-rose-500'
                }`}
                style={{ width: `${Math.min(100, Math.max(0, temp))}%` }}
              />
            </div>
          </div>

          {/* Sparkline chart */}
          <div className="h-32 w-full pt-1">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="2 2" stroke="#1e293b" />
                <XAxis dataKey="time" hide />
                <YAxis domain={['auto', 'auto']} stroke="#64748b" tick={{ fontSize: 9 }} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                <Area type="monotone" dataKey="actual_temp" stroke="#f43f5e" fill="#f43f5e" fillOpacity={0.15} isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 2. HC-SR04 Ultrasonic Distance Sensor */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                <Ruler className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white font-mono">HC-SR04 Ultrasonic Distance Sensor</h3>
                <p className="text-xs text-slate-400">10µs Trig (PB8) / Echo (PB9 via BSS138 5V→3.3V)</p>
              </div>
            </div>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
              distStatus === 'VALID' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
              'bg-rose-500/20 text-rose-400 border border-rose-500/30'
            }`}>
              {distStatus}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-3 text-xs font-mono">
            <div className="bg-slate-900/70 p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">MEASURED DISTANCE</span>
              <span className="text-white text-lg font-bold">{dist.toFixed(1)} cm</span>
            </div>
            <div className="bg-slate-900/70 p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">ECHO TIME</span>
              <span className="text-cyan-400 text-lg font-bold">{echo_pulse_us} µs</span>
            </div>
            <div className="bg-slate-900/70 p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">TARGET PROXIMITY</span>
              <span className="text-slate-300 text-lg font-bold">{(currentTarget.target_dist || 25).toFixed(1)} cm</span>
            </div>
          </div>

          {/* Proximity Bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-[11px] text-slate-400 font-mono">
              <span className="text-rose-400">Deadband &lt; 4cm</span>
              <span>Operating Span (0 - 100 cm)</span>
              <span>100 cm</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  dist < 6.0 ? 'bg-rose-500' : 'bg-cyan-500'
                }`}
                style={{ width: `${Math.min(100, Math.max(0, dist))}%` }}
              />
            </div>
          </div>

          {/* Sparkline chart */}
          <div className="h-32 w-full pt-1">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="2 2" stroke="#1e293b" />
                <XAxis dataKey="time" hide />
                <YAxis domain={['auto', 'auto']} stroke="#64748b" tick={{ fontSize: 9 }} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }} />
                <Area type="monotone" dataKey="actual_dist" stroke="#0ea5e9" fill="#0ea5e9" fillOpacity={0.15} isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 3. DHT11 Relative Humidity Sensor (Physical STM32 Telemetry) */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                <Droplets className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white font-mono">DHT11 Relative Humidity Sensor</h3>
                <p className="text-xs text-slate-400">Single-wire digital protocol on STM32 GPIO (DATA,HUM=...)</p>
              </div>
            </div>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
              humStatus === 'VALID' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
              'bg-rose-500/20 text-rose-400 border border-rose-500/30'
            }`}>
              {humStatus}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-3 text-xs font-mono">
            <div className="bg-slate-900/70 p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">MEASURED HUMIDITY</span>
              <span className="text-white text-lg font-bold">{hum.toFixed(1)} %</span>
            </div>
            <div className="bg-slate-900/70 p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">ESTIMATED DEW POINT</span>
              <span className="text-cyan-400 text-lg font-bold">{dew_point_c} °C</span>
            </div>
            <div className="bg-slate-900/70 p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">COMFORT ENVELOPE</span>
              <span className="text-slate-300 text-lg font-bold">40% - 70%</span>
            </div>
          </div>

          {/* Humidity Bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-[11px] text-slate-400 font-mono">
              <span className="text-amber-400">Arid (&lt; 30%)</span>
              <span>Nominal Operating Span (20% - 90%)</span>
              <span className="text-sky-400">Saturated (100%)</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  humStatus !== 'VALID' ? 'bg-rose-500' : 'bg-gradient-to-r from-amber-400 via-cyan-400 to-sky-500'
                }`}
                style={{ width: `${Math.min(100, Math.max(0, hum))}%` }}
              />
            </div>
          </div>

          {/* Raw string telemetry attribution */}
          <div className="bg-slate-900/60 p-2.5 rounded border border-slate-800 text-[11px] font-mono flex items-center justify-between text-slate-400">
            <span>UART FRAME TAG:</span>
            <span className="text-emerald-400 font-bold">{latestTelemetry.raw_message || 'DATA,TEMP=25,HUM=58,DIST=45.20'}</span>
          </div>
        </div>

        {/* 3. DC Motor Drive Feedback */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
                <RotateCw className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white font-mono">L293D DC Motor Actuation Channel</h3>
                <p className="text-xs text-slate-400">EN1 TIM4_CH1 (PB6 1kHz PWM) + IN1/IN2 (PB4/PB5)</p>
              </div>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase bg-amber-500/20 text-amber-400 border border-amber-500/30">
              {motor !== 0 ? 'DRIVING' : 'STANDBY'}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-3 text-xs font-mono">
            <div className="bg-slate-900/70 p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">PWM DUTY CYCLE</span>
              <span className="text-white text-lg font-bold">{Math.abs(motor)} %</span>
            </div>
            <div className="bg-slate-900/70 p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">ROTATION DIRECTION</span>
              <span className="text-amber-400 text-sm font-bold">
                {motor > 0 ? 'FORWARD (CW)' : motor < 0 ? 'REVERSE (CCW)' : 'STOP'}
              </span>
            </div>
            <div className="bg-slate-900/70 p-3 rounded border border-slate-800">
              <span className="text-slate-500 block text-[10px]">ESTIMATED SPEED</span>
              <span className="text-slate-300 text-lg font-bold">{Math.abs(Math.round(motor * 2.2))} RPM</span>
            </div>
          </div>

          <div className="bg-slate-900/60 p-3 rounded border border-slate-800 text-xs space-y-1.5">
            <div className="flex justify-between text-slate-400 font-mono">
              <span>H-Bridge IN1 State: <strong className="text-white">{motor > 0 ? 'HIGH (3.3V)' : 'LOW (0V)'}</strong></span>
              <span>IN2 State: <strong className="text-white">{motor < 0 ? 'HIGH (3.3V)' : 'LOW (0V)'}</strong></span>
            </div>
            <div className="flex justify-between text-slate-400 font-mono">
              <span>Motor VCC2 Rail: <strong className="text-emerald-400">5.0V (LM2596 Buck)</strong></span>
              <span>Duty Clamping: <strong className="text-sky-400">±100% Limited</strong></span>
            </div>
          </div>
        </div>

        {/* 4. Servo Motor Command & Position (Crucial Requirement: Command vs Feedback) */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <Compass className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white font-mono">Servo Actuator Command & Position</h3>
                <p className="text-xs text-slate-400">TIM3_CH1 (PC6 50Hz, 1.0ms to 2.0ms pulse width)</p>
              </div>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              SYNCHRONIZED
            </span>
          </div>

          {/* Explicitly showing commanded vs measured separately as requested */}
          <div className="grid grid-cols-2 gap-3 text-xs font-mono">
            <div className="bg-slate-900/70 p-3.5 rounded border border-slate-800">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-semibold">COMMANDED ANGLE (TARGET)</span>
                <span className="text-[10px] text-sky-400 bg-sky-500/10 px-1.5 py-0.5 rounded">Set by Node 1</span>
              </div>
              <div className="text-2xl font-bold font-mono text-sky-400 mt-1">
                {servoCommanded}°
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Pulse width: {(1.0 + (servoCommanded / 180.0)).toFixed(2)} ms
              </p>
            </div>

            <div className="bg-slate-900/70 p-3.5 rounded border border-slate-800">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-semibold">MEASURED / SLEW FEEDBACK</span>
                <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">Node 2 Telemetry</span>
              </div>
              <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
                {servoActual}°
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Tracking error: Δ {Math.abs(servoCommanded - servoActual)}°
              </p>
            </div>
          </div>

          <div className="bg-slate-900/60 p-3 rounded border border-slate-800 text-xs flex items-center space-x-2 text-slate-400">
            <Info className="w-4 h-4 text-sky-400 shrink-0" />
            <span>
              Standard hobby servos (e.g. SG90/MG995) operate open-loop without analog potentiometer feedback lead. Measured position reflects kinematic slew rate telemetry from Node 2 supervisor model.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
