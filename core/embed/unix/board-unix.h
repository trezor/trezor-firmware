#ifndef _BOARD_UNIX_H
#define _BOARD_UNIX_H

#ifdef TREZOR_MODEL_T
#define USE_TOUCH 1
#define USE_SD_CARD 1
#define USE_SBU 1
#define USE_RGB_COLORS 1
#endif

#ifdef TREZOR_MODEL_1
#define USE_BUTTON 1
#endif

#ifdef TREZOR_MODEL_R
#define USE_BUTTON 1
#define USE_SBU 1
#endif

#include "display-unix.h"

#endif  //_BOARD_UNIX_H
