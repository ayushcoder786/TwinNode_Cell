"""
TwinNode Hardware Serial Interface Service
Manages USB Virtual COM Port communication with STM32 microcontrollers.
Supports both ASCII telemetry stream (DATA,TEMP=25,HUM=58,DIST=45.20)
and binary protocol packet framing. Features auto-reconnect, error resilience,
and LED command dispatch with acknowledgment tracking.
"""

import threading
import time
import re
import serial
import serial.tools.list_ports
from typing import List, Dict, Any, Optional, Callable
from backend.app.core.protocol import Packet, PacketParser

# Regex to parse: DATA,TEMP=25,HUM=58,DIST=45.20 (tolerant to whitespace, floats, integers)
ASCII_TELEMETRY_REGEX = re.compile(
    r"DATA\s*,\s*TEMP\s*=\s*([+-]?\d+(?:\.\d+)?)\s*,\s*HUM\s*=\s*([+-]?\d+(?:\.\d+)?)\s*,\s*DIST\s*=\s*([+-]?\d+(?:\.\d+)?)",
    re.IGNORECASE
)

class SerialService:
    def __init__(
        self,
        on_packet_received: Optional[Callable[[Packet], None]] = None,
        on_telemetry_received: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.port: str = "COM3"
        self.baudrate: int = 115200
        self.serial_conn: Optional[serial.Serial] = None
        self.is_connected: bool = False
        self.is_reconnecting: bool = False
        self.auto_reconnect: bool = True
        self.last_error: Optional[str] = None
        
        # Parsers & Callbacks
        self.binary_parser = PacketParser()
        self.on_packet_received = on_packet_received
        self.on_telemetry_received = on_telemetry_received
        
        # Threads & Control
        self._rx_thread: Optional[threading.Thread] = None
        self._reconnect_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._line_buffer = bytearray()
        
        # Diagnostic Counters
        self.bytes_rx = 0
        self.bytes_tx = 0
        self.packets_rx = 0
        self.lines_rx = 0
        self.parse_errors = 0
        self.last_rx_time = 0.0
        self.last_raw_message = ""
        
        # Latest Parsed Snapshot
        self.latest_telemetry: Optional[Dict[str, Any]] = None
        
        # LED Actuator Command & ACK State
        self.last_led_command_sent: str = "ALL_OFF"
        self.last_led_command_time: float = 0.0
        self.last_led_ack_status: str = "IDLE"  # IDLE, ACK_RECEIVED, NO_ACK_TIMEOUT, ERROR
        self.has_physical_optical_feedback: bool = False

    @staticmethod
    def list_ports() -> List[Dict[str, Any]]:
        """Discover connected serial COM ports with ST-Link detection."""
        ports = []
        for port in serial.tools.list_ports.comports():
            desc = port.description or ""
            is_stlink = any(k in desc for k in ["STMicroelectronics", "STLink", "STM32", "Virtual COM Port"])
            ports.append({
                "device": port.device,
                "description": desc,
                "hwid": port.hwid or "",
                "is_stlink": is_stlink
            })
        return ports

    def connect(self, port: str = "COM3", baudrate: int = 115200) -> bool:
        """Connect to the specified serial port."""
        if self.is_connected and self.port == port:
            return True

        self.disconnect()
        self.port = port
        self.baudrate = baudrate
        self.last_error = None
        self._stop_event.clear()

        try:
            self.serial_conn = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=0.2,
                write_timeout=0.5
            )
            self.is_connected = True
            self.is_reconnecting = False
            self.last_error = None
            
            # Start background RX thread
            self._rx_thread = threading.Thread(
                target=self._read_loop,
                daemon=True,
                name="TwinNode-Serial-RX"
            )
            self._rx_thread.start()
            print(f"[SerialService] Successfully connected to {port} @ {baudrate} baud.")
            return True

        except serial.SerialException as se:
            err_msg = str(se)
            if "PermissionError" in err_msg or "Access is denied" in err_msg:
                self.last_error = f"Port {port} is locked by another application (e.g., PuTTY or terminal). Please close PuTTY to allow TwinNode Cell to connect."
            elif "FileNotFoundError" in err_msg or "cannot find the file" in err_msg:
                self.last_error = f"Port {port} not found. Ensure STM32 USB cable is securely connected."
            else:
                self.last_error = f"Serial connection error on {port}: {err_msg}"
            
            print(f"[SerialService] {self.last_error}")
            self.is_connected = False
            self.serial_conn = None
            
            if self.auto_reconnect:
                self._trigger_reconnect()
            return False

        except Exception as e:
            self.last_error = f"Unexpected error opening {port}: {e}"
            print(f"[SerialService] {self.last_error}")
            self.is_connected = False
            self.serial_conn = None
            return False

    def disconnect(self):
        """Cleanly close the serial connection and terminate worker threads."""
        self._stop_event.set()
        
        if self._rx_thread and self._rx_thread.is_alive():
            if threading.current_thread() != self._rx_thread:
                self._rx_thread.join(timeout=1.0)
            self._rx_thread = None

        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception:
                pass

        self.serial_conn = None
        self.is_connected = False
        print("[SerialService] Disconnected from serial port.")

    def send_led_command(self, cmd_state: str) -> bool:
        """
        Send LED command to STM32.
        Mapping:
          NORMAL_OPERATION / GREEN -> "LED:GREEN\\n"
          WARNING / YELLOW         -> "LED:YELLOW\\n"
          FAULT / RED              -> "LED:RED\\n"
          EMERGENCY_STOP / OFF     -> "LED:OFF\\n"
        """
        # Normalize command
        cmd_upper = cmd_state.upper()
        if "GREEN" in cmd_upper:
            command_str = "LED:GREEN\n"
        elif "YELLOW" in cmd_upper or "WARN" in cmd_upper:
            command_str = "LED:YELLOW\n"
        elif "RED" in cmd_upper or "FAULT" in cmd_upper:
            command_str = "LED:RED\n"
        else:
            command_str = "LED:OFF\n"

        self.last_led_command_sent = command_str.strip()
        self.last_led_command_time = time.time()
        self.last_led_ack_status = "SENT_WAITING_ACK"

        if not self.is_connected or not self.serial_conn:
            self.last_led_ack_status = "DISCONNECTED"
            return False

        try:
            payload = command_str.encode("utf-8")
            self.serial_conn.write(payload)
            self.serial_conn.flush()
            self.bytes_tx += len(payload)
            return True
        except Exception as e:
            print(f"[SerialService] LED command write error: {e}")
            self.last_led_ack_status = "WRITE_ERROR"
            self._handle_disconnect(f"Write error during LED command: {e}")
            return False

    def send_packet(self, packet: Packet) -> bool:
        """Send a binary protocol packet."""
        if not self.is_connected or not self.serial_conn:
            return False
            
        try:
            data = packet.serialize()
            self.serial_conn.write(data)
            self.serial_conn.flush()
            self.bytes_tx += len(data)
            self.packets_rx += 1
            return True
        except Exception as e:
            print(f"[SerialService] Packet write error: {e}")
            self._handle_disconnect(f"Write error: {e}")
            return False

    def parse_ascii_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse incoming ASCII line:
        DATA,TEMP=25,HUM=58,DIST=45.20
        Also checks for ACK lines: ACK,LED=GREEN or OK
        """
        clean_line = line.strip()
        if not clean_line:
            return None

        # Check for LED Acknowledgment
        if "ACK" in clean_line.upper() or clean_line.upper() == "OK":
            self.last_led_ack_status = f"ACK_RECEIVED: {clean_line}"
            return {
                "type": "ACK",
                "raw_message": clean_line,
                "timestamp": time.time()
            }

        # Check for DATA format
        match = ASCII_TELEMETRY_REGEX.search(clean_line)
        if match:
            try:
                temp_val = float(match.group(1))
                hum_val = float(match.group(2))
                dist_val = float(match.group(3))

                # Sensor validity envelope check:
                # Temperature: -20°C to 125°C
                # Humidity: 0% to 100%
                # HC-SR04 Distance: 2.0 cm to 400.0 cm
                temp_valid = -20.0 <= temp_val <= 125.0
                hum_valid = 0.0 <= hum_val <= 100.0
                dist_valid = 2.0 <= dist_val <= 400.0
                is_valid = temp_valid and hum_valid and dist_valid

                parsed = {
                    "type": "TELEMETRY",
                    "temperature": temp_val,
                    "humidity": hum_val,
                    "distance": dist_val,
                    "sensor_validity": is_valid,
                    "raw_message": clean_line,
                    "timestamp": time.time(),
                    "data_source": "REAL_HARDWARE"
                }
                return parsed
            except (ValueError, IndexError) as ex:
                self.parse_errors += 1
                return {
                    "type": "ERROR",
                    "error": f"Numeric conversion error: {ex}",
                    "raw_message": clean_line,
                    "timestamp": time.time()
                }

        # Fallback for unrecognized line
        self.parse_errors += 1
        return {
            "type": "UNRECOGNIZED",
            "raw_message": clean_line,
            "timestamp": time.time()
        }

    def _read_loop(self):
        """Continuous serial read loop with line buffering and binary packet fallback."""
        while not self._stop_event.is_set():
            if not self.serial_conn or not self.serial_conn.is_open:
                break
                
            try:
                waiting = self.serial_conn.in_waiting
                if waiting > 0:
                    raw = self.serial_conn.read(waiting)
                    self.bytes_rx += len(raw)
                    self.last_rx_time = time.time()

                    # 1. Binary Packet Parser Feed
                    binary_packets = self.binary_parser.feed(raw)
                    for pkt in binary_packets:
                        self.packets_rx += 1
                        if self.on_packet_received:
                            self.on_packet_received(pkt)

                    # 2. ASCII Line Buffering & Parsing
                    self._line_buffer.extend(raw)
                    while b"\n" in self._line_buffer:
                        idx = self._line_buffer.index(b"\n")
                        line_bytes = self._line_buffer[:idx]
                        self._line_buffer = self._line_buffer[idx + 1:]
                        
                        line_str = line_bytes.decode("utf-8", errors="replace").strip("\r")
                        if line_str:
                            self.lines_rx += 1
                            self.last_raw_message = line_str
                            parsed_data = self.parse_ascii_line(line_str)
                            
                            if parsed_data and parsed_data.get("type") == "TELEMETRY":
                                self.latest_telemetry = parsed_data
                                if self.on_telemetry_received:
                                    self.on_telemetry_received(parsed_data)
                else:
                    time.sleep(0.01)

            except serial.SerialException as se:
                print(f"[SerialService] Read loop error: {se}")
                self._handle_disconnect(f"Serial read error: {se}")
                break
            except Exception as e:
                print(f"[SerialService] Read loop unexpected error: {e}")
                self._handle_disconnect(f"Unexpected error: {e}")
                break

    def _handle_disconnect(self, reason: str):
        """Handle hardware disconnection or port drop."""
        self.is_connected = False
        self.last_error = reason
        print(f"[SerialService] Disconnection detected: {reason}")
        if self.auto_reconnect:
            self._trigger_reconnect()

    def _trigger_reconnect(self):
        """Start auto-reconnect background thread."""
        if self.is_reconnecting or self._stop_event.is_set():
            return

        self.is_reconnecting = True
        self._reconnect_thread = threading.Thread(
            target=self._reconnect_loop,
            daemon=True,
            name="TwinNode-Serial-Reconnect"
        )
        self._reconnect_thread.start()

    def _reconnect_loop(self):
        """Periodically attempts to reopen port when device becomes available."""
        print(f"[SerialService] Auto-reconnect started for {self.port}...")
        while not self._stop_event.is_set() and not self.is_connected:
            time.sleep(2.0)
            # Check if port exists in available ports
            available_ports = [p["device"] for p in self.list_ports()]
            if self.port in available_ports:
                print(f"[SerialService] Port {self.port} detected. Attempting to connect...")
                if self.connect(self.port, self.baudrate):
                    print(f"[SerialService] Auto-reconnect successful to {self.port}!")
                    break
        self.is_reconnecting = False

    def get_status(self) -> Dict[str, Any]:
        """Comprehensive status dictionary for diagnostics and UI."""
        return {
            "is_connected": self.is_connected,
            "is_reconnecting": self.is_reconnecting,
            "port": self.port,
            "baudrate": self.baudrate,
            "bytes_rx": self.bytes_rx,
            "bytes_tx": self.bytes_tx,
            "packets_rx": self.packets_rx,
            "lines_rx": self.lines_rx,
            "parse_errors": self.parse_errors,
            "last_rx_time": self.last_rx_time,
            "last_raw_message": self.last_raw_message,
            "latest_telemetry": self.latest_telemetry,
            "last_error": self.last_error,
            "last_led_command_sent": self.last_led_command_sent,
            "last_led_ack_status": self.last_led_ack_status,
            "has_physical_optical_feedback": self.has_physical_optical_feedback
        }
