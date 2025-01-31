/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef TREZORHAL_NFC_H
#define TREZORHAL_NFC_H

#include <trezor_bsp.h>
#include <trezor_rtl.h>
#include "ndef.h"

#define NFC_MAX_UID_LEN 10

typedef enum{
  NFC_POLLER_TECH_A = 0x1,
  NFC_POLLER_TECH_B = 0x1 << 1 ,
  NFC_POLLER_TECH_F = 0x1 << 2,
  NFC_POLLER_TECH_V = 0x1 << 3,
  NFC_CARD_EMU_TECH_A = 0x1 << 4,
  NFC_CARD_EMU_TECH_F = 0x1 << 5,
} nfc_tech_t ;

typedef enum{
  NFC_DEV_TYPE_A,
  NFC_DEV_TYPE_B,
  NFC_DEV_TYPE_F,
  NFC_DEV_TYPE_V,
  NFC_DEV_TYPE_ST25TB,
  NFC_DEV_TYPE_AP2P,
  NFC_DEV_TYPE_UNKNOWN,
} nfc_dev_type_t;

typedef enum{
  NFC_STATE_IDLE,
  NFC_STATE_ACTIVATED,
} nfc_event_t;

typedef enum {
  NFC_OK,
  NFC_ERROR,
  NFC_NOT_INITIALIZED,
  NFC_SPI_BUS_ERROR,
  NFC_INITIALIZATION_FAILED,
} nfc_status_t;

typedef struct{
  uint8_t type;
  char uid[NFC_MAX_UID_LEN];
  uint8_t uid_len;
}nfc_dev_info_t;

nfc_status_t nfc_init();

nfc_status_t nfc_deinit();

nfc_status_t nfc_register_tech(nfc_tech_t tech);

nfc_status_t nfc_register_event_callback(nfc_event_t event_type, void (*cb_fn)(void));

nfc_status_t nfc_activate_stm();

nfc_status_t nfc_deactivate_stm();

nfc_status_t nfc_dev_read_info(nfc_dev_info_t *dev_info);

nfc_status_t nfc_feed_worker();

#endif  // TREZORHAL_NFC_H
