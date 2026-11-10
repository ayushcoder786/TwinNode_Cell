/**
  ******************************************************************************
  * @file           : test_generator.h
  * @brief          : Header for automated setpoint generation and sequence execution
  ******************************************************************************
  */

#ifndef __TEST_GENERATOR_H
#define __TEST_GENERATOR_H

#include "protocol.h"
#include <stdint.h>
#include <stdbool.h>

typedef enum {
    TEST_MODE_MANUAL,
    TEST_MODE_STEP_RESPONSE,
    TEST_MODE_OBSTACLE_APPROACH,
    TEST_MODE_THERMAL_SWEEP
} TestMode_t;

typedef struct {
    uint16_t   test_id;
    TestMode_t mode;
    bool       is_running;
    bool       is_paused;
    uint32_t   start_tick;
    uint32_t   step_tick;
    uint8_t    seq_num;
    
    /* Active Target Setpoints */
    float      target_temp;
    float      target_dist;
    int8_t     target_motor_speed;
    uint8_t    target_servo_angle;
    
    /* Last Received Telemetry */
    TelemetryPayload_t last_telemetry;
    uint32_t   last_telemetry_tick;
    bool       node2_connected;
    uint32_t   packets_sent;
    uint32_t   packets_received;
    uint32_t   crc_errors;
    uint32_t   timeouts;
} TestGenerator_t;

void TestGen_Init(TestGenerator_t *tg);
void TestGen_Update(TestGenerator_t *tg, uint32_t current_tick);
void TestGen_SetManualTargets(TestGenerator_t *tg, float temp, float dist, int8_t motor, uint8_t servo);
void TestGen_Start(TestGenerator_t *tg, uint16_t test_id, TestMode_t mode);
void TestGen_Stop(TestGenerator_t *tg);
void TestGen_EmergencyStop(TestGenerator_t *tg);

#endif /* __TEST_GENERATOR_H */
