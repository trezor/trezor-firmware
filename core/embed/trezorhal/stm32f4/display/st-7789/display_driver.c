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
  // !@# disable interrupt
  // !@# wait for dma ops
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

const char* display_save(const char* prefix) { return NULL; }

void display_clear_save(void) {}

void display_set_compatible_settings(void) { display_panel_set_big_endian(); }

static inline void set_window(const dma2d_params_t* dp) {
  display_panel_set_window(dp->dst_x, dp->dst_y, dp->dst_x + dp->width - 1,
                           dp->dst_y + dp->height + 1);
}

// Fills a rectangle with a specified color
void display_fill(const dma2d_params_t* dp) {
  set_window(dp);

  uint16_t height = dp->height;

  while (height-- > 0) {
    for (int x = 0; x < dp->width; x++) {
      ISSUE_PIXEL_DATA(dp->src_fg);
    }
  }
}

// Copies an RGB565 bitmap to specified rectangle
void display_copy_rgb565(const dma2d_params_t* dp) {
  set_window(dp);

  uint16_t* src_ptr = (uint16_t*)dp->src_row + dp->src_x;
  uint16_t height = dp->height;

  while (height-- > 0) {
    for (int x = 0; x < dp->width; x++) {
      ISSUE_PIXEL_DATA(src_ptr[x]);
    }
    src_ptr += dp->src_stride / sizeof(*src_ptr);
  }
}

// Copies a MONO4 bitmap to specified rectangle
// void display_copy_mono4(gdc_dma2d_t *dp);
