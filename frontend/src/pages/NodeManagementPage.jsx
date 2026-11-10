import React, { useState, useEffect } from 'react';
import { useTwinNode } from '../context/TwinNodeContext';
import {
  Cpu,
  Terminal,
  Radio,
  RefreshCw,
  Zap,
  CheckCircle2,
  XCircle,
  Shield,
  Activity,
  AlertTriangle,
  Lightbulb,
  Sliders,
  Send
} from 'lucide-react';

export const NodeManagementPage = () => {
  const {
    latestTelemetry,
    simulationMode,
    setSimulationMode,
    hardwareStatus,
    connectHardware,
    disconnectHardware,
    dispatchHardwareLed
  } = useTwinNode();

  const [ports, setPorts] = useState([]);
  const [selectedPort, setSelectedPort] = useState('COM3');
  const [baudrate, setBaudrate] = useState(115200);
  const [isConnecting, setIsConnecting] = useState(false);
  const [errorNotice, setErrorNotice] = useState(null);
  const [ledCommandStatus, setLedCommandStatus] = useState(null);
  const [terminalLogs, setTerminalLogs] = useState([
    '[INIT] TwinNode Host Communications Initialized.',
    '[SYSTEM] Single STM32F446RE serial telemetry listener ready (COM3 @ 115200 baud).'
  ]);

  const fetchPorts = async () => {
    try {
      const res = await fetch('/api/ports');
      const data = await res.json();
      setPorts(data.ports || []);
      if (data.ports && data.ports.length > 0) {
        const found = data.ports.find(p => p.device === 'COM3') || data.ports[0];
        setSelectedPort(found.device);
      }
    } catch (err) {
      console.error('Failed to fetch ports:', err);
    }
  };

  useEffect(() => {
    fetchPorts();
  }, []);

  // Update terminal logs on incoming raw serial messages
  useEffect(() => {
    if (latestTelemetry.raw_message) {
      setTerminalLogs(prev => [
        `[RX] ${latestTelemetry.raw_message} (T=${latestTelemetry.actual_temp}°C, H=${latestTelemetry.humidity || 50}%, D=${latestTelemetry.actual_dist}cm)`,
        ...prev.slice(0, 35)
      ]);
    }
  }, [latestTelemetry.raw_message, latestTelemetry.timestamp]);

  const handleConnect = async () => {
    setIsConnecting(true);
    setErrorNotice(null);
    try {
      const res = await connectHardware(selectedPort, baudrate);
      if (res && res.status === 'CONNECTED') {
        setTerminalLogs(prev => [
          `[CONNECTED] Port ${selectedPort} opened successfully @ ${baudrate} baud. Data provenance: REAL_HARDWARE.`,
          ...prev.slice(0, 35)
        ]);
      } else {
        const msg = res?.detail || res?.message || 'Connection failed. Port busy or inaccessible.';
        setErrorNotice(msg);
        setTerminalLogs(prev => [`[ERROR] ${msg}`, ...prev.slice(0, 35)]);
      }
    } catch (err) {
      setErrorNotice(String(err));
    } finally {
      setIsConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await disconnectHardware();
      setTerminalLogs(prev => [
        `[DISCONNECTED] Port closed. Enforced safe output state (LED:OFF).`,
        ...prev.slice(0, 35)
      ]);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendLed = async (cmd) => {
    setLedCommandStatus(`Sending ${cmd}...`);
    try {
      const res = await dispatchHardwareLed(cmd);
      if (res) {
        setLedCommandStatus(`${cmd} -> Sent! (ACK: ${res.ack_status})`);
        setTerminalLogs(prev => [
          `[TX] ${cmd} dispatched. ACK Status: ${res.ack_status}`,
          ...prev.slice(0, 35)
        ]);
      }
    } catch (err) {
      setLedCommandStatus(`Error: ${err}`);
    }
  };

  const isConnected = hardwareStatus?.is_connected;

  return (
    <div className="space-y-6">
      {/* Hardware Connection Card */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-slate-800 pb-3 gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
              <Radio className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white font-mono">STM32 Physical Hardware Live Link</h2>
              <p className="text-xs text-slate-400">
                Direct USB Virtual COM Port communication (COM3 @ 115200 8N1). Continuous parsing of{' '}
                <code className="text-sky-300 bg-slate-900 px-1 py-0.5 rounded font-mono">DATA,TEMP=...,HUM=...,DIST=...</code>.
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={fetchPorts}
              className="flex items-center space-x-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs border border-slate-700 transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Scan Ports</span>
            </button>
          </div>
        </div>

        {/* PuTTY Warning Notice */}
        {errorNotice && (
          <div className="bg-rose-500/15 border border-rose-500/40 rounded-lg p-3 text-xs text-rose-300 flex items-start space-x-2.5">
            <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
            <div>
              <strong className="font-semibold block mb-0.5">Serial Port Access Error</strong>
              {errorNotice}
              {errorNotice.includes('PuTTY') && (
                <p className="mt-1 text-slate-300">
                  Tip: Windows grants exclusive lock on COM ports. Close the PuTTY terminal window and click <strong>Connect Hardware</strong> again.
                </p>
              )}
            </div>
          </div>
        )}

        {/* Port Controls */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1.5">SERIAL COM PORT</label>
            <select
              value={selectedPort}
              onChange={(e) => setSelectedPort(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
            >
              {ports.length === 0 ? (
                <option value="COM3">COM3 (Default STM32 ST-LINK)</option>
              ) : (
                ports.map((p) => (
                  <option key={p.device} value={p.device}>
                    {p.device} - {p.description} {p.is_stlink ? '(ST-LINK)' : ''}
                  </option>
                ))
              )}
            </select>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1.5">BAUD RATE</label>
            <select
              value={baudrate}
              onChange={(e) => setBaudrate(Number(e.target.value))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-sky-500"
            >
              <option value="115200">115200 baud (Default)</option>
              <option value="9600">9600 baud</option>
              <option value="57600">57600 baud</option>
              <option value="230400">230400 baud</option>
            </select>
          </div>

          <div>
            {!isConnected ? (
              <button
                onClick={handleConnect}
                disabled={isConnecting}
                className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold uppercase tracking-wider transition"
              >
                {isConnecting ? 'Connecting...' : 'Connect Hardware'}
              </button>
            ) : (
              <button
                onClick={handleDisconnect}
                className="w-full py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-bold uppercase tracking-wider transition"
              >
                Disconnect
              </button>
            )}
          </div>

          <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800 text-xs font-mono flex items-center justify-between">
            <span className="text-slate-400">LINK STATUS:</span>
            <span className={`font-bold flex items-center gap-1.5 ${isConnected ? 'text-emerald-400' : 'text-slate-500'}`}>
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
              {isConnected ? 'ONLINE (COM3)' : 'DISCONNECTED'}
            </span>
          </div>
        </div>

        {/* Live Physical Telemetry Strip */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          <div className="bg-slate-900/80 p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-mono text-slate-400">TEMPERATURE (DHT11 / LM35)</div>
            <div className="text-2xl font-bold font-mono text-rose-400 mt-1">
              {latestTelemetry.actual_temp !== undefined ? `${latestTelemetry.actual_temp.toFixed(1)} °C` : '--'}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Operating Envelope: -10°C to 80°C</div>
          </div>

          <div className="bg-slate-900/80 p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-mono text-slate-400">RELATIVE HUMIDITY (DHT11)</div>
            <div className="text-2xl font-bold font-mono text-cyan-400 mt-1">
              {latestTelemetry.humidity !== undefined ? `${latestTelemetry.humidity.toFixed(1)} %` : '58.0 %'}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Operating Envelope: 20% to 90% RH</div>
          </div>

          <div className="bg-slate-900/80 p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-mono text-slate-400">DISTANCE (HC-SR04 ULTRASONIC)</div>
            <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
              {latestTelemetry.actual_dist !== undefined ? `${latestTelemetry.actual_dist.toFixed(1)} cm` : '--'}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Operating Envelope: 2.0 to 400.0 cm</div>
          </div>
        </div>

        {/* Traffic Statistics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
          <div className="bg-slate-900/50 p-2.5 rounded border border-slate-800/80 flex justify-between">
            <span className="text-slate-500">LINES RX:</span>
            <span className="text-emerald-400 font-bold">{hardwareStatus?.lines_rx || 0}</span>
          </div>
          <div className="bg-slate-900/50 p-2.5 rounded border border-slate-800/80 flex justify-between">
            <span className="text-slate-500">BYTES RX:</span>
            <span className="text-white font-bold">{hardwareStatus?.bytes_rx || 0} B</span>
          </div>
          <div className="bg-slate-900/50 p-2.5 rounded border border-slate-800/80 flex justify-between">
            <span className="text-slate-500">PARSE ERRORS:</span>
            <span className="text-amber-400 font-bold">{hardwareStatus?.parse_errors || 0}</span>
          </div>
          <div className="bg-slate-900/50 p-2.5 rounded border border-slate-800/80 flex justify-between">
            <span className="text-slate-500">AUTO-RECONNECT:</span>
            <span className="text-sky-400 font-bold">ENABLED</span>
          </div>
        </div>
      </div>

      {/* Interactive LED Actuator Dispatch & Safety Priority */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <Lightbulb className="w-5 h-5 text-amber-400" />
            <h3 className="text-sm font-semibold text-white">STM32 Actuator LED Control & Closed-Loop Dispatch</h3>
          </div>
          <span className="text-xs font-mono text-slate-400">
            Current State: <strong className="text-white">{latestTelemetry.led_state || 'ALL_OFF'}</strong>
          </span>
        </div>

        <p className="text-xs text-slate-400">
          ML predictions automatically dispatch LED state over serial. You can also manually test transmission.
          <br />
          <span className="text-amber-400 font-semibold">Safety Interlock:</span> Emergency Stop unconditionally overrides ML and sets{' '}
          <code className="text-slate-300 bg-slate-900 px-1 rounded">LED:OFF</code>.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <button
            onClick={() => handleSendLed('LED:GREEN')}
            className="p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 font-mono text-xs font-bold transition flex items-center justify-center gap-1.5"
          >
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
            LED:GREEN (Nominal)
          </button>

          <button
            onClick={() => handleSendLed('LED:YELLOW')}
            className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 font-mono text-xs font-bold transition flex items-center justify-center gap-1.5"
          >
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            LED:YELLOW (Warning)
          </button>

          <button
            onClick={() => handleSendLed('LED:RED')}
            className="p-3 rounded-lg border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 font-mono text-xs font-bold transition flex items-center justify-center gap-1.5"
          >
            <span className="w-2.5 h-2.5 rounded-full bg-rose-400" />
            LED:RED (Fault)
          </button>

          <button
            onClick={() => handleSendLed('LED:OFF')}
            className="p-3 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-xs font-bold transition flex items-center justify-center gap-1.5"
          >
            <span className="w-2.5 h-2.5 rounded-full bg-slate-500" />
            LED:OFF (Safe State)
          </button>
        </div>

        {ledCommandStatus && (
          <div className="text-xs font-mono text-sky-400 bg-slate-900/80 p-2.5 rounded border border-slate-800 flex items-center justify-between">
            <span>{ledCommandStatus}</span>
            <span className="text-[10px] text-slate-400 font-normal">
              Software command ACK tracking only; physical LED optical feedback not fitted.
            </span>
          </div>
        )}
      </div>

      {/* Live Terminal & Serial Message Console */}
      <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-white">Live Serial Telemetry Stream (COM3)</h3>
          </div>
          <button
            onClick={() => setTerminalLogs([])}
            className="text-[11px] text-slate-400 hover:text-white font-mono"
          >
            Clear Console
          </button>
        </div>

        <div className="bg-black/90 rounded-lg p-3.5 font-mono text-xs text-emerald-400 h-52 overflow-y-auto space-y-1 border border-slate-800">
          {terminalLogs.map((log, i) => (
            <div key={i} className="leading-relaxed">
              <span className="text-slate-500 select-none mr-2">&gt;</span>
              {log}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
