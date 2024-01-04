#ifndef _ST7789V_H
#define _ST7789V_H

#include STM32_HAL_H

typedef struct {
  uint16_t x;
  uint16_t y;
} display_padding_t;

#include TREZOR_BOARD

// ILI9341V, GC9307 and ST7789V drivers support 240px x 320px display resolution
#define MAX_DISPLAY_RESX 240
#define MAX_DISPLAY_RESY 320
#define DISPLAY_COLOR_MODE DMA2D_OUTPUT_RGB565
#define TREZOR_FONT_BPP 4

#ifdef USE_DISP_I8080_16BIT_DW
#define DISP_MEM_TYPE uint16_t
#elif USE_DISP_I8080_8BIT_DW
#define DISP_MEM_TYPE uint8_t
#else
#error "Unsupported display interface"
#endif

#define DISP_MEM_TYPE uint8_t

extern __IO DISP_MEM_TYPE *const DISPLAY_CMD_ADDRESS;
extern __IO DISP_MEM_TYPE *const DISPLAY_DATA_ADDRESS;

#define CMD(X) (*DISPLAY_CMD_ADDRESS = (X))
#define DATA(X) (*DISPLAY_DATA_ADDRESS = (X))

void display_set_little_endian(void);
void display_set_big_endian(void);
void display_set_slow_pwm(void);

#ifdef FRAMEBUFFER
#define DISPLAY_FRAMEBUFFER_WIDTH DISPLAY_RESX
#define DISPLAY_FRAMEBUFFER_HEIGHT DISPLAY_RESY

#define DISPLAY_EFFICIENT_CLEAR 1

static inline void display_pixel(uint8_t *fb, int16_t x, int16_t y,
                                 uint16_t color) {
  uint32_t p = 2 * (y * DISPLAY_FRAMEBUFFER_WIDTH + x);
  *((uint16_t *)(fb + p)) = color;
}
void display_efficient_clear(void);

#else

#ifdef USE_DISP_I8080_16BIT_DW
#define PIXELDATA(X) DATA(X)
#elif USE_DISP_I8080_8BIT_DW
#define PIXELDATA(X) \
  DATA((X)&0xFF);    \
  DATA((X) >> 8)
#endif

#endif

#endif  //_ST7789V_H
