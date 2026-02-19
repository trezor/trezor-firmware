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

#ifdef KERNEL_MODE

typedef struct {
  int angle;
  int backlight;
} dispay_driver_t;

dispay_driver_t g_display_driver = {0};

bool display_init(display_content_mode_t mode) { return true; }

void display_deinit(display_content_mode_t mode) {}

void display_set_unpriv_access(bool unpriv) {}

bool display_set_backlight(uint8_t level) {
  g_display_driver.backlight = level;
  return true;
}

uint8_t display_get_backlight(void) { return g_display_driver.backlight; }

int display_set_orientation(int angle) {
  g_display_driver.angle = angle;
  return angle;
}
int display_get_orientation(void) { return g_display_driver.angle; }

void display_wait_for_sync(void) {}

void display_refresh(void) {}

void display_fill(const gfx_bitblt_t *bb) {}

void display_copy_rgb565(const gfx_bitblt_t *bb) {}

void display_copy_mono1p(const gfx_bitblt_t *bb) {}

#endif  // KERNEL_MODE
