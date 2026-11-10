/**
  ******************************************************************************
  * @file           : protocol.h
  * @brief          : TwinNode Protocol definitions for Node 2
  ******************************************************************************
  */

#ifndef __PROTOCOL_H
#define __PROTOCOL_H

#include <stdint.h>
#include <stdbool.h>

#define SOF_BYTE1   0xAA
#define SOF_BYTE2   0x55
#define EOF_BYTE1   0x0D
#define EOF_BYTE2   0x0A

#define PROTOCOL_MAX_PAYLOAD 32

typedef enum {
    MSG_CMD_SETPOINT    = 0x01,
    MSG_TELEMETRY_DATA  = 0x02,
    MSG_ACK             = 0x03,
    MSG_NACK            = 0x04,
    MSG_HEARTBEAT       = 0x05,
    MSG_EMERGENCY_STOP  = 0x06,
    MSG_FAULT_ALERT     = 0x07,
    MSG_RESET_CMD       = 0x08
} MsgType_t;

typedef enum {
    FAULT_NONE                  = 0x00,
    FAULT_SETPOINT_DEVIATION    = 0x01,
    FAULT_ACTUATOR_STALL        = 0x02,
    FAULT_SENSOR_OUT_OF_RANGE   = 0x03,
    FAULT_SENSOR_DISCONNECTED   = 0x04,
    FAULT_COMM_TIMEOUT          = 0x05,
    FAULT_UNEXPECTED_RESPONSE   = 0x06,
    FAULT_EMERGENCY_STOP        = 0x07,
    FAULT_EQ_15_09_TRIGGERED    = 0x09
} FaultCode_t;

#pragma pack(push, 1)
typedef struct {
    int16_t  target_temp_scaled;
    int16_t  target_dist_scaled;
    int8_t   target_motor_speed;
    uint8_t  target_servo_angle;
    uint16_t flags;
} SetpointPayload_t;

typedef struct {
    int16_t  actual_temp_scaled;
    int16_t  actual_dist_scaled;
    int8_t   actual_motor_speed;
    uint8_t  actual_servo_angle;
    uint8_t  status_flags;
    uint8_t  fault_code;
    uint16_t loop_time_us;
} TelemetryPayload_t;
#pragma pack(pop)

typedef struct {
    uint8_t  payload_len;
    uint8_t  msg_type;
    uint8_t  seq_num;
    uint16_t test_id;
    uint8_t  payload[PROTOCOL_MAX_PAYLOAD];
    uint16_t crc16;
} ProtocolPacket_t;

uint16_t Protocol_CalculateCRC16(const uint8_t *data, uint16_t length);
uint16_t Protocol_SerializePacket(const ProtocolPacket_t *pkt, uint8_t *tx_buffer);
bool     Protocol_ParseByte(uint8_t byte, ProtocolPacket_t *out_pkt);
void     Protocol_InitParser(void);

#endif /* __PROTOCOL_H */
