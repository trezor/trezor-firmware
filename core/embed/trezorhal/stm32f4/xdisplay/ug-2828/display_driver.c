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
#include <string.h>

#include TREZOR_BOARD
#include STM32_HAL_H

#include "mpu.h"
#include "xdisplay.h"

#if (DISPLAY_RESX != 128) || (DISPLAY_RESY != 128)
#error "Incompatible display resolution"
#endif

// This file implements display driver for monochromatic display V-2864KSWEG01
// with 128x128 resolution connected to CPU via SPI interface.
//
// This type of displayed was used on some preliminary dev kits for T3T1 (Trezor
// TS3)

#define FRAME_BUFFER_SIZE (DISPLAY_RESX * DISPLAY_RESY)

__attribute__((section(".fb1"))) uint8_t g_framebuf[FRAME_BUFFER_SIZE];

// Display driver context.
typedef struct {
  // Set if the driver is initialized
  bool initialized;
  // Frame buffer (8-bit Mono)
  uint8_t *framebuf;
  // Current display orientation (0 or 180)
  int orientation_angle;
  // Current backlight level ranging from 0 to 255
  int backlight_level;
} display_driver_t;

// Display driver instance
static display_driver_t g_display_driver = {
    .initialized = false,
};

// Macros to access display parallel interface

// FSMC/FMC Bank 1 - NOR/PSRAM 1
#define DISPLAY_MEMORY_BASE 0x60000000
#define DISPLAY_MEMORY_PIN 16

#define CMD_ADDR *((__IO uint8_t *)((uint32_t)(DISPLAY_MEMORY_BASE)))
#define DATA_ADDR                                      \
  (*((__IO uint8_t *)((uint32_t)(DISPLAY_MEMORY_BASE | \
                                 (1 << DISPLAY_MEMORY_PIN)))))

#define ISSUE_CMD_BYTE(X) \
  do {                    \
    (CMD_ADDR) = (X);     \
  } while (0)
#define ISSUE_DATA_BYTE(X) \
  do {                     \
    (DATA_ADDR) = (X);     \
  } while (0)

// ---------------------------------------------------------------------------
// Display controller registers
// ---------------------------------------------------------------------------

#define OLED_SETCONTRAST 0x81
#define OLED_DISPLAYALLON_RESUME 0xA4
#define OLED_DISPLAYALLON 0xA5
#define OLED_NORMALDISPLAY 0xA6
#define OLED_INVERTDISPLAY 0xA7
#define OLED_DISPLAYOFF 0xAE
#define OLED_DISPLAYON 0xAF
#define OLED_SETDISPLAYOFFSET 0xD3
#define OLED_SETCOMPINS 0xDA
#define OLED_SETVCOMDETECT 0xDB
#define OLED_SETDISPLAYCLOCKDIV 0xD5
#define OLED_SETPRECHARGE 0xD9
#define OLED_SETMULTIPLEX 0xA8
#define OLED_SETLOWCOLUMN 0x00
#define OLED_SETHIGHCOLUMN 0x10
#define OLED_SETSTARTLINE 0x40
#define OLED_MEMORYMODE 0x20
#define OLED_COMSCANINC 0xC0
#define OLED_COMSCANDEC 0xC8
#define OLED_SEGREMAP 0xA0
#define OLED_CHARGEPUMP 0x8D

// Dipslay specific initialization sequence
static const uint8_t ug_2828tswig01_init_seq[] = {
    OLED_DISPLAYOFF,
    // Divide ratio 0, Oscillator Frequency +0%
    OLED_SETDISPLAYCLOCKDIV, 0x50,
    // Set Memory Addressing Mode - page addressing mode
    0x20,
    // Set Contrast Control Register
    OLED_SETCONTRAST, 0x8F,
    // Set DC-DC Setting: (Double Bytes Command)
    0xAD, 0x8A,
    // Set Segment Re-map
    OLED_SEGREMAP | 0x01,
    // Set COM Output Scan Direction
    OLED_COMSCANDEC,
    // Set Display Start Line:（Double Bytes Command）
    0xDC, 0x00,
    // Set Display Offset:（Double Bytes Command）
    OLED_SETDISPLAYOFFSET, 0x00,
    // Set Discharge / Pre-Charge Period (Double Bytes Command)
    OLED_SETPRECHARGE, 0x22,
    // Set VCOM Deselect Level
    OLED_SETVCOMDETECT, 0x35,
    // Set Multiplex Ratio
    OLED_SETMULTIPLEX, 0x7F,
    // Set Page
    0xB0,
    // Reset column
    OLED_SETLOWCOLUMN | 0, OLED_SETHIGHCOLUMN | 0,

    // Set Entire Display Off
    //   to be clear, this command turns off the function
    //   which turns entire display on, but it does not clear
    //   the data in display RAM
    OLED_DISPLAYALLON_RESUME,
    // Set Normal Display
    OLED_NORMALDISPLAY};

