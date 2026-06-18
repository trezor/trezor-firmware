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

// Headless ("none") display driver.
//
// Used by boards that have no display hardware (e.g. bare development
// boards). It implements the full `io/display.h` interface but performs no
// drawing: all bitblt operations are discarded and there is no framebuffer.
// This lets the boot chain (boardloader/bootloader) link and run on
// display-less hardware while the UI code keeps working (it simply renders to
// nowhere).

#include <trezor_rtl.h>

#include <io/display.h>

// All display entry points live in the kernel; the unprivileged side reaches
// them through syscall stubs (sys/syscall/.../syscall_stubs.c). Gating the
// whole driver on KERNEL_MODE avoids duplicate definitions in firmware builds.
#ifdef KERNEL_MODE

typedef struct {
  // Set if the driver is initialized
  bool initialized;
  // Current display orientation (always 0)
  int orientation_angle;
  // Current backlight level ranging from 0 to 255
  uint8_t backlight_level;
} display_driver_t;

static display_driver_t g_display_driver = {
    .initialized = false,
};

bool display_init(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (drv->initialized) {
    return true;
  }

  drv->backlight_level = 0;
  drv->orientation_angle = 0;
  drv->initialized = true;
  return true;
}

void display_deinit(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;
  drv->initialized = false;
}

void display_set_unpriv_access(bool unpriv) {}

bool display_set_backlight(uint8_t level) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return false;
  }

  drv->backlight_level = level;
  return true;
}

uint8_t display_get_backlight(void) {
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

  // The headless driver only supports the default orientation.
  if (angle == 0) {
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

#ifdef FRAMEBUFFER

bool display_get_frame_buffer(display_fb_info_t *fb) {
  memset(fb, 0, sizeof(display_fb_info_t));
  return false;
}

#else  // FRAMEBUFFER

void display_wait_for_sync(void) {}

#endif

void display_refresh(void) {}

void display_fill(const gfx_bitblt_t *bb) {}

void display_copy_rgb565(const gfx_bitblt_t *bb) {}

void display_copy_mono1p(const gfx_bitblt_t *bb) {}

#endif  // KERNEL_MODE
