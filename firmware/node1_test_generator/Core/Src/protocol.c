/**
  ******************************************************************************
  * @file           : protocol.c
  * @brief          : TwinNode Protocol implementation for STM32 HAL
  ******************************************************************************
  */

#include "protocol.h"
#include <string.h>

/* Parser State Machine */
typedef enum {
    STATE_WAIT_SOF1,
    STATE_WAIT_SOF2,
    STATE_GET_LEN,
    STATE_GET_TYPE,
    STATE_GET_SEQ,
    STATE_GET_TEST_ID_L,
    STATE_GET_TEST_ID_H,
    STATE_GET_PAYLOAD,
    STATE_GET_CRC_L,
    STATE_GET_CRC_H,
    STATE_WAIT_EOF1,
    STATE_WAIT_EOF2
} ParserState_t;

static ParserState_t rx_state = STATE_WAIT_SOF1;
static ProtocolPacket_t current_rx_pkt;
static uint8_t payload_idx = 0;
static uint8_t raw_crc_low = 0;

uint16_t Protocol_CalculateCRC16(const uint8_t *data, uint16_t length)
{
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < length; i++) {
        crc ^= ((uint16_t)data[i]) << 8;
        for (uint8_t bit = 0; bit < 8; bit++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc = crc << 1;
            }
        }
    }
    return crc;
}

uint16_t Protocol_SerializePacket(const ProtocolPacket_t *pkt, uint8_t *tx_buffer)
{
    if (!pkt || !tx_buffer) return 0;

    uint16_t idx = 0;
    tx_buffer[idx++] = SOF_BYTE1;
    tx_buffer[idx++] = SOF_BYTE2;
    tx_buffer[idx++] = pkt->payload_len;
    tx_buffer[idx++] = pkt->msg_type;
    tx_buffer[idx++] = pkt->seq_num;
    tx_buffer[idx++] = (uint8_t)(pkt->test_id & 0xFF);
    tx_buffer[idx++] = (uint8_t)((pkt->test_id >> 8) & 0xFF);

    if (pkt->payload_len > 0 && pkt->payload_len <= PROTOCOL_MAX_PAYLOAD) {
        memcpy(&tx_buffer[idx], pkt->payload, pkt->payload_len);
        idx += pkt->payload_len;
    }

    /* CRC is computed over Header (Len, Type, Seq, TestID) + Payload */
    uint16_t crc = Protocol_CalculateCRC16(&tx_buffer[2], idx - 2);
    tx_buffer[idx++] = (uint8_t)(crc & 0xFF);
    tx_buffer[idx++] = (uint8_t)((crc >> 8) & 0xFF);

    tx_buffer[idx++] = EOF_BYTE1;
    tx_buffer[idx++] = EOF_BYTE2;

    return idx;
}

void Protocol_InitParser(void)
{
    rx_state = STATE_WAIT_SOF1;
    payload_idx = 0;
    memset(&current_rx_pkt, 0, sizeof(current_rx_pkt));
}

bool Protocol_ParseByte(uint8_t byte, ProtocolPacket_t *out_pkt)
{
    switch (rx_state) {
        case STATE_WAIT_SOF1:
            if (byte == SOF_BYTE1) rx_state = STATE_WAIT_SOF2;
            break;

        case STATE_WAIT_SOF2:
            if (byte == SOF_BYTE2) rx_state = STATE_GET_LEN;
            else if (byte != SOF_BYTE1) rx_state = STATE_WAIT_SOF1;
            break;

        case STATE_GET_LEN:
            if (byte <= PROTOCOL_MAX_PAYLOAD) {
                current_rx_pkt.payload_len = byte;
                rx_state = STATE_GET_TYPE;
            } else {
                rx_state = STATE_WAIT_SOF1;
            }
            break;

        case STATE_GET_TYPE:
            current_rx_pkt.msg_type = byte;
            rx_state = STATE_GET_SEQ;
            break;

        case STATE_GET_SEQ:
            current_rx_pkt.seq_num = byte;
            rx_state = STATE_GET_TEST_ID_L;
            break;

        case STATE_GET_TEST_ID_L:
            current_rx_pkt.test_id = byte;
            rx_state = STATE_GET_TEST_ID_H;
            break;

        case STATE_GET_TEST_ID_H:
            current_rx_pkt.test_id |= ((uint16_t)byte << 8);
            payload_idx = 0;
            if (current_rx_pkt.payload_len > 0) {
                rx_state = STATE_GET_PAYLOAD;
            } else {
                rx_state = STATE_GET_CRC_L;
            }
            break;

        case STATE_GET_PAYLOAD:
            current_rx_pkt.payload[payload_idx++] = byte;
            if (payload_idx >= current_rx_pkt.payload_len) {
                rx_state = STATE_GET_CRC_L;
            }
            break;

        case STATE_GET_CRC_L:
            raw_crc_low = byte;
            rx_state = STATE_GET_CRC_H;
            break;

        case STATE_GET_CRC_H:
            current_rx_pkt.crc16 = (uint16_t)raw_crc_low | ((uint16_t)byte << 8);
            rx_state = STATE_WAIT_EOF1;
            break;

        case STATE_WAIT_EOF1:
            if (byte == EOF_BYTE1) rx_state = STATE_WAIT_EOF2;
            else rx_state = STATE_WAIT_SOF1;
            break;

        case STATE_WAIT_EOF2:
            rx_state = STATE_WAIT_SOF1;
            if (byte == EOF_BYTE2) {
                /* Verify CRC */
                uint8_t check_buf[4 + PROTOCOL_MAX_PAYLOAD];
                check_buf[0] = current_rx_pkt.payload_len;
                check_buf[1] = current_rx_pkt.msg_type;
                check_buf[2] = current_rx_pkt.seq_num;
                check_buf[3] = (uint8_t)(current_rx_pkt.test_id & 0xFF);
                check_buf[4] = (uint8_t)((current_rx_pkt.test_id >> 8) & 0xFF);
                if (current_rx_pkt.payload_len > 0) {
                    memcpy(&check_buf[5], current_rx_pkt.payload, current_rx_pkt.payload_len);
                }

                uint16_t calculated = Protocol_CalculateCRC16(check_buf, 5 + current_rx_pkt.payload_len);
                if (calculated == current_rx_pkt.crc16) {
                    if (out_pkt) {
                        memcpy(out_pkt, &current_rx_pkt, sizeof(ProtocolPacket_t));
                    }
                    return true;
                }
            }
            break;

        default:
            rx_state = STATE_WAIT_SOF1;
            break;
    }
    return false;
}
