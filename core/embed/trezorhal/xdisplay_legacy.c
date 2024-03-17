#include "xdisplay_legacy.h"
#include "xdisplay.h"

int display_orientation(int angle) {
  if (angle >= 0) {
    return display_set_orientation(angle);
  } else {
    return display_get_orientation();
  }
}

int display_backlight(int level) {
  if (level >= 0) {
    return display_set_backlight(level);
  } else {
    return display_get_backlight();
  }
}

void display_shift_window(uint16_t pixels){};

uint16_t display_get_window_offset(void) { return 0; }

void display_pixeldata_dirty(void) {}

uint8_t *display_get_wr_addr(void) { return (uint8_t *)0; }

void display_sync(void) {}

void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1) {}

void display_pixeldata(uint16_t c) {}

uint32_t *display_get_fb_addr(void) {
#ifdef XFRAMEBUFFER
  return (uint32_t *)display_get_frame_addr();
#else
  return (uint32_t *)0;
#endif
}

void display_offset(int set_xy[2], int *get_x, int *get_y) {
  *get_x = 0;
  *get_y = 0;
}

void display_clear(void) {}

void display_text_render_buffer(const char *text, int textlen, int font,
                                buffer_text_t *buffer, int text_offset) {}
