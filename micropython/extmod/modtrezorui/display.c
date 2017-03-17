/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "inflate.h"
#include "font_bitmap.h"
#include "font_robotomono_regular_20.h"
#include "font_roboto_regular_20.h"
#include "font_roboto_bold_20.h"

#include "trezor-qrenc/qr_encode.h"

#include "display.h"
#include <string.h>

static int BACKLIGHT = 0;
static int ORIENTATION = 0;
static int OFFSET[2] = {0, 0};

#if defined STM32_HAL_H
#include "display-stmhal.h"
#else
#include "display-unix.h"
#endif

// common display functions

static void set_color_table(uint16_t colortable[16], uint16_t fgcolor, uint16_t bgcolor)
{
    uint8_t cr, cg, cb;
    for (int i = 0; i < 16; i++) {
        cr = (((fgcolor & 0xF800) >> 11) * i + ((bgcolor & 0xF800) >> 11) * (15 - i)) / 15;
        cg = (((fgcolor & 0x07E0) >> 5) * i + ((bgcolor & 0x07E0) >> 5) * (15 - i)) / 15;
        cb = ((fgcolor & 0x001F) * i + (bgcolor & 0x001F) * (15 - i)) / 15;
        colortable[i] = (cr << 11) | (cg << 5) | cb;
    }
}

static inline void clamp_coords(int x, int y, int w, int h, int *x0, int *y0, int *x1, int *y1)
{
#define MIN(a,b) (((a)<(b))?(a):(b))
#define MAX(a,b) (((a)>(b))?(a):(b))
    *x0 = MAX(x, 0);
    *y0 = MAX(y, 0);
    *x1 = MIN(x + w - 1, DISPLAY_RESX - 1);
    *y1 = MIN(y + h - 1, DISPLAY_RESY - 1);
}

void display_clear(void)
{
    display_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);
    for (int i = 0; i < DISPLAY_RESX * DISPLAY_RESY * 2; i++) {
        DATA(0x00);
    }
}

void display_bar(int x, int y, int w, int h, uint16_t c)
{
    x += OFFSET[0];
    y += OFFSET[1];
    int x0, y0, x1, y1;
    clamp_coords(x, y, w, h, &x0, &y0, &x1, &y1);
    display_set_window(x0, y0, x1, y1);
    for (int i = 0; i < (x1 - x0 + 1) * (y1 - y0 + 1); i++) {
        DATA(c >> 8);
        DATA(c & 0xFF);
    }
}

#define CORNER_RADIUS 16

static const uint8_t cornertable[CORNER_RADIUS*CORNER_RADIUS] = {
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
    x += OFFSET[0];
    y += OFFSET[1];
    int x0, y0, x1, y1;
    clamp_coords(x, y, w, h, &x0, &y0, &x1, &y1);
    display_set_window(x0, y0, x1, y1);
    for (int j = y0; j <= y1; j++) {
        for (int i = x0; i <= x1; i++) {
            int rx = i - x;
            int ry = j - y;
            if (rx < CORNER_RADIUS / r && ry < CORNER_RADIUS / r) {
                uint8_t c = cornertable[rx * r + ry * r * CORNER_RADIUS];
                DATA(colortable[c] >> 8);
                DATA(colortable[c] & 0xFF);
            } else
            if (rx < CORNER_RADIUS / r && ry >= h - CORNER_RADIUS / r) {
                uint8_t c = cornertable[rx * r + (h - 1 - ry) * r * CORNER_RADIUS];
                DATA(colortable[c] >> 8);
                DATA(colortable[c] & 0xFF);
            } else
            if (rx >= w - CORNER_RADIUS / r && ry < CORNER_RADIUS / r) {
                uint8_t c = cornertable[(w - 1 - rx) * r + ry * r * CORNER_RADIUS];
                DATA(colortable[c] >> 8);
                DATA(colortable[c] & 0xFF);
            } else
            if (rx >= w - CORNER_RADIUS / r && ry >= h - CORNER_RADIUS / r) {
                uint8_t c = cornertable[(w - 1 - rx) * r + (h - 1 - ry) * r * CORNER_RADIUS];
                DATA(colortable[c] >> 8);
                DATA(colortable[c] & 0xFF);
            } else {
                DATA(c >> 8);
                DATA(c & 0xFF);
            }
        }
    }
}

static void inflate_callback_image(uint8_t byte, uint32_t pos, void *userdata)
{
    int w = ((int *)userdata)[0];
    int x0 = ((int *)userdata)[1];
    int x1 = ((int *)userdata)[2];
    int y0 = ((int *)userdata)[3];
    int y1 = ((int *)userdata)[4];
    int px = (pos / 2) % w;
    int py = (pos / 2) / w;
    if (px >= x0 && px <= x1 && py >= y0 && py <= y1) {
        DATA(byte);
    }
}

