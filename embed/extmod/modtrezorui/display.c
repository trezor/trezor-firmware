/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#include "inflate.h"
#include "font_bitmap.h"
#ifdef TREZOR_FONT_NORMAL_ENABLE
#include "font_roboto_regular_20.h"
#endif
#ifdef TREZOR_FONT_BOLD_ENABLE
#include "font_roboto_bold_20.h"
#endif
#ifdef TREZOR_FONT_MONO_ENABLE
#include "font_robotomono_regular_20.h"
#endif
#ifdef TREZOR_FONT_MONO_BOLD_ENABLE
#include "font_robotomono_bold_20.h"
#endif

#include "trezor-qrenc/qr_encode.h"

#include "common.h"
#include "display.h"

#include <string.h>
#include <stdarg.h>

static int DISPLAY_BACKLIGHT = -1;
static int DISPLAY_ORIENTATION = -1;

static struct {
    int x, y;
} DISPLAY_OFFSET;

#ifdef TREZOR_EMULATOR
#include "display-unix.h"
#else
#include "display-stm32.h"
#endif

// common display functions

static inline uint16_t interpolate_color(uint16_t color0, uint16_t color1, uint8_t step)
{
    uint8_t cr, cg, cb;
    cr = (((color0 & 0xF800) >> 11) * step + ((color1 & 0xF800) >> 11) * (15 - step)) / 15;
    cg = (((color0 & 0x07E0) >> 5) * step + ((color1 & 0x07E0) >> 5) * (15 - step)) / 15;
    cb = ((color0 & 0x001F) * step + (color1 & 0x001F) * (15 - step)) / 15;
    return (cr << 11) | (cg << 5) | cb;
}

static inline void set_color_table(uint16_t colortable[16], uint16_t fgcolor, uint16_t bgcolor)
{
    for (int i = 0; i < 16; i++) {
        colortable[i] = interpolate_color(fgcolor, bgcolor, i);
    }
}

static inline void clamp_coords(int x, int y, int w, int h, int *x0, int *y0, int *x1, int *y1)
{
    *x0 = MAX(x, 0);
    *y0 = MAX(y, 0);
    *x1 = MIN(x + w - 1, DISPLAY_RESX - 1);
    *y1 = MIN(y + h - 1, DISPLAY_RESY - 1);
}

void display_clear(void)
{
    const int saved_orientation = DISPLAY_ORIENTATION;
    display_orientation(0); // set MADCTL first so that we can set the window correctly next
    display_set_window(0, 0, MAX_DISPLAY_RESX - 1, MAX_DISPLAY_RESY - 1); // address the complete frame memory
    for (uint32_t i = 0; i < MAX_DISPLAY_RESX * MAX_DISPLAY_RESY; i++) {
        PIXELDATA(0x0000); // 2 bytes per pixel because we're using RGB 5-6-5 format
    }
    display_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1); // go back to restricted window
    display_orientation(saved_orientation); // if valid, go back to the saved orientation
}

void display_bar(int x, int y, int w, int h, uint16_t c)
{
    x += DISPLAY_OFFSET.x;
    y += DISPLAY_OFFSET.y;
    int x0, y0, x1, y1;
    clamp_coords(x, y, w, h, &x0, &y0, &x1, &y1);
    display_set_window(x0, y0, x1, y1);
    for (int i = 0; i < (x1 - x0 + 1) * (y1 - y0 + 1); i++) {
        PIXELDATA(c);
    }
}

#define CORNER_RADIUS 16

static const uint8_t cornertable[CORNER_RADIUS * CORNER_RADIUS] = {
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 5, 9, 12, 14, 15,
    0, 0, 0, 0, 0, 0, 0, 0, 3, 9, 15, 15, 15, 15, 15, 15,
    0, 0, 0, 0, 0, 0, 0, 8, 15, 15, 15, 15, 15, 15, 15, 15,
    0, 0, 0, 0, 0, 3, 12, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    0, 0, 0, 0, 3, 14, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    0, 0, 0, 3, 14, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    0, 0, 0, 12, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    0, 0, 8, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    0, 3, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    0, 9, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    1, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    5, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    9, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    12, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    14, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
};

