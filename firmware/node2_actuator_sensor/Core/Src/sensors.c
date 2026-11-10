/**
  ******************************************************************************
  * @file           : sensors.c
  * @brief          : Sensor drivers: LM35 ADC and HC-SR04 ultrasonic
  ******************************************************************************
  */

#include "sensors.h"

static ADC_HandleTypeDef *hadc1_inst = NULL;

#define LM35_FILTER_SAMPLES 8
static float lm35_history[LM35_FILTER_SAMPLES] = {25.0f};
static uint8_t filter_idx = 0;

/* Microsecond delay using DWT (Data Watchpoint and Trace) cycle counter */
static void DWT_Init(void)
{
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
}

static void Delay_us(uint32_t us)
{
    uint32_t start_cycles = DWT->CYCCNT;
    /* SystemCoreClock is 180MHz -> 180 cycles per microsecond */
    uint32_t target_cycles = us * (SystemCoreClock / 1000000);
    while ((DWT->CYCCNT - start_cycles) < target_cycles);
}

void Sensors_Init(ADC_HandleTypeDef *hadc)
{
    hadc1_inst = hadc;
    DWT_Init();

    /* Initialize filter history */
    for (int i = 0; i < LM35_FILTER_SAMPLES; i++) {
        lm35_history[i] = 25.0f;
    }

    /* Initialize HC-SR04 Trig Pin to Low */
    HAL_GPIO_WritePin(ULTRASONIC_TRIG_PORT, ULTRASONIC_TRIG_PIN, GPIO_PIN_RESET);
}

float LM35_ReadTemperature(void)
{
    if (!hadc1_inst) return 25.0f;

    HAL_ADC_Start(hadc1_inst);
    if (HAL_ADC_PollForConversion(hadc1_inst, 10) == HAL_OK)
    {
        uint32_t raw = HAL_ADC_GetValue(hadc1_inst);
        /* LM35: 10 mV/°C. Vref = 3.3V (3300 mV). ADC = 12-bit (4095 max) */
        float mv = ((float)raw * 3300.0f) / 4095.0f;
        float temp_c = mv / 10.0f;

        /* Apply moving average filter */
        lm35_history[filter_idx] = temp_c;
        filter_idx = (filter_idx + 1) % LM35_FILTER_SAMPLES;

        float sum = 0.0f;
        for (int i = 0; i < LM35_FILTER_SAMPLES; i++) {
            sum += lm35_history[i];
        }
        return sum / (float)LM35_FILTER_SAMPLES;
    }
    return 25.0f;
}

float HCSR04_ReadDistance(void)
{
    /* 1. Send 10µs trigger pulse */
    HAL_GPIO_WritePin(ULTRASONIC_TRIG_PORT, ULTRASONIC_TRIG_PIN, GPIO_PIN_RESET);
    Delay_us(2);
    HAL_GPIO_WritePin(ULTRASONIC_TRIG_PORT, ULTRASONIC_TRIG_PIN, GPIO_PIN_SET);
    Delay_us(10);
    HAL_GPIO_WritePin(ULTRASONIC_TRIG_PORT, ULTRASONIC_TRIG_PIN, GPIO_PIN_RESET);

    /* 2. Wait for Echo pin to go HIGH (with 5ms timeout) */
    uint32_t timeout_start = HAL_GetTick();
    while (HAL_GPIO_ReadPin(ULTRASONIC_ECHO_PORT, ULTRASONIC_ECHO_PIN) == GPIO_PIN_RESET)
    {
        if (HAL_GetTick() - timeout_start > 5) {
            return 0.0f; /* Timeout / Sensor disconnected */
        }
    }

    /* 3. Measure duration while Echo pin is HIGH */
    uint32_t echo_start_cycles = DWT->CYCCNT;
    uint32_t max_echo_cycles = 25000 * (SystemCoreClock / 1000000); /* 25ms timeout (~400cm max) */

    while (HAL_GPIO_ReadPin(ULTRASONIC_ECHO_PORT, ULTRASONIC_ECHO_PIN) == GPIO_PIN_SET)
    {
        if ((DWT->CYCCNT - echo_start_cycles) > max_echo_cycles) {
            return 400.0f; /* Out of range */
        }
    }

    uint32_t elapsed_cycles = DWT->CYCCNT - echo_start_cycles;
    uint32_t duration_us = elapsed_cycles / (SystemCoreClock / 1000000);

    /* Distance in cm = time in µs / 58.0 */
    float distance_cm = (float)duration_us / 58.0f;
    return distance_cm;
}

bool Sensors_IsLM35Valid(float temp)
{
    /* Normal operating room and industrial boundary: 2.0°C to 90.0°C */
    return (temp >= 2.0f && temp <= 90.0f);
}

bool Sensors_IsHCSR04Valid(float dist)
{
    /* Valid HC-SR04 physical response: 2.0cm to 400.0cm */
    return (dist >= 2.0f && dist <= 400.0f);
}
