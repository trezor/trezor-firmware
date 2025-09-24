#pragma once

#include <trezor_types.h>

#include <sys/sysevent.h>

#include "rust_types.h"
// common event function for screens that need UI + communication
uint32_t screen_prodtest_event(c_layout_t* layout, sysevents_t* signalled);

// void screen_prodtest_info(char* id, uint8_t id_len);

void screen_prodtest_welcome(c_layout_t* layout, char* id, uint8_t id_len);

void screen_prodtest_bars(const char* colors, size_t color_count);

void screen_prodtest_show_text(const char* text, uint8_t text_len);

void screen_prodtest_large_label(const char* text1, uint8_t text_len1,
                                const char* text2, uint8_t text_len2,
                                const char* text3, uint8_t text_len3);

void screen_prodtest_touch(int16_t x0, int16_t y0, int16_t w, int16_t h);

void screen_prodtest_border(void);

void screen_prodtest_draw(uint32_t* events, uint32_t events_len);
