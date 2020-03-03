/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
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
#include "common.h"
#include "memzero.h"
#include "oled.h"
#include "prompt.h"
#include "timer.h"
#include "util.h"

#define OLED_SETCONTRAST 0x81
#define OLED_DISPLAYALLON_RESUME 0xA4
#define OLED_DISPLAYALLON 0xA5
#define OLED_NORMALDISPLAY 0xA6
#define OLED_INVERTDISPLAY 0xA7
#define OLED_DISPLAYOFF 0xAE
#define OLED_DISPLAYON 0xAF
#define OLED_SETDISPLAYOFFSET 0xD3
#define OLED_SETCOMPINS 0xDA
#define OLED_SETVCOMDETECT 0xDB
#define OLED_SETDISPLAYCLOCKDIV 0xD5
#define OLED_SETPRECHARGE 0xD9
#define OLED_SETMULTIPLEX 0xA8
#define OLED_SETLOWCOLUMN 0x00
#define OLED_SETHIGHCOLUMN 0x10
#define OLED_SETSTARTLINE 0x40
#define OLED_MEMORYMODE 0x20
#define OLED_COMSCANINC 0xC0
#define OLED_COMSCANDEC 0xC8
#define OLED_SEGREMAP 0xA0
#define OLED_CHARGEPUMP 0x8D

/* Trezor has a display of size OLED_WIDTH x OLED_HEIGHT (128x64).
 * The contents of this display are buffered in _oledbuffer.  This is
 * an array of OLED_WIDTH * OLED_HEIGHT/8 bytes.  At byte y*OLED_WIDTH + x
 * it stores the column of pixels from (x,8y) to (x,8y+7); the LSB stores
 * the top most pixel.  The pixel (0,0) is the top left corner of the
 * display.
 */

static uint8_t _oledbuffer[OLED_BUFSIZE];
static bool is_debug_link = 0;
Ble_Info g_ble_info;
USB_Info g_usb_info;

/*
 * macros to convert coordinate to bit position
 */
#define OLED_OFFSET(x, y) (OLED_BUFSIZE - 1 - (x) - ((y) / 8) * OLED_WIDTH)
#define OLED_MASK(x, y) (1 << (7 - (y) % 8))

/*
 * Return the state of the pixel at x, y
 */
bool oledGetPixel(int x, int y) {
  return _oledbuffer[OLED_OFFSET(x, y)] & OLED_MASK(x, y);
}

/*
 * Draws a white pixel at x, y
 */
void oledDrawPixel(int x, int y) {
  if ((x < 0) || (y < 0) || (x >= OLED_WIDTH) || (y >= OLED_HEIGHT)) {
    return;
  }
  _oledbuffer[OLED_OFFSET(x, y)] |= OLED_MASK(x, y);
}

/*
 * Clears pixel at x, y
 */
void oledClearPixel(int x, int y) {
  if ((x < 0) || (y < 0) || (x >= OLED_WIDTH) || (y >= OLED_HEIGHT)) {
    return;
  }
  _oledbuffer[OLED_OFFSET(x, y)] &= ~OLED_MASK(x, y);
}

/*
 * Inverts pixel at x, y
 */
void oledInvertPixel(int x, int y) {
  if ((x < 0) || (y < 0) || (x >= OLED_WIDTH) || (y >= OLED_HEIGHT)) {
    return;
  }
  _oledbuffer[OLED_OFFSET(x, y)] ^= OLED_MASK(x, y);
}

#if !EMULATOR
/*
 * Send a block of data via the SPI bus.
 */
static inline void SPISend(uint32_t base, const uint8_t *data, int len) {
  delay(1);
  for (int i = 0; i < len; i++) {
    spi_send(base, data[i]);
  }
  while (!(SPI_SR(base) & SPI_SR_TXE))
    ;
  while ((SPI_SR(base) & SPI_SR_BSY))
    ;
}

/*
 * Initialize the display.
 */
