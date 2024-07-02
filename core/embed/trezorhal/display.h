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

#ifndef TREZORHAL_DISPLAY_H
#define TREZORHAL_DISPLAY_H

#if NEW_RENDERING
#include <xdisplay.h>
#else

#include <stdint.h>
#include "common.h"

#include TREZOR_BOARD

#ifdef DISPLAY_LEGACY_HEADER
#include DISPLAY_LEGACY_HEADER
#endif

#ifndef DISPLAY_FRAMEBUFFER_OFFSET_Y
#define DISPLAY_FRAMEBUFFER_OFFSET_Y 0
#endif

#ifndef DISPLAY_FRAMEBUFFER_OFFSET_X
#define DISPLAY_FRAMEBUFFER_OFFSET_X 0
#endif

#ifndef DISPLAY_FRAMEBUFFER_WIDTH
#define DISPLAY_FRAMEBUFFER_WIDTH 0
#endif

#ifndef DISPLAY_FRAMEBUFFER_HEIGHT
#define DISPLAY_FRAMEBUFFER_HEIGHT 0
#endif

#ifndef PIXELDATA
#define PIXELDATA(c) display_pixeldata(c)
#endif

void display_pixeldata(uint16_t c);
void display_pixeldata_dirty(void);

void display_reset_state();

void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1);
int display_orientation(int degrees);
int display_get_orientation(void);
int display_backlight(int val);

void display_init_all(void);
void display_reinit(void);
void display_sync(void);
void display_refresh(void);
void display_finish_actions(void);
const char *display_save(const char *prefix);
void display_clear_save(void);

void display_efficient_clear(void);
uint32_t *display_get_fb_addr(void);
uint8_t *display_get_wr_addr(void);
void display_shift_window(uint16_t pixels);
uint16_t display_get_window_offset(void);

typedef enum {
  // Clear the display content
  DISPLAY_RESET_CONTENT,
  // Keeps the display without any changes
  DISPLAY_RETAIN_CONTENT
} display_content_mode_t;

static inline void display_init(display_content_mode_t mode) {
  if (mode == DISPLAY_RESET_CONTENT) {
    display_init_all();
  } else {
    display_reinit();
  }
}

static inline void display_deinit(display_content_mode_t mode) {

#ifdef TREZOR_MODEL_T
  if (mode == DISPLAY_RESET_CONTENT) {
    display_orientation(0);
  }
#endif
  display_finish_actions();
}

#endif  // NEW_RENDERING
#endif  // TREZORHAL_DISPLAY_H
