"""
TwinNode Binary & ASCII Communication Protocol
Implements packet framing, validation, CRC16-CCITT, serialization, and deserialization.
"""

import struct
from enum import IntEnum
from typing import Optional, Tuple, Dict, Any
import json

SOF_BYTE1 = 0xAA
SOF_BYTE2 = 0x55
EOF_BYTE1 = 0x0D
EOF_BYTE2 = 0x0A

class MsgType(IntEnum):
    CMD_SETPOINT = 0x01
    TELEMETRY_DATA = 0x02
    ACK = 0x03
    NACK = 0x04
    HEARTBEAT = 0x05
    EMERGENCY_STOP = 0x06
    FAULT_ALERT = 0x07
    RESET_CMD = 0x08
    CONFIG_PARAM = 0x09

class FaultCode(IntEnum):
    NO_FAULT = 0x00
    SETPOINT_DEVIATION = 0x01
    ACTUATOR_RESPONSE_FAILURE = 0x02
    SENSOR_OUT_OF_RANGE = 0x03
    SENSOR_DISCONNECTED = 0x04
    COMMUNICATION_TIMEOUT = 0x05
    UNEXPECTED_RESPONSE = 0x06
    EMERGENCY_STOP = 0x07
    EQ_15_09_TRIGGERED = 0x09
    GENERAL_FAULT = 0xFF

def calculate_crc16(data: bytes, init: int = 0xFFFF) -> int:
    """CRC16-CCITT calculation matching STM32 hardware/firmware calculation."""
    crc = init
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

class Packet:
    def __init__(
        self,
        msg_type: MsgType,
        seq_num: int,
        test_id: int,
        payload: bytes = b"",
    ):
        self.msg_type = MsgType(msg_type)
        self.seq_num = seq_num & 0xFF
        self.test_id = test_id & 0xFFFF
        self.payload = payload

    def serialize(self) -> bytes:
        """
        Frame format:
        [SOF1(0xAA)][SOF2(0x55)][LEN(1B)][TYPE(1B)][SEQ(1B)][TEST_ID(2B,LE)][PAYLOAD(NB)][CRC16(2B,LE)][EOF1(0x0D)][EOF2(0x0A)]
        """
        payload_len = len(self.payload)
        header_and_body = struct.pack(
            "<BBBH",
            payload_len,
            int(self.msg_type),
            self.seq_num,
            self.test_id
        ) + self.payload
        
        crc = calculate_crc16(header_and_body)
        crc_bytes = struct.pack("<H", crc)
        
        return bytes([SOF_BYTE1, SOF_BYTE2]) + header_and_body + crc_bytes + bytes([EOF_BYTE1, EOF_BYTE2])

    @classmethod
    def create_setpoint_cmd(
        cls,
        seq_num: int,
        test_id: int,
        target_temp: float,
        target_dist: float,
        target_motor_speed: int,
        target_servo_angle: int,
        flags: int = 0
    ) -> "Packet":
        """
        Payload structure (10 bytes):
        - target_temp: int16 (temp * 100)
        - target_dist: int16 (dist * 10)
        - target_motor_speed: int8 (-100 to 100)
        - target_servo_angle: uint8 (0 to 180)
        - flags: uint16
        """
        temp_scaled = int(round(target_temp * 100))
        dist_scaled = int(round(target_dist * 10))
        motor_speed = max(-100, min(100, target_motor_speed))
        servo_angle = max(0, min(180, target_servo_angle))
        
        payload = struct.pack(
            "<hhbBH",
            temp_scaled,
            dist_scaled,
            motor_speed,
            servo_angle,
            flags
        )
        return cls(MsgType.CMD_SETPOINT, seq_num, test_id, payload)

    @classmethod
    def create_telemetry(
        cls,
        seq_num: int,
        test_id: int,
        actual_temp: float,
        actual_dist: float,
        actual_motor_speed: int,
        actual_servo_angle: int,
        status_flags: int = 0,
        fault_code: FaultCode = FaultCode.NO_FAULT,
        loop_time_us: int = 0
    ) -> "Packet":
        """
        Telemetry Payload structure (12 bytes):
        - actual_temp: int16 (temp * 100)
        - actual_dist: int16 (dist * 10)
        - actual_motor_speed: int8 (-100 to 100)
        - actual_servo_angle: uint8 (0 to 180)
        - status_flags: uint8
        - fault_code: uint8
        - loop_time_us: uint16
        """
        temp_scaled = int(round(actual_temp * 100))
        dist_scaled = int(round(actual_dist * 10))
        payload = struct.pack(
            "<hhbBBBH",
            temp_scaled,
            dist_scaled,
            actual_motor_speed,
            actual_servo_angle,
            status_flags,
            int(fault_code),
            loop_time_us
        )
        return cls(MsgType.TELEMETRY_DATA, seq_num, test_id, payload)

    @classmethod
    def create_heartbeat(cls, seq_num: int, test_id: int, node_id: int = 1) -> "Packet":
        payload = struct.pack("<B", node_id)
        return cls(MsgType.HEARTBEAT, seq_num, test_id, payload)

    @classmethod
    def create_emergency_stop(cls, seq_num: int, test_id: int, reason_code: int = 1) -> "Packet":
        payload = struct.pack("<B", reason_code)
        return cls(MsgType.EMERGENCY_STOP, seq_num, test_id, payload)

    @classmethod
    def create_ack(cls, seq_num: int, test_id: int, acked_seq: int) -> "Packet":
        payload = struct.pack("<B", acked_seq)
        return cls(MsgType.ACK, seq_num, test_id, payload)

    def parse_payload(self) -> Dict[str, Any]:
        """Decode typed payload into friendly dictionary."""
        if self.msg_type == MsgType.CMD_SETPOINT and len(self.payload) >= 8:
            temp_scaled, dist_scaled, motor_speed, servo_angle, flags = struct.unpack("<hhbBH", self.payload[:8])
            return {
                "target_temp": temp_scaled / 100.0,
                "target_dist": dist_scaled / 10.0,
                "target_motor_speed": motor_speed,
                "target_servo_angle": servo_angle,
                "flags": flags
            }
        elif self.msg_type == MsgType.TELEMETRY_DATA and len(self.payload) >= 10:
            temp_scaled, dist_scaled, motor_speed, servo_angle, status_flags, fault_code, loop_time = struct.unpack("<hhbBBBH", self.payload[:10])
            return {
                "actual_temp": temp_scaled / 100.0,
                "actual_dist": dist_scaled / 10.0,
                "actual_motor_speed": motor_speed,
                "actual_servo_angle": servo_angle,
                "status_flags": status_flags,
                "fault_code": FaultCode(fault_code) if fault_code in FaultCode._value2member_map_ else fault_code,
                "loop_time_us": loop_time
            }
        elif self.msg_type == MsgType.HEARTBEAT and len(self.payload) >= 1:
            return {"node_id": self.payload[0]}
        elif self.msg_type == MsgType.EMERGENCY_STOP and len(self.payload) >= 1:
            return {"reason_code": self.payload[0]}
        elif self.msg_type == MsgType.ACK and len(self.payload) >= 1:
            return {"acked_seq": self.payload[0]}
        return {"raw_payload": self.payload.hex()}


