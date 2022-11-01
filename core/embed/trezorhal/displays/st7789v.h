#ifndef _ST7789V_H
#define _ST7789V_H

#include STM32_HAL_H

// ILI9341V, GC9307 and ST7789V drivers support 240px x 320px display resolution
#define MAX_DISPLAY_RESX 240
#define MAX_DISPLAY_RESY 320
#define DISPLAY_RESX 240
#define DISPLAY_RESY 240
#define TREZOR_FONT_BPP 4

extern __IO uint8_t *const DISPLAY_CMD_ADDRESS;
extern __IO uint8_t *const DISPLAY_DATA_ADDRESS;

#define CMD(X) (*DISPLAY_CMD_ADDRESS = (X))
#define DATA(X) (*DISPLAY_DATA_ADDRESS = (X))
#define PIXELDATA(X) \
  DATA((X)&0xFF);    \
  DATA((X) >> 8)

void display_set_little_endian(void);
void display_set_big_endian(void);
void display_set_slow_pwm(void);

#endif  //_ST7789V_H
