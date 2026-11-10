/**
  ******************************************************************************
  * @file           : safety.h
  * @brief          : Node 2 Autonomous Safety & Fault Trip Supervisor
  ******************************************************************************
  */

#ifndef __SAFETY_H
#define __SAFETY_H

#include "protocol.h"
#include <stdbool.h>

typedef struct {
    bool        is_tripped;
    FaultCode_t active_fault;
    uint32_t    trip_tick;
    uint32_t    last_valid_comm_tick;
    uint32_t    stall_check_tick;
} SafetySupervisor_t;

void        Safety_Init(SafetySupervisor_t *safety);
FaultCode_t Safety_Evaluate(SafetySupervisor_t *safety, float temp, float dist, int8_t motor_cmd, uint32_t current_tick);
void        Safety_TriggerManualAbort(SafetySupervisor_t *safety, FaultCode_t fault);
void        Safety_Reset(SafetySupervisor_t *safety);

#endif /* __SAFETY_H */
