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

#include "keyboard.h"
#include <string.h>
#include "buttons.h"
#include "memzero.h"
#include "messages-common.pb.h"
#include "messages.h"
#include "messages.pb.h"
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
#define MAX_INPUT_LEN 50
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
#define LABEL_CANCEL "Exit"
#define LABEL_DONE "OK"

#define CURSOR_WIDTH 5
#define CURSOR_HEIGHT 2
static int select_index = -1;
static int kbd_layout = 0;
static char oldTiny = '\0';

enum {
  STATUS_IN_PROGRESS = 0,
  STATUS_DONE = 1,
  STATUS_CANCELLED = 2,
} status = STATUS_IN_PROGRESS;

#define INPUT_OFFSET KBD_X_OFFSET
#define TEXT_OFFSET 0
CONFIDENTIAL char input[MAX_INPUT_LEN + 1] = "";

typedef struct {
  int select_index;
  bool input_done;
  int kbd_layout;
  bool left_shift;
  bool right_shift;
} State;

static void drawBtn(int i, const char *text) {
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

static void drawBtnLeft(const char *label) {
  int x = KBD_X_OFFSET - BTN_X_SEP;
  oledBox(0, OLED_HEIGHT - 9, x, OLED_HEIGHT - 1, false);
  if (label)
    oledDrawStringCenter(KBD_X_OFFSET / 2 - 1, OLED_HEIGHT - 8, label,
                         FONT_STANDARD);
  else
    oledDrawBitmap(3, OLED_HEIGHT - 7, &bmp_btn_up);
  oledInvert(0, OLED_HEIGHT - 9, x, OLED_HEIGHT - 1);
}

static void drawBtnRight(const char *label) {
  int x = KBD_X_OFFSET + KBD_COLS * (BTN_WIDTH + BTN_X_SEP) - 1;
  oledBox(x, OLED_HEIGHT - 9, OLED_WIDTH - 1, OLED_HEIGHT - 1, false);
  if (label)
    oledDrawStringCenter((OLED_WIDTH + x + 1) / 2, OLED_HEIGHT - 8, label,
                         FONT_STANDARD);
  else
    oledDrawBitmap(OLED_WIDTH - 14, OLED_HEIGHT - 8, &bmp_btn_right);
  oledInvert(x, OLED_HEIGHT - 9, OLED_WIDTH - 1, OLED_HEIGHT - 1);
}

static void drawKeyboard(void) {
  oledBox(KBD_X_OFFSET, KBD_Y_OFFSET, KBD_X_OFFSET + KBD_WIDTH - 1,
          KBD_Y_OFFSET + KBD_HEIGHT - 1, false);

  for (int i = 0; i < KBD_SIZE; ++i) {
    drawBtn(i, KBD_LABELS[kbd_layout][i]);
  }

  int x = KBD_X_OFFSET + 0 * (BTN_WIDTH + BTN_X_SEP);
  int y = KBD_Y_OFFSET + 3 * (BTN_HEIGHT + BTN_Y_SEP);
  if (input[0] == '\0') {
    oledDrawBitmap(x + 8, y + 2, &bmp_btn_cancel);
  } else {
    oledDrawBitmap(x + 3, y + 1, &bmp_btn_backspace);
  }

  x = KBD_X_OFFSET + 2 * (BTN_WIDTH + BTN_X_SEP);
  y = KBD_Y_OFFSET + 3 * (BTN_HEIGHT + BTN_Y_SEP);
  oledDrawBitmap(x + 8, y + 2, &bmp_btn_confirm);
}

static void drawCursor(void) {
  int x = INPUT_OFFSET + oledStringWidth(input, FONT_STANDARD);
  oledBox(x, FONT_HEIGHT - CURSOR_HEIGHT, x + CURSOR_WIDTH - 1, FONT_HEIGHT - 1,
          true);
}

static void invertBtn(int i, int j) {
  int x = KBD_X_OFFSET + i * (BTN_WIDTH + BTN_X_SEP);
  int y = KBD_Y_OFFSET + j * (BTN_HEIGHT + BTN_Y_SEP);
  oledInvert(x, y, x + BTN_WIDTH - 1, y + BTN_HEIGHT - 1);
  oledRefresh();
}

static void pressBtn(int btn) {
  int len = strlen(input);
  if (btn == BTN_DONE) {
    status = STATUS_DONE;
  } else if (btn == BTN_BACKSPACE) {
    if (len > 0) {
      input[len - 1] = '\0';
      if (len == 1) {
        // Replace backspace with cancel button.
        drawKeyboard();
        select_index = -2;  // Avoid accidentally pressing the cancel button.
      }
    } else if (select_index == -1) {
      // Cancel only if this is not a repeated pressing of backspace.
      status = STATUS_CANCELLED;
    }
  } else {
    int btn_len = strlen(KBD_LABELS[kbd_layout][btn]);
    int pos = len;
    if (select_index >= 0) {
      pos -= 1;
      select_index = (select_index + 1) % btn_len;
    } else {
      select_index = 0;
    }
    if (pos < MAX_INPUT_LEN) {
      input[pos] = KBD_LABELS[kbd_layout][btn][select_index];
      input[pos + 1] = '\0';
    }

    if (len == 0 && pos == 0) {
      // Replace cancel button with backspace.
      drawKeyboard();
    }

    if (btn_len == 1) {
      // If the button has only one symbol, then pressing it repeatedly should
      // cause the symbol to be typed repeatedly.
      select_index = -1;
    }
  }
  oledBox(TEXT_OFFSET, 0, OLED_WIDTH - 1, FONT_HEIGHT, false);
  oledDrawString(INPUT_OFFSET, 0, input, FONT_STANDARD);
  if (select_index < 0) drawCursor();
}

#define STATE_NONE 0
#define STATE_LEFT_DOWN 1
#define STATE_RIGHT_DOWN 2
#define STATE_SHIFT 4
#define STATE_LEFT_SHIFT (STATE_LEFT_DOWN | STATE_SHIFT)
#define STATE_RIGHT_SHIFT (STATE_RIGHT_DOWN | STATE_SHIFT)

#define EVENT_NONE 0
#define EVENT_LEFT 1
#define EVENT_RIGHT 2
#define EVENT_SHIFTED_LEFT 4
#define EVENT_SHIFTED_RIGHT 8
#define EVENT_LEFT_SHIFT 16
#define EVENT_RIGHT_SHIFT 32
#define EVENT_SHIFT_RELEASE 64

int button_handler(State *state) {
  int events = 0;

  buttonUpdate();
  if (button.YesReleased) {
    if (state->right_shift) {
      state->right_shift = false;
      events |= EVENT_SHIFT_RELEASE;
    } else {
      if (button.YesDown > button.NoDown) {
        // Right
        events |= EVENT_RIGHT;
      } else {
        // Shift + Right
        events |= EVENT_SHIFTED_RIGHT;
        state->left_shift = true;
      }
    }
  }

  if (button.NoReleased) {
    if (state->left_shift) {
      state->left_shift = false;
      events |= EVENT_SHIFT_RELEASE;
    } else {
      if (button.NoDown > button.YesDown) {
        // Left
        events |= EVENT_LEFT;
      } else {
        // Shift + Left
        events |= EVENT_SHIFTED_LEFT;
        state->right_shift = true;
      }
    }
  }

  if (button.NoDown == 1 && button.YesDown <= 1) {
    events |= EVENT_LEFT_SHIFT;
  }

  if (button.YesDown == 1 && button.NoDown <= 1) {
    events |= EVENT_RIGHT_SHIFT;
  }

  return events;
}

static bool host_cancelled(void) {
  return (msg_tiny_id == MessageType_MessageType_Cancel) ||
         (msg_tiny_id == MessageType_MessageType_Initialize);
}

static void usb_begin(ButtonRequestType type) {
  ButtonRequest resp = {0};

  memzero(&resp, sizeof(ButtonRequest));
  resp.has_code = true;
  resp.code = type;
  oldTiny = usbTiny(1);
  msg_write(MessageType_MessageType_ButtonRequest, &resp);

  while (!host_cancelled()) {
    usbPoll();

    // wait for ButtonAck
    if (msg_tiny_id == MessageType_MessageType_ButtonAck) {
      msg_tiny_id = 0xFFFF;
      break;
    }
  }
}

static bool usb_cancelled(void) {
  usbPoll();
  if (host_cancelled()) {
    msg_tiny_id = 0xFFFF;
    return true;
  }
  return false;
}

static void usb_finish(void) { usbTiny(oldTiny); }

const char *pin_keyboard(const char *text) {
  input[0] = '\0';
  select_index = -1;
  status = STATUS_IN_PROGRESS;
  kbd_layout = 3;

  usb_begin(ButtonRequestType_ButtonRequest_PinEntry);

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
  while (status == STATUS_IN_PROGRESS) {
    usbSleep(5);
    if (usb_cancelled()) {
      status = STATUS_CANCELLED;
      break;
    }

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
        if (input[0] == '\0') {
          label = LABEL_CANCEL;
        } else {
          label = LABEL_BACKSPACE;
        }
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
        if (input[0] == '\0') {
          label = LABEL_CANCEL;
        } else {
          label = LABEL_BACKSPACE;
        }
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

  usb_finish();

  // Wait for buttons to be released.
  while (button.NoDown || button.YesDown) {
    usbSleep(5);
    buttonUpdate();
  }

  if (status == STATUS_DONE) {
    return input;
  } else {
    return NULL;
  }
}

const char *passphrase_keyboard(const char *text) {
  input[0] = '\0';
  select_index = -1;
  status = STATUS_IN_PROGRESS;
  kbd_layout = 0;

  usb_begin(ButtonRequestType_ButtonRequest_PassphraseEntry);

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
  while (status == STATUS_IN_PROGRESS) {
    usbSleep(5);
    if (usb_cancelled()) {
      status = STATUS_CANCELLED;
      break;
    }

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
        if (input[0] == '\0') {
          label = LABEL_CANCEL;
        } else {
          label = LABEL_BACKSPACE;
        }
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

  usb_finish();

  // Wait for buttons to be released.
  while (button.NoDown || button.YesDown) {
    usbSleep(5);
    buttonUpdate();
  }

  if (status == STATUS_DONE) {
    return input;
  } else {
    return NULL;
  }
}
