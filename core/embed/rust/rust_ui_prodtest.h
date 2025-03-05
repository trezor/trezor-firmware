#include <trezor_types.h>

void screen_prodtest_info(char* id, uint8_t id_len);

void screen_prodtest_welcome(void);

void screen_prodtest_bars(const char* colors, size_t color_count);

void screen_prodtest_show_text(const char* text, uint8_t text_len);

void screen_prodtest_touch(int16_t x0, int16_t y0, int16_t w, int16_t h);

void screen_prodtest_border(void);

void screen_prodtest_draw(uint32_t* events, uint32_t events_len);