void oledInit() {
  static const uint8_t s[25] = {OLED_DISPLAYOFF,
                                OLED_SETDISPLAYCLOCKDIV,
                                0x80,
                                OLED_SETMULTIPLEX,
                                0x3F,  // 128x64
                                OLED_SETDISPLAYOFFSET,
                                0x00,
                                OLED_SETSTARTLINE | 0x00,
                                OLED_CHARGEPUMP,
                                0x14,
                                OLED_MEMORYMODE,
                                0x00,
                                OLED_SEGREMAP | 0x01,
                                OLED_COMSCANDEC,
                                OLED_SETCOMPINS,
                                0x12,  // 128x64
                                OLED_SETCONTRAST,
                                0xCF,
                                OLED_SETPRECHARGE,
                                0xF1,
                                OLED_SETVCOMDETECT,
                                0x40,
                                OLED_DISPLAYALLON_RESUME,
                                OLED_NORMALDISPLAY,
                                OLED_DISPLAYON};

  gpio_clear(OLED_DC_PORT, OLED_DC_PIN);  // set to CMD
  gpio_set(OLED_CS_PORT, OLED_CS_PIN);    // SPI deselect

  // Reset the LCD
  gpio_set(OLED_RST_PORT, OLED_RST_PIN);
  delay(40);
  gpio_clear(OLED_RST_PORT, OLED_RST_PIN);
  delay(400);
  gpio_set(OLED_RST_PORT, OLED_RST_PIN);

  // init
  gpio_clear(OLED_CS_PORT, OLED_CS_PIN);  // SPI select
  SPISend(SPI_BASE, s, 25);
  gpio_set(OLED_CS_PORT, OLED_CS_PIN);  // SPI deselect

  oledClear();
  oledRefresh();
}
#endif

/*
 * Clears the display buffer (sets all pixels to black)
 */
void oledClear() { memzero(_oledbuffer, sizeof(_oledbuffer)); }

void oledInvertDebugLink() {
  if (is_debug_link) {
    oledInvertPixel(OLED_WIDTH - 5, 0);
    oledInvertPixel(OLED_WIDTH - 4, 0);
    oledInvertPixel(OLED_WIDTH - 3, 0);
    oledInvertPixel(OLED_WIDTH - 2, 0);
    oledInvertPixel(OLED_WIDTH - 1, 0);
    oledInvertPixel(OLED_WIDTH - 4, 1);
    oledInvertPixel(OLED_WIDTH - 3, 1);
    oledInvertPixel(OLED_WIDTH - 2, 1);
    oledInvertPixel(OLED_WIDTH - 1, 1);
    oledInvertPixel(OLED_WIDTH - 3, 2);
    oledInvertPixel(OLED_WIDTH - 2, 2);
    oledInvertPixel(OLED_WIDTH - 1, 2);
    oledInvertPixel(OLED_WIDTH - 2, 3);
    oledInvertPixel(OLED_WIDTH - 1, 3);
    oledInvertPixel(OLED_WIDTH - 1, 4);
  }
}

/*
 * Refresh the display. This copies the buffer to the display to show the
 * contents.  This must be called after every operation to the buffer to
 * make the change visible.  All other operations only change the buffer
 * not the content of the display.
 */
#if !EMULATOR
void oledRefresh() {
  static const uint8_t s[3] = {OLED_SETLOWCOLUMN | 0x00,
                               OLED_SETHIGHCOLUMN | 0x00,
                               OLED_SETSTARTLINE | 0x00};

  // draw triangle in upper right corner
  oledInvertDebugLink();

  gpio_clear(OLED_CS_PORT, OLED_CS_PIN);  // SPI select
  SPISend(SPI_BASE, s, 3);
  gpio_set(OLED_CS_PORT, OLED_CS_PIN);  // SPI deselect

  gpio_set(OLED_DC_PORT, OLED_DC_PIN);    // set to DATA
  gpio_clear(OLED_CS_PORT, OLED_CS_PIN);  // SPI select
  SPISend(SPI_BASE, _oledbuffer, sizeof(_oledbuffer));
  gpio_set(OLED_CS_PORT, OLED_CS_PIN);    // SPI deselect
  gpio_clear(OLED_DC_PORT, OLED_DC_PIN);  // set to CMD

  // return it back
  oledInvertDebugLink();
}
#endif

