/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include STM32_HAL_H

#define DISPLAY_ILI9341V 0
#define DISPLAY_ST7789V  1

#define CMD(X)  (*((__IO uint8_t *)((uint32_t)(0x60000000))) = (X))
#define DATA(X) (*((__IO uint8_t *)((uint32_t)(0x60000000 | 0x10000))) = (X))

static TIM_HandleTypeDef TIM1_Handle;

#define LED_PWM_TIM_PERIOD (10000)

static uint32_t timer1_get_source_freq() {
    uint32_t source;
    // TIM1 is on APB2
    source = HAL_RCC_GetPCLK2Freq();
    if ((uint32_t)((RCC->CFGR & RCC_CFGR_PPRE2) >> 3) != RCC_HCLK_DIV1) {
        source *= 2;
    }
    return source;
}

static void __attribute__((unused)) display_sleep(void) {
#if DISPLAY_ILI9341V || DISPLAY_ST7789V
    CMD(0x28); // display off
    HAL_Delay(20);
    CMD(0x10); // enter sleep
#endif
}

static void display_unsleep(void) {
#if DISPLAY_ILI9341V || DISPLAY_ST7789V
    CMD(0x11); // exit sleep
    HAL_Delay(20);
    CMD(0x29); // display on
#endif
}

static uint16_t BUFFER_OFFSET_X = 0, BUFFER_OFFSET_Y = 0;

void display_set_orientation(int degrees)
{
#define RGB (0)
#define BGR (1 << 3)
#define MV  (1 << 5)
#define MX  (1 << 6)
#define MY  (1 << 7)
    // memory access control
    switch (degrees) {
        case 0:
            CMD(0x36);
#if DISPLAY_ILI9341V
            DATA(BGR | MX | MY);
            BUFFER_OFFSET_X = 0;
            BUFFER_OFFSET_Y = 80;
#endif
#if DISPLAY_ST7789V
            DATA(RGB | MX | MY );
            BUFFER_OFFSET_X = 0;
            BUFFER_OFFSET_Y = 80;
#endif
            break;
        case 90:
            CMD(0x36);
#if DISPLAY_ILI9341V
            DATA(BGR | MV | MX);
            BUFFER_OFFSET_X = 0;
            BUFFER_OFFSET_Y = 0;
#endif
#if DISPLAY_ST7789V
            DATA(RGB | MV | MY );
            BUFFER_OFFSET_X = 80;
            BUFFER_OFFSET_Y = 0;
#endif
            break;
        case 180:
            CMD(0x36);
#if DISPLAY_ILI9341V
            DATA(BGR);
            BUFFER_OFFSET_X = 0;
            BUFFER_OFFSET_Y = 0;
#endif
#if DISPLAY_ST7789V
            DATA(RGB);
            BUFFER_OFFSET_X = 0;
            BUFFER_OFFSET_Y = 0;
#endif
            break;
        case 270:
            CMD(0x36);
#if DISPLAY_ILI9341V
            DATA(BGR | MV | MY);
            BUFFER_OFFSET_X = 80;
            BUFFER_OFFSET_Y = 0;
#endif
#if DISPLAY_ST7789V
            DATA(RGB | MV | MX);
            BUFFER_OFFSET_X = 0;
            BUFFER_OFFSET_Y = 0;
#endif
            break;
    }
}

void display_set_backlight(int val)
{
    __HAL_TIM_SetCompare(&TIM1_Handle, TIM_CHANNEL_1, LED_PWM_TIM_PERIOD * BACKLIGHT / 255);
}

