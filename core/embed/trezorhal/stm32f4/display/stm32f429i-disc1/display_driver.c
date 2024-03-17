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

#include "display_internal.h"
#include "ili9341_spi.h"
#include "xdisplay.h"

#if (DISPLAY_RESX != 240) || (DISPLAY_RESY != 320)
#error "Incompatible display resolution"
#endif

// Display driver context.
typedef struct {
  // Current display orientation (0, 90, 180, 270)
  int orientation_angle;
  // Current backlight level ranging from 0 to 255
  int backlight_level;
} display_driver_t;

// Display driver instance
static display_driver_t g_display_driver;

void display_init(void) {
  display_driver_t *drv = &g_display_driver;
  memset(drv, 0, sizeof(display_driver_t));

  // Initialize LTDC controller
  BSP_LCD_Init();
  // Initialize external display controller
  ili9341_init();
}

void display_reinit(void) {
  display_driver_t *drv = &g_display_driver;
  memset(drv, 0, sizeof(display_driver_t));
}

void display_finish_actions(void) {
  // Not used and intentionally left empty
}

int display_set_backlight(int level) {
  display_driver_t *drv = &g_display_driver;

  // Just emulation, not doing anything
  drv->backlight_level = level;
  return level;
}

int display_get_backlight(void) {
  display_driver_t *drv = &g_display_driver;

  return drv->backlight_level;
}

int display_set_orientation(int angle) {
  display_driver_t *drv = &g_display_driver;

  if (angle == 0 || angle == 90 || angle == 180 || angle == 270) {
    // Just emulation, not doing anything
    drv->orientation_angle = angle;
  }

  return drv->orientation_angle;
}

int display_get_orientation(void) {
  display_driver_t *drv = &g_display_driver;

  return drv->orientation_angle;
}

void *display_get_frame_addr(void) { return (void *)FRAME_BUFFER_ADDR; }

void display_refresh(void) {
  // Do nothing as using just a single frame buffer
}

const char *display_save(const char *prefix) { return NULL; }

void display_clear_save(void) {}

void display_set_compatible_settings() {}

// Functions for drawing on display
/*

// Fills a rectangle with a specified color
void display_fill(gdc_dma2d_t *dp);

// Copies an RGB565 bitmap to specified rectangle
void display_copy_rgb565(gdc_dma2d_t *dp);

// Copies a MONO4 bitmap to specified rectangle
void display_copy_mono4(gdc_dma2d_t *dp);

// Copies a MONO1P bitmap to specified rectangle
void display_copy_mono1p(gdc_dma2d_t *dp);
*/