const uint8_t *oledGetBuffer() { return _oledbuffer; }

void oledSetDebugLink(bool set) {
  is_debug_link = set;
  oledRefresh();
}

void oledSetBuffer(uint8_t *buf, uint16_t usLen) {
  memcpy(_oledbuffer, buf, usLen);
}
void oledclearLine(uint8_t line) {
  if (line < (OLED_HEIGHT / 8)) {
    memzero(_oledbuffer + OLED_WIDTH * (OLED_HEIGHT / 8 - line - 1),
            OLED_WIDTH);
  }
}

void oledDrawChar(int x, int y, char c, uint8_t font) {
  if (x >= OLED_WIDTH || y >= OLED_HEIGHT || y <= -FONT_HEIGHT) {
    return;
  }

  int zoom = (font & FONT_DOUBLE) ? 2 : 1;
  int char_width = fontCharWidth(font & 0x7f, (uint8_t)c);
  const uint8_t *char_data = fontCharData(font & 0x7f, (uint8_t)c);

  if (x <= -char_width) {
    return;
  }

  for (int xo = 0; xo < char_width; xo++) {
    for (int yo = 0; yo < FONT_HEIGHT; yo++) {
      if (char_data[xo] & (1 << (FONT_HEIGHT - 1 - yo))) {
        if (zoom <= 1) {
          oledDrawPixel(x + xo, y + yo);
        } else {
          oledBox(x + xo, y + yo * zoom, x + (xo + 1) - 1,
                  y + (yo + 1) * zoom - 1, true);
        }
      }
    }
  }
}

static uint8_t convert_char(const char a) {
  static char last_was_utf8 = 0;

  uint8_t c = a;

  // non-printable ASCII character
  if (c < ' ') {
    last_was_utf8 = 0;
    return '_';
  }

  // regular ASCII character
  if (c < 0x80) {
    last_was_utf8 = 0;
    return c;
  }

  // UTF-8 handling: https://en.wikipedia.org/wiki/UTF-8#Description

  // bytes 11xxxxxx are first bytes of UTF-8 characters
  if (c >= 0xC0) {
    last_was_utf8 = 1;
    return '_';
  }

  if (last_was_utf8) {
    // bytes 10xxxxxx can be successive UTF-8 characters ...
    return 0;  // skip glyph
  } else {
    // ... or they are just non-printable ASCII characters
    return '_';
  }

  return 0;
}

int oledStringWidth(const char *text, uint8_t font) {
  if (!text) return 0;
  int space = (font & FONT_DOUBLE) ? 2 : 1;
  int l = 0;
  for (; *text; text++) {
    uint8_t c = convert_char(*text);
    if (c) {
      l += fontCharWidth(font & 0x7f, c) + space;
    }
  }
  return l;
}

void oledDrawString(int x, int y, const char *text, uint8_t font) {
  if (!text) return;
  int l = 0;
  int space = (font & FONT_DOUBLE) ? 2 : 1;
  for (; *text; text++) {
    uint8_t c = convert_char(*text);
    if (c) {
      oledDrawChar(x + l, y, c, font);
      l += fontCharWidth(font & 0x7f, c) + space;
    }
  }
}

void oledDrawStringCenter(int x, int y, const char *text, uint8_t font) {
  x = x - oledStringWidth(text, font) / 2;
  oledDrawString(x, y, text, font);
}

void oledDrawStringRight(int x, int y, const char *text, uint8_t font) {
  x -= oledStringWidth(text, font);
  oledDrawString(x, y, text, font);
}

void oledDrawBitmap(int x, int y, const BITMAP *bmp) {
  for (int i = 0; i < bmp->width; i++) {
    for (int j = 0; j < bmp->height; j++) {
      if (bmp->data[(i / 8) + j * bmp->width / 8] & (1 << (7 - i % 8))) {
        oledDrawPixel(x + i, y + j);
      } else {
        oledClearPixel(x + i, y + j);
      }
    }
  }
}

