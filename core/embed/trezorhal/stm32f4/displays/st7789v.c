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

#include <stdbool.h>
#include <stdint.h>
#include TREZOR_BOARD
#include "backlight_pwm.h"
#include "display_interface.h"
#include "memzero.h"
#include "st7789v.h"
#include STM32_HAL_H

#ifdef TREZOR_MODEL_T
#include "displays/panels/154a.h"
#include "displays/panels/lx154a2411.h"
#include "displays/panels/lx154a2422.h"
#include "displays/panels/tf15411a.h"
#endif

// using const volatile instead of #define results in binaries that change
// only in 1-byte when the flag changes.
// using #define leads compiler to over-optimize the code leading to bigger
// differencies in the resulting binaries.
const volatile uint8_t DISPLAY_ST7789V_INVERT_COLORS = 1;

// FSMC/FMC Bank 1 - NOR/PSRAM 1
#define DISPLAY_MEMORY_BASE 0x60000000
#define DISPLAY_MEMORY_PIN 16
#ifdef USE_DISP_I8080_16BIT_DW
#define DISPLAY_ADDR_SHIFT 2
#elif USE_DISP_I8080_8BIT_DW
#define DISPLAY_ADDR_SHIFT 1
#endif

__IO DISP_MEM_TYPE *const DISPLAY_CMD_ADDRESS =
    (__IO DISP_MEM_TYPE *const)((uint32_t)DISPLAY_MEMORY_BASE);
__IO DISP_MEM_TYPE *const DISPLAY_DATA_ADDRESS =
    (__IO DISP_MEM_TYPE *const)((uint32_t)DISPLAY_MEMORY_BASE |
                                (DISPLAY_ADDR_SHIFT << DISPLAY_MEMORY_PIN));

// section "9.1.3 RDDID (04h): Read Display ID"
// of ST7789V datasheet
#define DISPLAY_ID_ST7789V 0x858552U

// section "6.2.1. Read display identification information (04h)"
// of GC9307 datasheet
#define DISPLAY_ID_GC9307 0x009307U

// section "8.3.23 Read ID4 (D3h)"
// of ILI9341V datasheet
#define DISPLAY_ID_ILI9341V 0x009341U

static int DISPLAY_ORIENTATION = -1;
static display_padding_t DISPLAY_PADDING = {0};

void display_pixeldata(uint16_t c) { PIXELDATA(c); }

void display_pixeldata_dirty(void) {}

#ifdef DISPLAY_IDENTIFY

static uint32_t read_display_id(uint8_t command) {
  volatile uint8_t c = 0;
  uint32_t id = 0;
  CMD(command);
  c = *DISPLAY_DATA_ADDRESS;  // first returned value is a dummy value and
  // should be discarded
  c = *DISPLAY_DATA_ADDRESS;
  id |= (c << 16);
  c = *DISPLAY_DATA_ADDRESS;
  id |= (c << 8);
  c = *DISPLAY_DATA_ADDRESS;
  id |= c;
  return id;
}

static uint32_t display_identify(void) {
  static uint32_t id = 0x000000U;
  static char id_set = 0;

  if (id_set) return id;  // return if id has been already set

  id = read_display_id(0x04);  // RDDID: Read Display ID
  // the default RDDID for ILI9341 should be 0x8000.
  // some display modules return 0x0.
  // the ILI9341 has an extra id, let's check it here.
  if ((id != DISPLAY_ID_ST7789V) &&
      (id != DISPLAY_ID_GC9307)) {         // if not ST7789V and not GC9307
    uint32_t id4 = read_display_id(0xD3);  // Read ID4
    if (id4 == DISPLAY_ID_ILI9341V) {      // definitely found a ILI9341
      id = id4;
    }
  }
  id_set = 1;
  return id;
}
#else
static uint32_t display_identify(void) { return DISPLAY_ID_ST7789V; }
#endif

bool display_is_inverted() {
  bool inv_on = false;
  uint32_t id = display_identify();
  if (id == DISPLAY_ID_ST7789V) {
    volatile uint8_t c = 0;
    CMD(0x09);                  // read display status
    c = *DISPLAY_DATA_ADDRESS;  // don't care
    c = *DISPLAY_DATA_ADDRESS;  // don't care
    c = *DISPLAY_DATA_ADDRESS;  // don't care
    c = *DISPLAY_DATA_ADDRESS;
    if (c & 0x20) {
      inv_on = true;
    }
    c = *DISPLAY_DATA_ADDRESS;  // don't care
  }

  return inv_on;
}

void display_reset_state() {}

static void __attribute__((unused)) display_sleep(void) {
  uint32_t id = display_identify();
  if ((id == DISPLAY_ID_ILI9341V) || (id == DISPLAY_ID_GC9307) ||
      (id == DISPLAY_ID_ST7789V)) {
    CMD(0x28);     // DISPOFF: Display Off
    CMD(0x10);     // SLPIN: Sleep in
    HAL_Delay(5);  // need to wait 5 milliseconds after "sleep in" before
    // sending any new commands
  }
}

