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

#ifndef __OLED_H__
#define __OLED_H__

#include <stdbool.h>
#include <stdint.h>

#include "bitmaps.h"
#include "fonts.h"
#include "sys.h"

#define BLE_ADV_NAME "BiXin_abcd"
#define BLE_ADV_NAME_LEN 10

#define BLE_MAC_LEN 0x06
#define BLE_NAME_LEN 0x0A

typedef struct BLE_DEVICE_INFO {
  uint8_t ucBle_Mac[BLE_MAC_LEN];
  uint8_t ucBle_Name[BLE_NAME_LEN + 1];
  uint8_t ucBle_Version[2];

} Ble_Info;

typedef struct USB_DEVICE_INFO {
  uint8_t ucUsb_lable[33];
  uint8_t ucUsb_sn[13];
  uint8_t ucfingerprint[33];
} USB_Info;

#define OLED_WIDTH 128
#define OLED_HEIGHT 64
#define OLED_BUFSIZE (OLED_WIDTH * OLED_HEIGHT / 8)

// prompt info display
#define DISP_NOT_ACTIVE 0x01     // Not Activated
#define DISP_TOUCHPH 0x02        // It needs to touch the phone
#define DISP_NFC_LINK 0x03       // Connect by NFC
#define DISP_USB_LINK 0x04       // Connect by USB
#define DISP_COMPUTER_LINK 0x05  // Connect to a computer
#define DISP_INPUTPIN \
  0x06  // Enter PIN code according to the prompts on the
        // right screen
#define DISP_BUTTON_OK_RO_NO 0x07     // Press OK to confirm, Press < to Cancel
#define DISP_GEN_PRI_KEY 0x08         // Generating private key...
#define DISP_ACTIVE_SUCCESS 0x09      // Activated
#define DISP_BOTTON_UP_OR_DOWN 0x0A   // Turn up or down to view
#define DISP_SN 0x0B                  // Serial NO.
#define DISP_VERSION 0x0C             // Firmware version
#define DISP_CONFIRM_PUB_KEY 0x0D     // Confirm public key
#define DISP_BOTTON_OK_SIGN 0x0E      // Press OK to sign
#define DISP_SIGN_SUCCESS 0x0F        // Signed! Touch it to the phone closely
#define DISP_SIGN_PRESS_OK_HOME 0x10  // Signed! Press OK to return to homepage
#define DISP_SIGN_SUCCESS_VIEW \
  0x11                               // Signed! Please view
                                     // transaction on your
                                     // phone
#define DISP_UPDATGE_APP_GOING 0x12  // Upgrading, do not turn off
#define DISP_UPDATGE_SUCCESS \
  0x13                               // Firmware upgraded, press OK to return to
                                     // homepage
#define DISP_PRESSKEY_POWEROFF 0x14  // power off
#define DISP_BLE_NAME 0x15           // ble name
#define DISP_EXPORT_PRIVATE_KEY 0x16     // export encrypted private key
#define DISP_IMPORT_PRIVATE_KEY 0x17     // import private key
#define DISP_UPDATE_SETTINGS 0x18        // update settings
#define DISP_BIXIN_KEY_INITIALIZED 0x19  // Bixin Key initialized
#define DISP_CONFIRM_PIN 0x1A            // confirm pin

extern Ble_Info g_ble_info;
extern USB_Info g_usb_info;

void oledInit(void);
void oledClear(void);
void oledRefresh(void);

void oledSetDebugLink(bool set);
void oledInvertDebugLink(void);

void oledSetBuffer(uint8_t *buf, uint16_t usLen);
void oledclearLine(uint8_t line);
const uint8_t *oledGetBuffer(void);
bool oledGetPixel(int x, int y);
void oledDrawPixel(int x, int y);
void oledClearPixel(int x, int y);
void oledInvertPixel(int x, int y);
void oledDrawChar(int x, int y, char c, uint8_t font);
int oledStringWidth(const char *text, uint8_t font);
void oledDrawString(int x, int y, const char *text, uint8_t font);
void oledDrawStringCenter(int x, int y, const char *text, uint8_t font);
void oledDrawStringRight(int x, int y, const char *text, uint8_t font);
void oledDrawBitmap(int x, int y, const BITMAP *bmp);
void oledInvert(int x1, int y1, int x2, int y2);
void oledBox(int x1, int y1, int x2, int y2, bool set);
void oledHLine(int y);
void oledFrame(int x1, int y1, int x2, int y2);
void oledSwipeLeft(void);
void oledSwipeRight(void);
void oledSCA(int y1, int y2, int val);
void oledSCAInside(int y1, int y2, int val, int a, int b);
void vDisp_PromptInfo(uint8_t ucIndex, bool ucMode);

#endif
