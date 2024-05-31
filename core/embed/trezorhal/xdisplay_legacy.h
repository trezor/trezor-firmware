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

#ifndef TREZORHAL_DISPLAY_LEGACY_H
#define TREZORHAL_DISPLAY_LEGACY_H

#include <buffers.h>
#include <stdint.h>

// These declarations will be removed after the final cleanup
// of display drivers. They are here just to simplify integration
// with the legacy code.
//
// Most of these functions are not called when NEW_RENDERING=1,
// and they are only needed for successful code compilation.

#define DISPLAY_FRAMEBUFFER_WIDTH 768
#define DISPLAY_FRAMEBUFFER_HEIGHT 480
#define DISPLAY_FRAMEBUFFER_OFFSET_X 0
#define DISPLAY_FRAMEBUFFER_OFFSET_Y 0

int display_orientation(int angle);
int display_backlight(int level);
void display_refresh(void);
void display_shift_window(uint16_t pixels);
uint16_t display_get_window_offset(void);
void display_pixeldata_dirty(void);
uint8_t* display_get_wr_addr(void);
void display_sync(void);
void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1);
void display_pixeldata(uint16_t c);
uint32_t* display_get_fb_addr(void);

void display_clear(void);
void display_text_render_buffer(const char* text, int textlen, int font,
                                buffer_text_t* buffer, int text_offset);

#define PIXELDATA(c) display_pixeldata(c)

#endif  // TREZORHAL_DISPLAY_LEGACY_H
