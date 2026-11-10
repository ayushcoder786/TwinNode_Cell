/**
  ******************************************************************************
  * @file           : actuators.h
  * @brief          : Node 2 Actuator System (Red, Yellow, Green LEDs + PWM Brightness, Optional Servo)
  *                   L293D DC Motor control retired per project architecture upgrade.
  ******************************************************************************
  */

#ifndef __ACTUATORS_H
#define __ACTUATORS_H

#include "main.h"

typedef enum {
    LED_STATE_NORMAL = 0,         /* Green ON (Nominal Operation) */
    LED_STATE_WARNING = 1,        /* Yellow ON (Setpoint Deviation / Latency Warning) */
    LED_STATE_FAULT = 2,          /* Red ON (Active Hardware / Sensor Fault) */
    LED_STATE_EMERGENCY_STOP = 3  /* All Actuator LEDs OFF (Safety Shutdown) */
} LedState_t;

/* Initialization */
void Actuators_Init(TIM_HandleTypeDef *htim_red_led, TIM_HandleTypeDef *htim_servo);

/* 3-LED Actuation API */
void LED_SetState(LedState_t state);
void LED_SetRedBrightness(uint8_t brightness_pct);
LedState_t LED_GetState(void);
uint8_t LED_GetRedBrightness(void);

/* Optional Servo Positioning API */
void Servo_SetAngle(uint8_t angle_deg);
uint8_t Servo_GetAngle(void);

/* Backwards-Compatibility Stubs (Motor Retired) */
void Motor_SetSpeed(int8_t speed_pct);
void Motor_Halt(void);
int8_t Motor_GetSpeed(void);

#endif /* __ACTUATORS_H */
