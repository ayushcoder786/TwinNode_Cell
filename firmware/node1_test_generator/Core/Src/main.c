/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Node 1 (Test Setpoint Generator) Main Application
  *                   Hardware: STM32F446RE NUCLEO-64
  ******************************************************************************
  */

#include "main.h"
#include "protocol.h"
#include "test_generator.h"

/* Peripheral Handles */
UART_HandleTypeDef huart1; /* Inter-Node UART to Node 2 (PA9/PA10) */
UART_HandleTypeDef huart2; /* ST-LINK VCP UART to Host PC (PA2/PA3) */

/* Global Instances */
static TestGenerator_t test_gen;
static ProtocolPacket_t parsed_node2_pkt;

/* Ring Buffer for USART1 (Node 2) */
static uint8_t u1_rx_byte = 0;
#define U1_RING_SIZE 256
static volatile uint8_t  u1_ring_buf[U1_RING_SIZE];
static volatile uint16_t u1_ring_head = 0;
static volatile uint16_t u1_ring_tail = 0;

/* Ring Buffer for USART2 (Host PC) */
static uint8_t u2_rx_byte = 0;
#define U2_RING_SIZE 256
static volatile uint8_t  u2_ring_buf[U2_RING_SIZE];
static volatile uint16_t u2_ring_head = 0;
static volatile uint16_t u2_ring_tail = 0;

/* Forward Declarations */
static void MX_GPIO_Init(void);
static void MX_USART1_UART_Init(void);
static void MX_USART2_UART_Init(void);
static void ProcessHostCommands(void);
static void ProcessNode2Telemetry(void);
static void SendSetpointToNode2(void);
static void StreamTelemetryToHost(void);

/**
  * @brief  The application entry point.
  */
int main(void)
{
    /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
    HAL_Init();

    /* Configure the system clock (180 MHz PLL) */
    SystemClock_Config();

    /* Initialize all configured peripherals */
    MX_GPIO_Init();
    MX_USART1_UART_Init();
    MX_USART2_UART_Init();

    /* Initialize Protocol and Test Generator */
    Protocol_InitParser();
    TestGen_Init(&test_gen);

    /* Start non-blocking character reception interrupts */
    HAL_UART_Receive_IT(&huart1, &u1_rx_byte, 1);
    HAL_UART_Receive_IT(&huart2, &u2_rx_byte, 1);

    /* Transmit initial startup banner to host PC */
    const char *banner = "\r\n{\"type\":\"boot\",\"node\":1,\"fw_version\":\"1.0.0\",\"mcu\":\"STM32F446RE\",\"status\":\"READY\"}\r\n";
    HAL_UART_Transmit(&huart2, (uint8_t*)banner, strlen(banner), 500);

    uint32_t last_dispatch_tick = 0;
    uint32_t last_heartbeat_tick = 0;

    /* Main Supervised Execution Loop */
    while (1)
    {
        uint32_t current_tick = HAL_GetTick();

        /* 1. Process incoming commands from Host PC (USB VCP) */
        ProcessHostCommands();

        /* 2. Process incoming telemetry packets from Node 2 (USART1) */
        ProcessNode2Telemetry();

        /* 3. Advance automated test generator state machine */
        TestGen_Update(&test_gen, current_tick);

        /* 4. Periodic 10Hz (100ms) setpoint dispatch to Node 2 */
        if (current_tick - last_dispatch_tick >= DISPATCH_INTERVAL_MS)
        {
            last_dispatch_tick = current_tick;
            SendSetpointToNode2();
            StreamTelemetryToHost();

            /* Check Node 2 Communication Timeout */
            if (test_gen.node2_connected && (current_tick - test_gen.last_telemetry_tick > COMM_TIMEOUT_MS))
            {
                test_gen.node2_connected = false;
                test_gen.timeouts++;
                /* Alert host of communication drop */
                const char *timeout_msg = "{\"type\":\"alarm\",\"code\":\"COMM_TIMEOUT\",\"desc\":\"Node 2 telemetry lost >1500ms\"}\r\n";
                HAL_UART_Transmit(&huart2, (uint8_t*)timeout_msg, strlen(timeout_msg), 100);
            }
        }

        /* 5. Heartbeat & LED indicator (500ms) */
        if (current_tick - last_heartbeat_tick >= HEARTBEAT_INTERVAL_MS)
        {
            last_heartbeat_tick = current_tick;
            if (test_gen.node2_connected) {
                HAL_GPIO_TogglePin(LD2_GPIO_PORT, LD2_PIN); /* Normal steady pulse */
            } else {
                HAL_GPIO_WritePin(LD2_GPIO_PORT, LD2_PIN, GPIO_PIN_SET); /* Solid on when disconnected */
            }
        }

        /* 6. Local Emergency Stop Button Check (B1 User Button on PC13 - Active LOW) */
        if (HAL_GPIO_ReadPin(B1_GPIO_PORT, B1_PIN) == GPIO_PIN_RESET)
        {
            HAL_Delay(50); /* Debounce */
            if (HAL_GPIO_ReadPin(B1_GPIO_PORT, B1_PIN) == GPIO_PIN_RESET)
            {
                TestGen_EmergencyStop(&test_gen);
                /* Send Emergency Stop packet immediately to Node 2 */
                ProtocolPacket_t estop_pkt;
                estop_pkt.payload_len = 1;
                estop_pkt.msg_type = MSG_EMERGENCY_STOP;
                estop_pkt.seq_num = ++test_gen.seq_num;
                estop_pkt.test_id = test_gen.test_id;
                estop_pkt.payload[0] = 0x01; /* Reason: Manual Button */

                uint8_t tx_buf[32];
                uint16_t len = Protocol_SerializePacket(&estop_pkt, tx_buf);
                HAL_UART_Transmit(&huart1, tx_buf, len, 50);

                const char *estop_msg = "{\"type\":\"alarm\",\"code\":\"EMERGENCY_STOP\",\"desc\":\"Hardware Pushbutton B1 Tripped\"}\r\n";
                HAL_UART_Transmit(&huart2, (uint8_t*)estop_msg, strlen(estop_msg), 100);

                while (HAL_GPIO_ReadPin(B1_GPIO_PORT, B1_PIN) == GPIO_PIN_RESET) {
                    HAL_Delay(10);
                }
            }
        }
    }
}