/*
 * Inverts box between (x1,y1) and (x2,y2) inclusive.
 */
void oledInvert(int x1, int y1, int x2, int y2) {
  x1 = MAX(x1, 0);
  y1 = MAX(y1, 0);
  x2 = MIN(x2, OLED_WIDTH - 1);
  y2 = MIN(y2, OLED_HEIGHT - 1);
  for (int x = x1; x <= x2; x++) {
    for (int y = y1; y <= y2; y++) {
      oledInvertPixel(x, y);
    }
  }
}

/*
 * Draw a filled rectangle.
 */
void oledBox(int x1, int y1, int x2, int y2, bool set) {
  x1 = MAX(x1, 0);
  y1 = MAX(y1, 0);
  x2 = MIN(x2, OLED_WIDTH - 1);
  y2 = MIN(y2, OLED_HEIGHT - 1);
  for (int x = x1; x <= x2; x++) {
    for (int y = y1; y <= y2; y++) {
      set ? oledDrawPixel(x, y) : oledClearPixel(x, y);
    }
  }
}

void oledHLine(int y) {
  if (y < 0 || y >= OLED_HEIGHT) {
    return;
  }
  for (int x = 0; x < OLED_WIDTH; x++) {
    oledDrawPixel(x, y);
  }
}

/*
 * Draw a rectangle frame.
 */
void oledFrame(int x1, int y1, int x2, int y2) {
  for (int x = x1; x <= x2; x++) {
    oledDrawPixel(x, y1);
    oledDrawPixel(x, y2);
  }
  for (int y = y1 + 1; y < y2; y++) {
    oledDrawPixel(x1, y);
    oledDrawPixel(x2, y);
  }
}

/*
 * Animates the display, swiping the current contents out to the left.
 * This clears the display.
 */
void oledSwipeLeft(void) {
  for (int i = 0; i < OLED_WIDTH; i++) {
    for (int j = 0; j < OLED_HEIGHT / 8; j++) {
      for (int k = OLED_WIDTH - 1; k > 0; k--) {
        _oledbuffer[j * OLED_WIDTH + k] = _oledbuffer[j * OLED_WIDTH + k - 1];
      }
      _oledbuffer[j * OLED_WIDTH] = 0;
    }
    oledRefresh();
  }
}

/*
 * Animates the display, swiping the current contents out to the right.
 * This clears the display.
 */
void oledSwipeRight(void) {
  for (int i = 0; i < OLED_WIDTH / 4; i++) {
    for (int j = 0; j < OLED_HEIGHT / 8; j++) {
      for (int k = 0; k < OLED_WIDTH / 4 - 1; k++) {
        _oledbuffer[k * 4 + 0 + j * OLED_WIDTH] =
            _oledbuffer[k * 4 + 4 + j * OLED_WIDTH];
        _oledbuffer[k * 4 + 1 + j * OLED_WIDTH] =
            _oledbuffer[k * 4 + 5 + j * OLED_WIDTH];
        _oledbuffer[k * 4 + 2 + j * OLED_WIDTH] =
            _oledbuffer[k * 4 + 6 + j * OLED_WIDTH];
        _oledbuffer[k * 4 + 3 + j * OLED_WIDTH] =
            _oledbuffer[k * 4 + 7 + j * OLED_WIDTH];
      }
      _oledbuffer[j * OLED_WIDTH + OLED_WIDTH - 1] = 0;
      _oledbuffer[j * OLED_WIDTH + OLED_WIDTH - 2] = 0;
      _oledbuffer[j * OLED_WIDTH + OLED_WIDTH - 3] = 0;
      _oledbuffer[j * OLED_WIDTH + OLED_WIDTH - 4] = 0;
    }
    oledRefresh();
  }
}

/*
 * Mitigate SCA on lines y1-y2 by setting at least width pixels white
 * Pixels grow from the outside (left/right border of the screen)
 */
