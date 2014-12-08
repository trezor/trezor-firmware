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

#include <libopencm3/stm32/gpio.h>
#include <libopencm3/stm32/spi.h>

#include <string.h>

#include "oled.h"
#include "util.h"

#define OLED_SETCONTRAST		0x81
#define OLED_DISPLAYALLON_RESUME	0xA4
#define OLED_DISPLAYALLON		0xA5
#define OLED_NORMALDISPLAY		0xA6
#define OLED_INVERTDISPLAY		0xA7
#define OLED_DISPLAYOFF			0xAE
#define OLED_DISPLAYON			0xAF
#define OLED_SETDISPLAYOFFSET		0xD3
#define OLED_SETCOMPINS			0xDA
#define OLED_SETVCOMDETECT		0xDB
#define OLED_SETDISPLAYCLOCKDIV		0xD5
#define OLED_SETPRECHARGE		0xD9
#define OLED_SETMULTIPLEX		0xA8
#define OLED_SETLOWCOLUMN		0x00
#define OLED_SETHIGHCOLUMN		0x10
#define OLED_SETSTARTLINE		0x40
#define OLED_MEMORYMODE			0x20
#define OLED_COMSCANINC			0xC0
#define OLED_COMSCANDEC			0xC8
#define OLED_SEGREMAP			0xA0
#define OLED_CHARGEPUMP			0x8D

#define SPI_BASE			SPI1
#define OLED_DC_PORT			GPIOB
#define OLED_DC_PIN			GPIO0	// PB0 | Data/Command
#define OLED_CS_PORT			GPIOA
#define OLED_CS_PIN			GPIO4	// PA4 | SPI Select
#define OLED_RST_PORT			GPIOB
#define OLED_RST_PIN			GPIO1	// PB1 | Reset display

#define OLED_BUFSET(X,Y)		_oledbuffer[OLED_BUFSIZE - 1 - (X) - ((Y)/8)*OLED_WIDTH] |= (1 << (7 - (Y)%8))
#define OLED_BUFCLR(X,Y)		_oledbuffer[OLED_BUFSIZE - 1 - (X) - ((Y)/8)*OLED_WIDTH] &= ~(1 << (7 - (Y)%8))
#define OLED_BUFTGL(X,Y)		_oledbuffer[OLED_BUFSIZE - 1 - (X) - ((Y)/8)*OLED_WIDTH] ^= (1 << (7 - (Y)%8))

static uint8_t _oledbuffer[OLED_BUFSIZE];
static char is_debug_mode = 0;

inline void SPISend(uint32_t base, uint8_t *data, int len)
{
	int i;
	delay(400);
	for (i = 0; i < len; i++) {
		spi_send(base, data[i]);
	}
	delay(800);
}

void oledInit()
{
	static uint8_t s[25] = {
		OLED_DISPLAYOFF,
		OLED_SETDISPLAYCLOCKDIV,
		0x80,
		OLED_SETMULTIPLEX,
		0x3F, // 128x64
		OLED_SETDISPLAYOFFSET,
		0x00,
		OLED_SETSTARTLINE | 0x00,
		OLED_CHARGEPUMP,
		0x14,
		OLED_MEMORYMODE,
		0x00,
		OLED_SEGREMAP | 0x01,
		OLED_COMSCANDEC,
		OLED_SETCOMPINS,
		0x12, // 128x64
		OLED_SETCONTRAST,
		0xCF,
		OLED_SETPRECHARGE,
		0xF1,
		OLED_SETVCOMDETECT,
		0x40,
		OLED_DISPLAYALLON_RESUME,
		OLED_NORMALDISPLAY,
		OLED_DISPLAYON
	};

	gpio_clear(OLED_DC_PORT, OLED_DC_PIN);		// set to CMD
	gpio_set(OLED_CS_PORT, OLED_CS_PIN);		// SPI deselect

	// Reset the LCD
	gpio_set(OLED_RST_PORT, OLED_RST_PIN);
	delay(40);
	gpio_clear(OLED_RST_PORT, OLED_RST_PIN);
	delay(400);
	gpio_set(OLED_RST_PORT, OLED_RST_PIN);

	// init
	gpio_clear(OLED_CS_PORT, OLED_CS_PIN);		// SPI select
	SPISend(SPI_BASE, s, 25);
	gpio_set(OLED_CS_PORT, OLED_CS_PIN);		// SPI deselect

	oledClear();
	oledRefresh();
}

void oledClear()
{
	memset(_oledbuffer, 0, sizeof(_oledbuffer));
}