/**
  * @brief Dispatches setpoint packet to Node 2 over USART1
  */
static void SendSetpointToNode2(void)
{
    SetpointPayload_t sp;
    sp.target_temp_scaled = (int16_t)(test_gen.target_temp * 100.0f);
    sp.target_dist_scaled = (int16_t)(test_gen.target_dist * 10.0f);
    sp.target_motor_speed = test_gen.target_motor_speed;
    sp.target_servo_angle = test_gen.target_servo_angle;
    sp.flags = test_gen.is_running ? 0x01 : 0x00;

    ProtocolPacket_t pkt;
    pkt.payload_len = sizeof(SetpointPayload_t);
    pkt.msg_type = MSG_CMD_SETPOINT;
    pkt.seq_num = ++test_gen.seq_num;
    pkt.test_id = test_gen.test_id;
    memcpy(pkt.payload, &sp, sizeof(SetpointPayload_t));

    uint8_t tx_buf[32];
    uint16_t len = Protocol_SerializePacket(&pkt, tx_buf);
    HAL_UART_Transmit(&huart1, tx_buf, len, 50);
    test_gen.packets_sent++;
}

/**
  * @brief Streams formatted JSON telemetry to Host PC over USART2
  */
static void StreamTelemetryToHost(void)
{
    char json_buf[192];
    float actual_temp = (float)test_gen.last_telemetry.actual_temp_scaled / 100.0f;
    float actual_dist = (float)test_gen.last_telemetry.actual_dist_scaled / 10.0f;
    int actual_motor = test_gen.last_telemetry.actual_motor_speed;
    int actual_servo = test_gen.last_telemetry.actual_servo_angle;
    float loop_latency = (float)test_gen.last_telemetry.loop_time_us / 1000.0f;

    snprintf(json_buf, sizeof(json_buf),
        "{\"type\":\"telemetry\",\"test_id\":%u,\"seq\":%u,\"n1_stat\":\"ONLINE\",\"n2_stat\":\"%s\","
        "\"tgt_temp\":%.1f,\"act_temp\":%.1f,\"tgt_dist\":%.1f,\"act_dist\":%.1f,"
        "\"tgt_motor\":%d,\"act_motor\":%d,\"tgt_servo\":%u,\"act_servo\":%u,"
        "\"latency_ms\":%.1f,\"fault\":%u}\r\n",
        test_gen.test_id,
        test_gen.seq_num,
        test_gen.node2_connected ? "ONLINE" : "OFFLINE",
        test_gen.target_temp, actual_temp,
        test_gen.target_dist, actual_dist,
        test_gen.target_motor_speed, actual_motor,
        test_gen.target_servo_angle, actual_servo,
        loop_latency,
        test_gen.last_telemetry.fault_code
    );

    HAL_UART_Transmit(&huart2, (uint8_t*)json_buf, strlen(json_buf), 100);
}

/**
  * @brief Parses incoming bytes from Node 2 ring buffer
  */
static void ProcessNode2Telemetry(void)
{
    while (u1_ring_head != u1_ring_tail)
    {
        uint8_t byte = u1_ring_buf[u1_ring_tail];
        u1_ring_tail = (u1_ring_tail + 1) % U1_RING_SIZE;

        if (Protocol_ParseByte(byte, &parsed_node2_pkt))
        {
            if (parsed_node2_pkt.msg_type == MSG_TELEMETRY_DATA &&
                parsed_node2_pkt.payload_len >= sizeof(TelemetryPayload_t))
            {
                memcpy(&test_gen.last_telemetry, parsed_node2_pkt.payload, sizeof(TelemetryPayload_t));
                test_gen.last_telemetry_tick = HAL_GetTick();
                test_gen.node2_connected = true;
                test_gen.packets_received++;
            }
        }
    }
}

