/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#include "inflate.h"
#include "font_robotomono_regular.h"
#include "font_roboto_regular.h"
#include "font_roboto_bold.h"

#include "trezor-qrenc/qr_encode.h"

#include "display.h"
#include <string.h>

#if defined STM32_HAL_H
#include "display-stmhal.h"
#elif defined UNIX
#include "display-unix.h"
#else
#error Unsupported port. Only STMHAL and UNIX ports are supported.
#endif

// common display functions

void DATAS(const void *bytes, int len)
{
    const uint8_t *c = (const uint8_t *)bytes;
    while (len-- > 0) {
        DATA(*c);
        c++;
    }
}

void set_color_table(uint16_t colortable[16], uint16_t fgcolor, uint16_t bgcolor)
{
    uint8_t cr, cg, cb;
    for (int i = 0; i < 16; i++) {
        cr = (((fgcolor & 0xF800) >> 11) * i + ((bgcolor & 0xF800) >> 11) * (15 - i)) / 15;
        cg = (((fgcolor & 0x07E0) >> 5) * i + ((bgcolor & 0x07E0) >> 5) * (15 - i)) / 15;
        cb = ((fgcolor & 0x001F) * i + (bgcolor & 0x001F) * (15 - i)) / 15;
        colortable[i] = (cr << 11) | (cg << 5) | cb;
    }
}

void display_bar(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint16_t c)
{
    display_set_window(x, y, w, h);
    for (int i = 0; i < w * h; i++) {
        DATA(c >> 8);
        DATA(c & 0xFF);
    }
    display_update();
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


void display_bar_radius(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint16_t c, uint16_t b)
{
    uint16_t colortable[16];
    set_color_table(colortable, c, b);
    display_set_window(x, y, w, h);
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (x < CORNER_RADIUS && y < CORNER_RADIUS) {
                uint8_t c = cornertable[x + y * CORNER_RADIUS];
                DATA(colortable[c] >> 8);
                DATA(colortable[c] & 0xFF);
            } else
            if (x < CORNER_RADIUS && y >= h - CORNER_RADIUS) {
                uint8_t c = cornertable[x + (h - 1 - y) * CORNER_RADIUS];
                DATA(colortable[c] >> 8);
                DATA(colortable[c] & 0xFF);
            } else
            if (x >= w - CORNER_RADIUS && y < CORNER_RADIUS) {
                uint8_t c = cornertable[(w - 1 - x) + y * CORNER_RADIUS];
                DATA(colortable[c] >> 8);
                DATA(colortable[c] & 0xFF);
            } else
            if (x >= w - CORNER_RADIUS && y >= h - CORNER_RADIUS) {
                uint8_t c = cornertable[(w - 1 - x) + (h - 1 - y) * CORNER_RADIUS];
                DATA(colortable[c] >> 8);
                DATA(colortable[c] & 0xFF);
            } else {
                DATA(c >> 8);
                DATA(c & 0xFF);
            }
        }
    }
    display_update();
}

void display_blit(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const void *data, int datalen)
{
    display_set_window(x, y, w, h);
    DATAS(data, datalen);
    display_update();
}

static void inflate_callback_image(uint8_t byte, uint32_t pos, void *userdata)
{
    DATA(byte);
}

void display_image(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const void *data, int datalen)
{
    display_set_window(x, y, w, h);
    sinf_inflate(data, datalen, inflate_callback_image, NULL);
    display_update();
}

static void inflate_callback_icon(uint8_t byte, uint32_t pos, void *userdata)
{
    uint16_t *colortable = (uint16_t *)userdata;
    DATA(colortable[byte >> 4] >> 8);
    DATA(colortable[byte >> 4] & 0xFF);
    DATA(colortable[byte & 0x0F] >> 8);
    DATA(colortable[byte & 0x0F] & 0xFF);
}