void oledRefresh()
{
	static uint8_t s[3] = {OLED_SETLOWCOLUMN | 0x00, OLED_SETHIGHCOLUMN | 0x00, OLED_SETSTARTLINE | 0x00};

	// draw triangle in upper right corner
	if (is_debug_mode) {
		OLED_BUFTGL(OLED_WIDTH - 5, 0); OLED_BUFTGL(OLED_WIDTH - 4, 0); OLED_BUFTGL(OLED_WIDTH - 3, 0); OLED_BUFTGL(OLED_WIDTH - 2, 0); OLED_BUFTGL(OLED_WIDTH - 1, 0);
		OLED_BUFTGL(OLED_WIDTH - 4, 1); OLED_BUFTGL(OLED_WIDTH - 3, 1); OLED_BUFTGL(OLED_WIDTH - 2, 1); OLED_BUFTGL(OLED_WIDTH - 1, 1); 
		OLED_BUFTGL(OLED_WIDTH - 3, 2); OLED_BUFTGL(OLED_WIDTH - 2, 2); OLED_BUFTGL(OLED_WIDTH - 1, 2);
		OLED_BUFTGL(OLED_WIDTH - 2, 3); OLED_BUFTGL(OLED_WIDTH - 1, 3);
		OLED_BUFTGL(OLED_WIDTH - 1, 4);
	}

	gpio_clear(OLED_CS_PORT, OLED_CS_PIN);		// SPI select
	SPISend(SPI_BASE, s, 3);
	gpio_set(OLED_CS_PORT, OLED_CS_PIN);		// SPI deselect

	gpio_set(OLED_DC_PORT, OLED_DC_PIN);		// set to DATA
	gpio_clear(OLED_CS_PORT, OLED_CS_PIN);		// SPI select
	SPISend(SPI_BASE, _oledbuffer, sizeof(_oledbuffer));
	gpio_set(OLED_CS_PORT, OLED_CS_PIN);		// SPI deselect
	gpio_clear(OLED_DC_PORT, OLED_DC_PIN);		// set to CMD

	// return it back
	if (is_debug_mode) {
		OLED_BUFTGL(OLED_WIDTH - 5, 0); OLED_BUFTGL(OLED_WIDTH - 4, 0); OLED_BUFTGL(OLED_WIDTH - 3, 0); OLED_BUFTGL(OLED_WIDTH - 2, 0); OLED_BUFTGL(OLED_WIDTH - 1, 0);
		OLED_BUFTGL(OLED_WIDTH - 4, 1); OLED_BUFTGL(OLED_WIDTH - 3, 1); OLED_BUFTGL(OLED_WIDTH - 2, 1); OLED_BUFTGL(OLED_WIDTH - 1, 1); 
		OLED_BUFTGL(OLED_WIDTH - 3, 2); OLED_BUFTGL(OLED_WIDTH - 2, 2); OLED_BUFTGL(OLED_WIDTH - 1, 2);
		OLED_BUFTGL(OLED_WIDTH - 2, 3); OLED_BUFTGL(OLED_WIDTH - 1, 3);
		OLED_BUFTGL(OLED_WIDTH - 1, 4);
	}
}

const uint8_t *oledGetBuffer()
{
	return _oledbuffer;
}

void oledSetDebug(char set)
{
	is_debug_mode = set;
	oledRefresh();
}

void oledSetBuffer(uint8_t *buf)
{
	memcpy(_oledbuffer, buf, sizeof(_oledbuffer));
}

void oledDrawPixel(int x, int y)
{
	if ((x < 0) || (y < 0) || (x >= OLED_WIDTH) || (y >= OLED_HEIGHT)) return;
	OLED_BUFSET(x,y);
}

void oledClearPixel(int x, int y)
{
	if ((x < 0) || (y < 0) || (x >= OLED_WIDTH) || (y >= OLED_HEIGHT)) return;
	OLED_BUFCLR(x,y);
}

void oledDrawChar(int x, int y, char c)
{
	uint8_t width, *column;

	if ((x >= OLED_WIDTH) || (y >= OLED_HEIGHT)) return;

	if (c < FONT_START) {
		c = ' ';
	}

	if (c > FONT_END) {
		c = '_';
	}

	width = font_data[(int)(c - FONT_START)][0];
	column = (uint8_t *)(font_data[(int)(c - FONT_START)] + 1);

	int xoffset, yoffset;
	for (xoffset = 0; xoffset < width; xoffset++) {
		for (yoffset = 0; yoffset < FONT_HEIGHT; yoffset++) {
			if (column[xoffset] & (1 << (FONT_HEIGHT - 1 - yoffset))) {
				oledDrawPixel(x + xoffset, y + yoffset);
			}
		}
	}
}

void oledDrawString(int x, int y, const char* text)
{
	if (!text) return;
	const char *c;
	int l = 0;
	for (c = text; *c; c++) {
		oledDrawChar(x + l, y, *c);
		l += fontCharWidth(*c) + 1;
	}
}

