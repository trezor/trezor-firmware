/*
 * This file is part of the TREZOR project.
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

#include <string.h>

#include "layout.h"
#include "oled.h"

void layoutDialog(const BITMAP *icon, const char *btnNo, const char *btnYes, const char *desc, const char *line1, const char *line2, const char *line3, const char *line4, const char *line5, const char *line6)
{
	int left = 0;
	oledClear();
	if (icon) {
		oledDrawBitmap(0, 0, icon);
		left = icon->width + 4;
	}
	if (line1) oledDrawString(left, 0 * 9, line1);
	if (line2) oledDrawString(left, 1 * 9, line2);
	if (line3) oledDrawString(left, 2 * 9, line3);
	if (line4) oledDrawString(left, 3 * 9, line4);
	if (desc) {
		oledDrawStringCenter(OLED_HEIGHT - 2 * 9 - 1, desc);
		if (btnYes || btnNo) {
			oledHLine(OLED_HEIGHT - 21);
		}
	} else {
		if (line5) oledDrawString(left, 4 * 9, line5);
		if (line6) oledDrawString(left, 5 * 9, line6);
		if (btnYes || btnNo) {
			oledHLine(OLED_HEIGHT - 13);
		}
	}
	if (btnNo) {
		oledDrawString(1, OLED_HEIGHT - 8, "\x15");
		oledDrawString(fontCharWidth('\x15') + 3, OLED_HEIGHT - 8, btnNo);
		oledInvert(0, OLED_HEIGHT - 9, fontCharWidth('\x15') + oledStringWidth(btnNo) + 2, OLED_HEIGHT - 1);
	}
	if (btnYes) {
		oledDrawString(OLED_WIDTH - fontCharWidth('\x06') - 1, OLED_HEIGHT - 8, "\x06");
		oledDrawString(OLED_WIDTH - oledStringWidth(btnYes) - fontCharWidth('\x06') - 3, OLED_HEIGHT - 8, btnYes);
		oledInvert(OLED_WIDTH - oledStringWidth(btnYes) - fontCharWidth('\x06') - 4, OLED_HEIGHT - 9, OLED_WIDTH - 1, OLED_HEIGHT - 1);
	}
	oledRefresh();
}

void layoutProgressUpdate(bool refresh)
{
	static uint8_t step = 0;
	switch (step) {
		case 0:
			oledDrawBitmap(40, 0, &bmp_gears0);
			break;
		case 1:
			oledDrawBitmap(40, 0, &bmp_gears1);
			break;
		case 2:
			oledDrawBitmap(40, 0, &bmp_gears2);
			break;
		case 3:
			oledDrawBitmap(40, 0, &bmp_gears3);
			break;
	}
	step = (step + 1) % 4;
	if (refresh) {
		oledRefresh();
	}
}

void layoutProgress(const char *desc, int permil)
{
	oledClear();
	layoutProgressUpdate(false);
	// progressbar
	oledFrame(0, OLED_HEIGHT - 8, OLED_WIDTH - 1, OLED_HEIGHT - 1);
	oledBox(1, OLED_HEIGHT - 7, OLED_WIDTH - 2, OLED_HEIGHT - 2, 0);
	permil = permil * (OLED_WIDTH - 4) / 1000;
	if (permil < 0) {
		permil = 0;
	}
	if (permil > OLED_WIDTH - 4) {
		permil = OLED_WIDTH - 4;
	}
	oledBox(2, OLED_HEIGHT - 6, 1 + permil, OLED_HEIGHT - 3, 1);
	// text
	oledBox(0, OLED_HEIGHT - 16, OLED_WIDTH - 1, OLED_HEIGHT - 16 + 7, 0);
	if (desc) {
		oledDrawStringCenter(OLED_HEIGHT - 16, desc);
	}
	oledRefresh();
}