void display_icon(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const void *data, int datalen, uint16_t fgcolor, uint16_t bgcolor)
{
    display_set_window(x, y, w, h);
    uint16_t colortable[16];
    set_color_table(colortable, fgcolor, bgcolor);
    sinf_inflate(data, datalen, inflate_callback_icon, colortable);
    display_update();
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
        case 0:
            return Font_RobotoMono_Regular_20[c - ' '];
        case 1:
            return Font_Roboto_Regular_20[c - ' '];
        case 2:
            return Font_Roboto_Bold_20[c - ' '];
    }
    return 0;
}

// first two bytes are width and height of the glyph
// third, fourth and fifth bytes are advance, bearingX and bearingY of the horizontal metrics of the glyph
// rest is packed 4-bit glyph data
void display_text(uint8_t x, uint8_t y, const uint8_t *text, int textlen, uint8_t font, uint16_t fgcolor, uint16_t bgcolor)
{
    uint32_t px = x;
    uint16_t colortable[16];
    set_color_table(colortable, fgcolor, bgcolor);

    // render glyphs
    for (int i = 0; i < textlen; i++) {
        const uint8_t *g = get_glyph(font, text[i]);
        if (!g) continue;
        // g[0], g[1] = width, height
        // g[2]       = advance
        // g[3], g[4] = bearingX, bearingY
        if (g[0] && g[1]) {
            display_set_window(px + (int8_t)(g[3]), y - (int8_t)(g[4]), g[0], g[1]);
            for (int j = 0; j < g[0] * g[1]; j++) {
                uint8_t c;
                if (j % 2 == 0) {
                    c = g[5 + j/2] >> 4;
                } else {
                    c = g[5 + j/2] & 0x0F;
                }
                DATA(colortable[c] >> 8);
                DATA(colortable[c] & 0xFF);
            }
            display_update();
        }
        px += g[2];
    }
}

// compute the width of the text (in pixels)
uint32_t display_text_width(const uint8_t *text, int textlen, uint8_t font)
{
    uint32_t w = 0;
    for (int i = 0; i < textlen; i++) {
        const uint8_t *g = get_glyph(font, text[i]);
        if (!g) continue;
        w += g[2];
    }
    return w;
}

void display_qrcode(uint8_t x, uint8_t y, const char *data, int datalen, int scale)
{
    uint8_t bitdata[QR_MAX_BITDATA];
    int side = qr_encode(QR_LEVEL_M, 0, data, datalen, bitdata);
    display_set_window(x, y, side * scale, side * scale);
    for (int i = 0; i < side * scale; i++) {
        for (int j = 0; j < side; j++) {
            int a = j * side + (i / scale);
            if (bitdata[a / 8] & (1 << (7 - a % 8))) {
                for (a = 0; a < scale * 2; a++) { DATA(0x00); }
            } else {
                for (a = 0; a < scale * 2; a++) { DATA(0xFF); }
            }
        }
    }
    display_update();
}

#include "loader.h"

static void inflate_callback_loader(uint8_t byte, uint32_t pos, void *userdata)
{
    uint8_t *out = (uint8_t *)userdata;
    out[pos] = byte;
}

void display_loader(uint16_t progress, uint16_t fgcolor, uint16_t bgcolor, const uint8_t *icon, uint32_t iconlen, uint16_t iconfgcolor)
{
    uint16_t colortable[16], iconcolortable[16];
    set_color_table(colortable, fgcolor, bgcolor);
    if (icon) {
        set_color_table(iconcolortable, iconfgcolor, bgcolor);
    }
    display_set_window(RESX / 2 - img_loader_size, RESY * 2 / 5 - img_loader_size, img_loader_size * 2, img_loader_size * 2);
    if (icon && memcmp(icon, "TOIg\x60\x00\x60\x00", 8) == 0 && iconlen == 12 + *(uint32_t *)(icon + 8)) {
        uint8_t icondata[96 * 96 / 2];
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
            if (icon && mx + my > (48 * 2) && mx >= img_loader_size - 48 && my >= img_loader_size - 48) {
                int i = (x - (img_loader_size - 48)) + (y - (img_loader_size - 48)) * 96;
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
    display_update();
}

void display_raw(uint8_t reg, const uint8_t *data, int datalen)
{
    if (reg) {
        CMD(reg);
    }
    DATAS(data, datalen);
}
