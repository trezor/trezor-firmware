
#ifndef TREZORHAL_DISPLAY_LEGACY_H
#define TREZORHAL_DISPLAY_LEGACY_H

#include <buffers.h>
#include <stdint.h>

#define DISPLAY_FRAMEBUFFER_WIDTH 768
#define DISPLAY_FRAMEBUFFER_HEIGHT 480
#define DISPLAY_FRAMEBUFFER_OFFSET_X 0
#define DISPLAY_FRAMEBUFFER_OFFSET_Y 0

// Functions emulating legacy API
//

int display_orientation(int angle);
int display_backlight(int level);
void display_refresh(void);
void display_shift_window(uint16_t pixels);
uint16_t display_get_window_offset(void);
void display_pixeldata_dirty(void);
uint8_t* display_get_wr_addr(void);
void display_sync(void);
void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1);
void display_pixeldata(uint16_t c);
uint32_t* display_get_fb_addr(void);

void display_clear(void);
void display_text_render_buffer(const char* text, int textlen, int font,
                                buffer_text_t* buffer, int text_offset);

#define PIXELDATA(c) display_pixeldata(c)

#endif  // TREZORHAL_DISPLAY_LEGACY_H
