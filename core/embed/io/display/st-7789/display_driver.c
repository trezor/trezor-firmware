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

#include <trezor_rtl.h>

#include <io/display.h>
#include <sys/mpu.h>

#include "display_fb.h"
#include "display_internal.h"
#include "display_io.h"
#include "display_panel.h"

#include <io/backlight.h>

#ifndef BOARDLOADER
#include "../bg_copy/bg_copy.h"
#endif

#define INTERNAL_FB_WIDTH 240
#define INTERNAL_FB_HEIGHT 320

#if (DISPLAY_RESX > INTERNAL_FB_WIDTH) || (DISPLAY_RESY > INTERNAL_FB_HEIGHT)
#error "Incompatible display resolution"
#endif

#ifdef KERNEL_MODE

// Display driver instance
display_driver_t g_display_driver = {
    .initialized = false,
};

bool display_init(display_content_mode_t mode) {
  display_driver_t* drv = &g_display_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(display_driver_t));

#ifdef FRAMEBUFFER
  display_fb_init();
#endif

  if (mode == DISPLAY_RESET_CONTENT) {
#if defined TREZOR_MODEL_T2T1 && !defined BOARDLOADER
    // This is required for the model T to work correctly.
    // Boardloader does this by constant in binary, other stages need to read
    // this from the display
    display_panel_preserve_inversion();
#endif
    display_io_init_gpio();
    display_io_init_fmc();
    display_panel_init();
    display_panel_set_little_endian();
    backlight_init(BACKLIGHT_RESET);
  } else {
    // Reinitialize FMC to set correct timing
    // We have to do this in reinit because boardloader is fixed.
    display_io_init_fmc();

    // Important for model T as this is not set in boardloader
    display_panel_set_little_endian();
    display_panel_reinit();
    backlight_init(BACKLIGHT_RETAIN);
  }

#ifdef FRAMEBUFFER
#ifndef BOARDLOADER
  display_io_init_te_interrupt();
#endif
#endif

  gfx_bitblt_init();

  drv->initialized = true;
  return true;
}

void display_deinit(display_content_mode_t mode) {
  display_driver_t* drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

#ifndef BOARDLOADER
  // Ensure that the ready frame buffer is transferred to
  // the display controller
  display_ensure_refreshed();
#ifdef FRAMEBUFFER
  // Disable periodical interrupt
  NVIC_DisableIRQ(DISPLAY_TE_INTERRUPT_NUM);
#endif
#endif

  gfx_bitblt_deinit();

  mpu_set_active_fb(NULL, 0);

  backlight_deinit(mode == DISPLAY_RESET_CONTENT ? BACKLIGHT_RESET
                                                 : BACKLIGHT_RETAIN);

#ifdef TREZOR_MODEL_T2T1
  // This ensures backward compatibility with legacy bootloader/firmware
  // that relies on this hardware settings from the previous boot stage
  if (mode == DISPLAY_RESET_CONTENT) {
    display_set_orientation(0);
  }
  display_panel_set_big_endian();
#endif

  drv->initialized = false;
}

int display_set_backlight(int level) {
  display_driver_t* drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

#ifndef BOARDLOADER
  // if turning on the backlight, wait until the panel is refreshed
  if (backlight_get() < level && !is_mode_exception()) {
    display_ensure_refreshed();
  }
#endif

  return backlight_set(level);
}

int display_get_backlight(void) { return backlight_get(); }

int display_set_orientation(int angle) {
  display_driver_t* drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  if (angle != drv->orientation_angle) {
    if (angle == 0 || angle == 90 || angle == 180 || angle == 270) {
      drv->orientation_angle = angle;

#ifdef FRAMEBUFFER
      display_fb_clear();
#endif

      display_panel_set_window(0, 0, INTERNAL_FB_WIDTH - 1,
                               INTERNAL_FB_HEIGHT - 1);
      for (uint32_t i = 0; i < INTERNAL_FB_WIDTH * INTERNAL_FB_HEIGHT; i++) {
        // 2 bytes per pixel because we're using RGB 5-6-5 format
        ISSUE_PIXEL_DATA(0x0000);
      }

      display_panel_rotate(angle);
    }
  }

  return drv->orientation_angle;
}

int display_get_orientation(void) {
  display_driver_t* drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  return drv->orientation_angle;
}

#endif  // KERNEL_MODE
