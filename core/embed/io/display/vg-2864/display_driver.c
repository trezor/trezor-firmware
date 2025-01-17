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

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/display.h>
#include <rtl/sizedefs.h>
#include <sys/mpu.h>

#ifdef USE_TRUSTZONE
#include <sys/trustzone.h>
#endif

#ifdef USE_CONSUMPTION_MASK
#include <sec/consumption_mask.h>
#endif

#ifdef KERNEL_MODE
#if (DISPLAY_RESX != 128) || (DISPLAY_RESY != 64)
#error "Incompatible display resolution"
#endif

// Hardware requires physical frame buffer alignment
#ifdef USE_TRUSTZONE
#define PHYSICAL_FRAME_BUFFER_ALIGNMENT TZ_SRAM_ALIGNMENT
#else
#define PHYSICAL_FRAME_BUFFER_ALIGNMENT 4
#endif

// This file implements display driver for monochromatic display V-2864KSWEG01
// with 128x64 resolution connected to CPU via SPI interface.
//
// This type of display is used with T3B1 model (Trezor TS3)
#define FRAME_BUFFER_SIZE \
  ALIGN_UP_CONST(DISPLAY_RESX *DISPLAY_RESY, PHYSICAL_FRAME_BUFFER_ALIGNMENT)

static
    __attribute__((section(".fb1"), aligned(PHYSICAL_FRAME_BUFFER_ALIGNMENT)))
    uint8_t g_framebuf[FRAME_BUFFER_SIZE];

