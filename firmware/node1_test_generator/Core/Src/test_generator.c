/**
  ******************************************************************************
  * @file           : test_generator.c
  * @brief          : Automated test generator and profile sequence logic
  ******************************************************************************
  */

#include "test_generator.h"

void TestGen_Init(TestGenerator_t *tg)
{
    if (!tg) return;
    tg->test_id = 1001;
    tg->mode = TEST_MODE_MANUAL;
    tg->is_running = false;
    tg->is_paused = false;
    tg->start_tick = 0;
    tg->step_tick = 0;
    tg->seq_num = 0;
    
    tg->target_temp = 25.0f;
    tg->target_dist = 25.0f;
    tg->target_motor_speed = 0;
    tg->target_servo_angle = 90;
    
    tg->node2_connected = false;
    tg->last_telemetry_tick = 0;
    tg->packets_sent = 0;
    tg->packets_received = 0;
    tg->crc_errors = 0;
    tg->timeouts = 0;
}

void TestGen_Start(TestGenerator_t *tg, uint16_t test_id, TestMode_t mode)
{
    if (!tg) return;
    tg->test_id = test_id;
    tg->mode = mode;
    tg->is_running = true;
    tg->is_paused = false;
    tg->start_tick = HAL_GetTick();
    tg->step_tick = tg->start_tick;
}

void TestGen_Stop(TestGenerator_t *tg)
{
    if (!tg) return;
    tg->is_running = false;
    tg->is_paused = false;
    tg->target_motor_speed = 0;
}

void TestGen_EmergencyStop(TestGenerator_t *tg)
{
    if (!tg) return;
    tg->is_running = false;
    tg->is_paused = false;
    tg->target_motor_speed = 0;
}

void TestGen_SetManualTargets(TestGenerator_t *tg, float temp, float dist, int8_t motor, uint8_t servo)
{
    if (!tg) return;
    tg->target_temp = temp;
    tg->target_dist = dist;
    tg->target_motor_speed = motor;
    tg->target_servo_angle = servo;
}

void TestGen_Update(TestGenerator_t *tg, uint32_t current_tick)
{
    if (!tg || !tg->is_running || tg->is_paused) return;

    /* Profile Generation State Machine */
    uint32_t elapsed_step = current_tick - tg->step_tick;

    switch (tg->mode) {
        case TEST_MODE_STEP_RESPONSE:
            /* Alternates motor between +60% and -60% every 3 seconds to measure rise/fall time */
            if (elapsed_step >= 3000) {
                tg->step_tick = current_tick;
                if (tg->target_motor_speed > 0) {
                    tg->target_motor_speed = -60;
                    tg->target_servo_angle = 45;
                } else {
                    tg->target_motor_speed = 60;
                    tg->target_servo_angle = 135;
                }
            }
            break;

        case TEST_MODE_OBSTACLE_APPROACH:
            /* Command forward movement towards obstacle until within 10cm, then back off */
            if (tg->last_telemetry.actual_dist_scaled > 0) {
                float dist_cm = (float)tg->last_telemetry.actual_dist_scaled / 10.0f;
                if (dist_cm <= 10.0f) {
                    tg->target_motor_speed = -35; /* Reverse away */
                } else if (dist_cm >= 40.0f) {
                    tg->target_motor_speed = 35;  /* Forward approach */
                }
            }
            break;

        case TEST_MODE_THERMAL_SWEEP:
            /* Ramp target temperature gradually from 25°C to 50°C */
            if (elapsed_step >= 2000) {
                tg->step_tick = current_tick;
                if (tg->target_temp < 50.0f) {
                    tg->target_temp += 1.0f;
                } else {
                    tg->target_temp = 25.0f;
                }
            }
            break;

        case TEST_MODE_MANUAL:
        default:
            /* Setpoints governed by manual host commands */
            break;
    }
}