void display_bar_radius(int x, int y, int w, int h, uint16_t c, uint16_t b, uint8_t r)
{
    if (r != 2 && r != 4 && r != 8 && r != 16) {
        return;
    } else {
        r = 16 / r;
    }
    uint16_t colortable[16];
    set_color_table(colortable, c, b);
    x += DISPLAY_OFFSET.x;
    y += DISPLAY_OFFSET.y;
    int x0, y0, x1, y1;
    clamp_coords(x, y, w, h, &x0, &y0, &x1, &y1);
    display_set_window(x0, y0, x1, y1);
    for (int j = y0; j <= y1; j++) {
        for (int i = x0; i <= x1; i++) {
            int rx = i - x;
            int ry = j - y;
            if (rx < CORNER_RADIUS / r && ry < CORNER_RADIUS / r) {
                uint8_t c = cornertable[rx * r + ry * r * CORNER_RADIUS];
                PIXELDATA(colortable[c]);
            } else
            if (rx < CORNER_RADIUS / r && ry >= h - CORNER_RADIUS / r) {
                uint8_t c = cornertable[rx * r + (h - 1 - ry) * r * CORNER_RADIUS];
                PIXELDATA(colortable[c]);
            } else
            if (rx >= w - CORNER_RADIUS / r && ry < CORNER_RADIUS / r) {
                uint8_t c = cornertable[(w - 1 - rx) * r + ry * r * CORNER_RADIUS];
                PIXELDATA(colortable[c]);
            } else
            if (rx >= w - CORNER_RADIUS / r && ry >= h - CORNER_RADIUS / r) {
                uint8_t c = cornertable[(w - 1 - rx) * r + (h - 1 - ry) * r * CORNER_RADIUS];
                PIXELDATA(colortable[c]);
            } else {
                PIXELDATA(c);
            }
        }
    }
}

static void inflate_callback_image(uint8_t byte1, uint32_t pos, void *userdata)
{
    static uint8_t byte0;
    if (pos % 2 == 0) {
        byte0 = byte1;
        return;
    }
    const int w = ((const int *)userdata)[0];
    const int x0 = ((const int *)userdata)[1];
    const int x1 = ((const int *)userdata)[2];
    const int y0 = ((const int *)userdata)[3];
    const int y1 = ((const int *)userdata)[4];
    const int px = (pos / 2) % w;
    const int py = (pos / 2) / w;
    if (px >= x0 && px <= x1 && py >= y0 && py <= y1) {
        PIXELDATA((byte0 << 8) | byte1);
    }
}

void display_image(int x, int y, int w, int h, const void *data, int datalen)
{
    x += DISPLAY_OFFSET.x;
    y += DISPLAY_OFFSET.y;
    int x0, y0, x1, y1;
    clamp_coords(x, y, w, h, &x0, &y0, &x1, &y1);
    display_set_window(x0, y0, x1, y1);
    int userdata[5] = {w, x0 - x, x1 - x, y0 - y, y1 - y};
    sinf_inflate(data, datalen, inflate_callback_image, userdata);
}

static void inflate_callback_avatar(uint8_t byte1, uint32_t pos, void *userdata)
{
#define AVATAR_BORDER_SIZE  4
#define AVATAR_BORDER_LOW   (AVATAR_IMAGE_SIZE / 2 - AVATAR_BORDER_SIZE) * (AVATAR_IMAGE_SIZE / 2 - AVATAR_BORDER_SIZE)
#define AVATAR_BORDER_HIGH  (AVATAR_IMAGE_SIZE / 2) * (AVATAR_IMAGE_SIZE / 2)
#define AVATAR_ANTIALIAS    1
    static uint8_t byte0;
    if (pos % 2 == 0) {
        byte0 = byte1;
        return;
    }
    const int w = ((const int *)userdata)[0];
    const int x0 = ((const int *)userdata)[1];
    const int x1 = ((const int *)userdata)[2];
    const int y0 = ((const int *)userdata)[3];
    const int y1 = ((const int *)userdata)[4];
    const int fgcolor = ((const int *)userdata)[5];
    const int bgcolor = ((const int *)userdata)[6];
    const int px = (pos / 2) % w;
    const int py = (pos / 2) / w;
    if (px >= x0 && px <= x1 && py >= y0 && py <= y1) {
        int d = (px - w / 2) * (px - w / 2) + (py - w / 2) * (py - w / 2);
        // inside border area
        if (d < AVATAR_BORDER_LOW) {
            PIXELDATA((byte0 << 8) | byte1);
        } else
        // outside border area
        if (d > AVATAR_BORDER_HIGH) {
            PIXELDATA(bgcolor);
        // border area
        } else {
#if AVATAR_ANTIALIAS
            d = 31 * (d - AVATAR_BORDER_LOW) / (AVATAR_BORDER_HIGH - AVATAR_BORDER_LOW);
            uint16_t c;
            if (d >= 16) {
                c = interpolate_color(bgcolor, fgcolor, d - 16);
            } else {
                c = interpolate_color(fgcolor, (byte0 << 8) | byte1 , d);
            }
            PIXELDATA(c);
#else
            PIXELDATA(fgcolor);
#endif
        }
    }
}

