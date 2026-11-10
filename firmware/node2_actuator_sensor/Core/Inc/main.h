/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for Node 2 (Sensing and Actuation Node)
  *                   Hardware: STM32 NUCLEO-F446RE
  ******************************************************************************
  */

#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

#include "stm32f4xx_hal.h"
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>

/* Pin Assignments for STM32F446RE NUCLEO-64 */

/* User LED LD2 */
#define LD2_PIN                 GPIO_PIN_5
#define LD2_GPIO_PORT           GPIOA

/* Inter-Node USART1 (to Node 1) */
#define INTERNODE_UART_TX_PIN   GPIO_PIN_9
#define INTERNODE_UART_RX_PIN   GPIO_PIN_10
#define INTERNODE_UART_PORT     GPIOA

/* LED Actuator System (Node 2 — Replacing L293D DC Motor) */
#define LED_GREEN_PIN           GPIO_PIN_4   /* PB4: Green LED (Normal Operation) */
#define LED_GREEN_PORT          GPIOB
#define LED_YELLOW_PIN          GPIO_PIN_5   /* PB5: Yellow LED (Warning / Latency / Drift) */
#define LED_YELLOW_PORT         GPIOB
#define LED_RED_PIN             GPIO_PIN_6   /* PB6: Red LED (Fault Condition / TIM4_CH1 PWM) */
#define LED_RED_PORT            GPIOB

/* Legacy Aliases for Pin Compatibility */
#define MOTOR_EN1_PIN           LED_RED_PIN
#define MOTOR_EN1_PORT          LED_RED_PORT
#define MOTOR_IN1_PIN           LED_GREEN_PIN
#define MOTOR_IN1_PORT          LED_GREEN_PORT
#define MOTOR_IN2_PIN           LED_YELLOW_PIN
#define MOTOR_IN2_PORT          LED_YELLOW_PORT

/* Servo Motor (Auxiliary / Optional) */
#define SERVO_PWM_PIN           GPIO_PIN_6   /* PC6: TIM3_CH1 PWM (50 Hz) */
#define SERVO_PWM_PORT          GPIOC


/* LM35 Analog Temperature Sensor */
#define LM35_ADC_PIN            GPIO_PIN_0   /* PA0: ADC1_IN0 (0-3.3V) */
#define LM35_ADC_PORT           GPIOA

/* HC-SR04 Ultrasonic Distance Sensor */
#define ULTRASONIC_TRIG_PIN     GPIO_PIN_8   /* PB8: GPIO Output */
#define ULTRASONIC_TRIG_PORT    GPIOB
#define ULTRASONIC_ECHO_PIN     GPIO_PIN_9   /* PB9: GPIO Input (via BSS138 3.3V) */
#define ULTRASONIC_ECHO_PORT    GPIOB

/* Safety Thresholds */
#define SAFETY_MIN_DIST_CM      4.0f         /* Collision avoidance threshold */
#define SAFETY_MAX_TEMP_C       85.0f        /* Thermal cutoff threshold */
#define COMM_FAILSAFE_TIMEOUT_MS 1500        /* Failsafe actuator shutdown */

/* Function Prototypes */
void Error_Handler(void);
void SystemClock_Config(void);

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
