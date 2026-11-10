/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Node 2 (Sensing and Actuation Node) Main Application
  *                   Hardware: STM32F446RE NUCLEO-64
  ******************************************************************************
  */

#include "main.h"
#include "protocol.h"
#include "actuators.h"
#include "sensors.h"
#include "safety.h"

/* Peripheral Handles */
UART_HandleTypeDef huart1; /* Inter-Node UART to Node 1 (PA9 TX, PA10 RX) */
TIM_HandleTypeDef  htim3;  /* Servo PWM: PC6 (TIM3_CH1, 50 Hz) */
TIM_HandleTypeDef  htim4;  /* L293D Motor PWM: PB6 (TIM4_CH1, 1 kHz) */
ADC_HandleTypeDef  hadc1;  /* LM35 Analog: PA0 (ADC1_IN0) */

/* Global State */
static SafetySupervisor_t safety;
static ProtocolPacket_t   parsed_cmd_pkt;
static uint16_t           active_test_id = 1001;
static uint8_t            tx_seq_num = 0;

/* Active Commands Received from Node 1 */
static int8_t  cmd_motor_speed = 0;
static uint8_t cmd_servo_angle = 90;
static uint16_t cmd_flags = 0;

/* Ring Buffer for USART1 Reception */
static uint8_t u1_rx_byte = 0;
#define U1_RING_SIZE 256
static volatile uint8_t  u1_ring_buf[U1_RING_SIZE];
static volatile uint16_t u1_ring_head = 0;
static volatile uint16_t u1_ring_tail = 0;

/* Forward Declarations */
static void MX_GPIO_Init(void);
static void MX_USART1_UART_Init(void);
static void MX_TIM3_Init(void);
static void MX_TIM4_Init(void);
static void MX_ADC1_Init(void);
static void ProcessIncomingPackets(void);
static void SendTelemetryResponse(float temp, float dist, uint16_t loop_time_us);

/**
  * @brief  The application entry point.
  */
int main(void)
{
    /* Reset peripherals & initialize HAL */
    HAL_Init();

    /* Configure 180 MHz PLL Clock */
    SystemClock_Config();

    /* Initialize Peripherals */
    MX_GPIO_Init();
    MX_USART1_UART_Init();
    MX_TIM3_Init();
    MX_TIM4_Init();
    MX_ADC1_Init();

    /* Initialize Subsystems */
    Protocol_InitParser();
    Actuators_Init(&htim4, &htim3);
    Sensors_Init(&hadc1);
    Safety_Init(&safety);

    /* Start non-blocking UART interrupt reception */
    HAL_UART_Receive_IT(&huart1, &u1_rx_byte, 1);

    uint32_t last_loop_tick = 0;
    uint32_t last_led_tick = 0;

    /* Main Execution Loop */
    while (1)
    {
        uint32_t current_tick = HAL_GetTick();

        /* 1. Process Setpoint Command Packets from Node 1 */
        ProcessIncomingPackets();

        /* 2. Sensor Acquisition & Safety Supervision (100ms cycle) */
        if (current_tick - last_loop_tick >= 100)
        {
            uint32_t loop_start_cycles = DWT->CYCCNT;
            last_loop_tick = current_tick;

            /* Acquire Sensor Readings */
            float current_temp = LM35_ReadTemperature();
            float current_dist = HCSR04_ReadDistance();

            /* Evaluate Safety Envelope */
            FaultCode_t active_fault = Safety_Evaluate(&safety, current_temp, current_dist, cmd_motor_speed, current_tick);

            /* Actuator Command Dispatch (if not tripped) */
            if (!safety.is_tripped)
            {
                if (active_fault == FAULT_NO_FAULT) {
                    LED_SetState(LED_STATE_NORMAL);
                } else if (active_fault == FAULT_SETPOINT_DEVIATION || active_fault == FAULT_COMMUNICATION_TIMEOUT) {
                    LED_SetState(LED_STATE_WARNING);
                } else {
                    LED_SetState(LED_STATE_FAULT);
                }
                Servo_SetAngle(cmd_servo_angle);
            }
            else
            {
                /* E-STOP: All Actuator LEDs OFF per safety specification */
                LED_SetState(LED_STATE_EMERGENCY_STOP);
            }


            /* Calculate Execution Loop Latency */
            uint32_t loop_cycles = DWT->CYCCNT - loop_start_cycles;
            uint16_t loop_time_us = (uint16_t)(loop_cycles / (SystemCoreClock / 1000000));

            /* Transmit Telemetry Back to Node 1 */
            SendTelemetryResponse(current_temp, current_dist, loop_time_us);
        }

        /* 3. LED Status Indicator */
        if (current_tick - last_led_tick >= (safety.is_tripped ? 100 : 500))
        {
            last_led_tick = current_tick;
            HAL_GPIO_TogglePin(LD2_GPIO_PORT, LD2_PIN);
        }

        /* 4. Local User Button PC13 Emergency Trip */
        if (HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13) == GPIO_PIN_RESET)
        {
            HAL_Delay(30);
            if (HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13) == GPIO_PIN_RESET)
            {
                Safety_TriggerManualAbort(&safety, FAULT_EMERGENCY_STOP);
            }
        }
    }
}

