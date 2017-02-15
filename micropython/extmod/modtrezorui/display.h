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
int display_orientation(int degrees);
int display_backlight(int val);
int *display_offset(int xy[2]);

void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1);

void display_clear(void);
void display_refresh(void);

void display_bar(int x, int y, int w, int h, uint16_t c);
void display_bar_radius(int x, int y, int w, int h, uint16_t c, uint16_t b, uint8_t r);
void display_image(int x, int y, int w, int h, const void *data, int datalen);
void display_icon(int x, int y, int w, int h, const void *data, int datalen, uint16_t fgcolor, uint16_t bgcolor);
void display_qrcode(int x, int y, const char *data, int datalen, uint8_t scale);
void display_loader(uint16_t progress, int yoffset, uint16_t fgcolor, uint16_t bgcolor, const uint8_t *icon, uint32_t iconlen, uint16_t iconfgcolor);
void display_print(const char *text, int textlen);
void display_text(int x, int y, const char *text, int textlen, uint8_t font, uint16_t fgcolor, uint16_t bgcolor);
void display_text_center(int x, int y, const char *text, int textlen, uint8_t font, uint16_t fgcolor, uint16_t bgcolor);
void display_text_right(int x, int y, const char *text, int textlen, uint8_t font, uint16_t fgcolor, uint16_t bgcolor);
int display_text_width(const char *text, int textlen, uint8_t font);

void display_raw(uint8_t reg, const uint8_t *data, int datalen);
void display_save(const char *filename);

#endif
