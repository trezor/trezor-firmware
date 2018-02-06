/*
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef __OLED_H__
#define __OLED_H__

#include <stdint.h>
#include <stdbool.h>

#include "bitmaps.h"
#include "fonts.h"

#define OLED_WIDTH   128
#define OLED_HEIGHT  64
#define OLED_BUFSIZE (OLED_WIDTH * OLED_HEIGHT / 8)

void oledInit(void);
void oledClear(void);
void oledRefresh(void);

void oledSetDebugLink(bool set);
void oledInvertDebugLink(void);

void oledSetBuffer(uint8_t *buf);
const uint8_t *oledGetBuffer(void);
void oledDrawPixel(int x, int y);
void oledClearPixel(int x, int y);
void oledInvertPixel(int x, int y);
void oledDrawChar(int x, int y, char c, int zoom);
int oledStringWidth(const char *text, int font);

void oledDrawString(int x, int y, const char* text, int font);
void oledDrawStringCenter(int y, const char* text, int font);
void oledDrawStringRight(int x, int y, const char* text, int font);
void oledDrawBitmap(int x, int y, const BITMAP *bmp);
void oledInvert(int x1, int y1, int x2, int y2);
void oledBox(int x1, int y1, int x2, int y2, bool set);
void oledHLine(int y);
void oledFrame(int x1, int y1, int x2, int y2);
void oledSwipeLeft(void);
void oledSwipeRight(void);

#endif
