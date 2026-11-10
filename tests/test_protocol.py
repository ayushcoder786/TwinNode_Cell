import pytest
from backend.app.core.protocol import (
    Packet,
    PacketParser,
    MsgType,
    FaultCode,
    calculate_crc16
)

def test_crc16_calculation():
    test_data = b"123456789"
    # Standard CCITT 0x1021 init 0xFFFF on "123456789" is 0x29B1
    crc = calculate_crc16(test_data)
    assert isinstance(crc, int)
    assert 0 <= crc <= 0xFFFF

def test_packet_setpoint_serialization_roundtrip():
    pkt = Packet.create_setpoint_cmd(
        seq_num=42,
        test_id=1001,
        target_temp=26.5,
        target_dist=30.0,
        target_motor_speed=75,
        target_servo_angle=120,
        flags=1
    )
    serialized = pkt.serialize()
    assert len(serialized) > 10
    assert serialized[0] == 0xAA
    assert serialized[1] == 0x55
    assert serialized[-2] == 0x0D
    assert serialized[-1] == 0x0A

    parser = PacketParser()
    parsed_list = parser.feed(serialized)
    assert len(parsed_list) == 1
    
    parsed = parsed_list[0]
    assert parsed.msg_type == MsgType.CMD_SETPOINT
    assert parsed.seq_num == 42
    assert parsed.test_id == 1001

    payload = parsed.parse_payload()
    assert payload["target_temp"] == pytest.approx(26.5, 0.01)
    assert payload["target_dist"] == pytest.approx(30.0, 0.1)
    assert payload["target_motor_speed"] == 75
    assert payload["target_servo_angle"] == 120

def test_packet_telemetry_serialization_roundtrip():
    pkt = Packet.create_telemetry(
        seq_num=10,
        test_id=2002,
        actual_temp=24.8,
        actual_dist=18.5,
        actual_motor_speed=-40,
        actual_servo_angle=85,
        status_flags=1,
        fault_code=FaultCode.NO_FAULT,
        loop_time_us=1250
    )
    serialized = pkt.serialize()
    parser = PacketParser()
    parsed_list = parser.feed(serialized)
    assert len(parsed_list) == 1
    
    parsed = parsed_list[0]
    assert parsed.msg_type == MsgType.TELEMETRY_DATA
    payload = parsed.parse_payload()
    assert payload["actual_temp"] == pytest.approx(24.8, 0.01)
    assert payload["actual_dist"] == pytest.approx(18.5, 0.1)
    assert payload["actual_motor_speed"] == -40
    assert payload["actual_servo_angle"] == 85
    assert payload["loop_time_us"] == 1250

def test_parser_corrupted_data_rejection():
    pkt = Packet.create_heartbeat(seq_num=1, test_id=100)
    data = bytearray(pkt.serialize())
    # Corrupt CRC
    data[-4] ^= 0xFF
    
    parser = PacketParser()
    parsed = parser.feed(bytes(data))
    assert len(parsed) == 0 # Corrupted frame must be dropped
