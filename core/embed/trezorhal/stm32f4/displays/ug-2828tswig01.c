/*
 * This file is part of the Trezor project, https://trezor.io/
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

#include <stdint.h>
#include TREZOR_BOARD
#include "display_interface.h"
#include "memzero.h"
#include STM32_HAL_H

// FSMC/FMC Bank 1 - NOR/PSRAM 1
#define DISPLAY_MEMORY_BASE 0x60000000
#define DISPLAY_MEMORY_PIN 16

#define CMD(X) (*((__IO uint8_t *)((uint32_t)(DISPLAY_MEMORY_BASE))) = (X))
#define ADDR                                           \
  (*((__IO uint8_t *)((uint32_t)(DISPLAY_MEMORY_BASE | \
                                 (1 << DISPLAY_MEMORY_PIN)))))
#define DATA(X) (ADDR) = (X)

// noop on TR as we don't need to push data to display
#define PIXELDATA_DIRTY()

static int DISPLAY_BACKLIGHT = -1;
static int DISPLAY_ORIENTATION = -1;
struct {
  uint8_t RAM[DISPLAY_RESY / 8][DISPLAY_RESX];
  uint32_t row;
  uint32_t col;
  uint32_t window_x0;
  uint32_t window_x1;
  uint32_t window_y0;
  uint32_t window_y1;
} DISPLAY_STATE;

static void display_set_page_and_col(uint8_t page, uint8_t col) {
  if (page < (DISPLAY_RESY / 8)) {
    CMD(0xB0 | (page & 0xF));

    if (col < DISPLAY_RESX) {
      CMD(0x10 | ((col & 0x70) >> 4));
      CMD(0x00 | (col & 0x0F));
    } else {
      // Reset column to start
      CMD(0x10);
      CMD(0x00);
    }
  }
}

void display_pixeldata(uint16_t c) {
  uint8_t data = DISPLAY_STATE.RAM[DISPLAY_STATE.row / 8][DISPLAY_STATE.col];

  uint8_t bit = 1 << (DISPLAY_STATE.row % 8);

  // set to white if highest bits of all R, G, B values are set to 1
  // bin(10000 100000 10000) = hex(0x8410)
  // otherwise set to black
  if (c & 0x8410) {
    data |= bit;
  } else {
    data &= ~bit;
  }

  DISPLAY_STATE.RAM[DISPLAY_STATE.row / 8][DISPLAY_STATE.col] = data;

  DISPLAY_STATE.col++;

  if (DISPLAY_STATE.col > DISPLAY_STATE.window_x1) {
    // next line
    DISPLAY_STATE.col = DISPLAY_STATE.window_x0;
    DISPLAY_STATE.row++;

    if (DISPLAY_STATE.row > DISPLAY_STATE.window_y1) {
      // reached end of the window, go to start
      DISPLAY_STATE.row = DISPLAY_STATE.window_y1;
    }

    // set display to start of next line, sets also page, even if it stays on
    // the same one
    display_set_page_and_col(DISPLAY_STATE.row / 8, DISPLAY_STATE.col);
  }
}

#define PIXELDATA(c) display_pixeldata(c)

void display_reset_state(void) {
  memzero(DISPLAY_STATE.RAM, sizeof(DISPLAY_STATE.RAM));
  DISPLAY_STATE.row = 0;
  DISPLAY_STATE.col = 0;
  DISPLAY_STATE.window_x0 = 0;
  DISPLAY_STATE.window_x1 = DISPLAY_RESX - 1;
  DISPLAY_STATE.window_y0 = 0;
  DISPLAY_STATE.window_y1 = DISPLAY_RESY - 1;
}

static void __attribute__((unused)) display_sleep(void) {
  CMD(0xAE);  // DISPOFF: Display Off
  HAL_Delay(5);
  HAL_GPIO_WritePin(GPIOD, GPIO_PIN_8, GPIO_PIN_RESET);  // Vpp disable
}

static void display_unsleep(void) {
  HAL_GPIO_WritePin(GPIOD, GPIO_PIN_8, GPIO_PIN_SET);  // Vpp enable
  HAL_Delay(100);                                      // 100 ms mandatory wait
  CMD(0xAF);                                           // Display ON
}

void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1) {
  if (x1 >= DISPLAY_RESX) {
    x1 = DISPLAY_RESX - 1;
  }
  if (y1 >= DISPLAY_RESY) {
    y1 = DISPLAY_RESY - 1;
  }

  if (x0 < DISPLAY_RESX && x1 < DISPLAY_RESX && x0 <= x1 && y0 < DISPLAY_RESY &&
      y1 < DISPLAY_RESY && y0 <= y1) {
    DISPLAY_STATE.window_x0 = x0;
    DISPLAY_STATE.window_x1 = x1;
    DISPLAY_STATE.window_y0 = y0;
    DISPLAY_STATE.window_y1 = y1;
    DISPLAY_STATE.row = y0;
    DISPLAY_STATE.col = x0;

    display_set_page_and_col(DISPLAY_STATE.row / 8, DISPLAY_STATE.col);
  }
}

int display_orientation(int degrees) {
  if (degrees != DISPLAY_ORIENTATION) {
    if (degrees == 0 || degrees == 180) {
      DISPLAY_ORIENTATION = degrees;
      if (degrees == 0) {
        // Set Segment Re-map: (A0H - A1H)
        CMD(0xA1);
        // Set COM Output Scan Direction
        CMD(0xC8);
      }
      if (degrees == 180) {
        // Set Segment Re-map: (A0H - A1H)
        CMD(0xA0);
        // Set COM Output Scan Direction
        CMD(0xC0);
      }
    }
  }

  return DISPLAY_ORIENTATION;
}

int display_get_orientation(void) { return DISPLAY_ORIENTATION; }

int display_backlight(int val) {
  if (DISPLAY_BACKLIGHT != val && val >= 0 && val <= 255) {
    DISPLAY_BACKLIGHT = val;
    // Set Contrast Control Register: (Double Bytes Command)
    CMD(0x81);
    CMD(val & 0xFF);
  }
  return DISPLAY_BACKLIGHT;
}

static void send_init_seq_SH1107(void) {
  // Display OFF
  CMD(0xAE);

  // Set Display Clock Divide Ratio/Oscillator Frequency: (Double Bytes Command)
  CMD(0xD5);
  // Divide ratio 0, Oscillator Frequency +0%
  CMD(0x50);

  // Set Memory Addressing Mode - page addressing mode
  CMD(0x20);

  // Set Contrast Control Register: (Double Bytes Command)
  CMD(0x81);
  CMD(0x8F);

  // Set DC-DC Setting: (Double Bytes Command)
  CMD(0xAD);
  CMD(0x8A);

  // Set Segment Re-map: (A0H - A1H)
  // CMD(0xA0);
  CMD(0xA1);

  // Set COM Output Scan Direction
  CMD(0xC8);
  // CMD(0xC0);

  // Set Display Start Line:（Double Bytes Command）
  CMD(0xDC);
  CMD(0x00);

  // Set Display Offset:（Double Bytes Command）
  CMD(0xD3);
  CMD(0x00);

  // Set Discharge / Pre-Charge Period (Double Bytes Command)
  CMD(0xD9);
  CMD(0x22);

  // Set VCOM Deselect Level
  CMD(0xDB);
  CMD(0x35);

  // Set Multiplex Ratio
  CMD(0xA8);
  CMD(0x7F);

  // Set Page
  CMD(0xB0);
  // Set Column
  CMD(0x00);
  CMD(0x10);

  // Set Entire Display Off
  //   to be clear, this command turns of the function
  //   which turns entire display on, but it does not clear
  //   the data in display RAM
  CMD(0xA4);

  // Set Normal Display
  CMD(0xA6);

  HAL_GPIO_WritePin(GPIOD, GPIO_PIN_8, GPIO_PIN_SET);  // Vpp enable

  // Vpp stabilization period
  HAL_Delay(100);

  display_set_window(0, 0, MAX_DISPLAY_RESX - 1, MAX_DISPLAY_RESY - 1);
  for (int i = 0; i < DISPLAY_RESY; i++) {
    for (int j = 0; j < DISPLAY_RESX; j++) {
      display_pixeldata(0);
    }
  }

  // Display ON
  CMD(0xAF);
}

void display_init_seq(void) {
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_RESET);  // LCD_RST/PC14
  // wait 10 milliseconds. only needs to be low for 10 microseconds.
  // my dev display module ties display reset and touch panel reset together.
  // keeping this low for max(display_reset_time, ctpm_reset_time) aids
  // development and does not hurt.
  HAL_Delay(10);

  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_SET);  // LCD_RST/PC14
  // max wait time for hardware reset is 120 milliseconds
  // (experienced display flakiness using only 5ms wait before sending commands)
  HAL_Delay(120);

  send_init_seq_SH1107();

  display_unsleep();
}

void display_init(void) {
  // init peripherals
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();
  __HAL_RCC_GPIOE_CLK_ENABLE();
  __HAL_RCC_FMC_CLK_ENABLE();

  GPIO_InitTypeDef GPIO_InitStructure;

  // LCD_RST/PC14
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Pin = GPIO_PIN_14;
  // default to keeping display in reset
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_RESET);
  HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);

  // VPP Enable
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Pin = GPIO_PIN_8;
  HAL_GPIO_WritePin(GPIOD, GPIO_PIN_8, GPIO_PIN_RESET);
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);

  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Alternate = GPIO_AF12_FMC;
  //                     LCD_CS/PD7   LCD_RS/PD11   LCD_RD/PD4   LCD_WR/PD5
  GPIO_InitStructure.Pin = GPIO_PIN_7 | GPIO_PIN_11 | GPIO_PIN_4 | GPIO_PIN_5;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
  //                       LCD_D0/PD14   LCD_D1/PD15   LCD_D2/PD0   LCD_D3/PD1
  GPIO_InitStructure.Pin = GPIO_PIN_14 | GPIO_PIN_15 | GPIO_PIN_0 | GPIO_PIN_1;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
  //                       LCD_D4/PE7   LCD_D5/PE8   LCD_D6/PE9   LCD_D7/PE10
  GPIO_InitStructure.Pin = GPIO_PIN_7 | GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10;
  HAL_GPIO_Init(GPIOE, &GPIO_InitStructure);

  // Reference UM1725 "Description of STM32F4 HAL and LL drivers",
  // section 64.2.1 "How to use this driver"
  SRAM_HandleTypeDef external_display_data_sram = {0};
  external_display_data_sram.Instance = FMC_NORSRAM_DEVICE;
  external_display_data_sram.Extended = FMC_NORSRAM_EXTENDED_DEVICE;
  external_display_data_sram.Init.NSBank = FMC_NORSRAM_BANK1;
  external_display_data_sram.Init.DataAddressMux = FMC_DATA_ADDRESS_MUX_DISABLE;
  external_display_data_sram.Init.MemoryType = FMC_MEMORY_TYPE_SRAM;
  external_display_data_sram.Init.MemoryDataWidth = FMC_NORSRAM_MEM_BUS_WIDTH_8;
  external_display_data_sram.Init.BurstAccessMode =
      FMC_BURST_ACCESS_MODE_DISABLE;
  external_display_data_sram.Init.WaitSignalPolarity =
      FMC_WAIT_SIGNAL_POLARITY_LOW;
  external_display_data_sram.Init.WrapMode = FMC_WRAP_MODE_DISABLE;
  external_display_data_sram.Init.WaitSignalActive = FMC_WAIT_TIMING_BEFORE_WS;
  external_display_data_sram.Init.WriteOperation = FMC_WRITE_OPERATION_ENABLE;
  external_display_data_sram.Init.WaitSignal = FMC_WAIT_SIGNAL_DISABLE;
  external_display_data_sram.Init.ExtendedMode = FMC_EXTENDED_MODE_DISABLE;
  external_display_data_sram.Init.AsynchronousWait =
      FMC_ASYNCHRONOUS_WAIT_DISABLE;
  external_display_data_sram.Init.WriteBurst = FMC_WRITE_BURST_DISABLE;
  external_display_data_sram.Init.ContinuousClock =
      FMC_CONTINUOUS_CLOCK_SYNC_ONLY;
  external_display_data_sram.Init.PageSize = FMC_PAGE_SIZE_NONE;

  // reference RM0090 section 37.5 Table 259, 37.5.4, Mode 1 SRAM, and 37.5.6
  FMC_NORSRAM_TimingTypeDef normal_mode_timing = {0};
  normal_mode_timing.AddressSetupTime = 10;
  normal_mode_timing.AddressHoldTime = 10;
  normal_mode_timing.DataSetupTime = 10;
  normal_mode_timing.BusTurnAroundDuration = 0;
  normal_mode_timing.CLKDivision = 2;
  normal_mode_timing.DataLatency = 2;
  normal_mode_timing.AccessMode = FMC_ACCESS_MODE_A;

  HAL_SRAM_Init(&external_display_data_sram, &normal_mode_timing, NULL);

  display_init_seq();
}

void display_sync(void) {}

void display_refresh(void) {
  for (int y = 0; y < (DISPLAY_RESY / 8); y++) {
    display_set_page_and_col(y, 0);
    for (int x = 0; x < DISPLAY_RESX; x++) {
      DATA(DISPLAY_STATE.RAM[y][x]);
    }
  }
}

void display_reinit(void) {}

const char *display_save(const char *prefix) { return NULL; }

void display_clear_save(void) {}