// Display driver context.
typedef struct {
  // Set if the driver is initialized
  bool initialized;
  // SPI driver instance
  SPI_HandleTypeDef spi;
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

// Display controller registers
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

// Display controller initialization sequence
static const uint8_t vg_2864ksweg01_init_seq[] = {OLED_DISPLAYOFF,
                                                  OLED_SETDISPLAYCLOCKDIV,
                                                  0x80,
                                                  OLED_SETMULTIPLEX,
                                                  0x3F,  // 128x64
                                                  OLED_SETDISPLAYOFFSET,
                                                  0x00,
                                                  OLED_SETSTARTLINE | 0x00,
                                                  OLED_CHARGEPUMP,
                                                  0x14,
                                                  OLED_MEMORYMODE,
                                                  0x00,
                                                  OLED_SEGREMAP | 0x01,
                                                  OLED_COMSCANDEC,
                                                  OLED_SETCOMPINS,
                                                  0x12,  // 128x64
                                                  OLED_SETCONTRAST,
                                                  0xCF,
                                                  OLED_SETPRECHARGE,
                                                  0xF1,
                                                  OLED_SETVCOMDETECT,
                                                  0x40,
                                                  OLED_DISPLAYALLON_RESUME,
                                                  OLED_NORMALDISPLAY,
                                                  OLED_DISPLAYON};

// Configures SPI driver/controller
static bool display_init_spi(display_driver_t *drv) {
  drv->spi.Instance = OLED_SPI;
  drv->spi.State = HAL_SPI_STATE_RESET;
  drv->spi.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_16;
  drv->spi.Init.Direction = SPI_DIRECTION_2LINES;
  drv->spi.Init.CLKPhase = SPI_PHASE_1EDGE;
  drv->spi.Init.CLKPolarity = SPI_POLARITY_LOW;
  drv->spi.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
  drv->spi.Init.CRCPolynomial = 7;
  drv->spi.Init.DataSize = SPI_DATASIZE_8BIT;
  drv->spi.Init.FirstBit = SPI_FIRSTBIT_MSB;
  drv->spi.Init.NSS = SPI_NSS_HARD_OUTPUT;
  drv->spi.Init.TIMode = SPI_TIMODE_DISABLE;
  drv->spi.Init.Mode = SPI_MODE_MASTER;

  return (HAL_OK == HAL_SPI_Init(&drv->spi)) ? true : false;
}

// Sends specified number of bytes to the display via SPI interface
static void display_send_bytes(display_driver_t *drv, const uint8_t *data,
                               size_t len) {
  volatile int32_t timeout = 1000;
  for (int i = 0; i < timeout; i++)
    ;

  if (HAL_OK != HAL_SPI_Transmit(&drv->spi, (uint8_t *)data, len, 1000)) {
    // TODO: error
    return;
  }
  while (HAL_SPI_STATE_READY != HAL_SPI_GetState(&drv->spi)) {
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

#define COLLECT_ROW_BYTE_REV(src)                     \
  (0 | (*(src + (0 * DISPLAY_RESX)) >= 128 ? 1 : 0) | \
   (*(src + (1 * DISPLAY_RESX)) >= 128 ? 2 : 0) |     \
   (*(src + (2 * DISPLAY_RESX)) >= 128 ? 4 : 0) |     \
   (*(src + (3 * DISPLAY_RESX)) >= 128 ? 8 : 0) |     \
   (*(src + (4 * DISPLAY_RESX)) >= 128 ? 16 : 0) |    \
   (*(src + (5 * DISPLAY_RESX)) >= 128 ? 32 : 0) |    \
   (*(src + (6 * DISPLAY_RESX)) >= 128 ? 64 : 0) |    \
   (*(src + (7 * DISPLAY_RESX)) >= 128 ? 128 : 0))

// Copies the framebuffer to the display via SPI interface
static void display_sync_with_fb(display_driver_t *drv) {
  static const uint8_t cursor_set_seq[3] = {OLED_SETLOWCOLUMN | 0x00,
                                            OLED_SETHIGHCOLUMN | 0x00,
                                            OLED_SETSTARTLINE | 0x00};

  // SPI select
  HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_RESET);
  // Set the cursor to the screen top-left corner
  display_send_bytes(drv, &cursor_set_seq[0], sizeof(cursor_set_seq));

  // SPI deselect
  HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_SET);
  // Set to DATA
  HAL_GPIO_WritePin(OLED_DC_PORT, OLED_DC_PIN, GPIO_PIN_SET);
  // SPI select
  HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_RESET);

  // Send whole framebuffer to the display

  mpu_set_active_fb(drv->framebuf, FRAME_BUFFER_SIZE);

  if (drv->orientation_angle == 0) {
    for (int y = DISPLAY_RESY / 8 - 1; y >= 0; y--) {
      uint8_t buff[DISPLAY_RESX];
      uint8_t *src = &drv->framebuf[y * DISPLAY_RESX * 8];

      for (int x = DISPLAY_RESX - 1; x >= 0; x--) {
        buff[x] = COLLECT_ROW_BYTE(src);
        src++;
      }

      if (HAL_OK != HAL_SPI_Transmit(&drv->spi, &buff[0], sizeof(buff), 1000)) {
        // TODO: error
        return;
      }
    }
  } else {
    for (int y = 0; y < DISPLAY_RESY / 8; y++) {
      uint8_t buff[DISPLAY_RESX];
      uint8_t *src = &drv->framebuf[y * DISPLAY_RESX * 8];

      for (int x = 0; x < DISPLAY_RESX; x++) {
        buff[x] = COLLECT_ROW_BYTE_REV(src);
        src++;
      }

      if (HAL_OK != HAL_SPI_Transmit(&drv->spi, &buff[0], sizeof(buff), 1000)) {
        // TODO: error
        return;
      }
    }
  }

  while (HAL_SPI_STATE_READY != HAL_SPI_GetState(&drv->spi)) {
  }
  mpu_set_active_fb(NULL, 0);

  // SPI deselect
  HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_SET);
  // Set to CMD
  HAL_GPIO_WritePin(OLED_DC_PORT, OLED_DC_PIN, GPIO_PIN_RESET);
}

