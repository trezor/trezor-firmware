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
  NFC_CARD_EMU_TECH_A = 0x1 << 0,
  NFC_CARD_EMU_TECH_F = 0x1 << 1,
} nfc_tech_t;

typedef enum {
  NFC_DEV_TYPE_A,
  NFC_DEV_TYPE_B,
  NFC_DEV_TYPE_F,
  NFC_DEV_TYPE_V,
  NFC_DEV_TYPE_ST25TB,
  NFC_DEV_TYPE_AP2P,
  NFC_DEV_TYPE_POLL_TYPE_A,
  NFC_DEV_TYPE_POLL_TYPE_F,
  NFC_DEV_TYPE_UNKNOWN,
} nfc_dev_type_t;

typedef enum {
  NFC_DEV_INTERFACE_RF,
  NFC_DEV_INTERFACE_ISODEP,
  NFC_DEV_INTERFACE_NFCDEP,
  NFC_DEV_INTERFACE_UNKNOWN,
} nfc_dev_interface_t;

typedef enum {
  NFC_OK = 0,
  NFC_ERROR,
  NFC_WRONG_STATE,
  NFC_PARAM,
  NFC_NOT_INITIALIZED,
  NFC_SPI_BUS_ERROR,
  NFC_INITIALIZATION_FAILED,
} nfc_status_t;

/**
 * @brief NFC poll events
 */
typedef enum {
  NFC_NO_EVENT = 0,
  NFC_EVENT_CONNECTED,
  NFC_EVENT_DISCONNECTED,
} nfc_event_t;

typedef enum {
  NFC_DISCOVERY_TYPE_CARD_READER = 0,
  NFC_DISCOVERY_TYPE_CARD_EMULATION,
} nfc_discovery_type_t;

/**
 * @brief NFC poll state
 */
typedef struct {
  bool connected;
} nfc_state_t;

typedef struct {
  uint8_t type;
  nfc_dev_interface_t interface;
  char uid[NFC_MAX_UID_BUF_SIZE];  // Plus one for string termination
  uint8_t uid_len;
} nfc_dev_info_t;

// Initialize NFC driver including supportive RFAL middleware and polling
// mechanism.
nfc_status_t nfc_init(void);

// Deinitialize NFC driver
void nfc_deinit(void);

// Activates the NFC RFAL state machine to explore the previously registered
// technologies. The RFAL handles low-level NFC protocols and provides
// information about the activated device. This function only starts the
// exploration; you must regularly call nfc_get_event() to continue processing
// NFC operations.
nfc_status_t nfc_start_discovery(nfc_discovery_type_t discovery_type);

// Deactivate the NFC RFAL state machine (put in IDLE state).
nfc_status_t nfc_stop_discovery(void);

// Get current events of NFC device.
bool nfc_get_event(nfc_event_t *event);

// Get current state of NFC device.
void nfc_get_state(nfc_state_t *state);

// Read the general device information of the activated NFC device.
nfc_status_t nfc_dev_read_info(nfc_dev_info_t *dev_info);

// Write the NDEF message with the trezor.io URI to the activated NFC device.
nfc_status_t nfc_dev_write_ndef_uri(void);

// Transceive data with the activated NFC device. This is a blocking call.
nfc_status_t nfc_transceive(const uint8_t *tx_data, uint16_t tx_data_len,
                            uint8_t **rx_data, uint16_t **rx_data_len);
