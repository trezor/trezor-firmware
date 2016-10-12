/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#ifndef __DISPLAY_H__
#define __DISPLAY_H__

#include <stdint.h>

#define DISPLAY_RESX 240
#define DISPLAY_RESY 240

#define FONT_MONO   0
#define FONT_NORMAL 1
#define FONT_BOLD   2

#define LOADER_ICON_SIZE 64

void display_init(void);
void display_set_window(uint16_t x, uint16_t y, uint16_t w, uint16_t h);
int display_orientation(int degrees);
int display_backlight(int val);
int *display_offset(int xy[2]);

void set_color_table(uint16_t colortable[16], uint16_t fgcolor, uint16_t bgcolor);
void display_clear(void);
void display_refresh(void);
void display_bar(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint16_t c);
void display_bar_radius(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint16_t c, uint16_t b, uint8_t r);
void display_blit(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const void *data, int datalen);
void display_image(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const void *data, int datalen);
void display_icon(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const void *data, int datalen, uint16_t fgcolor, uint16_t bgcolor);
void display_text(uint8_t x, uint8_t y, const char *text, int textlen, uint8_t font, uint16_t fgcolor, uint16_t bgcolor);
void display_text_center(uint8_t x, uint8_t y, const char *text, int textlen, uint8_t font, uint16_t fgcolor, uint16_t bgcolor);
void display_text_right(uint8_t x, uint8_t y, const char *text, int textlen, uint8_t font, uint16_t fgcolor, uint16_t bgcolor);
uint32_t display_text_width(const char *text, int textlen, uint8_t font);
void display_qrcode(uint8_t x, uint8_t y, const char *data, int datalen, int scale);
void display_loader(uint16_t progress, uint16_t fgcolor, uint16_t bgcolor, const uint8_t *icon, uint32_t iconlen, uint16_t iconfgcolor);
void display_raw(uint8_t reg, const uint8_t *data, int datalen);
void display_save(const char *filename);

#endif