static void display_unsleep(void) {
  uint32_t id = display_identify();
  if ((id == DISPLAY_ID_ILI9341V) || (id == DISPLAY_ID_GC9307) ||
      (id == DISPLAY_ID_ST7789V)) {
    CMD(0x11);     // SLPOUT: Sleep Out
    HAL_Delay(5);  // need to wait 5 milliseconds after "sleep out" before
    // sending any new commands
    CMD(0x29);  // DISPON: Display On
  }
}

void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1) {
  x0 += DISPLAY_PADDING.x;
  x1 += DISPLAY_PADDING.x;
  y0 += DISPLAY_PADDING.y;
  y1 += DISPLAY_PADDING.y;
  uint32_t id = display_identify();
  if ((id == DISPLAY_ID_ILI9341V) || (id == DISPLAY_ID_GC9307) ||
      (id == DISPLAY_ID_ST7789V)) {
    CMD(0x2A);
    DATA(x0 >> 8);
    DATA(x0 & 0xFF);
    DATA(x1 >> 8);
    DATA(x1 & 0xFF);  // column addr set
    CMD(0x2B);
    DATA(y0 >> 8);
    DATA(y0 & 0xFF);
    DATA(y1 >> 8);
    DATA(y1 & 0xFF);  // row addr set
    CMD(0x2C);
  }
}

int display_orientation(int degrees) {
  if (degrees != DISPLAY_ORIENTATION) {
    if (degrees == 0 || degrees == 90 || degrees == 180 || degrees == 270) {
      DISPLAY_ORIENTATION = degrees;

      display_set_window(0, 0, MAX_DISPLAY_RESX - 1, MAX_DISPLAY_RESY - 1);
      for (uint32_t i = 0; i < MAX_DISPLAY_RESX * MAX_DISPLAY_RESY; i++) {
        // 2 bytes per pixel because we're using RGB 5-6-5 format
        PIXELDATA(0x0000);
      }
#ifdef TREZOR_MODEL_T
      uint32_t id = display_identify();
      if (id == DISPLAY_ID_GC9307) {
        tf15411a_rotate(degrees, &DISPLAY_PADDING);
      } else {
        lx154a2422_rotate(degrees, &DISPLAY_PADDING);
      }
#else
      DISPLAY_PANEL_ROTATE(degrees, &BUFFER_OFFSET);
#endif
    }
  }
  return DISPLAY_ORIENTATION;
}

int display_get_orientation(void) { return DISPLAY_ORIENTATION; }

int display_backlight(int val) { return backlight_pwm_set(val); }

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

  // identify the controller we will communicate with
#ifdef TREZOR_MODEL_T
  uint32_t id = display_identify();
  if (id == DISPLAY_ID_GC9307) {
    tf15411a_init_seq();
  } else if (id == DISPLAY_ID_ST7789V) {
    if (DISPLAY_ST7789V_INVERT_COLORS) {
      lx154a2422_init_seq();
    } else {
      lx154a2411_init_seq();
    }
  } else if (id == DISPLAY_ID_ILI9341V) {
    _154a_init_seq();
  }
#else
  DISPLAY_PANEL_INIT_SEQ();
#endif

  display_unsleep();
}

void display_setup_fmc(void) {
  // Reference UM1725 "Description of STM32F4 HAL and LL drivers",
  // section 64.2.1 "How to use this driver"
  SRAM_HandleTypeDef external_display_data_sram = {0};
  external_display_data_sram.Instance = FMC_NORSRAM_DEVICE;
  external_display_data_sram.Extended = FMC_NORSRAM_EXTENDED_DEVICE;
  external_display_data_sram.Init.NSBank = FMC_NORSRAM_BANK1;
  external_display_data_sram.Init.DataAddressMux = FMC_DATA_ADDRESS_MUX_DISABLE;
  external_display_data_sram.Init.MemoryType = FMC_MEMORY_TYPE_SRAM;
#ifdef USE_DISP_I8080_16BIT_DW
  external_display_data_sram.Init.MemoryDataWidth =
      FMC_NORSRAM_MEM_BUS_WIDTH_16;
#elif USE_DISP_I8080_8BIT_DW
  external_display_data_sram.Init.MemoryDataWidth = FMC_NORSRAM_MEM_BUS_WIDTH_8;
#endif
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
  normal_mode_timing.AddressSetupTime = 5;
  normal_mode_timing.AddressHoldTime = 1;  // don't care
  normal_mode_timing.DataSetupTime = 6;
  normal_mode_timing.BusTurnAroundDuration = 0;  // don't care
  normal_mode_timing.CLKDivision = 2;            // don't care
  normal_mode_timing.DataLatency = 2;            // don't care
  normal_mode_timing.AccessMode = FMC_ACCESS_MODE_A;

  HAL_SRAM_Init(&external_display_data_sram, &normal_mode_timing, NULL);
}