void display_init(void) {
    // init peripherials
    __GPIOE_CLK_ENABLE();
    __TIM1_CLK_ENABLE();
    __FSMC_CLK_ENABLE();

    GPIO_InitTypeDef GPIO_InitStructure;

    // LCD_RST/PC14
    GPIO_InitStructure.Pin = GPIO_PIN_14;
    GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStructure.Pull = GPIO_PULLUP;
    GPIO_InitStructure.Speed = GPIO_SPEED_HIGH;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_SET);

    // LCD_FMARK/PD12
    GPIO_InitStructure.Pin = GPIO_PIN_12;
    GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
    GPIO_InitStructure.Pull = GPIO_NOPULL;
    GPIO_InitStructure.Speed = GPIO_SPEED_HIGH;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);

    // LCD_PWM/PB13
    GPIO_InitStructure.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStructure.Pull      = GPIO_NOPULL;
    GPIO_InitStructure.Speed     = GPIO_SPEED_HIGH;
    GPIO_InitStructure.Alternate = GPIO_AF1_TIM1;
    GPIO_InitStructure.Pin       = GPIO_PIN_13;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);

    GPIO_InitStructure.Alternate = GPIO_AF12_FSMC;
    //                             LCD_CS/PD7   LCD_RS/PD11   LCD_RD/PD4   LCD_WR/PD5
    GPIO_InitStructure.Pin       = GPIO_PIN_7 | GPIO_PIN_11 | GPIO_PIN_4 | GPIO_PIN_5;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
    //                             LCD_D0/PD14   LCD_D1/PD15   LCD_D2/PD0   LCD_D3/PD1
    GPIO_InitStructure.Pin       = GPIO_PIN_14 | GPIO_PIN_15 | GPIO_PIN_0 | GPIO_PIN_1;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
    //                             LCD_D4/PE7   LCD_D5/PE8   LCD_D6/PE9   LCD_D7/PE10
    GPIO_InitStructure.Pin       = GPIO_PIN_7 | GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10;
    HAL_GPIO_Init(GPIOE, &GPIO_InitStructure);

    // enable PWM timer
    TIM1_Handle.Instance = TIM1;
    TIM1_Handle.Init.Period = LED_PWM_TIM_PERIOD - 1;
    TIM1_Handle.Init.Prescaler = timer1_get_source_freq() / 1000000 - 1; // TIM runs at 1MHz
    TIM1_Handle.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    TIM1_Handle.Init.CounterMode = TIM_COUNTERMODE_UP;
    TIM1_Handle.Init.RepetitionCounter = 0;
    HAL_TIM_PWM_Init(&TIM1_Handle);

    TIM_OC_InitTypeDef TIM_OC_InitStructure;
    TIM_OC_InitStructure.Pulse = 0;
    TIM_OC_InitStructure.OCMode = TIM_OCMODE_PWM2;
    TIM_OC_InitStructure.OCPolarity = TIM_OCPOLARITY_HIGH;
    TIM_OC_InitStructure.OCFastMode = TIM_OCFAST_DISABLE;
    TIM_OC_InitStructure.OCNPolarity = TIM_OCNPOLARITY_HIGH;
    TIM_OC_InitStructure.OCIdleState = TIM_OCIDLESTATE_SET;
    TIM_OC_InitStructure.OCNIdleState = TIM_OCNIDLESTATE_SET;
    HAL_TIM_PWM_ConfigChannel(&TIM1_Handle, &TIM_OC_InitStructure, TIM_CHANNEL_1);
    HAL_TIM_PWM_Start(&TIM1_Handle, TIM_CHANNEL_1);
    HAL_TIMEx_PWMN_Start(&TIM1_Handle, TIM_CHANNEL_1);

    // timing values from:
    // http://ele-tech.com/html/it-is-developed-that-embedded-stm32-fsmc-interface-drives-tft-lcd-to-be-designed.html

    FSMC_NORSRAM_InitTypeDef FSMC_NORSRAMInitStructure;
    FSMC_NORSRAM_TimingTypeDef FSMC_NORSRAMTimingStructure;

    FSMC_NORSRAMTimingStructure.AddressSetupTime = 2;
    FSMC_NORSRAMTimingStructure.AddressHoldTime = 0;
    FSMC_NORSRAMTimingStructure.DataSetupTime = 5;
    FSMC_NORSRAMTimingStructure.BusTurnAroundDuration = 0;
    FSMC_NORSRAMTimingStructure.CLKDivision = 0;
    FSMC_NORSRAMTimingStructure.DataLatency = 0;
    FSMC_NORSRAMTimingStructure.AccessMode = FSMC_ACCESS_MODE_B;

    FSMC_NORSRAMInitStructure.NSBank = FSMC_NORSRAM_BANK1;
    FSMC_NORSRAMInitStructure.DataAddressMux = FSMC_DATA_ADDRESS_MUX_DISABLE;
    FSMC_NORSRAMInitStructure.MemoryType = FSMC_MEMORY_TYPE_NOR;
    FSMC_NORSRAMInitStructure.MemoryDataWidth = FSMC_NORSRAM_MEM_BUS_WIDTH_8;
    FSMC_NORSRAMInitStructure.BurstAccessMode = FSMC_BURST_ACCESS_MODE_DISABLE;
    FSMC_NORSRAMInitStructure.WaitSignalPolarity = FSMC_WAIT_SIGNAL_POLARITY_LOW;
    FSMC_NORSRAMInitStructure.WrapMode = FSMC_WRAP_MODE_DISABLE;
    FSMC_NORSRAMInitStructure.WaitSignalActive = FSMC_WAIT_TIMING_BEFORE_WS;
    FSMC_NORSRAMInitStructure.WriteOperation = FSMC_WRITE_OPERATION_ENABLE;
    FSMC_NORSRAMInitStructure.WaitSignal = FSMC_WAIT_SIGNAL_DISABLE;
    FSMC_NORSRAMInitStructure.ExtendedMode = FSMC_EXTENDED_MODE_DISABLE;
    FSMC_NORSRAMInitStructure.AsynchronousWait = FSMC_ASYNCHRONOUS_WAIT_DISABLE;
    FSMC_NORSRAMInitStructure.WriteBurst = FSMC_WRITE_BURST_DISABLE;
    FSMC_NORSRAMInitStructure.PageSize = FSMC_PAGE_SIZE_NONE;

    FSMC_NORSRAM_Init(FSMC_NORSRAM_DEVICE, &FSMC_NORSRAMInitStructure);
    FSMC_NORSRAM_Timing_Init(FSMC_NORSRAM_DEVICE, &FSMC_NORSRAMTimingStructure, FSMC_NORSRAMInitStructure.NSBank);