/**
  * @brief Parses incoming command frames from Node 1
  */
static void ProcessIncomingPackets(void)
{
    while (u1_ring_head != u1_ring_tail)
    {
        uint8_t byte = u1_ring_buf[u1_ring_tail];
        u1_ring_tail = (u1_ring_tail + 1) % U1_RING_SIZE;

        if (Protocol_ParseByte(byte, &parsed_cmd_pkt))
        {
            safety.last_valid_comm_tick = HAL_GetTick();
            active_test_id = parsed_cmd_pkt.test_id;

            if (parsed_cmd_pkt.msg_type == MSG_CMD_SETPOINT &&
                parsed_cmd_pkt.payload_len >= sizeof(SetpointPayload_t))
            {
                SetpointPayload_t sp;
                memcpy(&sp, parsed_cmd_pkt.payload, sizeof(SetpointPayload_t));

                cmd_motor_speed = sp.target_motor_speed;
                cmd_servo_angle = sp.target_servo_angle;
                cmd_flags = sp.flags;

                if (safety.is_tripped && (cmd_flags & 0x02)) {
                    /* Flag 0x02 indicates reset request from supervisor */
                    Safety_Reset(&safety);
                }
            }
            else if (parsed_cmd_pkt.msg_type == MSG_EMERGENCY_STOP)
            {
                Safety_TriggerManualAbort(&safety, FAULT_EMERGENCY_STOP);
            }
            else if (parsed_cmd_pkt.msg_type == MSG_RESET_CMD)
            {
                Safety_Reset(&safety);
            }
        }
    }
}

/**
  * @brief Formats and transmits telemetry packet back to Node 1
  */
static void SendTelemetryResponse(float temp, float dist, uint16_t loop_time_us)
{
    TelemetryPayload_t tel;
    tel.actual_temp_scaled = (int16_t)(temp * 100.0f);
    tel.actual_dist_scaled = (int16_t)(dist * 10.0f);
    tel.actual_motor_speed = Motor_GetSpeed();
    tel.actual_servo_angle = Servo_GetAngle();
    tel.status_flags = safety.is_tripped ? 0x02 : 0x01;
    tel.fault_code = (uint8_t)safety.active_fault;
    tel.loop_time_us = loop_time_us;

    ProtocolPacket_t pkt;
    pkt.payload_len = sizeof(TelemetryPayload_t);
    pkt.msg_type = MSG_TELEMETRY_DATA;
    pkt.seq_num = ++tx_seq_num;
    pkt.test_id = active_test_id;
    memcpy(pkt.payload, &tel, sizeof(TelemetryPayload_t));

    uint8_t tx_buf[32];
    uint16_t len = Protocol_SerializePacket(&pkt, tx_buf);
    HAL_UART_Transmit(&huart1, tx_buf, len, 50);
}