void display_avatar(int x, int y, const void *data, int datalen, uint16_t fgcolor, uint16_t bgcolor)
{
    x += DISPLAY_OFFSET.x;
    y += DISPLAY_OFFSET.y;
    int x0, y0, x1, y1;
    clamp_coords(x, y, AVATAR_IMAGE_SIZE, AVATAR_IMAGE_SIZE, &x0, &y0, &x1, &y1);
    display_set_window(x0, y0, x1, y1);
    int userdata[7] = {AVATAR_IMAGE_SIZE, x0 - x, x1 - x, y0 - y, y1 - y, fgcolor, bgcolor};
    sinf_inflate(data, datalen, inflate_callback_avatar, userdata);
}

static void inflate_callback_icon(uint8_t byte, uint32_t pos, void *userdata)
{
    const uint16_t *colortable = (const uint16_t *)(((const int *)userdata) + 5);
    const int w = ((const int *)userdata)[0];
    const int x0 = ((const int *)userdata)[1];
    const int x1 = ((const int *)userdata)[2];
    const int y0 = ((const int *)userdata)[3];
    const int y1 = ((const int *)userdata)[4];
    const int px = (pos * 2) % w;
    const int py = (pos * 2) / w;
    if (px >= x0 && px <= x1 && py >= y0 && py <= y1) {
        PIXELDATA(colortable[byte >> 4]);
        PIXELDATA(colortable[byte & 0x0F]);
    }
}

void display_icon(int x, int y, int w, int h, const void *data, int datalen, uint16_t fgcolor, uint16_t bgcolor)
{
    x += DISPLAY_OFFSET.x;
    y += DISPLAY_OFFSET.y;
    x &= ~1; // cannot draw at odd coordinate
    int x0, y0, x1, y1;
    clamp_coords(x, y, w, h, &x0, &y0, &x1, &y1);
    display_set_window(x0, y0, x1, y1);
    int userdata[5 + 16 * sizeof(uint16_t) / sizeof(int)] = {w, x0 - x, x1 - x, y0 - y, y1 - y};
    set_color_table((uint16_t *)(userdata + 5), fgcolor, bgcolor);
    sinf_inflate(data, datalen, inflate_callback_icon, userdata);
}

static const uint8_t *get_glyph(int font, uint8_t c)
{
    if (c >= ' ' && c <= '~') {
    // do nothing - valid ASCII
    } else
    // UTF-8 handling: https://en.wikipedia.org/wiki/UTF-8#Description
    if (c >= 0xC0) {
        // bytes 11xxxxxx are first byte of UTF-8 characters
        c = '_';
    } else {
        // bytes 10xxxxxx are successive UTF-8 characters
        return 0;
    }
    switch (font) {
#ifdef TREZOR_FONT_NORMAL_ENABLE
        case FONT_NORMAL:
            return Font_Roboto_Regular_20[c - ' '];
#endif
#ifdef TREZOR_FONT_BOLD_ENABLE
        case FONT_BOLD:
            return Font_Roboto_Bold_20[c - ' '];
#endif
#ifdef TREZOR_FONT_MONO_ENABLE
        case FONT_MONO:
            return Font_RobotoMono_Regular_20[c - ' '];
#endif
#ifdef TREZOR_FONT_MONO_BOLD_ENABLE
        case FONT_MONO_BOLD:
            return Font_RobotoMono_Bold_20[c - ' '];
#endif
    }
    return 0;
}