//    FSMC_NORSRAM_Extended_Timing_Init(FSMC_NORSRAM_EXTENDED_DEVICE, &FSMC_NORSRAMTimingStructure, FSMC_NORSRAMInitStructure.NSBank, FSMC_NORSRAMInitStructure.ExtendedMode);
    __FSMC_NORSRAM_ENABLE(FSMC_NORSRAM_DEVICE, FSMC_NORSRAMInitStructure.NSBank);

    // hardware reset
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_RESET);
    HAL_Delay(20);
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_SET);
    HAL_Delay(5);
#if DISPLAY_ILI9341V
    CMD(0x01);                                      // software reset
    HAL_Delay(20);
    CMD(0x28);                                      // display off
    CMD(0xCF); DATA(0x00); DATA(0xC1); DATA(0x30;
    CMD(0xED); DATA(0x64); DATA(0x03); DATA(0x12); DATA(0x81);
    CMD(0xE8); DATA(0x85); DATA(0x10); DATA(0x7A);
    CMD(0xCB); DATA(0x39); DATA(0x2C); DATA(0x00); DATA(0x34); DATA(0x02);
    CMD(0xF7); DATA(0x20);
    CMD(0xEA); DATA(0x00); DATA(0x00);
    CMD(0xC0); DATA(0x23);                          // power control   VRH[5:0]
    CMD(0xC1); DATA(0x12);                          // power control   SAP[2:0] BT[3:0]
    CMD(0xC5); DATA(0x60); DATA(0x44);              // vcm control 1
    CMD(0xC7); DATA(0x8A);                          // vcm control 2
    CMD(0x3A); DATA(0x55);                          // memory access control (16-bit 565)
    CMD(0xB1); DATA(0x00); DATA(0x18);              // framerate
    CMD(0xB6); DATA(0x0A); DATA(0xA2);              // display function control
    CMD(0xF6); DATA(0x01); DATA(0x30); DATA(0x00);  // interface control
    CMD(0xF2); DATA(0x00);                          // 3 gamma func disable
    CMD(0x26); DATA(0x01);                          // gamma func enable
    // gamma curve 1
    CMD(0xE0); DATA(0x0F); DATA(0x2F); DATA(0x2C); DATA(0x0B); DATA(0x0F); DATA(0x09); DATA(0x56); DATA(0xD9); DATA(0x4A); DATA(0x0B); DATA(0x14); DATA(0x05); DATA(0x0C); DATA(0x06); DATA(0x00);
    // gamma curve 2
    CMD(0xE1); DATA(0x00); DATA(0x10); DATA(0x13); DATA(0x04); DATA(0x10); DATA(0x06); DATA(0x25); DATA(0x26); DATA(0x3B); DATA(0x04); DATA(0x0B); DATA(0x0A); DATA(0x33); DATA(0x39); DATA(0x0F);
    CMD(0x21);                                      // invert colors
#endif
#if DISPLAY_ST7789V
    CMD(0x01);                                      // software reset
    HAL_Delay(20);
    CMD(0x28);                                      // display off
    CMD(0x3A); DATA(0x55);                          // COLMOD: Interface Pixel format
    CMD(0xB2); DATA(0x08); DATA(0x08); DATA(0x00); DATA(0x22); DATA(0x22); // PORCTRK: Porch setting
    CMD(0xB7); DATA(0x35);                          // GCTRL: Gate Control
    CMD(0xC2); DATA(0x01); DATA(0xFF);              // VDVVRHEN: VDV and VRH Command Enable
    CMD(0xC3); DATA(0x0B);                          // VRHS: VRH Set
    CMD(0xC4); DATA(0x20);                          // VDVS: VDV Set
    CMD(0xBB); DATA(0x20);                          // VCOMS: VCOM setting
    CMD(0xC5); DATA(0x20);                          // VCMOFSET
    // CMD(0xC6); DATA(0x0F);                       // FRCTRL2: Framerate Control (60 Hz)
    CMD(0x35); DATA(0x00);                          // TEON: Tearing Effect Line On
    CMD(0xD0); DATA(0xA4); DATA(0xA1);              // PWCTRL1: Power Control 1
    // gamma curve 1
    // CMD(0xE0); DATA(0x70); DATA(0x2C); DATA(0x2E); DATA(0x15); DATA(0x10); DATA(0x09); DATA(0x48); DATA(0x33); DATA(0x53); DATA(0x0B); DATA(0x19); DATA(0x18); DATA(0x20); DATA(0x25);
    // gamma curve 2
    // CMD(0xE1); DATA(0x70); DATA(0x2C); DATA(0x2E); DATA(0x15); DATA(0x10); DATA(0x09); DATA(0x48); DATA(0x33); DATA(0x53); DATA(0x0B); DATA(0x19); DATA(0x18); DATA(0x20); DATA(0x25);
    CMD(0x26); DATA(0x01);                          // gamma func (gc3) enable
    CMD(0x20);                                      // don't invert colors
#endif
    display_set_orientation(0);
    display_set_backlight(0);
    // clear buffer
    display_clear();
    display_unsleep();
}

static void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1) {
    x0 += BUFFER_OFFSET_X; y0 += BUFFER_OFFSET_Y;
    x1 += BUFFER_OFFSET_X; y1 += BUFFER_OFFSET_Y;
#if DISPLAY_ILI9341V || DISPLAY_ST7789V
    CMD(0x2A); DATA(x0 >> 8); DATA(x0 & 0xFF); DATA(x1 >> 8); DATA(x1 & 0xFF); // column addr set
    CMD(0x2B); DATA(y0 >> 8); DATA(y0 & 0xFF); DATA(y1 >> 8); DATA(y1 & 0xFF); // row addr set
    CMD(0x2C);
#endif
}

void display_refresh(void) {
    while (GPIO_PIN_RESET == HAL_GPIO_ReadPin(GPIOD, GPIO_PIN_12)) { }
    while (GPIO_PIN_SET == HAL_GPIO_ReadPin(GPIOD, GPIO_PIN_12)) { }
}
