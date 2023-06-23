#ifndef _DISPLAY_UNIX_H
#define _DISPLAY_UNIX_H

#include <stdint.h>

#ifdef TREZOR_MODEL_T
// ILI9341V, GC9307 and ST7789V drivers support 240px x 320px display resolution
#define MAX_DISPLAY_RESX 240
#define MAX_DISPLAY_RESY 320
#define DISPLAY_RESX 240
#define DISPLAY_RESY 240
#define TREZOR_FONT_BPP 4
#endif

#ifdef TREZOR_MODEL_R
#define MAX_DISPLAY_RESX 128
#define MAX_DISPLAY_RESY 64
#define DISPLAY_RESX 128
#define DISPLAY_RESY 64
#define TREZOR_FONT_BPP 1
#endif

#ifdef TREZOR_MODEL_1
#define MAX_DISPLAY_RESX 128
#define MAX_DISPLAY_RESY 64
#define DISPLAY_RESX 128
#define DISPLAY_RESY 64
#define TREZOR_FONT_BPP 1
#endif

extern uint8_t *const DISPLAY_DATA_ADDRESS;

#endif  //_DISPLAY_UNIX_H
