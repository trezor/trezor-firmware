/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#include STM32_HAL_H

#define CMD(X)  (*((__IO uint8_t *)((uint32_t)(0x60000000))) = (X))
#define DATA(X) (*((__IO uint8_t *)((uint32_t)(0x60000000 | 0x10000))) = (X))

void DATAS(const void *bytes, int len);

void display_sram_init(void) {
    __GPIOE_CLK_ENABLE();
    __FSMC_CLK_ENABLE();

/*
    // LCD_RST/PA3
    GPIO_InitStructure.Pin = GPIO_PIN_3;
    GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStructure.Pull = GPIO_PULLUP;
    GPIO_InitStructure.Speed = GPIO_SPEED_HIGH;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_3, GPIO_PIN_SET);
*/

    GPIO_InitTypeDef GPIO_InitStructure;

    GPIO_InitStructure.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStructure.Pull      = GPIO_PULLUP;
    GPIO_InitStructure.Speed     = GPIO_SPEED_HIGH;
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
}

/*
static void display_sleep(void) {
    CMD(0x28); // display off
    HAL_Delay(20);
    CMD(0x10); // enter sleep
}
*/

static void display_unsleep(void) {
    CMD(0x11); // exit sleep
    HAL_Delay(20);
    CMD(0x29); // display
}

static uint8_t WINDOW_OFFSET_X = 0, WINDOW_OFFSET_Y = 0;

int display_orientation(int degrees)
{
    if (degrees != ORIENTATION) {
        // memory access control
        switch (degrees) {
            case 0:
                CMD(0x36); DATA(0x08 | (1<<6) | (1<<7));
                WINDOW_OFFSET_X = 0;
                WINDOW_OFFSET_Y = 80;
                ORIENTATION = 0;
                break;
            case 90:
                CMD(0x36); DATA(0x08 | (1<<5) | (1<<6));
                WINDOW_OFFSET_X = 0;
                WINDOW_OFFSET_Y = 0;
                ORIENTATION = 90;
                break;
            case 180:
                CMD(0x36); DATA(0x08);
                WINDOW_OFFSET_X = 0;
                WINDOW_OFFSET_Y = 0;
                ORIENTATION = 180;
                break;
            case 270:
                CMD(0x36); DATA(0x08 | (1<<5) | (1<<7));
                WINDOW_OFFSET_X = 80;
                WINDOW_OFFSET_Y = 0;
                ORIENTATION = 270;
                break;
        }
    }
    return ORIENTATION;
}

void display_init(void) {
    display_sram_init();
    CMD(0x01); // software reset
    HAL_Delay(20);
    CMD(0x28); // display off
    CMD(0xCF); DATAS("\x00\xC1\x30", 3);
    CMD(0xED); DATAS("\x64\x03\x12\x81", 4);
    CMD(0xE8); DATAS("\x85\x10\x7A", 3);
    CMD(0xCB); DATAS("\x39\x2C\x00\x34\x02", 5);
    CMD(0xF7); DATA(0x20);
    CMD(0xEA); DATAS("\x00\x00", 2);
    CMD(0xC0); DATA(0x23);                // power control   VRH[5:0]
    CMD(0xC1); DATA(0x12);                // power control   SAP[2:0] BT[3:0]
    CMD(0xC5); DATAS("\x60\x44", 2);      // vcm control 1
    CMD(0xC7); DATA(0x8A);                // vcm control 2
    display_orientation(0);
    CMD(0x3A); DATA(0x55);                // memory access control (16-bit 565)
    CMD(0xB1); DATAS("\x00\x18", 2);      // framerate
    CMD(0xB6); DATAS("\x0A\xA2", 2);      // display function control
    CMD(0xF6); DATAS("\x01\x30\x00", 3);  // interface control
    CMD(0xF2); DATA(0x00);                // 3 gamma func disable
    CMD(0x26); DATA(0x01);                // gamma func enable
    CMD(0xE0); DATAS("\x0F\x2F\x2C\x0B\x0F\x09\x56\xD9\x4A\x0B\x14\x05\x0C\x06\x00", 15); // gamma curve 1
    CMD(0xE1); DATAS("\x00\x10\x13\x04\x10\x06\x25\x26\x3B\x04\x0B\x0A\x33\x39\x0F", 15); // gamma curve 2
    CMD(0x21);                            // invert colors
    display_unsleep();
}

void display_set_window(uint16_t x, uint16_t y, uint16_t w, uint16_t h) {
    x += WINDOW_OFFSET_X;
    y += WINDOW_OFFSET_Y;
    uint16_t x1 = x + w - 1;
    uint16_t y1 = y + h - 1;
    CMD(0x2A); DATA(x >> 8); DATA(x & 0xFF); DATA(x1 >> 8); DATA(x1 & 0xFF); // column addr set
    CMD(0x2B); DATA(y >> 8); DATA(y & 0xFF); DATA(y1 >> 8); DATA(y1 & 0xFF); // row addr set
    CMD(0x2C);
}

void display_update(void) {
}

int display_backlight(int val)
{
    if (val >= 0 && val <= 255) {
        BACKLIGHT = val;
    }
    return BACKLIGHT;
}