void display_image(int x, int y, int w, int h, const void *data, int datalen)
{
    x += OFFSET[0];
    y += OFFSET[1];
    int x0, y0, x1, y1;
    clamp_coords(x, y, w, h, &x0, &y0, &x1, &y1);
    display_set_window(x0, y0, x1, y1);
    int userdata[5];
    userdata[0] = w;
    userdata[1] = x0 - x;
    userdata[2] = x1 - x;
    userdata[3] = y0 - y;
    userdata[4] = y1 - y;
    sinf_inflate(data, datalen, inflate_callback_image, userdata);
}

static void inflate_callback_icon(uint8_t byte, uint32_t pos, void *userdata)
{
    uint16_t *colortable = (uint16_t *)(((int *)userdata) + 5);
    int w = ((int *)userdata)[0];
    int x0 = ((int *)userdata)[1];
    int x1 = ((int *)userdata)[2];
    int y0 = ((int *)userdata)[3];
    int y1 = ((int *)userdata)[4];
    int px = (pos * 2) % w;
    int py = (pos * 2) / w;
    if (px >= x0 && px <= x1 && py >= y0 && py <= y1) {
        DATA(colortable[byte >> 4] >> 8);
        DATA(colortable[byte >> 4] & 0xFF);
        DATA(colortable[byte & 0x0F] >> 8);
        DATA(colortable[byte & 0x0F] & 0xFF);
    }
}

void display_icon(int x, int y, int w, int h, const void *data, int datalen, uint16_t fgcolor, uint16_t bgcolor)
{
    x += OFFSET[0];
    y += OFFSET[1];
    x &= ~1; // cannot draw at odd coordinate
    int x0, y0, x1, y1;
    clamp_coords(x, y, w, h, &x0, &y0, &x1, &y1);
    display_set_window(x0, y0, x1, y1);
    int userdata[5 + 16 * sizeof(uint16_t) / sizeof(int)];
    userdata[0] = w;
    userdata[1] = x0 - x;
    userdata[2] = x1 - x;
    userdata[3] = y0 - y;
    userdata[4] = y1 - y;
    set_color_table((uint16_t *)(userdata + 5), fgcolor, bgcolor);
    sinf_inflate(data, datalen, inflate_callback_icon, userdata);
}

static const uint8_t *get_glyph(uint8_t font, uint8_t c)
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
        case FONT_MONO:
            return Font_RobotoMono_Regular_20[c - ' '];
        case FONT_NORMAL:
            return Font_Roboto_Regular_20[c - ' '];
        case FONT_BOLD:
            return Font_Roboto_Bold_20[c - ' '];
    }
    return 0;
}

// display text using bitmap font
void display_print(const char *text, int textlen)
{
    #define COLS (DISPLAY_RESX / 6)
    #define ROWS (DISPLAY_RESY / 8)
    static char textbuf[ROWS][COLS];
    static uint8_t row = 0, col = 0;

    // determine text length if not provided
    if (textlen < 0) {
        textlen = strlen(text);
    }

    for (int i = 0; i < textlen; i++) {
        switch (text[i]) {
             case '\r':
                 break;
             case '\n':
                 row++;
                 col = 0;
                 break;
             default:
                 textbuf[row][col] = text[i];
                 col++;
                 break;
        }
        if (col >= COLS) {
            col = 0;
            row++;
        }
        if (row >= ROWS) {
            for (int j = 0; j < ROWS - 1; j++) {
                memcpy(textbuf[j], textbuf[j + 1], COLS);
            }
            memset(textbuf[ROWS - 1], 0x00, COLS);
            row = ROWS - 1;
        }
    }

    display_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);
    for (int i = 0; i < DISPLAY_RESX * DISPLAY_RESY; i++) {
        int x = (i % DISPLAY_RESX);
        int y = (i / DISPLAY_RESX);
        int j = y % 8; y /= 8;
        int k = x % 6; x /= 6;
        char c = textbuf[y][x] & 0x7F;
        // char invert = textbuf[y][x] & 0x80;
        if (c < ' ') c = ' ';
        const uint8_t *g = Font_Bitmap + (5 * (c - ' '));
        if (k < 5 && (g[k] & (1 << j))) {
            DATA(0xFF);
            DATA(0xFF);
        } else {
            DATA(0x00);
            DATA(0x00);
        }
    }
}

