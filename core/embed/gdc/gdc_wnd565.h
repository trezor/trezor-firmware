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

#ifndef GDC_WND565_H
#define GDC_WND565_H

#include "gdc_core.h"

// ------------------------------------------------------------------------
// GDC for displays RGB565 with register/window API like ST7789
//
// This module serves as a driver for specific types of displays with
// internal memory acting as a frame buffer and a specific interface
// for writing to this framebuffer by putting pixels into the
// specified rectangle window.

typedef void (*gdc_release_cb_t)(void* context);

// Driver configuration
typedef struct {
  // TODO
  uintptr_t reg_address;

  // GDC size in pixels
  gdc_size_t size;

  // Release callback invoked when gdc_release() is called
  gdc_release_cb_t release;
  // Context for release callback
  void* context;

} gdc_wnd565_config_t;

// Driver-specific GDC structure
typedef struct {
  // GDC virtual method table
  // (Must be the first field of the structure)
  const gdc_vmt_t* vmt;

  // Fake bitmap structure
  gdc_bitmap_t bitmap;

  // Current drawing window/rectangle
  gdc_rect_t rect;
  // Cursor position in the window
  int cursor_x;
  int cursor_y;

} gdc_wnd565_t;

// Initializes GDC context
gdc_t* gdc_wnd565_init(gdc_wnd565_t* gdc, gdc_wnd565_config_t* config);

#endif  // GDC_WND565_H