bool display_init(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(display_driver_t));
  drv->backlight_level = 255;
  drv->framebuf = g_framebuf;

  if (mode == DISPLAY_RESET_CONTENT) {
    OLED_DC_CLK_ENA();
    OLED_CS_CLK_ENA();
    OLED_RST_CLK_ENA();
    OLED_SPI_SCK_CLK_ENA();
    OLED_SPI_MOSI_CLK_ENA();
    OLED_SPI_CLK_ENA();

    GPIO_InitTypeDef GPIO_InitStructure;

    // Set GPIO for OLED display
    GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStructure.Pull = GPIO_NOPULL;
    GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStructure.Alternate = 0;
    GPIO_InitStructure.Pin = OLED_CS_PIN;
    HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_RESET);
    HAL_GPIO_Init(OLED_CS_PORT, &GPIO_InitStructure);
    GPIO_InitStructure.Pin = OLED_DC_PIN;
    HAL_GPIO_WritePin(OLED_DC_PORT, OLED_DC_PIN, GPIO_PIN_RESET);
    HAL_GPIO_Init(OLED_DC_PORT, &GPIO_InitStructure);
    GPIO_InitStructure.Pin = OLED_RST_PIN;
    HAL_GPIO_WritePin(OLED_RST_PORT, OLED_RST_PIN, GPIO_PIN_RESET);
    HAL_GPIO_Init(OLED_RST_PORT, &GPIO_InitStructure);

    // Enable SPI 1 for OLED display
    GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStructure.Pull = GPIO_NOPULL;
    GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStructure.Alternate = OLED_SPI_AF;
    GPIO_InitStructure.Pin = OLED_SPI_SCK_PIN;
    HAL_GPIO_Init(OLED_SPI_SCK_PORT, &GPIO_InitStructure);
    GPIO_InitStructure.Pin = OLED_SPI_MOSI_PIN;
    HAL_GPIO_Init(OLED_SPI_MOSI_PORT, &GPIO_InitStructure);

    // Initialize SPI controller
    display_init_spi(drv);

    // Set to CMD
    HAL_GPIO_WritePin(OLED_DC_PORT, OLED_DC_PIN, GPIO_PIN_RESET);
    // SPI deselect
    HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_SET);

    // Reset the LCD
    HAL_GPIO_WritePin(OLED_RST_PORT, OLED_RST_PIN, GPIO_PIN_SET);
    HAL_Delay(1);
    HAL_GPIO_WritePin(OLED_RST_PORT, OLED_RST_PIN, GPIO_PIN_RESET);
    HAL_Delay(1);
    HAL_GPIO_WritePin(OLED_RST_PORT, OLED_RST_PIN, GPIO_PIN_SET);

    // SPI select
    HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_RESET);
    // Send initialization command sequence
    display_send_bytes(drv, &vg_2864ksweg01_init_seq[0],
                       sizeof(vg_2864ksweg01_init_seq));
    // SPI deselect
    HAL_GPIO_WritePin(OLED_CS_PORT, OLED_CS_PIN, GPIO_PIN_SET);

    // Clear display internal framebuffer
    display_sync_with_fb(drv);
  } else {
    display_init_spi(drv);
  }

  gfx_bitblt_init();

  drv->initialized = true;
  return true;
}

void display_deinit(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  mpu_set_active_fb(NULL, 0);

  gfx_bitblt_deinit();

  drv->initialized = false;
}

#ifdef USE_TRUSTZONE
void display_set_unpriv_access(bool unpriv) {
  tz_set_sram_unpriv((uint32_t)g_framebuf, FRAME_BUFFER_SIZE, unpriv);
}
#endif  // USE_TRUSTZONE

int display_set_backlight(int level) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  drv->backlight_level = 255;
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
      display_sync_with_fb(drv);
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
    mpu_set_active_fb(fb->ptr, FRAME_BUFFER_SIZE);
    return true;
  }
}

void display_refresh(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

#if defined USE_CONSUMPTION_MASK && !defined BOARDLOADER
  // This is an intentional randomization of the consumption masking algorithm
  // after every change on the display
  consumption_mask_randomize();
#endif

  // Disable access to the frame buffer from the unprivileged code
  mpu_set_active_fb(NULL, 0);

  // Copy the frame buffer to the display
  display_sync_with_fb(drv);
}

void display_fill(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = &(((uint8_t *)fb.ptr)[DISPLAY_RESX * bb_new.dst_y]);
  bb_new.dst_stride = DISPLAY_RESX;

  gfx_mono8_fill(&bb_new);
}

void display_copy_mono1p(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = &(((uint8_t *)fb.ptr)[DISPLAY_RESX * bb_new.dst_y]);
  bb_new.dst_stride = DISPLAY_RESX;

  gfx_mono8_copy_mono1p(&bb_new);
}

#endif
