import React, { createContext, useContext, useState, useEffect, useRef } from 'react';

const TwinNodeContext = createContext(null);

export const TwinNodeProvider = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [simulationMode, setSimulationModeState] = useState(true);
  const [testStatus, setTestStatus] = useState('IDLE'); // IDLE, RUNNING, PAUSED, STOPPED
  const [activeTestId, setActiveTestId] = useState(1001);
  const [activeTestName, setActiveTestName] = useState('BENCH_VALIDATION_01');
  const [activeProfile, setActiveProfile] = useState('STANDARD_INDUSTRIAL');
  
  const [currentTarget, setCurrentTarget] = useState({
    target_temp: 25.0,
    target_dist: 25.0,
    target_motor_speed: 0,
    target_servo_angle: 90
  });

  const [ledState, setLedState] = useState('GREEN_ON');
  const [latestPrediction, setLatestPrediction] = useState({
    predicted_label: 'NORMAL_OPERATION',
    confidence: 0.99,
    anomaly_score: 0.01,
    is_anomaly: false,
    suggested_led: 'GREEN_ON',
    fault_type: 'NOMINAL',
    recommended_action: 'System operating nominally.',
    data_source: 'SIMULATION'
  });
  const [mlPredictionHistory, setMlPredictionHistory] = useState([]);

  const [hardwareStatus, setHardwareStatus] = useState({
    is_connected: false,
    is_reconnecting: false,
    port: 'COM3',
    baudrate: 115200,
    bytes_rx: 0,
    bytes_tx: 0,
    lines_rx: 0,
    last_raw_message: '',
    last_error: null,
    last_led_command_sent: 'ALL_OFF',
    last_led_ack_status: 'IDLE'
  });

  const [latestTelemetry, setLatestTelemetry] = useState({
    timestamp: Date.now() / 1000,
    node1_status: 'ONLINE',
    node2_status: 'ONLINE',
    target_temp: 25.0,
    actual_temp: 24.5,
    humidity: 50.0,
    target_dist: 25.0,
    actual_dist: 25.0,
    target_motor_speed: 0,
    actual_motor_speed: 0,
    target_servo_angle: 90,
    actual_servo_angle: 90,
    comm_latency_ms: 12.5,
    fault_code: 0,
    is_simulated: true,
    led_state: 'GREEN_ON',
    raw_message: '',
    data_source: 'SIMULATION'
  });

  const [telemetryHistory, setTelemetryHistory] = useState([]);
  const [activeFaults, setActiveFaults] = useState([]);
  const [faultHistory, setFaultHistory] = useState([]);
  const [sampleCount, setSampleCount] = useState(0);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Initialize and connect WebSocket
  useEffect(() => {
    let unmounted = false;

    const connectWebSocket = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (unmounted) return;
        setIsConnected(true);
        console.log('[TwinNode WS] Connected to backend stream.');
      };

      ws.onmessage = (event) => {
        if (unmounted) return;
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'INIT_STATE') {
            setSimulationModeState(data.simulation_mode);
            setTestStatus(data.test_status);
            setActiveTestId(data.active_test_id);
            setActiveTestName(data.active_test_name);
            if (data.current_target) setCurrentTarget(data.current_target);
            if (data.latest_telemetry) setLatestTelemetry(data.latest_telemetry);
            if (data.latest_prediction) setLatestPrediction(data.latest_prediction);
            if (data.led_state) setLedState(data.led_state);
            if (data.active_faults) setActiveFaults(data.active_faults);
            if (data.active_profile) setActiveProfile(data.active_profile);
            if (data.hardware_status) setHardwareStatus(data.hardware_status);
          } else if (data.type === 'TELEMETRY_UPDATE') {
            const tel = data.telemetry;
            setLatestTelemetry(tel);
            setTestStatus(data.test_status);
            if (data.hardware_status) setHardwareStatus(data.hardware_status);
            if (data.latest_prediction) {
              setLatestPrediction(data.latest_prediction);
              setMlPredictionHistory(prev => [data.latest_prediction, ...prev].slice(0, 40));
            }
            if (data.led_state) setLedState(data.led_state);
            if (data.active_faults) {
              setActiveFaults(data.active_faults);
              // Append newly active faults to history
              data.active_faults.forEach(f => {
                setFaultHistory(prev => {
                  if (!prev.some(item => item.fault_code === f.fault_code && Math.abs(item.timestamp - f.timestamp) < 2)) {
                    return [f, ...prev].slice(0, 50);
                  }
                  return prev;
                });
              });
            }
            if (data.sample_count !== undefined) setSampleCount(data.sample_count);
            if (data.active_test_id !== undefined) setActiveTestId(data.active_test_id);


            // Maintain rolling buffer of 35 samples for charts
            setTelemetryHistory(prev => {
              const timeLabel = new Date((tel.timestamp || Date.now() / 1000) * 1000).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
              const point = {
                time: timeLabel,
                timestamp: tel.timestamp,
                target_temp: tel.target_temp,
                actual_temp: tel.actual_temp,
                target_dist: tel.target_dist,
                actual_dist: tel.actual_dist,
                target_motor: tel.target_motor_speed,
                actual_motor: tel.actual_motor_speed,
                target_servo: tel.target_servo_angle,
                actual_servo: tel.actual_servo_angle,
                latency: tel.comm_latency_ms
              };
              return [...prev, point].slice(-35);
            });
          }
        } catch (err) {
          console.error('[TwinNode WS] Parse error:', err);
        }
      };

      ws.onclose = () => {
        if (unmounted) return;
        setIsConnected(false);
        console.warn('[TwinNode WS] Disconnected. Reconnecting in 2s...');
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 2000);
      };

      ws.onerror = (err) => {
        console.error('[TwinNode WS] Socket error:', err);
        ws.close();
      };
    };

    connectWebSocket();

    return () => {
      unmounted = true;
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, []);

  // REST API Actions
  const startTest = async (name, profile, targets) => {
    try {
      const res = await fetch('/api/test/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, profile, targets })
      });
      const data = await res.json();
      setTestStatus('RUNNING');
      setActiveTestId(data.test_id);
      setActiveTestName(name);
      return data;
    } catch (err) {
      console.error('Failed to start test:', err);
    }
  };

  const pauseTest = async () => {
    try {
      await fetch('/api/test/pause', { method: 'POST' });
      setTestStatus('PAUSED');
    } catch (err) {
      console.error('Failed to pause test:', err);
    }
  };

  const resumeTest = async () => {
    try {
      await fetch('/api/test/resume', { method: 'POST' });
      setTestStatus('RUNNING');
    } catch (err) {
      console.error('Failed to resume test:', err);
    }
  };

  const stopTest = async () => {
    try {
      await fetch('/api/test/stop', { method: 'POST' });
      setTestStatus('STOPPED');
    } catch (err) {
      console.error('Failed to stop test:', err);
    }
  };

  const resetTest = async () => {
    try {
      await fetch('/api/test/reset', { method: 'POST' });
      setTestStatus('IDLE');
      setActiveFaults([]);
      setTelemetryHistory([]);
    } catch (err) {
      console.error('Failed to reset test:', err);
    }
  };

  const emergencyStop = async () => {
    try {
      const res = await fetch('/api/test/emergency_stop', { method: 'POST' });
      const data = await res.json();
      setTestStatus('STOPPED');
      if (data.fault) {
        setActiveFaults(prev => [data.fault, ...prev]);
      }
    } catch (err) {
      console.error('Failed to trigger emergency stop:', err);
    }
  };

  const updateSetpoints = async (newTargets) => {
    setCurrentTarget(prev => ({ ...prev, ...newTargets }));
    try {
      await fetch('/api/test/setpoints', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTargets)
      });
    } catch (err) {
      console.error('Failed to update setpoints:', err);
    }
  };

  const setSimulationMode = async (enabled) => {
    try {
      const res = await fetch('/api/mode/simulation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled })
      });
      const data = await res.json();
      setSimulationModeState(data.simulation_mode);
    } catch (err) {
      console.error('Failed to toggle simulation mode:', err);
    }
  };

  const acknowledgeFault = async (faultCode) => {
    try {
      await fetch('/api/faults/acknowledge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fault_code: faultCode })
      });
      setActiveFaults(prev => prev.map(f => f.fault_code === faultCode ? { ...f, is_acknowledged: true } : f));
    } catch (err) {
      console.error('Failed to acknowledge fault:', err);
    }
  };

  const resetFaults = async () => {
    try {
      await fetch('/api/faults/reset', { method: 'POST' });
      setActiveFaults([]);
    } catch (err) {
      console.error('Failed to reset faults:', err);
    }
  };

  const injectSimulationFault = async (faultKey, state) => {
    try {
      const res = await fetch('/api/simulation/fault_injection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fault_key: faultKey, state })
      });
      return await res.json();
    } catch (err) {
      console.error('Failed to inject simulation fault:', err);
    }
  };

  const actuateLED = async (state, duty = 100) => {
    try {
      const res = await fetch('/api/ml/actuate-led', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state, pwm_duty_cycle: duty })
      });
      const data = await res.json();
      if (data.status === 'COMMAND_DISPATCHED') {
        setLedState(state);
      }
      return data;
    } catch (err) {
      console.error('Failed to actuate LED:', err);
    }
  };

  const connectHardware = async (port = 'COM3', baudrate = 115200) => {
    try {
      const res = await fetch('/api/hardware/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ port, baudrate })
      });
      const data = await res.json();
      if (res.ok) {
        setSimulationModeState(false);
      }
      return data;
    } catch (err) {
      console.error('Failed to connect hardware:', err);
      return { status: 'ERROR', detail: String(err) };
    }
  };

  const disconnectHardware = async () => {
    try {
      const res = await fetch('/api/hardware/disconnect', { method: 'POST' });
      const data = await res.json();
      return data;
    } catch (err) {
      console.error('Failed to disconnect hardware:', err);
    }
  };

  const dispatchHardwareLed = async (command) => {
    try {
      const res = await fetch('/api/hardware/led-command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command })
      });
      return await res.json();
    } catch (err) {
      console.error('Failed to dispatch LED command:', err);
    }
  };

  const fetchHardwareStatus = async () => {
    try {
      const res = await fetch('/api/hardware/status');
      const data = await res.json();
      if (data.serial) {
        setHardwareStatus(data.serial);
      }
      return data;
    } catch (err) {
      console.error('Failed to fetch hardware status:', err);
    }
  };

  return (
    <TwinNodeContext.Provider value={{
      isConnected,
      simulationMode,
      hardwareStatus,
      connectHardware,
      disconnectHardware,
      dispatchHardwareLed,
      fetchHardwareStatus,
      testStatus,
      activeTestId,
      activeTestName,
      activeProfile,
      currentTarget,
      latestTelemetry,
      telemetryHistory,
      activeFaults,
      faultHistory,
      sampleCount,
      latestPrediction,
      ledState,
      mlPredictionHistory,
      actuateLED,
      startTest,
      pauseTest,
      resumeTest,
      stopTest,
      resetTest,
      emergencyStop,
      updateSetpoints,
      setSimulationMode,
      acknowledgeFault,
      resetFaults,
      injectSimulationFault
    }}>
      {children}
    </TwinNodeContext.Provider>
  );

};

export const useTwinNode = () => {
  const context = useContext(TwinNodeContext);
  if (!context) {
    throw new Error('useTwinNode must be used within a TwinNodeProvider');
  }
  return context;
};
