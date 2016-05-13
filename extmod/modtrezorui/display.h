/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#ifndef __DISPLAY_H__
#define __DISPLAY_H__

#define RESX 240
#define RESY 240

void display_init(void);
void display_set_window(uint16_t x, uint16_t y, uint16_t w, uint16_t h);
void display_update(void);
void display_orientation(int degrees);
void display_backlight(uint8_t val);

void set_color_table(uint16_t colortable[16], uint16_t fgcolor, uint16_t bgcolor);
void display_bar(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint16_t c);
void display_bar_radius(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint16_t c, uint16_t b);
void display_blit(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const void *data, int datalen);
void display_image(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const void *data, int datalen);
void display_icon(uint8_t x, uint8_t y, uint8_t w, uint8_t h, const void *data, int datalen, uint16_t fgcolor, uint16_t bgcolor);
void display_text(uint8_t x, uint8_t y, const uint8_t *text, int textlen, uint8_t font, uint16_t fgcolor, uint16_t bgcolor);
uint32_t display_text_width(const uint8_t *text, int textlen, uint8_t font);
void display_qrcode(uint8_t x, uint8_t y, const char *data, int datalen, int scale);
void display_loader(uint16_t progress, uint16_t fgcolor, uint16_t bgcolor, const uint8_t *icon, uint32_t iconlen, uint16_t iconfgcolor);
void display_raw(uint8_t reg, const uint8_t *data, int datalen);

#endif
