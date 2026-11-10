/**
  ******************************************************************************
  * @file           : actuators.c
  * @brief          : Actuator driver for Red, Yellow, Green LEDs and Optional Servo PWM
  *                   Controls Green LED on PB4 (GPIO), Yellow LED on PB5 (GPIO),
  *                   Red LED on PB6 (TIM4_CH1 PWM brightness), and Optional Servo on PC6.
  ******************************************************************************
  */

#include "actuators.h"

static TIM_HandleTypeDef *htim4_red_led = NULL;
static TIM_HandleTypeDef *htim3_servo = NULL;
static LedState_t current_led_state = LED_STATE_NORMAL;
static uint8_t red_led_brightness = 100;
static uint8_t current_servo_angle = 90;

void Actuators_Init(TIM_HandleTypeDef *htim_red_led, TIM_HandleTypeDef *htim_servo)
{
    htim4_red_led = htim_red_led;
    htim3_servo = htim_servo;

    /* Start Red LED PWM on PB6 (TIM4_CH1, 1 kHz) */
    if (htim4_red_led) {
        HAL_TIM_PWM_Start(htim4_red_led, TIM_CHANNEL_1);
        __HAL_TIM_SET_COMPARE(htim4_red_led, TIM_CHANNEL_1, 0);
    }

    /* Start optional Servo PWM on PC6 (TIM3_CH1, 50 Hz) */
    if (htim3_servo) {
        HAL_TIM_PWM_Start(htim3_servo, TIM_CHANNEL_1);
        __HAL_TIM_SET_COMPARE(htim3_servo, TIM_CHANNEL_1, 1500); // 90 degrees
        current_servo_angle = 90;
    }

    /* Default to Normal state: Green ON, Yellow OFF, Red OFF */
    LED_SetState(LED_STATE_NORMAL);
}

void LED_SetState(LedState_t state)
{
    current_led_state = state;

    switch (state) {
        case LED_STATE_NORMAL:
            /* Green ON, Yellow OFF, Red OFF */
            HAL_GPIO_WritePin(LED_GREEN_PORT, LED_GREEN_PIN, GPIO_PIN_SET);
            HAL_GPIO_WritePin(LED_YELLOW_PORT, LED_YELLOW_PIN, GPIO_PIN_RESET);
            if (htim4_red_led) {
                __HAL_TIM_SET_COMPARE(htim4_red_led, TIM_CHANNEL_1, 0);
            }
            break;

        case LED_STATE_WARNING:
            /* Green OFF, Yellow ON, Red OFF */
            HAL_GPIO_WritePin(LED_GREEN_PORT, LED_GREEN_PIN, GPIO_PIN_RESET);
            HAL_GPIO_WritePin(LED_YELLOW_PORT, LED_YELLOW_PIN, GPIO_PIN_SET);
            if (htim4_red_led) {
                __HAL_TIM_SET_COMPARE(htim4_red_led, TIM_CHANNEL_1, 0);
            }
            break;

        case LED_STATE_FAULT: {
            /* Green OFF, Yellow OFF, Red ON with PWM brightness */
            HAL_GPIO_WritePin(LED_GREEN_PORT, LED_GREEN_PIN, GPIO_PIN_RESET);
            HAL_GPIO_WritePin(LED_YELLOW_PORT, LED_YELLOW_PIN, GPIO_PIN_RESET);
            uint32_t compare = ((uint32_t)red_led_brightness * 1000) / 100;
            if (htim4_red_led) {
                __HAL_TIM_SET_COMPARE(htim4_red_led, TIM_CHANNEL_1, compare);
            }
            break;
        }

        case LED_STATE_EMERGENCY_STOP:
        default:
            /* All LEDs OFF (Hardware Safety State) */
            HAL_GPIO_WritePin(LED_GREEN_PORT, LED_GREEN_PIN, GPIO_PIN_RESET);
            HAL_GPIO_WritePin(LED_YELLOW_PORT, LED_YELLOW_PIN, GPIO_PIN_RESET);
            if (htim4_red_led) {
                __HAL_TIM_SET_COMPARE(htim4_red_led, TIM_CHANNEL_1, 0);
            }
            break;
    }
}

void LED_SetRedBrightness(uint8_t brightness_pct)
{
    if (brightness_pct > 100) brightness_pct = 100;
    red_led_brightness = brightness_pct;
    if (current_led_state == LED_STATE_FAULT && htim4_red_led) {
        uint32_t compare = ((uint32_t)red_led_brightness * 1000) / 100;
        __HAL_TIM_SET_COMPARE(htim4_red_led, TIM_CHANNEL_1, compare);
    }
}

LedState_t LED_GetState(void)
{
    return current_led_state;
}

uint8_t LED_GetRedBrightness(void)
{
    return red_led_brightness;
}

void Servo_SetAngle(uint8_t angle_deg)
{
    if (angle_deg > 180) angle_deg = 180;
    current_servo_angle = angle_deg;
    uint32_t pulse_us = 1000 + (((uint32_t)angle_deg * 1000) / 180);
    if (htim3_servo) {
        __HAL_TIM_SET_COMPARE(htim3_servo, TIM_CHANNEL_1, pulse_us);
    }
}

uint8_t Servo_GetAngle(void)
{
    return current_servo_angle;
}

/* Stubs for backwards-compatibility */
void Motor_SetSpeed(int8_t speed_pct)
{
    /* Motor retired: map speed status to LED states for backward telemetry */
    if (speed_pct == 0) {
        LED_SetState(LED_STATE_NORMAL);
    } else if (speed_pct < 0) {
        LED_SetState(LED_STATE_WARNING);
    }
}

void Motor_Halt(void)
{
    LED_SetState(LED_STATE_EMERGENCY_STOP);
}

int8_t Motor_GetSpeed(void)
{
    return (current_led_state == LED_STATE_NORMAL) ? 0 : (current_led_state == LED_STATE_WARNING ? 50 : 100);
}
