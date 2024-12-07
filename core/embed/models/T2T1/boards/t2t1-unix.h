#ifndef BOARDS_T2T1_UNIX_H
#define BOARDS_T2T1_UNIX_H

#define ORIENTATION_NSEW 1

#ifdef TREZOR_EMULATOR_RASPI
#define WINDOW_WIDTH 480
#define WINDOW_HEIGHT 320
#define TOUCH_OFFSET_X 110
#define TOUCH_OFFSET_Y 40

#define BACKGROUND_FILE "background_raspi.h"
#define BACKGROUND_NAME background_raspi_jpg

#else
#define WINDOW_WIDTH 400
#define WINDOW_HEIGHT 600
#define TOUCH_OFFSET_X 80
#define TOUCH_OFFSET_Y 110

#define BACKGROUND_FILE "T2T1/background_T.h"
#define BACKGROUND_NAME background_T_jpg

#endif

#endif  // BOARDS_T2T1_UNIX_H
