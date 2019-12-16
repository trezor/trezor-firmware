/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2019 SatoshiLabs
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <string.h>
#include "buttons.h"
#include "memzero.h"
#include "oled.h"
#include "usb.h"

#define BTN_WIDTH 23
#define BTN_HEIGHT 11
#define BTN_X_SEP 4
#define BTN_Y_SEP 3
#define KBD_COLS 3
#define KBD_ROWS 4
#define KBD_SIZE (KBD_COLS * KBD_ROWS)
#define KBD_X_OFFSET 26
#define KBD_Y_OFFSET 10
#define KBD_HEIGHT (KBD_ROWS * (BTN_HEIGHT + BTN_Y_SEP) - BTN_Y_SEP + 1)
#define KBD_WIDTH (KBD_COLS * (BTN_WIDTH + BTN_X_SEP) - BTN_X_SEP + 1)
#define KBD_COUNT 4
#define MAX_INPUT_LEN 15
const char *KBD_LABELS[KBD_COUNT][KBD_SIZE] = {
    {"abc", "def", "ghi", "jkl", "mno", "pqr", "stu", "vwx", "yz ", "", "*#",
     ""},
    {"ABC", "DEF", "GHI", "JKL", "MNO", "PQR", "STU", "VWX", "YZ ", "", "*#",
     ""},
    {"_<>", ".:@", "/|\\", "!()", "+%&", "-[]", "?{}", ",'`", ";\"~", "",
     "$^=", ""},
    {"1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", ""},
};

#define BTN_BACKSPACE 9
#define BTN_DONE 11
#define LABEL_BACKSPACE "Bksp"
#define LABEL_DONE "OK"

#define CURSOR_WIDTH 5
#define CURSOR_HEIGHT 2
int select_index = -1;
bool input_done = false;
int kbd_layout = 0;

#define INPUT_OFFSET KBD_X_OFFSET
#define TEXT_OFFSET 0
CONFIDENTIAL char input[MAX_INPUT_LEN + 1] = "";

void drawBtn(int i, const char *text) {
  int x = KBD_X_OFFSET + (i % KBD_COLS) * (BTN_WIDTH + BTN_X_SEP);
  int y = KBD_Y_OFFSET + (i / KBD_COLS) * (BTN_HEIGHT + BTN_Y_SEP);
  for (int j = 0; j < BTN_WIDTH; j++) {
    oledDrawPixel(x + j, y - 1);
    oledDrawPixel(x + j, y + BTN_HEIGHT);
  }
  for (int j = 0; j < BTN_HEIGHT; j++) {
    oledDrawPixel(x - 1, y + j);
    oledDrawPixel(x + BTN_WIDTH, y + j);
  }
  oledDrawStringCenter(x + BTN_WIDTH / 2 + 1, y + 2, text, FONT_STANDARD);
}

void drawBtnLeft(const char *label) {
  int x = KBD_X_OFFSET - BTN_X_SEP;
  oledBox(0, OLED_HEIGHT - 9, x, OLED_HEIGHT - 1, false);
  if (label)
    oledDrawStringCenter(KBD_X_OFFSET / 2 - 1, OLED_HEIGHT - 8, label,
                         FONT_STANDARD);
  else
    oledDrawBitmap(3, OLED_HEIGHT - 7, &bmp_btn_up);
  oledInvert(0, OLED_HEIGHT - 9, x, OLED_HEIGHT - 1);
}

void drawBtnRight(const char *label) {
  int x = KBD_X_OFFSET + KBD_COLS * (BTN_WIDTH + BTN_X_SEP) - 1;
  oledBox(x, OLED_HEIGHT - 9, OLED_WIDTH - 1, OLED_HEIGHT - 1, false);
  if (label)
    oledDrawStringCenter((OLED_WIDTH + x + 1) / 2, OLED_HEIGHT - 8, label,
                         FONT_STANDARD);
  else
    oledDrawBitmap(OLED_WIDTH - 14, OLED_HEIGHT - 8, &bmp_btn_right);
  oledInvert(x, OLED_HEIGHT - 9, OLED_WIDTH - 1, OLED_HEIGHT - 1);
}

