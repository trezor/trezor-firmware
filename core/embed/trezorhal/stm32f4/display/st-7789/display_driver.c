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

#include <string.h>

#include <xdisplay.h>

#include "display_fb.h"
#include "display_io.h"
#include "display_panel.h"

#include "backlight_pwm.h"
#include "supervise.h"

#ifndef BOARDLOADER
#include "bg_copy.h"
#endif

#if (DISPLAY_RESX != 240) || (DISPLAY_RESY != 240)
#error "Incompatible display resolution"
#endif

// Display driver context.
typedef struct {
  // Current display orientation (0, 90, 180, 270)
  int orientation_angle;
} display_driver_t;

// Display driver instance
static display_driver_t g_display_driver;

void display_init(void) {
  display_driver_t* drv = &g_display_driver;
  memset(drv, 0, sizeof(display_driver_t));

  display_io_init_gpio();
  display_io_init_fmc();
  display_panel_init();
  display_panel_set_little_endian();
  backlight_pwm_init();

#ifdef XFRAMEBUFFER
  display_io_init_te_interrupt();
#endif
}

void display_reinit(void) {
  display_driver_t* drv = &g_display_driver;
  memset(drv, 0, sizeof(display_driver_t));

  // Reinitialize FMC to set correct timing
  // We have to do this in reinit because boardloader is fixed.
  display_io_init_fmc();

  // Important for model T as this is not set in boardloader
  display_panel_set_little_endian();
  display_panel_init_gamma();
  backlight_pwm_reinit();

#ifdef XFRAMEBUFFER
  display_io_init_te_interrupt();
#endif
}

void display_finish_actions(void) {
#ifdef XFRAMEBUFFER
#ifndef BOARDLOADER
  bg_copy_wait();
#endif
#endif
}

int display_set_backlight(int level) {
#ifdef XFRAMEBUFFER
#ifndef BOARDLOADER
  // wait for DMA transfer to finish before changing backlight
  // so that we know that panel has current data
  if (backlight_pwm_get() != level && !is_mode_handler()) {
    bg_copy_wait();
  }
#endif
#endif

  return backlight_pwm_set(level);
}

int display_get_backlight(void) { return backlight_pwm_get(); }

int display_set_orientation(int angle) {
  display_driver_t* drv = &g_display_driver;

  if (angle != drv->orientation_angle) {
    if (angle == 0 || angle == 90 || angle == 180 || angle == 270) {
      drv->orientation_angle = angle;

#ifdef XFRAMEBUFFER
      memset(physical_frame_buffer_0, 0, sizeof(physical_frame_buffer_0));
      memset(physical_frame_buffer_1, 0, sizeof(physical_frame_buffer_1));
#endif

      display_panel_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);
      for (uint32_t i = 0; i < DISPLAY_RESX * DISPLAY_RESY; i++) {
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

  return drv->orientation_angle;
}

#ifndef XFRAMEBUFFER
void display_refresh(void) {
  // if the framebuffer is not used the implementation is empty
}
#endif

void display_wait_for_sync(void) {
#ifdef DISPLAY_TE_PIN
  uint32_t id = display_panel_identify();
  if (id && (id != DISPLAY_ID_GC9307)) {
    // synchronize with the panel synchronization signal
    // in order to avoid visual tearing effects
    while (GPIO_PIN_SET == HAL_GPIO_ReadPin(DISPLAY_TE_PORT, DISPLAY_TE_PIN))
      ;
    while (GPIO_PIN_RESET == HAL_GPIO_ReadPin(DISPLAY_TE_PORT, DISPLAY_TE_PIN))
      ;
  }
#endif
}

void display_set_compatible_settings(void) { display_panel_set_big_endian(); }

static inline void set_window(const gl_bitblt_t* bb) {
  display_panel_set_window(bb->dst_x, bb->dst_y, bb->dst_x + bb->width - 1,
                           bb->dst_y + bb->height + 1);
}

void display_fill(const gl_bitblt_t* bb) {
  set_window(bb);

  uint16_t height = bb->height;

  while (height-- > 0) {
    for (int x = 0; x < bb->width; x++) {
      ISSUE_PIXEL_DATA(bb->src_fg);
    }
  }
}

void display_copy_rgb565(const gl_bitblt_t* bb) {
  set_window(bb);

  uint16_t* src_ptr = (uint16_t*)bb->src_row + bb->src_x;
  uint16_t height = bb->height;

  while (height-- > 0) {
    for (int x = 0; x < bb->width; x++) {
      ISSUE_PIXEL_DATA(src_ptr[x]);
    }
    src_ptr += bb->src_stride / sizeof(*src_ptr);
  }
}

void display_copy_mono1p(const gl_bitblt_t* bb) {
  set_window(bb);

  uint8_t* src = (uint8_t*)bb->src_row;
  uint16_t src_ofs = bb->src_stride * bb->src_y + bb->src_x;
  uint16_t height = bb->height;

  while (height-- > 0) {
    for (int x = 0; x < bb->width; x++) {
      uint8_t mask = 1 << (7 - ((src_ofs + x) & 7));
      uint8_t data = src[(src_ofs + x) / 8];
      ISSUE_PIXEL_DATA((data & mask) ? bb->src_fg : bb->src_bg);
    }
    src_ofs += bb->src_stride;
  }
}

void display_copy_mono4(const gl_bitblt_t* bb) {
  set_window(bb);

  const gl_color16_t* gradient = gl_color16_gradient_a4(bb->src_fg, bb->src_bg);

  uint8_t* src_row = (uint8_t*)bb->src_row;
  uint16_t height = bb->height;

  while (height-- > 0) {
    for (int x = 0; x < bb->width; x++) {
      uint8_t fg_data = src_row[(x + bb->src_x) / 2];
      uint8_t fg_lum = (x + bb->src_x) & 1 ? fg_data >> 4 : fg_data & 0xF;
      ISSUE_PIXEL_DATA(gradient[fg_lum]);
    }
    src_row += bb->src_stride / sizeof(*src_row);
  }
}