/**
  * @brief UART RX Complete Callback
  */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1)
    {
        uint16_t next_head = (u1_ring_head + 1) % U1_RING_SIZE;
        if (next_head != u1_ring_tail) {
            u1_ring_buf[u1_ring_head] = u1_rx_byte;
            u1_ring_head = next_head;
        }
        HAL_UART_Receive_IT(&huart1, &u1_rx_byte, 1);
    }
}

/**
  * @brief System Clock Configuration (180 MHz from HSI PLL)
  */
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    __HAL_RCC_PWR_CLK_ENABLE();
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    RCC_OscInitStruct.HSIState = RCC_HSI_ON;
    RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
    RCC_OscInitStruct.PLL.PLLM = 16;
    RCC_OscInitStruct.PLL.PLLN = 360;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
    RCC_OscInitStruct.PLL.PLLQ = 2;
    RCC_OscInitStruct.PLL.PLLR = 2;
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
    {
        Error_Handler();
    }

    if (HAL_PWREx_EnableOverDrive() != HAL_OK)
    {
        Error_Handler();
    }

    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                                |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_SYSCLK_DIV4;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_SYSCLK_DIV2;

    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_5) != HAL_OK)
    {
        Error_Handler();
    }
}

/**
  * @brief USART1 Initialization (Inter-Node Bus: PA9 TX, PA10 RX)
  */
static void MX_USART1_UART_Init(void)
{
    __HAL_RCC_USART1_CLK_ENABLE();

    huart1.Instance = USART1;
    huart1.Init.BaudRate = 115200;
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart1.Init.OverSampling = UART_OVERSAMPLING_16;
    if (HAL_UART_Init(&huart1) != HAL_OK)
    {
        Error_Handler();
    }
}

/**
  * @brief TIM3 Initialization Function (Servo PWM: PC6 TIM3_CH1, 50 Hz)
  * APB1 timer clock = 90MHz (APB1 x 2). Prescaler 90-1 = 89 -> 1MHz. ARR = 20000-1 = 19999 -> 50Hz.
  */
static void MX_TIM3_Init(void)
{
    __HAL_RCC_TIM3_CLK_ENABLE();

    TIM_OC_InitTypeDef sConfigOC = {0};

    htim3.Instance = TIM3;
    htim3.Init.Prescaler = 89;
    htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim3.Init.Period = 19999;
    htim3.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
    if (HAL_TIM_PWM_Init(&htim3) != HAL_OK)
    {
        Error_Handler();
    }

    sConfigOC.OCMode = TIM_OCMODE_PWM1;
    sConfigOC.Pulse = 1500; /* Center 90 deg */
    sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
    sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
    if (HAL_TIM_PWM_ConfigChannel(&htim3, &sConfigOC, TIM_CHANNEL_1) != HAL_OK)
    {
        Error_Handler();
    }
}

/**
  * @brief TIM4 Initialization Function (Motor PWM: PB6 TIM4_CH1, 1 kHz)
  * APB1 timer clock = 90MHz. Prescaler 90-1 = 89 -> 1MHz. ARR = 1000-1 = 999 -> 1kHz.
  */
static void MX_TIM4_Init(void)
{
    __HAL_RCC_TIM4_CLK_ENABLE();

    TIM_OC_InitTypeDef sConfigOC = {0};

    htim4.Instance = TIM4;
    htim4.Init.Prescaler = 89;
    htim4.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim4.Init.Period = 999;
    htim4.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim4.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
    if (HAL_TIM_PWM_Init(&htim4) != HAL_OK)
    {
        Error_Handler();
    }

    sConfigOC.OCMode = TIM_OCMODE_PWM1;
    sConfigOC.Pulse = 0; /* Motor initial 0% duty */
    sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
    sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
    if (HAL_TIM_PWM_ConfigChannel(&htim4, &sConfigOC, TIM_CHANNEL_1) != HAL_OK)
    {
        Error_Handler();
    }
}

