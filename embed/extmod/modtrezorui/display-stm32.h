/*
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include STM32_HAL_H

#ifndef DISPLAY_ILI9341V
#define DISPLAY_ILI9341V 0
#endif

#ifndef DISPLAY_ST7789V
#define DISPLAY_ST7789V 1
#endif

// FSMC/FMC Bank 1 - NOR/PSRAM 1
#define DISPLAY_MEMORY_BASE  0x60000000
#define DISPLAY_MEMORY_PIN   16

#define CMD(X)          (*((__IO uint8_t *)((uint32_t)(DISPLAY_MEMORY_BASE))) = (X))
#define DATA(X)         (*((__IO uint8_t *)((uint32_t)(DISPLAY_MEMORY_BASE | (1 << DISPLAY_MEMORY_PIN)))) = (X))
#define PIXELDATA(X)    DATA((X) >> 8); DATA((X) & 0xFF)

#define LED_PWM_TIM_PERIOD (10000)

static void __attribute__((unused)) display_sleep(void)
{
#if DISPLAY_ILI9341V || DISPLAY_ST7789V
    CMD(0x28); // DISPOFF: Display Off
    CMD(0x10); // SLPIN: Sleep in
    HAL_Delay(5); // need to wait 5 milliseconds after "sleep in" before sending any new commands
#endif
}

static void display_unsleep(void)
{
#if DISPLAY_ILI9341V || DISPLAY_ST7789V
    CMD(0x11); // SLPOUT: Sleep Out
    HAL_Delay(5); // need to wait 5 milliseconds after "sleep out" before sending any new commands
    CMD(0x29); // DISPON: Display On
#endif
}

static struct {
    uint16_t x, y;
} BUFFER_OFFSET;

static void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1)
{
    x0 += BUFFER_OFFSET.x; x1 += BUFFER_OFFSET.x;
    y0 += BUFFER_OFFSET.y; y1 += BUFFER_OFFSET.y;
#if DISPLAY_ILI9341V || DISPLAY_ST7789V
    CMD(0x2A); DATA(x0 >> 8); DATA(x0 & 0xFF); DATA(x1 >> 8); DATA(x1 & 0xFF); // column addr set
    CMD(0x2B); DATA(y0 >> 8); DATA(y0 & 0xFF); DATA(y1 >> 8); DATA(y1 & 0xFF); // row addr set
    CMD(0x2C);
#endif
}

void display_set_orientation(int degrees)
{
#if DISPLAY_ILI9341V || DISPLAY_ST7789V
    #define MV  (1 << 5)
    #define MX  (1 << 6)
    #define MY  (1 << 7)
    // MADCTL: Memory Data Access Control
    // reference section 9.3 in the ILI9341 manual; 8.12 in the ST7789V manual
    char BX = 0, BY = 0;
    uint8_t display_command_parameter = 0;
    switch (degrees) {
        case 0:
            display_command_parameter = 0;
            break;
        case 90:
            display_command_parameter = MV | MX;
            break;
        case 180:
            display_command_parameter = MX | MY;
            BY = 1;
            break;
        case 270:
            display_command_parameter = MV | MY;
            BX = 1;
            break;
    }
    CMD(0x36); DATA(display_command_parameter);
    display_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1); // reset the column and page extents
#endif
    BUFFER_OFFSET.x = BX ? (MAX_DISPLAY_RESY - DISPLAY_RESY) : 0;
    BUFFER_OFFSET.y = BY ? (MAX_DISPLAY_RESY - DISPLAY_RESY) : 0;
}

void display_set_backlight(int val)
{
    TIM1->CCR1 = LED_PWM_TIM_PERIOD * val / 255;
}

void display_hardware_reset(void)
{
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_RESET); // LCD_RST/PC14
    // wait 10 milliseconds. only needs to be low for 10 microseconds.
    // my dev display module ties display reset and touch panel reset together.
    // keeping this low for max(display_reset_time, ctpm_reset_time) aids development and does not hurt.
    HAL_Delay(10);
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_SET); // LCD_RST/PC14
    HAL_Delay(120); // max wait time for hardware reset is 120 milliseconds (experienced display flakiness using only 5ms wait before sending commands)
}

void display_init(void)
{
    // init peripherials
    __HAL_RCC_GPIOE_CLK_ENABLE();
    __HAL_RCC_TIM1_CLK_ENABLE();
    __HAL_RCC_FMC_CLK_ENABLE();

    GPIO_InitTypeDef GPIO_InitStructure;

    // LCD_PWM/PA7 (backlight control)
    GPIO_InitStructure.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStructure.Pull      = GPIO_NOPULL;
    GPIO_InitStructure.Speed     = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStructure.Alternate = GPIO_AF1_TIM1;
    GPIO_InitStructure.Pin       = GPIO_PIN_7;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);

    // enable PWM timer
    TIM_HandleTypeDef TIM1_Handle;
    TIM1_Handle.Instance = TIM1;
    TIM1_Handle.Init.Period = LED_PWM_TIM_PERIOD - 1;
    // TIM1/APB2 source frequency equals to SystemCoreClock in our configuration, we want 1 MHz
    TIM1_Handle.Init.Prescaler = SystemCoreClock / 1000000 - 1;
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

    display_backlight(0);

    HAL_TIM_PWM_Start(&TIM1_Handle, TIM_CHANNEL_1);
    HAL_TIMEx_PWMN_Start(&TIM1_Handle, TIM_CHANNEL_1);

    // LCD_RST/PC14
    GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStructure.Pull = GPIO_NOPULL;
    GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
    GPIO_InitStructure.Alternate = 0;
    GPIO_InitStructure.Pin = GPIO_PIN_14;
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_RESET); // default to keeping display in reset
    HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);

    // LCD_FMARK/PD12 (tearing effect)
    GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
    GPIO_InitStructure.Pull = GPIO_NOPULL;
    GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStructure.Alternate = 0;
    GPIO_InitStructure.Pin = GPIO_PIN_12;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);

    GPIO_InitStructure.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStructure.Pull      = GPIO_NOPULL;
    GPIO_InitStructure.Speed     = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStructure.Alternate = GPIO_AF12_FMC;
    //                             LCD_CS/PD7   LCD_RS/PD11   LCD_RD/PD4   LCD_WR/PD5
    GPIO_InitStructure.Pin       = GPIO_PIN_7 | GPIO_PIN_11 | GPIO_PIN_4 | GPIO_PIN_5;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
    //                             LCD_D0/PD14   LCD_D1/PD15   LCD_D2/PD0   LCD_D3/PD1
    GPIO_InitStructure.Pin       = GPIO_PIN_14 | GPIO_PIN_15 | GPIO_PIN_0 | GPIO_PIN_1;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
    //                             LCD_D4/PE7   LCD_D5/PE8   LCD_D6/PE9   LCD_D7/PE10
    GPIO_InitStructure.Pin       = GPIO_PIN_7 | GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10;
    HAL_GPIO_Init(GPIOE, &GPIO_InitStructure);

    // Reference UM1725 "Description of STM32F4 HAL and LL drivers", section 64.2.1 "How to use this driver"
    SRAM_HandleTypeDef external_display_data_sram;
    external_display_data_sram.Instance = FMC_NORSRAM_DEVICE;
    external_display_data_sram.Init.NSBank = FMC_NORSRAM_BANK1;
    external_display_data_sram.Init.DataAddressMux = FMC_DATA_ADDRESS_MUX_DISABLE;
    external_display_data_sram.Init.MemoryType = FMC_MEMORY_TYPE_SRAM;
    external_display_data_sram.Init.MemoryDataWidth = FMC_NORSRAM_MEM_BUS_WIDTH_8;
    external_display_data_sram.Init.BurstAccessMode = FMC_BURST_ACCESS_MODE_DISABLE;
    external_display_data_sram.Init.WaitSignalPolarity = FMC_WAIT_SIGNAL_POLARITY_LOW;
    external_display_data_sram.Init.WrapMode = FMC_WRAP_MODE_DISABLE;
    external_display_data_sram.Init.WaitSignalActive = FMC_WAIT_TIMING_BEFORE_WS;
    external_display_data_sram.Init.WriteOperation = FMC_WRITE_OPERATION_ENABLE;
    external_display_data_sram.Init.WaitSignal = FMC_WAIT_SIGNAL_DISABLE;
    external_display_data_sram.Init.ExtendedMode = FMC_EXTENDED_MODE_DISABLE;
    external_display_data_sram.Init.AsynchronousWait = FMC_ASYNCHRONOUS_WAIT_DISABLE;
    external_display_data_sram.Init.WriteBurst = FMC_WRITE_BURST_DISABLE;
    external_display_data_sram.Init.ContinuousClock = FMC_CONTINUOUS_CLOCK_SYNC_ONLY;
    external_display_data_sram.Init.PageSize = FMC_PAGE_SIZE_NONE;

    // reference RM0090 section 37.5 Table 259, 37.5.4, Mode 1 SRAM, and 37.5.6
    FMC_NORSRAM_TimingTypeDef normal_mode_timing;
    normal_mode_timing.AddressSetupTime = 4;
    normal_mode_timing.AddressHoldTime = 1;
    normal_mode_timing.DataSetupTime = 4;
    normal_mode_timing.BusTurnAroundDuration = 0;
    normal_mode_timing.CLKDivision = 2;
    normal_mode_timing.DataLatency = 2;
    normal_mode_timing.AccessMode = FMC_ACCESS_MODE_A;

    HAL_SRAM_Init(&external_display_data_sram, &normal_mode_timing, NULL);

    display_hardware_reset();
#if DISPLAY_ILI9341V
    // most recent manual: https://www.newhavendisplay.com/app_notes/ILI9341.pdf
    CMD(0x35); DATA(0x00); // TEON: Tearing Effect Line On; V-blanking only
    CMD(0x3A); DATA(0x55); // COLMOD: Interface Pixel format; 65K color: 16-bit/pixel (RGB 5-6-5 bits input)
    CMD(0xB6); DATA(0x0A); DATA(0xC2); DATA(0x27); DATA(0x00); // Display Function Control: gate scan direction 319 -> 0
    CMD(0xF6); DATA(0x09); DATA(0x30); DATA(0x00); // Interface Control: XOR BGR as ST7789V does
    // the above config is the most important and definitely necessary
    CMD(0xCF); DATA(0x00); DATA(0xC1); DATA(0x30);
    CMD(0xED); DATA(0x64); DATA(0x03); DATA(0x12); DATA(0x81);
    CMD(0xE8); DATA(0x85); DATA(0x10); DATA(0x7A);
    CMD(0xF7); DATA(0x20);
    CMD(0xEA); DATA(0x00); DATA(0x00);
    CMD(0xC0); DATA(0x23);                          // power control   VRH[5:0]
    CMD(0xC1); DATA(0x12);                          // power control   SAP[2:0] BT[3:0]
    CMD(0xC5); DATA(0x60); DATA(0x44);              // vcm control 1
    CMD(0xC7); DATA(0x8A);                          // vcm control 2
    CMD(0xB1); DATA(0x00); DATA(0x18);              // framerate
    CMD(0xF2); DATA(0x00);                          // 3 gamma func disable
    // gamma curve 1
    CMD(0xE0); DATA(0x0F); DATA(0x2F); DATA(0x2C); DATA(0x0B); DATA(0x0F); DATA(0x09); DATA(0x56); DATA(0xD9); DATA(0x4A); DATA(0x0B); DATA(0x14); DATA(0x05); DATA(0x0C); DATA(0x06); DATA(0x00);
    // gamma curve 2
    CMD(0xE1); DATA(0x00); DATA(0x10); DATA(0x13); DATA(0x04); DATA(0x10); DATA(0x06); DATA(0x25); DATA(0x26); DATA(0x3B); DATA(0x04); DATA(0x0B); DATA(0x0A); DATA(0x33); DATA(0x39); DATA(0x0F);
#endif
#if DISPLAY_ST7789V
    CMD(0x35); DATA(0x00); // TEON: Tearing Effect Line On; V-blanking only
    CMD(0x3A); DATA(0x55); // COLMOD: Interface Pixel format; 65K color: 16-bit/pixel (RGB 5-6-5 bits input)
    CMD(0xDF); DATA(0x5A); DATA(0x69); DATA(0x02); DATA(0x01); // CMD2EN: Commands in command table 2 can be executed when EXTC level is Low
    CMD(0xC0); DATA(0x20); // LCMCTRL: LCM Control: XOR RGB setting
    CMD(0xE4); DATA(0x1D); DATA(0x0A); DATA(0x11); // GATECTRL: Gate Control; NL = 240 gate lines, first scan line is gate 80.; gate scan direction 319 -> 0
    // the above config is the most important and definitely necessary
    CMD(0xD0); DATA(0xA4); DATA(0xA1);              // PWCTRL1: Power Control 1
    // gamma curve 1
    // CMD(0xE0); DATA(0x70); DATA(0x2C); DATA(0x2E); DATA(0x15); DATA(0x10); DATA(0x09); DATA(0x48); DATA(0x33); DATA(0x53); DATA(0x0B); DATA(0x19); DATA(0x18); DATA(0x20); DATA(0x25);
    // gamma curve 2
    // CMD(0xE1); DATA(0x70); DATA(0x2C); DATA(0x2E); DATA(0x15); DATA(0x10); DATA(0x09); DATA(0x48); DATA(0x33); DATA(0x53); DATA(0x0B); DATA(0x19); DATA(0x18); DATA(0x20); DATA(0x25);
#endif
    display_clear();
    display_unsleep();
}

void display_refresh(void)
{
    // synchronize with the panel synchronization signal in order to avoid visual tearing effects
    while (GPIO_PIN_RESET == HAL_GPIO_ReadPin(GPIOD, GPIO_PIN_12)) { }
    while (GPIO_PIN_SET == HAL_GPIO_ReadPin(GPIOD, GPIO_PIN_12)) { }
}

void display_save(const char *prefix)
{
}