class PacketParser:
    """Stream parser for serial bytes with state machine and buffering."""
    def __init__(self):
        self.buffer = bytearray()
        self.ascii_buffer = ""

    def feed(self, data: bytes) -> list[Packet]:
        packets = []
        self.buffer.extend(data)

        # Process binary framed packets
        while len(self.buffer) >= 9: # minimum valid packet size
            # Look for SOF
            sof_idx = -1
            for i in range(len(self.buffer) - 1):
                if self.buffer[i] == SOF_BYTE1 and self.buffer[i+1] == SOF_BYTE2:
                    sof_idx = i
                    break
            
            if sof_idx == -1:
                # Keep last byte in case it's SOF_BYTE1
                if len(self.buffer) > 0 and self.buffer[-1] == SOF_BYTE1:
                    self.buffer = self.buffer[-1:]
                else:
                    self.buffer.clear()
                break
            
            if sof_idx > 0:
                # Discard noise before SOF
                del self.buffer[:sof_idx]

            # Buffer now starts with SOF1, SOF2
            if len(self.buffer) < 5:
                break # Need more data for header

            payload_len = self.buffer[2]
            expected_total_len = 2 + 1 + 1 + 1 + 2 + payload_len + 2 + 2 # SOF(2)+LEN(1)+TYPE(1)+SEQ(1)+ID(2)+PAYLOAD(N)+CRC(2)+EOF(2)
            
            if len(self.buffer) < expected_total_len:
                break # Wait for full packet

            # Check EOF
            if self.buffer[expected_total_len - 2] != EOF_BYTE1 or self.buffer[expected_total_len - 1] != EOF_BYTE2:
                # Malformed frame: skip SOF and search again
                del self.buffer[:2]
                continue

            # Extract frame body
            header_and_body = bytes(self.buffer[2:expected_total_len - 4])
            received_crc = struct.unpack("<H", self.buffer[expected_total_len - 4:expected_total_len - 2])[0]
            calc_crc = calculate_crc16(header_and_body)

            if received_crc == calc_crc:
                msg_type = MsgType(self.buffer[3])
                seq_num = self.buffer[4]
                test_id = struct.unpack("<H", self.buffer[5:7])[0]
                payload = bytes(self.buffer[7:7 + payload_len])
                
                packet = Packet(msg_type, seq_num, test_id, payload)
                packets.append(packet)
                del self.buffer[:expected_total_len]
            else:
                # CRC mismatch, discard header and resume
                del self.buffer[:2]

        return packets
