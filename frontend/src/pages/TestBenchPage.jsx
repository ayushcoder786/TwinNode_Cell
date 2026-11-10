import React, { useState } from 'react';
import { useTwinNode } from '../context/TwinNodeContext';
import {
  Play,
  Pause,
  Square,
  RotateCcw,
  AlertOctagon,
  Sliders,
  ShieldCheck,
  Zap,
  Activity,
  Layers
} from 'lucide-react';

export const TestBenchPage = () => {
  const {
    testStatus,
    activeTestId,
    activeTestName,
    activeProfile,
    currentTarget,
    latestTelemetry,
    sampleCount,
    startTest,
    pauseTest,
    resumeTest,
    stopTest,
    resetTest,
    emergencyStop,
    updateSetpoints
  } = useTwinNode();

  const [testNameInput, setTestNameInput] = useState(activeTestName || 'BENCH_QUAL_01');
  const [profileInput, setProfileInput] = useState(activeProfile || 'STANDARD_INDUSTRIAL');

  // Sliders local state
  const [targetTemp, setTargetTemp] = useState(currentTarget.target_temp || 25.0);
  const [targetDist, setTargetDist] = useState(currentTarget.target_dist || 25.0);
  const [targetMotor, setTargetMotor] = useState(currentTarget.target_motor_speed || 0);
  const [targetServo, setTargetServo] = useState(currentTarget.target_servo_angle || 90);

  const handleApplySetpoints = () => {
    updateSetpoints({
      target_temp: parseFloat(targetTemp),
      target_dist: parseFloat(targetDist),
      target_motor_speed: parseInt(targetMotor, 10),
      target_servo_angle: parseInt(targetServo, 10)
    });
  };

  const handleStart = () => {
    startTest(testNameInput, profileInput, {
      target_temp: parseFloat(targetTemp),
      target_dist: parseFloat(targetDist),
      target_motor_speed: parseInt(targetMotor, 10),
      target_servo_angle: parseInt(targetServo, 10)
    });
  };

  const handleProfilePreset = (preset) => {
    if (preset === 'STEP_RESPONSE') {
      setTargetMotor(75);
      setTargetServo(150);
      setTargetDist(15.0);
    } else if (preset === 'OBSTACLE_APPROACH') {
      setTargetMotor(40);
      setTargetDist(8.0);
      setTargetServo(90);
    } else if (preset === 'THERMAL_STRESS') {
      setTargetTemp(45.0);
      setTargetMotor(20);
      setTargetServo(90);
    } else if (preset === 'IDLE_CENTER') {
      setTargetTemp(25.0);
      setTargetDist(30.0);
      setTargetMotor(0);
      setTargetServo(90);
    }
  };

  return (
    <div className="space-y-6">
      {/* Test Execution Controller Bar */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center space-x-2">
              <Sliders className="w-5 h-5 text-sky-400" />
              <h2 className="text-base font-bold text-white font-mono">Test Bench Execution Engine</h2>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Supervise automated test sequences, configure dynamic setpoints, and enforce safe operating limits.
            </p>
          </div>

          {/* Test Action Controls */}
          <div className="flex items-center space-x-2">
            {testStatus === 'RUNNING' ? (
              <button
                onClick={pauseTest}
                className="flex items-center space-x-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-bold uppercase transition"
              >
                <Pause className="w-4 h-4" />
                <span>Pause</span>
              </button>
            ) : testStatus === 'PAUSED' ? (
              <button
                onClick={resumeTest}
                className="flex items-center space-x-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold uppercase transition"
              >
                <Play className="w-4 h-4" />
                <span>Resume</span>
              </button>
            ) : (
              <button
                onClick={handleStart}
                className="flex items-center space-x-1.5 px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold uppercase transition shadow-lg shadow-emerald-950"
              >
                <Play className="w-4 h-4" />
                <span>Start Test</span>
              </button>
            )}

            <button
              onClick={stopTest}
              disabled={testStatus === 'IDLE' || testStatus === 'STOPPED'}
              className="flex items-center space-x-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 rounded-lg text-xs font-bold uppercase border border-slate-700 transition"
            >
              <Square className="w-4 h-4" />
              <span>Stop</span>
            </button>

            <button
              onClick={resetTest}
              className="flex items-center space-x-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-bold uppercase border border-slate-700 transition"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Reset</span>
            </button>

            <button
              onClick={emergencyStop}
              className="flex items-center space-x-1.5 px-4 py-2 bg-rose-600 hover:bg-rose-500 active:scale-95 text-white rounded-lg text-xs font-bold uppercase border border-rose-400 glow-rose transition shadow-md"
            >
              <AlertOctagon className="w-4 h-4" />
              <span>E-Stop</span>
            </button>
          </div>
        </div>

        {/* Test Parameters Configuration */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">TEST CAMPAIGN NAME</label>
            <input
              type="text"
              value={testNameInput}
              onChange={(e) => setTestNameInput(e.target.value)}
              disabled={testStatus === 'RUNNING'}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500 disabled:opacity-60"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">CONDITION VALIDATION PROFILE</label>
            <select
              value={profileInput}
              onChange={(e) => setProfileInput(e.target.value)}
              disabled={testStatus === 'RUNNING'}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500 disabled:opacity-60"
            >
              <option value="STANDARD_INDUSTRIAL">Standard Industrial Plant Profile</option>
              <option value="SENSITIVE_BENCH">High Sensitivity Validation Profile</option>
            </select>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5 flex items-center justify-around text-xs font-mono">
            <div>
              <span className="text-slate-500 block text-[10px]">CAPTURED SAMPLES</span>
              <span className="text-white font-bold text-sm">{sampleCount}</span>
            </div>
            <div className="h-6 w-px bg-slate-800" />
            <div>
              <span className="text-slate-500 block text-[10px]">LOOP LATENCY</span>
              <span className="text-sky-400 font-bold text-sm">{latestTelemetry.comm_latency_ms || 0} ms</span>
            </div>
          </div>
        </div>
      </div>

      {/* Dynamic Setpoint Configuration Sliders */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-sm font-semibold text-white">Live Physical Setpoint Controls</h3>
            <p className="text-xs text-slate-400">Configure target values and dispatch directly to Node 1.</p>
          </div>
          <button
            onClick={handleApplySetpoints}
            className="px-4 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-bold uppercase tracking-wider transition shadow-sm"
          >
            Dispatch Setpoints
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Target Temperature Slider */}
          <div className="bg-slate-900/70 border border-slate-800/80 rounded-xl p-4 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-white">LM35 Target Temperature</span>
              <span className="text-xs font-mono font-bold text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                {parseFloat(targetTemp).toFixed(1)} °C
              </span>
            </div>
            <input
              type="range"
              min="15.0"
              max="70.0"
              step="0.5"
              value={targetTemp}
              onChange={(e) => setTargetTemp(e.target.value)}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-rose-500"
            />
            <div className="flex justify-between text-[10px] font-mono text-slate-500">
              <span>Min: 15.0°C</span>
              <span>Ambient: ~25.0°C</span>
              <span>Max: 70.0°C</span>
            </div>
          </div>

          {/* Target Ultrasonic Distance Slider */}
          <div className="bg-slate-900/70 border border-slate-800/80 rounded-xl p-4 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-white">HC-SR04 Target Distance</span>
              <span className="text-xs font-mono font-bold text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                {parseFloat(targetDist).toFixed(1)} cm
              </span>
            </div>
            <input
              type="range"
              min="5.0"
              max="120.0"
              step="1.0"
              value={targetDist}
              onChange={(e) => setTargetDist(e.target.value)}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
            />
            <div className="flex justify-between text-[10px] font-mono text-slate-500">
              <span>Deadband: 4.0cm</span>
              <span>Safe Bench: 25.0cm</span>
              <span>Max: 120.0cm</span>
            </div>
          </div>

          {/* Target DC Motor Speed Slider */}
          <div className="bg-slate-900/70 border border-slate-800/80 rounded-xl p-4 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-white">DC Motor Speed & Direction</span>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setTargetMotor(0)}
                  className="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded"
                >
                  Halt (0%)
                </button>
                <span className="text-xs font-mono font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                  {targetMotor}% {targetMotor > 0 ? '(CW)' : targetMotor < 0 ? '(CCW)' : '(STOP)'}
                </span>
              </div>
            </div>
            <input
              type="range"
              min="-100"
              max="100"
              step="5"
              value={targetMotor}
              onChange={(e) => setTargetMotor(e.target.value)}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-amber-500"
            />
            <div className="flex justify-between text-[10px] font-mono text-slate-500">
              <span>-100% Full Reverse</span>
              <span>0% Neutral</span>
              <span>+100% Full Forward</span>
            </div>
          </div>

          {/* Target Servo Angle Slider */}
          <div className="bg-slate-900/70 border border-slate-800/80 rounded-xl p-4 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs font-semibold text-white">Servo Angular Position</span>
              <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                {targetServo}°
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="180"
              step="5"
              value={targetServo}
              onChange={(e) => setTargetServo(e.target.value)}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
            />
            <div className="flex justify-between gap-1 pt-1">
              {[0, 45, 90, 135, 180].map((angle) => (
                <button
                  key={angle}
                  onClick={() => setTargetServo(angle)}
                  className="flex-1 py-1 bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-300 rounded border border-slate-700 transition"
                >
                  {angle}°
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Preset Profiles & Safe Operating Limits */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Preset Profiles */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-3">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-sky-400" />
            <h3 className="text-sm font-semibold text-white">Validation Sequence Presets</h3>
          </div>
          <p className="text-xs text-slate-400">
            Quickly stage standard industrial test patterns to validate settling time and dynamic response.
          </p>

          <div className="grid grid-cols-2 gap-2.5 pt-2">
            <button
              onClick={() => handleProfilePreset('STEP_RESPONSE')}
              className="p-3 bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 rounded-lg text-left transition"
            >
              <span className="block text-xs font-bold text-white">Step Response Transient</span>
              <span className="block text-[11px] text-slate-400 mt-0.5">Motor +75%, Servo 150°, Dist 15cm</span>
            </button>
            <button
              onClick={() => handleProfilePreset('OBSTACLE_APPROACH')}
              className="p-3 bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 rounded-lg text-left transition"
            >
              <span className="block text-xs font-bold text-white">Proximity Collision Test</span>
              <span className="block text-[11px] text-slate-400 mt-0.5">Motor +40%, Approach 8.0cm</span>
            </button>
            <button
              onClick={() => handleProfilePreset('THERMAL_STRESS')}
              className="p-3 bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 rounded-lg text-left transition"
            >
              <span className="block text-xs font-bold text-white">Thermal Elevation Cycle</span>
              <span className="block text-[11px] text-slate-400 mt-0.5">Target 45.0°C, Slow Traverse</span>
            </button>
            <button
              onClick={() => handleProfilePreset('IDLE_CENTER')}
              className="p-3 bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 rounded-lg text-left transition"
            >
              <span className="block text-xs font-bold text-white">Neutral Benchmark State</span>
              <span className="block text-[11px] text-slate-400 mt-0.5">Motor 0%, Servo 90°, Dist 30cm</span>
            </button>
          </div>
        </div>

        {/* Safe Operating Limits */}
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-3">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-white">Enforced Safe Operating Boundaries</h3>
          </div>
          <p className="text-xs text-slate-400">
            Hardware protective envelopes checked by both firmware safety routines and supervisor engine.
          </p>

          <div className="space-y-2 pt-2 text-xs font-mono">
            <div className="flex justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">LM35 Thermal Cutoff Envelope</span>
              <span className="text-white font-semibold">2.0°C to 90.0°C</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">Ultrasonic Collision Deadband</span>
              <span className="text-white font-semibold">≥ 4.0 cm Minimum</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">L293D Current Overload Protection</span>
              <span className="text-white font-semibold">Stall auto-trip &lt; 1200ms</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">Inter-Node UART Heartbeat Trip</span>
              <span className="text-white font-semibold">1500 ms (Node 2 Failsafe Stop)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
