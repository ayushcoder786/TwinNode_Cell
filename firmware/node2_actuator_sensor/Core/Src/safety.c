/**
  ******************************************************************************
  * @file           : safety.c
  * @brief          : Node 2 Autonomous Safety & Fault Trip Supervisor
  ******************************************************************************
  */

#include "safety.h"
#include "actuators.h"
#include "main.h"

void Safety_Init(SafetySupervisor_t *safety)
{
    if (!safety) return;
    safety->is_tripped = false;
    safety->active_fault = FAULT_NONE;
    safety->trip_tick = 0;
    safety->last_valid_comm_tick = HAL_GetTick();
    safety->stall_check_tick = 0;
}

FaultCode_t Safety_Evaluate(SafetySupervisor_t *safety, float temp, float dist, int8_t motor_cmd, uint32_t current_tick)
{
    if (!safety) return FAULT_NONE;

    /* 1. Communication Loss Watchdog: If no valid packet from Node 1 for >1500ms */
    if (current_tick - safety->last_valid_comm_tick > COMM_FAILSAFE_TIMEOUT_MS)
    {
        Motor_Halt();
        Servo_SetAngle(90);
        safety->is_tripped = true;
        safety->active_fault = FAULT_COMM_TIMEOUT;
        return FAULT_COMM_TIMEOUT;
    }

    /* If already latched in E-Stop or Critical Trip, keep actuators safe */
    if (safety->is_tripped)
    {
        Motor_Halt();
        return safety->active_fault;
    }

    /* 2. Collision Proximity Safety Trip: Cart within 4.0cm of obstacle */
    if (dist > 0.1f && dist < SAFETY_MIN_DIST_CM && motor_cmd > 0)
    {
        Motor_Halt();
        safety->is_tripped = true;
        safety->active_fault = FAULT_ACTUATOR_STALL;
        safety->trip_tick = current_tick;
        return FAULT_ACTUATOR_STALL;
    }

    /* 3. Thermal Cutoff Safety Trip: LM35 > 85.0°C */
    if (temp > SAFETY_MAX_TEMP_C)
    {
        Motor_Halt();
        safety->is_tripped = true;
        safety->active_fault = FAULT_SENSOR_OUT_OF_RANGE;
        safety->trip_tick = current_tick;
        return FAULT_SENSOR_OUT_OF_RANGE;
    }

    /* 4. Sensor Disconnection Safety: LM35 grounded/floating <= 0.5°C */
    if (temp <= 0.5f)
    {
        safety->active_fault = FAULT_SENSOR_DISCONNECTED;
        return FAULT_SENSOR_DISCONNECTED;
    }

    safety->active_fault = FAULT_NONE;
    return FAULT_NONE;
}

void Safety_TriggerManualAbort(SafetySupervisor_t *safety, FaultCode_t fault)
{
    if (!safety) return;
    Motor_Halt();
    Servo_SetAngle(90);
    safety->is_tripped = true;
    safety->active_fault = fault;
    safety->trip_tick = HAL_GetTick();
}

void Safety_Reset(SafetySupervisor_t *safety)
{
    if (!safety) return;
    safety->is_tripped = false;
    safety->active_fault = FAULT_NONE;
    safety->last_valid_comm_tick = HAL_GetTick();
}