void drawKeyboard(void) {
  oledBox(KBD_X_OFFSET, KBD_Y_OFFSET, KBD_X_OFFSET + KBD_WIDTH - 1,
          KBD_Y_OFFSET + KBD_HEIGHT - 1, false);

  for (int i = 0; i < KBD_SIZE; ++i) {
    drawBtn(i, KBD_LABELS[kbd_layout][i]);
  }

  int x = KBD_X_OFFSET + 0 * (BTN_WIDTH + BTN_X_SEP);
  int y = KBD_Y_OFFSET + 3 * (BTN_HEIGHT + BTN_Y_SEP);
  oledDrawBitmap(x + 3, y + 1, &bmp_btn_backspace);

  x = KBD_X_OFFSET + 2 * (BTN_WIDTH + BTN_X_SEP);
  y = KBD_Y_OFFSET + 3 * (BTN_HEIGHT + BTN_Y_SEP);
  oledDrawBitmap(x + 8, y + 2, &bmp_btn_confirm);
}

void drawCursor(void) {
  int x = INPUT_OFFSET + oledStringWidth(input, FONT_STANDARD);
  oledBox(x, FONT_HEIGHT - CURSOR_HEIGHT, x + CURSOR_WIDTH - 1, FONT_HEIGHT - 1,
          true);
}

void invertBtn(int i, int j) {
  int x = KBD_X_OFFSET + i * (BTN_WIDTH + BTN_X_SEP);
  int y = KBD_Y_OFFSET + j * (BTN_HEIGHT + BTN_Y_SEP);
  oledInvert(x, y, x + BTN_WIDTH - 1, y + BTN_HEIGHT - 1);
  oledRefresh();
}

void pressBtn(int btn) {
  if (btn == BTN_DONE) {
    input_done = true;
  } else if (btn == BTN_BACKSPACE) {
    int len = strlen(input);
    if (len > 0) input[len - 1] = '\0';
  } else {
    int len = strlen(input);
    int btn_len = strlen(KBD_LABELS[kbd_layout][btn]);
    if (select_index >= 0) {
      len -= 1;
      select_index = (select_index + 1) % btn_len;
    } else {
      select_index = 0;
    }
    if (len < MAX_INPUT_LEN) {
      input[len] = KBD_LABELS[kbd_layout][btn][select_index];
      input[len + 1] = '\0';
    }

    if (btn_len == 1) {
      select_index = -1;
    }
  }
  oledBox(TEXT_OFFSET, 0, OLED_WIDTH - 1, FONT_HEIGHT, false);
  oledDrawString(INPUT_OFFSET, 0, input, FONT_STANDARD);
  if (select_index < 0) drawCursor();
}

const char *pin_keyboard(const char *text) {
  input[0] = '\0';
  select_index = -1;
  input_done = false;
  kbd_layout = 3;

  oledClear();
  oledDrawString(TEXT_OFFSET, 0, text, FONT_STANDARD);
  drawKeyboard();
  drawBtnLeft(NULL);
  drawBtnRight(NULL);

  int i = 0;
  int j = 0;
  bool left_shift = false;
  bool right_shift = false;
  invertBtn(i, j);
  while (!input_done) {
    usbSleep(5);
    bool refresh = false;

    buttonUpdate();
    if (button.YesReleased) {
      if (right_shift) {
        right_shift = false;
        select_index = -1;
        drawCursor();
        drawBtnLeft(NULL);
        drawBtnRight(NULL);
      } else {
        invertBtn(i, j);
        if (button.YesDown > button.NoDown) {
          // Right
          if (i == KBD_COLS - 1) {
            i = 0;
            j = (j + 1) % KBD_ROWS;
          } else {
            i = i + 1;
          }
          select_index = -1;
          drawCursor();
          drawBtnLeft(NULL);
          drawBtnRight(NULL);
        } else {
          // Shift + Right
          pressBtn(i + j * KBD_COLS);
          left_shift = true;
          drawBtnLeft("");
        }
        invertBtn(i, j);
      }
      refresh = true;
    } else if (button.NoReleased) {
      if (left_shift) {
        left_shift = false;
        select_index = -1;
        drawCursor();
        drawBtnLeft(NULL);
        drawBtnRight(NULL);
      } else {
        invertBtn(i, j);
        if (button.NoDown > button.YesDown) {
          // Left
          i = 0;
          j = (j - 1 + KBD_ROWS) % KBD_ROWS;
          select_index = -1;
          drawCursor();
          drawBtnLeft(NULL);
          drawBtnRight(NULL);
        } else {
          // Shift + Left
          pressBtn(i + j * KBD_COLS);
          right_shift = true;
          drawBtnRight("");
        }
        invertBtn(i, j);
      }
      refresh = true;
    }

    if (button.NoDown == 1 && button.YesDown <= 1) {
      int btn = i + j * KBD_COLS;
      const char *label = NULL;
      if (btn == BTN_BACKSPACE) {
        label = LABEL_BACKSPACE;
      } else if (btn == BTN_DONE) {
        label = LABEL_DONE;
      } else {
        label = KBD_LABELS[kbd_layout][btn];
      }
      drawBtnRight(label);
      refresh = true;
    }

    if (button.YesDown == 1 && button.NoDown <= 1) {
      int btn = i + j * KBD_COLS;
      const char *label = NULL;
      if (btn == BTN_BACKSPACE) {
        label = LABEL_BACKSPACE;
      } else if (btn == BTN_DONE) {
        label = LABEL_DONE;
      } else {
        label = KBD_LABELS[kbd_layout][btn];
      }
      drawBtnLeft(label);
      refresh = true;
    }

    if (refresh) {
      oledRefresh();
    }
  }

  return input;
}

