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

#ifndef __LAYOUT2_H__
#define __LAYOUT2_H__

#include "bignum.h"
#include "bitmaps.h"
#include "coins.h"
#include "layout.h"
#include "trezor.h"

#include "messages-bitcoin.pb.h"
#include "messages-crypto.pb.h"
#include "messages-nem.pb.h"

#define DISP_BUFSIZE (2048)
#define DISP_PAGESIZE (96)

extern void *layoutLast;

#if DEBUG_LINK
#define layoutSwipe oledClear
#else
#define layoutSwipe oledSwipeLeft
#endif

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

void layoutDialogSwipe(const BITMAP *icon, const char *btnNo,
                       const char *btnYes, const char *desc, const char *line1,
                       const char *line2, const char *line3, const char *line4,
                       const char *line5, const char *line6);
void layoutProgressSwipe(const char *desc, int permil);

void layoutScreensaver(void);
void vlayoutLogo(void);
void layoutHome(void);
void layoutConfirmOutput(const CoinInfo *coin, const TxOutputType *out);
void layoutConfirmOmni(const uint8_t *data, uint32_t size);
void layoutConfirmOpReturn(const uint8_t *data, uint32_t size);
void layoutConfirmTx(const CoinInfo *coin, uint64_t amount_out,
                     uint64_t amount_fee);
void layoutFeeOverThreshold(const CoinInfo *coin, uint64_t fee);
void layoutSignMessage(const uint8_t *msg, uint32_t len);
void layoutVerifyAddress(const CoinInfo *coin, const char *address);
void layoutVerifyMessage(const uint8_t *msg, uint32_t len);
void layoutCipherKeyValue(bool encrypt, const char *key);
void layoutEncryptMessage(const uint8_t *msg, uint32_t len, bool signing);
void layoutDecryptMessage(const uint8_t *msg, uint32_t len,
                          const char *address);
void layoutResetWord(const char *word, int pass, int word_pos, bool last);
void layoutAddress(const char *address, const char *desc, bool qrcode,
                   bool ignorecase, const uint32_t *address_n,
                   size_t address_n_count, bool address_is_account);
void layoutPublicKey(const uint8_t *pubkey);
void layoutSignIdentity(const IdentityType *identity, const char *challenge);
void layoutDecryptIdentity(const IdentityType *identity);
void layoutU2FDialog(const char *verb, const char *appname);

void layoutNEMDialog(const BITMAP *icon, const char *btnNo, const char *btnYes,
                     const char *desc, const char *line1, const char *address);
void layoutNEMTransferXEM(const char *desc, uint64_t quantity,
                          const bignum256 *multiplier, uint64_t fee);
void layoutNEMNetworkFee(const char *desc, bool confirm, const char *fee1_desc,
                         uint64_t fee1, const char *fee2_desc, uint64_t fee2);
void layoutNEMTransferMosaic(const NEMMosaicDefinition *definition,
                             uint64_t quantity, const bignum256 *multiplier,
                             uint8_t network);
void layoutNEMTransferUnknownMosaic(const char *namespace, const char *mosaic,
                                    uint64_t quantity,
                                    const bignum256 *multiplier);
void layoutNEMTransferPayload(const uint8_t *payload, size_t length,
                              bool encrypted);
void layoutNEMMosaicDescription(const char *description);
void layoutNEMLevy(const NEMMosaicDefinition *definition, uint8_t network);

void layoutCosiCommitSign(const uint32_t *address_n, size_t address_n_count,
                          const uint8_t *data, uint32_t len, bool final_sign);

const char **split_message(const uint8_t *msg, uint32_t len, uint32_t rowlen);
const char **split_message_hex(const uint8_t *msg, uint32_t len);
void Disp_Page(const BITMAP *icon, const char *btnNo, const char *btnYes,
               const char *desc, uint8_t *pucInfoBuf, uint16_t usLen);

void vDISP_TurnPageUP(void);
void vDISP_TurnPageDOWN(void);
void layoutHomeInfo(void);
void vDisp_PromptInfo(uint8_t ucIndex, bool ucMode);

#endif