void display_init(void) {
  // init peripherals
  __HAL_RCC_GPIOE_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();
  __HAL_RCC_FMC_CLK_ENABLE();

  backlight_pwm_init();

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

#ifdef DISPLAY_TE_PIN
  // LCD_FMARK (tearing effect)
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Alternate = 0;
  GPIO_InitStructure.Pin = DISPLAY_TE_PIN;
  HAL_GPIO_Init(DISPLAY_TE_PORT, &GPIO_InitStructure);
#endif

  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Alternate = GPIO_AF12_FMC;
  //                       LCD_CS/PD7   LCD_RS/PD11   LCD_RD/PD4   LCD_WR/PD5
  GPIO_InitStructure.Pin = GPIO_PIN_7 | GPIO_PIN_11 | GPIO_PIN_4 | GPIO_PIN_5;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
  //                       LCD_D0/PD14   LCD_D1/PD15   LCD_D2/PD0   LCD_D3/PD1
  GPIO_InitStructure.Pin = GPIO_PIN_14 | GPIO_PIN_15 | GPIO_PIN_0 | GPIO_PIN_1;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
  //                       LCD_D4/PE7   LCD_D5/PE8   LCD_D6/PE9   LCD_D7/PE10
  GPIO_InitStructure.Pin = GPIO_PIN_7 | GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10;
  HAL_GPIO_Init(GPIOE, &GPIO_InitStructure);
#ifdef USE_DISP_I8080_16BIT_DW
  //                       LCD_D8/PE11   LCD_D9/PE12   LCD_D10/PE13 LCD_D11/PE14
  GPIO_InitStructure.Pin =
      GPIO_PIN_11 | GPIO_PIN_12 | GPIO_PIN_13 | GPIO_PIN_14;
  HAL_GPIO_Init(GPIOE, &GPIO_InitStructure);
  //                       LCD_D12/PE15
  GPIO_InitStructure.Pin = GPIO_PIN_15;
  HAL_GPIO_Init(GPIOE, &GPIO_InitStructure);
  //                       LCD_D13/PD8   LCD_D14/PD9   LCD_D15/PD10
  GPIO_InitStructure.Pin = GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
#endif

  display_setup_fmc();

  display_init_seq();

  display_set_little_endian();
}

void display_reinit(void) {
  // reinitialize FMC to set correct timing, have to do this in reinit because
  // boardloader is fixed.
  display_setup_fmc();

  // important for model T as this is not set in boardloader
  display_set_little_endian();

  DISPLAY_ORIENTATION = 0;

  backlight_pwm_reinit();

#ifdef TREZOR_MODEL_T
  uint32_t id = display_identify();
  if (id == DISPLAY_ID_ST7789V && display_is_inverted()) {
    // newest TT display - set proper gamma
    lx154a2422_gamma();
  } else if (id == DISPLAY_ID_ST7789V) {
    lx154a2411_gamma();
  }
#endif
}

void display_sync(void) {
#ifdef DISPLAY_TE_PIN
  uint32_t id = display_identify();
  if (id && (id != DISPLAY_ID_GC9307)) {
    // synchronize with the panel synchronization signal
    // in order to avoid visual tearing effects
    while (GPIO_PIN_SET == HAL_GPIO_ReadPin(DISPLAY_TE_PORT, DISPLAY_TE_PIN)) {
    }
    while (GPIO_PIN_RESET ==
           HAL_GPIO_ReadPin(DISPLAY_TE_PORT, DISPLAY_TE_PIN)) {
    }
  }
#endif
}

void display_refresh(void) {}

void display_set_little_endian(void) {
  uint32_t id = display_identify();
  if (id == DISPLAY_ID_GC9307) {
    // CANNOT SET ENDIAN FOR GC9307
  } else if (id == DISPLAY_ID_ST7789V) {
    CMD(0xB0);
    DATA(0x00);
    DATA(0xF8);
  } else if (id == DISPLAY_ID_ILI9341V) {
    // Interface Control: XOR BGR as ST7789V does
    CMD(0xF6);
    DATA(0x09);
    DATA(0x30);
    DATA(0x20);
  }
}

void display_set_big_endian(void) {
  uint32_t id = display_identify();
  if (id == DISPLAY_ID_GC9307) {
    // CANNOT SET ENDIAN FOR GC9307
  } else if (id == DISPLAY_ID_ST7789V) {
    CMD(0xB0);
    DATA(0x00);
    DATA(0xF0);
  } else if (id == DISPLAY_ID_ILI9341V) {
    // Interface Control: XOR BGR as ST7789V does
    CMD(0xF6);
    DATA(0x09);
    DATA(0x30);
    DATA(0x00);
  }
}

const char *display_save(const char *prefix) { return NULL; }

void display_clear_save(void) {}

uint8_t *display_get_wr_addr(void) { return (uint8_t *)DISPLAY_DATA_ADDRESS; }

uint16_t display_get_window_offset(void) { return 0; }

void display_shift_window(uint16_t pixels) {}
