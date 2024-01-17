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

#ifndef __DISPLAY_H__
#define __DISPLAY_H__

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "buffers.h"
#include "colors.h"
#include TREZOR_BOARD
#include "display_interface.h"
#include "fonts/fonts.h"

// provided by common

void display_clear(void);

void display_bar(int x, int y, int w, int h, uint16_t c);

void display_text(int x, int y, const char *text, int textlen, int font,
                  uint16_t fgcolor, uint16_t bgcolor);
void display_text_center(int x, int y, const char *text, int textlen, int font,
                         uint16_t fgcolor, uint16_t bgcolor);
void display_text_right(int x, int y, const char *text, int textlen, int font,
                        uint16_t fgcolor, uint16_t bgcolor);
void display_text_render_buffer(const char *text, int textlen, int font,
                                buffer_text_t *buffer, int text_offset);

void display_qrcode(int x, int y, const char *data, uint8_t scale);

void display_offset(int set_xy[2], int *get_x, int *get_y);

#endif