void oledSCA(int y1, int y2, int width) {
  y1 = MAX(y1, 0);
  y2 = MIN(y2, OLED_HEIGHT - 1);
  for (int y = y1; y <= y2; y++) {
    int pix = 0;
    for (int x = 0; x < OLED_WIDTH; x++) {
      pix += oledGetPixel(x, y);
    }
    if (width > pix) {
      pix = width - pix;
      for (int x = 0; x < pix / 2; x++) {
        oledDrawPixel(x, y);
      }
      for (int x = OLED_WIDTH - ((pix + 1) / 2); x < OLED_WIDTH; x++) {
        oledDrawPixel(x, y);
      }
    }
  }
}

/*
 * Mitigate SCA on lines y1-y2 by setting at least width pixels white
 * Pixels grow from the inside (from columns a/b to the right/left)
 */
void oledSCAInside(int y1, int y2, int width, int a, int b) {
  y1 = MAX(y1, 0);
  y2 = MIN(y2, OLED_HEIGHT - 1);
  for (int y = y1; y <= y2; y++) {
    int pix = 0;
    for (int x = 0; x < OLED_WIDTH; x++) {
      pix += oledGetPixel(x, y);
    }
    if (width > pix) {
      pix = width - pix;
      for (int x = a - pix / 2; x < a; x++) {
        oledDrawPixel(x, y);
      }
      for (int x = b; x < b + (pix + 1) / 2; x++) {
        oledDrawPixel(x, y);
      }
    }
  }
}

/*
 * display prompt info
 */
