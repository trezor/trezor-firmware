#ifndef __BITMAPS_H__
#define __BITMAPS_H__

#include <stdint.h>

typedef struct {
  uint8_t width, height;
  const uint8_t *data;
} BITMAP;

extern const BITMAP bmp_btn_cancel;
extern const BITMAP bmp_btn_confirm;
extern const BITMAP bmp_digit0;
extern const BITMAP bmp_digit1;
extern const BITMAP bmp_digit2;
extern const BITMAP bmp_digit3;
extern const BITMAP bmp_digit4;
extern const BITMAP bmp_digit5;
extern const BITMAP bmp_digit6;
extern const BITMAP bmp_digit7;
extern const BITMAP bmp_digit8;
extern const BITMAP bmp_digit9;
extern const BITMAP bmp_gears0;
extern const BITMAP bmp_gears1;
extern const BITMAP bmp_gears2;
extern const BITMAP bmp_gears3;
extern const BITMAP bmp_icon_error;
extern const BITMAP bmp_icon_info;
extern const BITMAP bmp_icon_ok;
extern const BITMAP bmp_icon_question;
extern const BITMAP bmp_icon_warning;
extern const BITMAP bmp_logo48;
extern const BITMAP bmp_logo48_empty;
extern const BITMAP bmp_logo64;
extern const BITMAP bmp_logo64_empty;
extern const BITMAP bmp_webauthn;

#endif
