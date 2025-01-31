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

#pragma once

#include <trezor_types.h>

#define NFC_MAX_UID_LEN 10
#define NFC_MAX_UID_BUF_SIZE ((NFC_MAX_UID_LEN + 1) * 2)

typedef enum {
  NFC_POLLER_TECH_A = 0x1,
  NFC_POLLER_TECH_B = 0x1 << 1,
  NFC_POLLER_TECH_F = 0x1 << 2,
  NFC_POLLER_TECH_V = 0x1 << 3,
  NFC_CARD_EMU_TECH_A = 0x1 << 4,
  NFC_CARD_EMU_TECH_F = 0x1 << 5,
} nfc_tech_t;

typedef enum {
  NFC_DEV_TYPE_A,
  NFC_DEV_TYPE_B,
  NFC_DEV_TYPE_F,
  NFC_DEV_TYPE_V,
  NFC_DEV_TYPE_ST25TB,
  NFC_DEV_TYPE_AP2P,
  NFC_DEV_TYPE_UNKNOWN,
} nfc_dev_type_t;

typedef enum {
  NFC_NO_EVENT,
  NFC_EVENT_DEACTIVATED,
  NFC_EVENT_ACTIVATED,
} nfc_event_t;

typedef enum {
  NFC_OK,
  NFC_ERROR,
  NFC_NOT_INITIALIZED,
  NFC_SPI_BUS_ERROR,
  NFC_INITIALIZATION_FAILED,
} nfc_status_t;

typedef struct {
  uint8_t type;
  char uid[NFC_MAX_UID_BUF_SIZE];  // Plus one for string termination
  uint8_t uid_len;
} nfc_dev_info_t;

// Initialize NFC driver including supportive RFAL middleware
nfc_status_t nfc_init(void);

// Deinitialize NFC driver
void nfc_deinit(void);

// Register NFC technology (or several) to be explored by NFC state machine
// use this function before activating the state machine with nfc_activate_stm()
nfc_status_t nfc_register_tech(const nfc_tech_t tech);

// Activates the NFC RFAL state machine to explore the previously registered
// technologies. The RFAL handles low-level NFC protocols and provides
// information about the activated device. This function only starts the
// exploration; you must regularly call nfc_get_event() to continue processing
// NFC operations.
nfc_status_t nfc_activate_stm(void);

// Deactivate the NFC RFAL state machine (put in IDLE state).
nfc_status_t nfc_deactivate_stm(void);

// Calls NFC RFAL worker to service the NFC state machine and expolore
// registered technologies. This function has to be actively called in loop
// (main NFC poll function), returns nfc event.
nfc_status_t nfc_get_event(nfc_event_t *event);

// Deactivate the currently activated NFC device and put RFAL state machine back
// to discovary state.
nfc_status_t nfc_dev_deactivate(void);

// Read the general device information of the activated NFC device.
nfc_status_t nfc_dev_read_info(nfc_dev_info_t *dev_info);

// Write the NDEF message with the trezor.io URI to the activated NFC device.
nfc_status_t nfc_dev_write_ndef_uri(void);