#ifndef TREZOR_PRINT_DISABLE

#define DISPLAY_PRINT_COLS (DISPLAY_RESX / 6)
#define DISPLAY_PRINT_ROWS (DISPLAY_RESY / 8)
static char display_print_buf[DISPLAY_PRINT_ROWS][DISPLAY_PRINT_COLS];
static uint16_t display_print_fgcolor = COLOR_WHITE, display_print_bgcolor = COLOR_BLACK;

// set colors for display_print function
void display_print_color(uint16_t fgcolor, uint16_t bgcolor)
{
    display_print_fgcolor = fgcolor;
    display_print_bgcolor = bgcolor;
}

// display text using bitmap font
void display_print(const char *text, int textlen)
{
    static uint8_t row = 0, col = 0;

    // determine text length if not provided
    if (textlen < 0) {
        textlen = strlen(text);
    }

    // print characters to internal buffer (display_print_buf)
    for (int i = 0; i < textlen; i++) {

        switch (text[i]) {
            case '\r':
                break;
            case '\n':
                row++;
                col = 0;
                break;
            default:
                display_print_buf[row][col] = text[i];
                col++;
                break;
        }

        if (col >= DISPLAY_PRINT_COLS) {
            col = 0;
            row++;
        }

        if (row >= DISPLAY_PRINT_ROWS) {
            for (int j = 0; j < DISPLAY_PRINT_ROWS - 1; j++) {
                memcpy(display_print_buf[j], display_print_buf[j + 1], DISPLAY_PRINT_COLS);
            }
            memset(display_print_buf[DISPLAY_PRINT_ROWS - 1], 0x00, DISPLAY_PRINT_COLS);
            row = DISPLAY_PRINT_ROWS - 1;
        }

    }

    // render buffer to display
    display_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);
    for (int i = 0; i < DISPLAY_RESX * DISPLAY_RESY; i++) {
        int x = (i % DISPLAY_RESX);
        int y = (i / DISPLAY_RESX);
        int j = y % 8; y /= 8;
        int k = x % 6; x /= 6;
        char c = display_print_buf[y][x] & 0x7F;
        // char invert = display_print_buf[y][x] & 0x80;
        if (c < ' ') c = ' ';
        const uint8_t *g = Font_Bitmap + (5 * (c - ' '));
        if (k < 5 && (g[k] & (1 << j))) {
            PIXELDATA(display_print_fgcolor);
        } else {
            PIXELDATA(display_print_bgcolor);
        }
    }
    display_refresh();
}

#ifdef TREZOR_EMULATOR
#define mini_vsnprintf vsnprintf
#include <stdio.h>
#else
#include "mini_printf.h"
#endif

// variadic display_print
void display_printf(const char *fmt, ...)
{
    if (!strchr(fmt, '%')) {
        display_print(fmt, strlen(fmt));
    } else {
        va_list va;
        va_start(va, fmt);
        char buf[256];
        int len = mini_vsnprintf(buf, sizeof(buf), fmt, va);
        display_print(buf, len);
        va_end(va);
    }
}

#endif // TREZOR_PRINT_DISABLE

static void display_text_render(int x, int y, const char *text, int textlen, int font, uint16_t fgcolor, uint16_t bgcolor)
{
    // determine text length if not provided
    if (textlen < 0) {
        textlen = strlen(text);
    }

    uint16_t colortable[16];
    set_color_table(colortable, fgcolor, bgcolor);

    // render glyphs
    for (int i = 0; i < textlen; i++) {
        const uint8_t *g = get_glyph(font, (uint8_t)text[i]);
        if (!g) continue;
        const uint8_t w = g[0]; // width
        const uint8_t h = g[1]; // height
        const uint8_t adv = g[2]; // advance
        const uint8_t bearX = g[3]; // bearingX
        const uint8_t bearY = g[4]; // bearingY
        if (w && h) {
            const int sx = x + bearX;
            const int sy = y - bearY;
            int x0, y0, x1, y1;
            clamp_coords(sx, sy, w, h, &x0, &y0, &x1, &y1);
            display_set_window(x0, y0, x1, y1);
            for (int j = y0; j <= y1; j++) {
                for (int i = x0; i <= x1; i++) {
                    const int rx = i - sx;
                    const int ry = j - sy;
                    const int a = rx + ry * w;
                    #if FONT_BPP == 2
                    const uint8_t c = ((g[5 + a / 4] >> (6 - (a % 4) * 2)) & 0x03) * 5;
                    #elif FONT_BPP == 4
                    const uint8_t c = (g[5 + a / 2] >> (4 - (a % 2) * 4)) & 0x0F;
                    #else
                    #error Unsupported FONT_BPP value
                    #endif
                    PIXELDATA(colortable[c]);
                }
            }
        }
        x += adv;
    }
}