void vDisp_PromptInfo(uint8_t ucIndex, bool ucMode) {
  if (ucMode) {
    oledClear();
  }
  switch (ucIndex) {
    case DISP_NOT_ACTIVE:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_unactive);
      } else {
        oledDrawStringCenter(60, 48, "Not Activated", FONT_STANDARD);
      }
      break;
    case DISP_TOUCHPH:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_touch_phone);
      } else {
        oledDrawStringCenter(60, 48, "It needs to", FONT_STANDARD);
        oledDrawStringCenter(60, 56, "touch the phone", FONT_STANDARD);
      }
      break;
    case DISP_NFC_LINK:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_nfc_link);
      } else {
        oledDrawStringCenter(60, 48, "Connect by NFC", FONT_STANDARD);
      }
      break;
    case DISP_USB_LINK:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_usb_link);
      } else {
        oledDrawStringCenter(60, 48, "Connect by USB", FONT_STANDARD);
      }
      break;
    case DISP_COMPUTER_LINK:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_computerlink);
      } else {
        oledDrawStringCenter(60, 48, "Connect to a computer", FONT_STANDARD);
      }
      break;
    case DISP_INPUTPIN:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 0, &bmp_cn_input_pin);
      } else {
        oledDrawStringCenter(60, 40, "Enter PIN code", FONT_STANDARD);
        oledDrawStringCenter(60, 48, "according to prompts", FONT_STANDARD);
        oledDrawStringCenter(60, 56, "on the right screen", FONT_STANDARD);
      }
      break;
    case DISP_BUTTON_OK_RO_NO:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_button_yes_no);
      } else {
        oledDrawStringCenter(60, 48, "Press OK to confirm, ", FONT_STANDARD);
        oledDrawStringCenter(60, 56, "Press < to Cancel", FONT_STANDARD);
      }
      break;
    case DISP_GEN_PRI_KEY:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_prikey_gen);
      } else {
        oledDrawStringCenter(60, 48, "Generating private key...",
                             FONT_STANDARD);
      }
      break;
    case DISP_ACTIVE_SUCCESS:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_active_success);
      } else {
        oledDrawStringCenter(60, 48, "Activated", FONT_STANDARD);
      }
      break;
    case DISP_BOTTON_UP_OR_DOWN:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_updown_view);
      } else {
        oledDrawStringCenter(60, 30, "Turn left or right to view",
                             FONT_STANDARD);
      }
      break;
    case DISP_SN:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_sn);
      } else {
        oledDrawStringCenter(60, 48, "Serial NO.", FONT_STANDARD);
      }
      break;
    case DISP_VERSION:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_version);
      } else {
        oledDrawStringCenter(60, 48, "Firmware version", FONT_STANDARD);
      }
      break;
    case DISP_CONFIRM_PUB_KEY:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_confirm_pubkey);
      } else {
        oledDrawStringCenter(60, 48, "Confirm public key", FONT_STANDARD);
      }
      break;
    case DISP_BOTTON_OK_SIGN:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 48, &bmp_cn_sign_ok);
      } else {
        oledDrawStringCenter(60, 48, "Press OK to sign", FONT_STANDARD);
      }
      break;
    case DISP_SIGN_SUCCESS:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 32, &bmp_cn_sign_success_phone);
      } else {
        oledDrawStringCenter(60, 32, "Signed! Touch it to", FONT_STANDARD);
        oledDrawStringCenter(60, 56, "the phone closely", FONT_STANDARD);
      }
      break;
    case DISP_SIGN_PRESS_OK_HOME:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 32, &bmp_cn_sign_success_gohome);
      } else {
        oledDrawStringCenter(60, 32, "Signed! Press OK to", FONT_STANDARD);
        oledDrawStringCenter(60, 56, "return to homepage", FONT_STANDARD);
      }
      break;
    case DISP_SIGN_SUCCESS_VIEW:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 32, &bmp_cn_sign_ok_view);
      } else {
        oledDrawStringCenter(60, 40, "Signed!", FONT_STANDARD);
        oledDrawStringCenter(60, 48, "Please view transaction", FONT_STANDARD);
        oledDrawStringCenter(60, 56, "on your phone", FONT_STANDARD);
      }
      break;
    case DISP_UPDATGE_APP_GOING:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 32, &bmp_cn_updating_notpower_off);
      } else {
        oledDrawStringCenter(60, 48, "Upgrading,", FONT_STANDARD);
        oledDrawStringCenter(60, 56, "do not turn off", FONT_STANDARD);
      }
      break;
    case DISP_UPDATGE_SUCCESS:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 32, &bmp_cn_update_sucess);
      } else {
        oledDrawStringCenter(60, 40, "Firmware upgraded,", FONT_STANDARD);
        oledDrawStringCenter(60, 48, "press OK to ", FONT_STANDARD);
        oledDrawStringCenter(60, 56, "return to homepage", FONT_STANDARD);
      }
      break;
    case DISP_PRESSKEY_POWEROFF:
      oledClear();
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 0, &bmp_cn_poweroff);
      } else {
        oledDrawStringCenter(60, 30, "Power Off", FONT_STANDARD);
      }
      oledRefresh();
      delay(2000);
      oledClear();
      oledRefresh();
      return;
    case DISP_BLE_NAME:
      oledDrawStringCenter(60, 56, (const char *)g_ble_info.ucBle_Name,
                           FONT_STANDARD);
      break;
    case DISP_EXPORT_PRIVATE_KEY:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 32, &bmp_cn_export_encrypted_prikey);
      } else {
        oledDrawStringCenter(60, 48, "[Encrypted]", FONT_STANDARD);
        oledDrawStringCenter(60, 56, "Exporting private key…", FONT_STANDARD);
      }
      break;
    case DISP_IMPORT_PRIVATE_KEY:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 32, &bmp_cn_import_prikey);
      } else {
        oledDrawStringCenter(60, 56, "Importing private key", FONT_STANDARD);
      }
      break;
    case DISP_UPDATE_SETTINGS:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 32, &bmp_cn_update_settings);
      } else {
        oledDrawStringCenter(60, 56, "Settings updated", FONT_STANDARD);
      }
      break;
    case DISP_BIXIN_KEY_INITIALIZED:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 32, &bmp_cn_BixinKEY_initialized);
      } else {
        oledDrawStringCenter(60, 56, "BixinKEY initialized", FONT_STANDARD);
      }
      break;
    case DISP_CONFIRM_PIN:
      if (g_ucLanguageFlag) {
        oledDrawBitmap(0, 16, &bmp_cn_confirm_pin);
      }
      break;
    default:
      break;
  }
  if (ucMode) {
    oledRefresh();
  }
  g_ucPromptIndex = 0;
}
