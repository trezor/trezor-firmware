
#ifndef _LTDC_H
#define _LTDC_H

#include STM32_HAL_H

// ILI9341V, GC9307 and ST7789V drivers support 240px x 320px display resolution
#define MAX_DISPLAY_RESX 240
#define MAX_DISPLAY_RESY 320
#define DISPLAY_RESX 240
#define DISPLAY_RESY 240
#define TREZOR_FONT_BPP 4

extern uint8_t *const DISPLAY_DATA_ADDRESS;

#endif  //_LTDC_H