void display_text(int x, int y, const char *text, int textlen, int font, uint16_t fgcolor, uint16_t bgcolor)
{
    x += DISPLAY_OFFSET.x;
    y += DISPLAY_OFFSET.y;
    display_text_render(x, y, text, textlen, font, fgcolor, bgcolor);
}

void display_text_center(int x, int y, const char *text, int textlen, int font, uint16_t fgcolor, uint16_t bgcolor)
{
    x += DISPLAY_OFFSET.x;
    y += DISPLAY_OFFSET.y;
    int w = display_text_width(text, textlen, font);
    display_text_render(x - w / 2, y, text, textlen, font, fgcolor, bgcolor);
}

void display_text_right(int x, int y, const char *text, int textlen, int font, uint16_t fgcolor, uint16_t bgcolor)
{
    x += DISPLAY_OFFSET.x;
    y += DISPLAY_OFFSET.y;
    int w = display_text_width(text, textlen, font);
    display_text_render(x - w, y, text, textlen, font, fgcolor, bgcolor);
}

// compute the width of the text (in pixels)
int display_text_width(const char *text, int textlen, int font)
{
    int width = 0;
    // determine text length if not provided
    if (textlen < 0) {
        textlen = strlen(text);
    }
    for (int i = 0; i < textlen; i++) {
        const uint8_t *g = get_glyph(font, (uint8_t)text[i]);
        if (!g) continue;
        const uint8_t adv = g[2]; // advance
        width += adv;
        /*
        if (i != textlen - 1) {
            const uint8_t adv = g[2]; // advance
            width += adv;
        } else { // last character
            const uint8_t w = g[0]; // width
            const uint8_t bearX = g[3]; // bearingX
            width += (bearX + w);
        }
        */
    }
    return width;
}

void display_qrcode(int x, int y, const char *data, int datalen, uint8_t scale)
{
    if (scale < 1 || scale > 10) return;
    uint8_t bitdata[QR_MAX_BITDATA];
    int side = qr_encode(QR_LEVEL_M, 0, data, datalen, bitdata);
    x += DISPLAY_OFFSET.x - (side + 2) * scale / 2;
    y += DISPLAY_OFFSET.y - (side + 2) * scale / 2;
    int x0, y0, x1, y1;
    clamp_coords(x, y, (side + 2) * scale, (side + 2) * scale, &x0, &y0, &x1, &y1);
    display_set_window(x0, y0, x1, y1);
    for (int j = y0; j <= y1; j++) {
        for (int i = x0; i <= x1; i++) {
            int rx = (i - x) / scale - 1;
            int ry = (j - y) / scale - 1;
            // 1px border
            if (rx < 0 || ry < 0 || rx >= side || ry >= side) {
                PIXELDATA(0xFFFF);
                continue;
            }
            int a = ry * side + rx;
            if (bitdata[a / 8] & (1 << (7 - a % 8))) {
                PIXELDATA(0x0000);
            } else {
                PIXELDATA(0xFFFF);
            }
        }
    }
}

#include "loader.h"

static void inflate_callback_loader(uint8_t byte, uint32_t pos, void *userdata)
{
    uint8_t *out = (uint8_t *)userdata;
    out[pos] = byte;
}

