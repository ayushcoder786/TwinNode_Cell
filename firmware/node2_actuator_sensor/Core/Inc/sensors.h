/**
  ******************************************************************************
  * @file           : sensors.h
  * @brief          : Sensor acquisition for LM35 and HC-SR04
  ******************************************************************************
  */

#ifndef __SENSORS_H
#define __SENSORS_H

#include "main.h"

void  Sensors_Init(ADC_HandleTypeDef *hadc);
float LM35_ReadTemperature(void);
float HCSR04_ReadDistance(void);
bool  Sensors_IsLM35Valid(float temp);
bool  Sensors_IsHCSR04Valid(float dist);

#endif /* __SENSORS_H */