void oledDrawStringCenter(int y, const char* text)
{
	int x = ( OLED_WIDTH - fontStringWidth(text) ) / 2;
	oledDrawString(x, y, text);
}

void oledDrawStringRight(int x, int y, const char* text)
{
	x -= fontStringWidth(text);
	oledDrawString(x, y, text);
}

#define min(X,Y) ((X) < (Y) ? (X) : (Y))

void oledDrawBitmap(int x, int y, const BITMAP *bmp)
{
	int i, j;
	for (i = 0; i < min(bmp->width, OLED_WIDTH - x); i++) {
		for (j = 0; j < min(bmp->height, OLED_HEIGHT - y); j++) {
			if (bmp->data[(i / 8) + j * bmp->width / 8] & (1 << (7 - i % 8))) {
				OLED_BUFSET(x + i, y + j);
			} else {
				OLED_BUFCLR(x + i, y + j);
			}
		}
	}
}

void oledInvert(int x1, int y1, int x2, int y2)
{
	if ((x1 >= OLED_WIDTH) || (y1 >= OLED_HEIGHT) || (x2 >= OLED_WIDTH) || (y2 >= OLED_HEIGHT)) return;
	int x, y;
	for (x = x1; x <= x2; x++) {
		for (y = y1; y <= y2; y++) {
			OLED_BUFTGL(x,y);
		}
	}
}

void oledBox(int x1, int y1, int x2, int y2, char val)
{
	int x, y;
	for (x = x1; x <= x2; x++) {
		for (y = y1; y <= y2; y++) {
			val ? oledDrawPixel(x, y) : oledClearPixel(x, y);
		}
	}
}

void oledHLine(int y) {
	int x;
	for (x = 0; x < OLED_WIDTH; x++) {
		oledDrawPixel(x, y);
	}
}

void oledFrame(int x1, int y1, int x2, int y2)
{
	int x, y;
	for (x = x1; x <= x2; x++) {
		oledDrawPixel(x, y1);
		oledDrawPixel(x, y2);
	}
	for (y = y1 + 1; y < y2; y++) {
		oledDrawPixel(x1, y);
		oledDrawPixel(x2, y);
	}
}

void oledSwipeLeft(void)
{
	int i, j, k;
	for (i = 0; i < OLED_WIDTH / 4; i++) {
		for (j = 0; j < OLED_HEIGHT / 8; j++) {
			for (k = OLED_WIDTH / 4 - 1; k > 0; k--) {
				_oledbuffer[k * 4 + 3 + j * OLED_WIDTH] = _oledbuffer[k * 4 - 1 + j * OLED_WIDTH];
				_oledbuffer[k * 4 + 2 + j * OLED_WIDTH] = _oledbuffer[k * 4 - 2 + j * OLED_WIDTH];
				_oledbuffer[k * 4 + 1 + j * OLED_WIDTH] = _oledbuffer[k * 4 - 3 + j * OLED_WIDTH];
				_oledbuffer[k * 4 + 0 + j * OLED_WIDTH] = _oledbuffer[k * 4 - 4 + j * OLED_WIDTH];
			}
			_oledbuffer[j * OLED_WIDTH] = 0;
			_oledbuffer[j * OLED_WIDTH + 1] = 0;
			_oledbuffer[j * OLED_WIDTH + 2] = 0;
			_oledbuffer[j * OLED_WIDTH + 3] = 0;
		}
		oledRefresh();
	}
}

void oledSwipeRight(void)
{
	int i, j, k;
	for (i = 0; i < OLED_WIDTH / 4; i++) {
		for (j = 0; j < OLED_HEIGHT / 8; j++) {
			for (k = 0; k < OLED_WIDTH / 4 - 1; k++) {
				_oledbuffer[k * 4 + 0 + j * OLED_WIDTH] = _oledbuffer[k * 4 + 4 + j * OLED_WIDTH];
				_oledbuffer[k * 4 + 1 + j * OLED_WIDTH] = _oledbuffer[k * 4 + 5 + j * OLED_WIDTH];
				_oledbuffer[k * 4 + 2 + j * OLED_WIDTH] = _oledbuffer[k * 4 + 6 + j * OLED_WIDTH];
				_oledbuffer[k * 4 + 3 + j * OLED_WIDTH] = _oledbuffer[k * 4 + 7 + j * OLED_WIDTH];
			}
			_oledbuffer[j * OLED_WIDTH + OLED_WIDTH - 1] = 0;
			_oledbuffer[j * OLED_WIDTH + OLED_WIDTH - 2] = 0;
			_oledbuffer[j * OLED_WIDTH + OLED_WIDTH - 3] = 0;
			_oledbuffer[j * OLED_WIDTH + OLED_WIDTH - 4] = 0;
		}
		oledRefresh();
	}
}
