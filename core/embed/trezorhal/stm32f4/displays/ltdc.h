
#ifndef _LTDC_H
#define _LTDC_H

#include STM32_HAL_H

#define TREZOR_FONT_BPP 4
#define DISPLAY_FRAMEBUFFER_WIDTH MAX_DISPLAY_RESX
#define DISPLAY_FRAMEBUFFER_HEIGHT MAX_DISPLAY_RESY
#define DISPLAY_FB_BPP 2
#define DISPLAY_COLOR_MODE DMA2D_OUTPUT_RGB565
#define DISPLAY_EFFICIENT_CLEAR 1

extern uint8_t* const DISPLAY_DATA_ADDRESS;

static inline void display_pixel(uint8_t* fb, int16_t x, int16_t y,
                                 uint16_t color) {
  uint32_t p = DISPLAY_FB_BPP * (y * DISPLAY_FRAMEBUFFER_WIDTH + x);
  fb[p + 1] = (color >> 8);
  fb[p] = (color >> 0) & 0xff;
}

#endif  //_LTDC_H
