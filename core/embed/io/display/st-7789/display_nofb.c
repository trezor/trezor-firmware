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
#include <trezor_rtl.h>

#include <io/display.h>

#include "display_internal.h"
#include "display_io.h"
#include "display_panel.h"

#ifdef KERNEL_MODE

void display_refresh(void) {
  // If the framebuffer is not used then, we do not need
  // to refresh the display explicitly as we write the data
  // directly to the display internal RAM.

  // but still, we will wait before raising backlight
  // to make sure the display is showing new content
  display_driver_t* drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  drv->update_pending = 2;
}

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

void display_ensure_refreshed(void) {
#ifndef BOARDLOADER
  display_driver_t* drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  while (drv->update_pending > 0) {
    display_wait_for_sync();
    drv->update_pending--;
  }

#endif
}

static inline void set_window(const gfx_bitblt_t* bb) {
  display_panel_set_window(bb->dst_x, bb->dst_y, bb->dst_x + bb->width - 1,
                           bb->dst_y + bb->height + 1);
}

// Checks if the destination rectangle is withing the display bounds
static inline bool gfx_bitblt_check_dst_xy(const gfx_bitblt_t* bb) {
  if (bb->dst_x + bb->width < bb->dst_x) {  // overflow check
    return false;
  }

  if (bb->dst_x + bb->width > DISPLAY_RESX) {
    return false;
  }

  if (bb->dst_y + bb->height < bb->dst_y) {  // overflow check
    return false;
  }

  if (bb->dst_y + bb->height > DISPLAY_RESY) {
    return false;
  }

  return true;
}

// For future notice, if we ever want to do a new model using progressive
// rendering.
//
// Following functions can be optimized by using DMA (regular is likely enough)
// to copy the data, along with the fill function. If even more performance is
// needed, we could use double-slice similarly to double-framebuffer and render
// to one with DMA2D while copying the other to the display with DMA.

void display_fill(const gfx_bitblt_t* bb) {
  if (!gfx_bitblt_check_dst_xy(bb)) {
    return;
  }

  set_window(bb);

  uint16_t height = bb->height;

  while (height-- > 0) {
    for (int x = 0; x < bb->width; x++) {
      ISSUE_PIXEL_DATA(bb->src_fg);
    }
  }
}

void display_copy_rgb565(const gfx_bitblt_t* bb) {
  if (!gfx_bitblt_check_dst_xy(bb) || !gfx_bitblt_check_src_x(bb, 16)) {
    return;
  }

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

void display_copy_mono1p(const gfx_bitblt_t* bb) {
  if (!gfx_bitblt_check_dst_xy(bb) || !gfx_bitblt_check_src_x(bb, 1)) {
    return;
  }

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

#endif  // KERNEL_MODE
