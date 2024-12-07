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

#ifdef KERNEL_MODE

#include <io/display.h>
#include <sys/mpu.h>

#include "display_internal.h"
#include "ili9341_spi.h"

#if (DISPLAY_RESX != 240) || (DISPLAY_RESY != 320)
#error "Incompatible display resolution"
#endif

// Display driver context.
typedef struct {
  // Set if the driver is initialized
  bool initialized;
  // Pointer to the frame buffer
  uint16_t *framebuf;
  // Current display orientation (0, 90, 180, 270)
  int orientation_angle;
  // Current backlight level ranging from 0 to 255
  int backlight_level;
} display_driver_t;

// Display driver instance
static display_driver_t g_display_driver = {
    .initialized = false,
};

void display_init(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (drv->initialized) {
    return;
  }

  memset(drv, 0, sizeof(display_driver_t));
  drv->framebuf = (uint16_t *)FRAME_BUFFER_ADDR;

  if (mode == DISPLAY_RESET_CONTENT) {
    // Initialize LTDC controller
    BSP_LCD_Init();
    // Initialize external display controller
    ili9341_init();
  }

  drv->initialized = true;
}

void display_deinit(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  mpu_set_active_fb(NULL, 0);

  drv->initialized = false;
}

int display_set_backlight(int level) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  // Just emulation, not doing anything
  drv->backlight_level = level;
  return level;
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

  if (angle == 0 || angle == 90 || angle == 180 || angle == 270) {
    // Just emulation, not doing anything
    drv->orientation_angle = angle;
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
    fb->ptr = (void *)drv->framebuf;
    fb->stride = DISPLAY_RESX * sizeof(uint16_t);
    // Enable access to the frame buffer from the unprivileged code
    mpu_set_active_fb(fb->ptr, FRAME_BUFFER_SIZE);
    return true;
  }
}

void display_refresh(void) {
  // Do nothing as using just a single frame buffer

  // Disable access to the frame buffer from the unprivileged code
  mpu_set_active_fb(NULL, 0);
}

void display_fill(const gfx_bitblt_t *bb) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = drv->framebuf + (DISPLAY_RESX * bb_new.dst_y);
  bb_new.dst_stride = DISPLAY_RESX * sizeof(uint16_t);

  gfx_rgb565_fill(&bb_new);
}

void display_copy_rgb565(const gfx_bitblt_t *bb) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = drv->framebuf + (DISPLAY_RESX * bb_new.dst_y);
  bb_new.dst_stride = DISPLAY_RESX * sizeof(uint16_t);

  gfx_rgb565_copy_rgb565(&bb_new);
}

void display_copy_mono1p(const gfx_bitblt_t *bb) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = drv->framebuf + (DISPLAY_RESX * bb_new.dst_y);
  bb_new.dst_stride = DISPLAY_RESX * sizeof(uint16_t);

  gfx_rgb565_copy_mono1p(&bb_new);
}

void display_copy_mono4(const gfx_bitblt_t *bb) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = drv->framebuf + (DISPLAY_RESX * bb_new.dst_y);
  bb_new.dst_stride = DISPLAY_RESX * sizeof(uint16_t);

  gfx_rgb565_copy_mono4(&bb_new);
}

#endif