const char *passphrase_keyboard(const char *text) {
  input[0] = '\0';
  select_index = -1;
  input_done = false;
  kbd_layout = 0;

  oledClear();
  oledDrawString(TEXT_OFFSET, 0, text, FONT_STANDARD);
  drawKeyboard();
  drawBtnLeft(NULL);
  drawBtnRight(NULL);

  int i = 0;
  int j = 0;
  bool left_shift = false;
  bool right_shift = false;
  invertBtn(i, j);
  while (!input_done) {
    usbSleep(5);
    bool refresh = false;

    buttonUpdate();
    if (button.YesReleased) {
      if (right_shift) {
        right_shift = false;
        select_index = -1;
        drawCursor();
        drawBtnLeft(NULL);
        drawBtnRight(NULL);
      } else {
        invertBtn(i, j);
        if (button.YesDown > button.NoDown) {
          // Right
          if (i == KBD_COLS - 1) {
            i = 0;
            j = (j + 1) % KBD_ROWS;
          } else {
            i = i + 1;
          }
          select_index = -1;
          drawCursor();
          drawBtnLeft(NULL);
          drawBtnRight(NULL);
        } else {
          // Shift + Right
          pressBtn(i + j * KBD_COLS);
          left_shift = true;
          drawBtnLeft("");
        }
        invertBtn(i, j);
      }
      refresh = true;
    } else if (button.NoReleased) {
      if (left_shift) {
        left_shift = false;
        select_index = -1;
        drawCursor();
        drawBtnLeft(NULL);
        drawBtnRight(NULL);
      } else {
        invertBtn(i, j);
        if (button.NoDown > button.YesDown) {
          // Left
          i = 0;
          j = (j - 1 + KBD_ROWS) % KBD_ROWS;
          select_index = -1;
          drawCursor();
          drawBtnLeft(NULL);
          drawBtnRight(NULL);
        } else {
          // Shift + Left
          kbd_layout = (kbd_layout + 1) % KBD_COUNT;
          drawKeyboard();
          right_shift = true;
          drawBtnRight("");
        }
        invertBtn(i, j);
      }
      refresh = true;
    }

    if (button.NoDown == 1 && button.YesDown <= 1) {
      int btn = i + j * KBD_COLS;
      const char *label = NULL;
      if (btn == BTN_BACKSPACE) {
        label = LABEL_BACKSPACE;
      } else if (btn == BTN_DONE) {
        label = LABEL_DONE;
      } else {
        label = KBD_LABELS[kbd_layout][btn];
      }
      drawBtnRight(label);
      refresh = true;
    }

    if (button.YesDown == 1 && button.NoDown <= 1) {
      drawBtnLeft("0aA!");
      refresh = true;
    }

    if (refresh) {
      oledRefresh();
    }
  }

  return input;
}