/**
  * @brief Parses incoming commands from Host PC ring buffer
  */
static void ProcessHostCommands(void)
{
    static char cmd_buf[64];
    static uint8_t cmd_idx = 0;

    while (u2_ring_head != u2_ring_tail)
    {
        char c = (char)u2_ring_buf[u2_ring_tail];
        u2_ring_tail = (u2_ring_tail + 1) % U2_RING_SIZE;

        if (c == '\n' || c == '\r')
        {
            if (cmd_idx > 0)
            {
                cmd_buf[cmd_idx] = '\0';
                /* Parse simple ASCII or JSON command */
                if (strncmp(cmd_buf, "START", 5) == 0) {
                    TestGen_Start(&test_gen, 1001, TEST_MODE_MANUAL);
                } else if (strncmp(cmd_buf, "STOP", 4) == 0) {
                    TestGen_Stop(&test_gen);
                } else if (strncmp(cmd_buf, "ESTOP", 5) == 0) {
                    TestGen_EmergencyStop(&test_gen);
                } else if (strncmp(cmd_buf, "SET", 3) == 0) {
                    /* Format: SET T:25.0 D:30.0 M:50 S:90 */
                    float t = test_gen.target_temp, d = test_gen.target_dist;
                    int m = test_gen.target_motor_speed, s = test_gen.target_servo_angle;
                    sscanf(cmd_buf, "SET T:%f D:%f M:%d S:%d", &t, &d, &m, &s);
                    TestGen_SetManualTargets(&test_gen, t, d, (int8_t)m, (uint8_t)s);
                }
                cmd_idx = 0;
            }
        }
        else if (cmd_idx < sizeof(cmd_buf) - 1)
        {
            cmd_buf[cmd_idx++] = c;
        }
    }
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
    else if (huart->Instance == USART2)
    {
        uint16_t next_head = (u2_ring_head + 1) % U2_RING_SIZE;
        if (next_head != u2_ring_tail) {
            u2_ring_buf[u2_ring_head] = u2_rx_byte;
            u2_ring_head = next_head;
        }
        HAL_UART_Receive_IT(&huart2, &u2_rx_byte, 1);
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

    /* HSI 16MHz -> PLL -> 180MHz SysClk */
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

    /* Activate the Over-Drive mode for 180MHz */
    if (HAL_PWREx_EnableOverDrive() != HAL_OK)
    {
        Error_Handler();
    }

    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                                |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_SYSCLK_DIV4; /* 45 MHz */
    RCC_ClkInitStruct.APB2CLKDivider = RCC_SYSCLK_DIV2; /* 90 MHz */

    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_5) != HAL_OK)
    {
        Error_Handler();
    }
}

/**
  * @brief USART1 Initialization Function (Inter-Node Bus: PA9 TX, PA10 RX)
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
  * @brief USART2 Initialization Function (ST-LINK VCP to PC: PA2 TX, PA3 RX)
  */
static void MX_USART2_UART_Init(void)
{
    __HAL_RCC_USART2_CLK_ENABLE();

    huart2.Instance = USART2;
    huart2.Init.BaudRate = 115200;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;
    if (HAL_UART_Init(&huart2) != HAL_OK)
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
    __HAL_RCC_GPIOC_CLK_ENABLE();

    /* Configure GPIO pin Output Level for User LED LD2 */
    HAL_GPIO_WritePin(LD2_GPIO_PORT, LD2_PIN, GPIO_PIN_RESET);

    /* Configure User LED LD2 on PA5 */
    GPIO_InitStruct.Pin = LD2_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(LD2_GPIO_PORT, &GPIO_InitStruct);

    /* Configure User Button B1 on PC13 */
    GPIO_InitStruct.Pin = B1_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(B1_GPIO_PORT, &GPIO_InitStruct);

    /* Configure USART1 GPIO: PA9=TX, PA10=RX */
    GPIO_InitStruct.Pin = INTERNODE_UART_TX_PIN | INTERNODE_UART_RX_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF7_USART1;
    HAL_GPIO_Init(INTERNODE_UART_PORT, &GPIO_InitStruct);

    /* Configure USART2 GPIO: PA2=TX, PA3=RX */
    GPIO_InitStruct.Pin = HOST_UART_TX_PIN | HOST_UART_RX_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF7_USART2;
    HAL_GPIO_Init(HOST_UART_PORT, &GPIO_InitStruct);

    /* Enable USART Interrupts in NVIC */
    HAL_NVIC_SetPriority(USART1_IRQn, 1, 0);
    HAL_NVIC_EnableIRQ(USART1_IRQn);

    HAL_NVIC_SetPriority(USART2_IRQn, 2, 0);
    HAL_NVIC_EnableIRQ(USART2_IRQn);
}

void Error_Handler(void)
{
    __disable_irq();
    while (1)
    {
        HAL_GPIO_TogglePin(LD2_GPIO_PORT, LD2_PIN);
        for (volatile int i = 0; i < 200000; i++);
    }
}