static void __attribute__((unused)) display_sleep(void) {
  // Display OFF
  ISSUE_CMD_BYTE(OLED_DISPLAYOFF);
  HAL_Delay(5);
  // Vpp disable
  HAL_GPIO_WritePin(GPIOD, GPIO_PIN_8, GPIO_PIN_RESET);
}

static void display_resume(void) {
  // Vpp enable
  HAL_GPIO_WritePin(GPIOD, GPIO_PIN_8, GPIO_PIN_SET);
  // 100 ms mandatory wait
  HAL_Delay(100);
  // Display ON
  ISSUE_CMD_BYTE(OLED_DISPLAYON);
}

// Sets the display cursor to the specific row and column
static void display_set_page_and_col(uint8_t page, uint8_t col) {
  if (page < (DISPLAY_RESY / 8)) {
    ISSUE_CMD_BYTE(0xB0 | (page & 0xF));

    if (col < DISPLAY_RESX) {
      ISSUE_CMD_BYTE(OLED_SETHIGHCOLUMN | ((col & 0x70) >> 4));
      ISSUE_CMD_BYTE(OLED_SETLOWCOLUMN | (col & 0x0F));
    } else {
      // Reset column to start
      ISSUE_CMD_BYTE(OLED_SETHIGHCOLUMN);
      ISSUE_CMD_BYTE(OLED_SETLOWCOLUMN);
    }
  }
}

#define COLLECT_ROW_BYTE(src)                           \
  (0 | (*(src + (0 * DISPLAY_RESX)) >= 128 ? 128 : 0) | \
   (*(src + (1 * DISPLAY_RESX)) >= 128 ? 64 : 0) |      \
   (*(src + (2 * DISPLAY_RESX)) >= 128 ? 32 : 0) |      \
   (*(src + (3 * DISPLAY_RESX)) >= 128 ? 16 : 0) |      \
   (*(src + (4 * DISPLAY_RESX)) >= 128 ? 8 : 0) |       \
   (*(src + (5 * DISPLAY_RESX)) >= 128 ? 4 : 0) |       \
   (*(src + (6 * DISPLAY_RESX)) >= 128 ? 2 : 0) |       \
   (*(src + (7 * DISPLAY_RESX)) >= 128 ? 1 : 0))

// Copies the framebuffer to the display via SPI interface
static void display_sync_with_fb(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return NULL;
  }

  for (int y = 0; y < DISPLAY_RESY / 8; y++) {
    display_set_page_and_col(y, 0);
    uint8_t *src = &drv->framebuf[y * DISPLAY_RESX * 8];
    for (int x = 0; x < DISPLAY_RESX; x++) {
      ISSUE_DATA_BYTE(COLLECT_ROW_BYTE(src));
      src++;
    }
  }
}

static void display_init_controller(void) {
  // LCD_RST/PC14
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_RESET);
  // wait 10 milliseconds. only needs to be low for 10 microseconds.
  // my dev display module ties display reset and touch panel reset together.
  // keeping this low for max(display_reset_time, ctpm_reset_time) aids
  // development and does not hurt.
  HAL_Delay(10);

  // LCD_RST/PC14
  HAL_GPIO_WritePin(GPIOC, GPIO_PIN_14, GPIO_PIN_SET);
  // max wait time for hardware reset is 120 milliseconds
  // (experienced display flakiness using only 5ms wait before sending commands)
  HAL_Delay(120);

  // Apply initialization sequence specific to this display controller/panel
  for (int i = 0; i < sizeof(ug_2828tswig01_init_seq); i++) {
    ISSUE_CMD_BYTE(ug_2828tswig01_init_seq[i]);
  }

  // Resume the suspended display
  display_resume();
  // Clear display internal framebuffer
  display_sync_with_fb();
}