void display_loader(uint16_t progress, int yoffset, uint16_t fgcolor, uint16_t bgcolor, const uint8_t *icon, uint32_t iconlen, uint16_t iconfgcolor)
{
    uint16_t colortable[16], iconcolortable[16];
    set_color_table(colortable, fgcolor, bgcolor);
    if (icon) {
        set_color_table(iconcolortable, iconfgcolor, bgcolor);
    }
    if ((DISPLAY_RESY / 2 - img_loader_size + yoffset < 0) ||
        (DISPLAY_RESY / 2 + img_loader_size - 1 + yoffset >= DISPLAY_RESY)) {
       return;
    }
    display_set_window(DISPLAY_RESX / 2 - img_loader_size, DISPLAY_RESY / 2 - img_loader_size + yoffset, DISPLAY_RESX / 2 + img_loader_size - 1, DISPLAY_RESY / 2 + img_loader_size - 1 + yoffset);
    if (icon && memcmp(icon, "TOIg", 4) == 0 && LOADER_ICON_SIZE == *(uint16_t *)(icon + 4) && LOADER_ICON_SIZE == *(uint16_t *)(icon + 6) && iconlen == 12 + *(uint32_t *)(icon + 8)) {
        uint8_t icondata[LOADER_ICON_SIZE * LOADER_ICON_SIZE / 2];
        sinf_inflate(icon + 12, iconlen - 12, inflate_callback_loader, icondata);
        icon = icondata;
    } else {
        icon = NULL;
    }
    for (int y = 0; y < img_loader_size * 2; y++) {
        for (int x = 0; x < img_loader_size * 2; x++) {
            int mx = x, my = y;
            uint16_t a;
            if ((mx >= img_loader_size) && (my >= img_loader_size)) {
                mx = img_loader_size * 2 - 1 - x;
                my = img_loader_size * 2 - 1 - y;
                a = 499 - (img_loader[my][mx] >> 8);
            } else
            if (mx >= img_loader_size) {
                mx = img_loader_size * 2 - 1 - x;
                a = img_loader[my][mx] >> 8;
            } else
            if (my >= img_loader_size) {
                my = img_loader_size * 2 - 1 - y;
                a = 500 + (img_loader[my][mx] >> 8);
            } else {
                a = 999 - (img_loader[my][mx] >> 8);
            }
            // inside of circle - draw glyph
            #define LOADER_ICON_CORNER_CUT 2
            if (icon && mx + my > (((LOADER_ICON_SIZE / 2) + LOADER_ICON_CORNER_CUT) * 2) && mx >= img_loader_size - (LOADER_ICON_SIZE / 2) && my >= img_loader_size - (LOADER_ICON_SIZE / 2)) {
                int i = (x - (img_loader_size - (LOADER_ICON_SIZE / 2))) + (y - (img_loader_size - (LOADER_ICON_SIZE / 2))) * LOADER_ICON_SIZE;
                uint8_t c;
                if (i % 2) {
                    c = icon[i / 2] & 0x0F;
                } else {
                    c = (icon[i / 2] & 0xF0) >> 4;
                }
                PIXELDATA(iconcolortable[c]);
            } else {
                uint8_t c;
                if (progress > a) {
                    c = (img_loader[my][mx] & 0x00F0) >> 4;
                } else {
                    c = img_loader[my][mx] & 0x000F;
                }
                PIXELDATA(colortable[c]);
            }
        }
    }
}

void display_offset(int set_xy[2], int *get_x, int *get_y)
{
    if (set_xy) {
        DISPLAY_OFFSET.x = set_xy[0];
        DISPLAY_OFFSET.y = set_xy[1];
    }
    *get_x = DISPLAY_OFFSET.x;
    *get_y = DISPLAY_OFFSET.y;
}

int display_orientation(int degrees)
{
    if (degrees != DISPLAY_ORIENTATION) {
        if (degrees == 0 || degrees == 90 || degrees == 180 || degrees == 270) {
            DISPLAY_ORIENTATION = degrees;
            display_set_orientation(degrees);
        }
    }
    return DISPLAY_ORIENTATION;
}

int display_backlight(int val)
{
    if (DISPLAY_BACKLIGHT != val && val >= 0 && val <= 255) {
        DISPLAY_BACKLIGHT = val;
        display_set_backlight(val);
    }
    return DISPLAY_BACKLIGHT;
}

void display_fade(int start, int end, int delay)
{
    for (int i = 0; i < 100; i++) {
        display_backlight(start + i * (end - start) / 100);
        hal_delay(delay / 100);
    }
    display_backlight(end);
}
