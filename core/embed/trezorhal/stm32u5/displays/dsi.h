#ifndef DSI_H_
#define DSI_H_

#include STM32_HAL_H

#define DISPLAY_COLOR_MODE DMA2D_OUTPUT_ARGB8888
#define DISPLAY_FRAMEBUFFER_WIDTH 768
#define DISPLAY_FRAMEBUFFER_HEIGHT 480
#define DISPLAY_FRAMEBUFFER_OFFSET_X 120
#define DISPLAY_FRAMEBUFFER_OFFSET_Y 120

#define DISPLAY_EFFICIENT_CLEAR 1

extern uint8_t* const DISPLAY_DATA_ADDRESS;

uint32_t rgb565_to_rgb888(uint16_t color);

static inline void display_pixel(uint8_t* fb, int16_t x, int16_t y,
                                 uint16_t color) {
  uint32_t p = 4 * ((y + 120) * DISPLAY_FRAMEBUFFER_WIDTH + (x + 120));
  uint32_t c = rgb565_to_rgb888(color);
  *((uint32_t*)(fb + p)) = c;
}

#endif
