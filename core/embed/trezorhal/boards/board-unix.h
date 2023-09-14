#ifndef _BOARD_UNIX_H
#define _BOARD_UNIX_H

#ifdef TREZOR_MODEL_T
#define USE_TOUCH 1
#define USE_SD_CARD 1
#define USE_SBU 1
#define USE_RGB_COLORS 1
#define USE_BACKLIGHT 1
#endif

#ifdef TREZOR_MODEL_1
#define USE_BUTTON 1
#endif

#ifdef TREZOR_MODEL_R
#define USE_BUTTON 1
#define USE_SBU 1
#define USE_OPTIGA 1
#endif

#include "display-unix.h"

#ifdef TREZOR_MODEL_R
#define USE_BUTTON 1
#elif TREZOR_MODEL_T
#define USE_TOUCH 1
#endif

#endif  //_BOARD_UNIX_H