// first two bytes are width and height of the glyph
// third, fourth and fifth bytes are advance, bearingX and bearingY of the horizontal metrics of the glyph
// rest is packed 4-bit glyph data
void display_text(int x, int y, const char *text, int textlen, uint8_t font, uint16_t fgcolor, uint16_t bgcolor)
{
    uint16_t colortable[16];
    set_color_table(colortable, fgcolor, bgcolor);

    // determine text length if not provided
    if (textlen < 0) {
        textlen = strlen(text);
    }

    int px = x + OFFSET[0];
    y += OFFSET[1];
    // render glyphs
    for (int i = 0; i < textlen; i++) {
        const uint8_t *g = get_glyph(font, (uint8_t)text[i]);
        if (!g) continue;
        // g[0], g[1] = width, height
        // g[2]       = advance
        // g[3], g[4] = bearingX, bearingY
        if (g[0] && g[1]) {
            int sx = px + (int8_t)(g[3]);
            int sy = y - (int8_t)(g[4]);
            int w = g[0];
            int h = g[1];
            int x0, y0, x1, y1;
            clamp_coords(sx, sy, w, h, &x0, &y0, &x1, &y1);
            display_set_window(x0, y0, x1, y1);
            for (int j = y0; j <= y1; j++) {
                for (int i = x0; i <= x1; i++) {
                    int rx = i - sx;
                    int ry = j - sy;
                    int a = rx + ry * w;
                    uint8_t c;
                    if (a % 2 == 0) {
                        c = g[5 + a/2] >> 4;
                    } else {
                        c = g[5 + a/2] & 0x0F;
                    }
                    DATA(colortable[c] >> 8);
                    DATA(colortable[c] & 0xFF);
                }
            }
        }
        px += g[2];
    }
}

void display_text_center(int x, int y, const char *text, int textlen, uint8_t font, uint16_t fgcolor, uint16_t bgcolor)
{
    int w = display_text_width(text, textlen, font);
    display_text(x - w / 2, y, text, textlen, font, fgcolor, bgcolor);
}

void display_text_right(int x, int y, const char *text, int textlen, uint8_t font, uint16_t fgcolor, uint16_t bgcolor)
{
    int w = display_text_width(text, textlen, font);
    display_text(x - w, y, text, textlen, font, fgcolor, bgcolor);
}

// compute the width of the text (in pixels)
int display_text_width(const char *text, int textlen, uint8_t font)
{
    int w = 0;
    // determine text length if not provided
    if (textlen < 0) {
        textlen = strlen(text);
    }
    for (int i = 0; i < textlen; i++) {
        const uint8_t *g = get_glyph(font, (uint8_t)text[i]);
        if (!g) continue;
        w += g[2];
    }
    return w;
}

void display_qrcode(int x, int y, const char *data, int datalen, uint8_t scale)
{
    if (scale < 1 || scale > 10) return;
    uint8_t bitdata[QR_MAX_BITDATA];
    int side = qr_encode(QR_LEVEL_M, 0, data, datalen, bitdata);
    x += OFFSET[0];
    y += OFFSET[1];
    int x0, y0, x1, y1;
    clamp_coords(x, y, side * scale, side * scale, &x0, &y0, &x1, &y1);
    display_set_window(x0, y0, x1, y1);
    for (int j = y0; j <= y1; j++) {
        for (int i = x0; i <= x1; i++) {
            int rx = i - x;
            int ry = j - y;
            int a = (rx / scale)  * side + (ry / scale);
            if (bitdata[a / 8] & (1 << (7 - a % 8))) {
                DATA(0x00); DATA(0x00);
            } else {
                DATA(0xFF); DATA(0xFF);
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
                DATA(iconcolortable[c] >> 8);
                DATA(iconcolortable[c] & 0xFF);
            } else {
                uint8_t c;
                if (progress > a) {
                    c = (img_loader[my][mx] & 0x00F0) >> 4;
                } else {
                    c = img_loader[my][mx] & 0x000F;
                }
                DATA(colortable[c] >> 8);
                DATA(colortable[c] & 0xFF);
            }
        }
    }
}

int *display_offset(int xy[2])
{
    if (xy) {
        OFFSET[0] = xy[0];
        OFFSET[1] = xy[1];
    }
    return OFFSET;
}

int display_orientation(int degrees)
{
    if (degrees != ORIENTATION) {
        if (degrees == 0 || degrees == 90 || degrees == 180 || degrees == 270) {
            ORIENTATION = degrees;
            display_set_orientation(degrees);
        }
    }
    return ORIENTATION;
}

int display_backlight(int val)
{
    if (BACKLIGHT != val && val >= 0 && val <= 255) {
        BACKLIGHT = val;
        display_set_backlight(val);
    }
    return BACKLIGHT;
}
