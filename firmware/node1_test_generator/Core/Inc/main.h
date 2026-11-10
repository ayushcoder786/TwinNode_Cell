/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for Node 1 (Test Setpoint Generator)
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

/* Pin Definitions for NUCLEO-F446RE */
/* LD2 User Green LED */
#define LD2_PIN                 GPIO_PIN_5
#define LD2_GPIO_PORT           GPIOA

/* B1 User Blue Pushbutton */
#define B1_PIN                  GPIO_PIN_13
#define B1_GPIO_PORT            GPIOC

/* USART2: ST-LINK Virtual COM Port to Host PC */
#define HOST_UART_TX_PIN        GPIO_PIN_2
#define HOST_UART_RX_PIN        GPIO_PIN_3
#define HOST_UART_PORT          GPIOA

/* USART1: Inter-Node Bus to Node 2 */
#define INTERNODE_UART_TX_PIN   GPIO_PIN_9
#define INTERNODE_UART_RX_PIN   GPIO_PIN_10
#define INTERNODE_UART_PORT     GPIOA

/* System Timing Constants */
#define DISPATCH_INTERVAL_MS    100   /* 10 Hz setpoint command dispatch */
#define COMM_TIMEOUT_MS         1500  /* Telemetry timeout threshold */
#define HEARTBEAT_INTERVAL_MS   500   /* LED toggle interval */

/* Function Prototypes */
void Error_Handler(void);
void SystemClock_Config(void);

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