static void display_init_interface(void) {
  // init peripherals
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();
  __HAL_RCC_GPIOE_CLK_ENABLE();
  __HAL_RCC_FMC_CLK_ENABLE();

  GPIO_InitTypeDef GPIO_InitStructure = {0};

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
  //                       LCD_CS/PD7   LCD_RS/PD11   LCD_RD/PD4   LCD_WR/PD5
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
  SRAM_HandleTypeDef display_sram = {0};
  display_sram.Instance = FMC_NORSRAM_DEVICE;
  display_sram.Extended = FMC_NORSRAM_EXTENDED_DEVICE;
  display_sram.Init.NSBank = FMC_NORSRAM_BANK1;
  display_sram.Init.DataAddressMux = FMC_DATA_ADDRESS_MUX_DISABLE;
  display_sram.Init.MemoryType = FMC_MEMORY_TYPE_SRAM;
  display_sram.Init.MemoryDataWidth = FMC_NORSRAM_MEM_BUS_WIDTH_8;
  display_sram.Init.BurstAccessMode = FMC_BURST_ACCESS_MODE_DISABLE;
  display_sram.Init.WaitSignalPolarity = FMC_WAIT_SIGNAL_POLARITY_LOW;
  display_sram.Init.WrapMode = FMC_WRAP_MODE_DISABLE;
  display_sram.Init.WaitSignalActive = FMC_WAIT_TIMING_BEFORE_WS;
  display_sram.Init.WriteOperation = FMC_WRITE_OPERATION_ENABLE;
  display_sram.Init.WaitSignal = FMC_WAIT_SIGNAL_DISABLE;
  display_sram.Init.ExtendedMode = FMC_EXTENDED_MODE_DISABLE;
  display_sram.Init.AsynchronousWait = FMC_ASYNCHRONOUS_WAIT_DISABLE;
  display_sram.Init.WriteBurst = FMC_WRITE_BURST_DISABLE;
  display_sram.Init.ContinuousClock = FMC_CONTINUOUS_CLOCK_SYNC_ONLY;
  display_sram.Init.PageSize = FMC_PAGE_SIZE_NONE;

  // reference RM0090 section 37.5 Table 259, 37.5.4, Mode 1 SRAM, and 37.5.6
  FMC_NORSRAM_TimingTypeDef normal_mode_timing = {0};
  normal_mode_timing.AddressSetupTime = 10;
  normal_mode_timing.AddressHoldTime = 10;
  normal_mode_timing.DataSetupTime = 10;
  normal_mode_timing.BusTurnAroundDuration = 0;
  normal_mode_timing.CLKDivision = 2;
  normal_mode_timing.DataLatency = 2;
  normal_mode_timing.AccessMode = FMC_ACCESS_MODE_A;

  HAL_SRAM_Init(&display_sram, &normal_mode_timing, NULL);
}

void display_init(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (drv->initialized) {
    return;
  }

  memset(drv, 0, sizeof(display_driver_t));
  drv->framebuf = g_framebuf;

  if (mode == DISPLAY_RESET_CONTENT) {
    // Initialize GPIO & FSMC controller
    display_init_interface();
    // Initialize display controller
    display_init_controller();
  }

  drv->initialized = true;
}

void display_deinit(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  mpu_set_unpriv_fb(NULL, 0);

  drv->initialized = false;
}

int display_set_backlight(int level) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  if (level != drv->backlight_level) {
    if (level >= 0 && level <= 255) {
      drv->backlight_level = level;
      // Set Contrast Control Register: (Double Bytes Command)
      ISSUE_CMD_BYTE(OLED_SETCONTRAST);
      ISSUE_CMD_BYTE(level & 0xFF);
    }
  }

  return drv->backlight_level;
}

int display_get_backlight(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  return drv->backlight_level;
}

int display_set_orientation(int angle) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  if (angle != drv->orientation_angle) {
    if (angle == 0 || angle == 180) {
      drv->orientation_angle = angle;
      if (angle == 0) {
        // Set Segment Re-map: (A0H - A1H)
        ISSUE_CMD_BYTE(OLED_SEGREMAP | 0x01);
        // Set COM Output Scan Direction
        ISSUE_CMD_BYTE(OLED_COMSCANDEC);
      } else {
        // Set Segment Re-map: (A0H - A1H)
        ISSUE_CMD_BYTE(OLED_SEGREMAP | 0x00);
        // Set COM Output Scan Direction
        ISSUE_CMD_BYTE(OLED_COMSCANINC);
      }
    }
  }

  return drv->orientation_angle;
}

int display_get_orientation(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  return drv->orientation_angle;
}

bool display_get_frame_buffer(display_fb_info_t *fb) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    fb->ptr = NULL;
    fb->stride = 0;
    return false;
  } else {
    fb->ptr = &drv->framebuf[0];
    fb->stride = DISPLAY_RESX;
    // Enable access to the frame buffer from the unprivileged code
    mpu_set_unpriv_fb(fb->ptr, FRAME_BUFFER_SIZE);
    return true;
  }
}

void display_refresh(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return NULL;
  }

  // Disable access to the frame buffer from the unprivileged code
  mpu_set_unpriv_fb(NULL, 0);

  // Copy the frame buffer to the display
  display_sync_with_fb();
}

void display_fill(const gfx_bitblt_t *bb) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return NULL;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = &drv->framebuf[DISPLAY_RESX * bb_new.dst_y];
  bb_new.dst_stride = DISPLAY_RESX;

  mono8_fill(&bb_new);
}

void display_copy_mono1p(const gfx_bitblt_t *bb) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return NULL;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = &drv->framebuf[DISPLAY_RESX * bb_new.dst_y];
  bb_new.dst_stride = DISPLAY_RESX;

  mono8_copy_mono1p(&bb_new);
}