/**
  * @brief ADC1 Initialization Function (LM35 Temp: PA0 ADC1_IN0)
  */
static void MX_ADC1_Init(void)
{
    __HAL_RCC_ADC1_CLK_ENABLE();

    ADC_ChannelConfTypeDef sConfig = {0};

    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV4;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.ScanConvMode = DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.NbrOfConversion = 1;
    hadc1.Init.DMAContinuousRequests = DISABLE;
    hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    if (HAL_ADC_Init(&hadc1) != HAL_OK)
    {
        Error_Handler();
    }

    sConfig.Channel = ADC_CHANNEL_0;
    sConfig.Rank = 1;
    sConfig.SamplingTime = ADC_SAMPLETIME_84CYCLES;
    if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
    {
        Error_Handler();
    }
}

/**
  * @brief GPIO Initialization Function
  */
static void MX_GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    /* Initial Output States: Safe Low for Motor & Sensors */
    HAL_GPIO_WritePin(LD2_GPIO_PORT, LD2_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(MOTOR_IN1_PORT, MOTOR_IN1_PIN | MOTOR_IN2_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(ULTRASONIC_TRIG_PORT, ULTRASONIC_TRIG_PIN, GPIO_PIN_RESET);

    /* LD2 User LED on PA5 */
    GPIO_InitStruct.Pin = LD2_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(LD2_GPIO_PORT, &GPIO_InitStruct);

    /* LM35 Analog Pin on PA0 (ADC1_IN0) */
    GPIO_InitStruct.Pin = LM35_ADC_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_ANALOG;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(LM35_ADC_PORT, &GPIO_InitStruct);

    /* User Button B1 on PC13 */
    GPIO_InitStruct.Pin = GPIO_PIN_13;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

    /* L293D Direction Pins: PB4 (IN1), PB5 (IN2) */
    GPIO_InitStruct.Pin = MOTOR_IN1_PIN | MOTOR_IN2_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

    /* HC-SR04 Trig Pin on PB8 */
    GPIO_InitStruct.Pin = ULTRASONIC_TRIG_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_MEDIUM;
    HAL_GPIO_Init(ULTRASONIC_TRIG_PORT, &GPIO_InitStruct);

    /* HC-SR04 Echo Pin on PB9 (Shifted 3.3V) */
    GPIO_InitStruct.Pin = ULTRASONIC_ECHO_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(ULTRASONIC_ECHO_PORT, &GPIO_InitStruct);

    /* TIM4_CH1 (PB6) Motor PWM Alternate Function */
    GPIO_InitStruct.Pin = MOTOR_EN1_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF2_TIM4;
    HAL_GPIO_Init(MOTOR_EN1_PORT, &GPIO_InitStruct);

    /* TIM3_CH1 (PC6) Servo PWM Alternate Function */
    GPIO_InitStruct.Pin = SERVO_PWM_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF2_TIM3;
    HAL_GPIO_Init(SERVO_PWM_PORT, &GPIO_InitStruct);

    /* USART1 GPIOs: PA9=TX, PA10=RX */
    GPIO_InitStruct.Pin = INTERNODE_UART_TX_PIN | INTERNODE_UART_RX_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF7_USART1;
    HAL_GPIO_Init(INTERNODE_UART_PORT, &GPIO_InitStruct);

    /* Enable USART1 Interrupt */
    HAL_NVIC_SetPriority(USART1_IRQn, 1, 0);
    HAL_NVIC_EnableIRQ(USART1_IRQn);
}

void Error_Handler(void)
{
    __disable_irq();
    while (1)
    {
        HAL_GPIO_TogglePin(LD2_GPIO_PORT, LD2_PIN);
        for (volatile int i = 0; i < 100000; i++);
    }
}
