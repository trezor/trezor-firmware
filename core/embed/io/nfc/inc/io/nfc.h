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

/**
 * @brief Must correspond to RFAL_FEATURE_ISO_DEP_APDU_MAX_LEN in
 * rfal_platform.h
 */
#define NFC_MAX_APDU_LEN 512

/** @brief Supported NFC types. **/
typedef enum {
  NFC_DEV_TYPE_A,
  NFC_DEV_TYPE_B,
  NFC_DEV_TYPE_UNKNOWN,
} nfc_dev_type_t;

/** @brief NFC interface */
typedef enum {
  NFC_DEV_INTERFACE_RF,
  NFC_DEV_INTERFACE_ISODEP,
  NFC_DEV_INTERFACE_UNKNOWN,
} nfc_dev_interface_t;

/** @brief NFC-A Listen device types */
typedef enum {
  NFCA_T2T,
  NFCA_T4T,
  NFCA_UNKNOWN_TYPE,
} nfc_nfca_listen_device_type_t;

/** @brief NFC poll events */
typedef enum {
  NFC_NO_EVENT = 0,
  NFC_EVENT_CONNECTED,
  NFC_EVENT_DISCONNECTED,
  NFC_EVENT_TRANSCEIVE_DONE,
} nfc_event_t;

/** @brief NFC card details */
typedef struct {
  nfc_dev_type_t type;                     //!< NFC card type
  nfc_nfca_listen_device_type_t tag_type;  //!< NFC-A tag type
  nfc_dev_interface_t interface;           //!< NFC card interface
  uint8_t uid[NFC_MAX_UID_LEN];            //!< Card UID (raw bytes)
  uint8_t uid_len;                         //!< Card UID length in bytes
} nfc_dev_info_t;

/** @brief NFC APDU message buffer structure */
typedef struct {
  uint8_t data[NFC_MAX_APDU_LEN];
  uint16_t data_len;
} nfc_apdu_message_t;

/**
 * @brief Initialize NFC driver including supportive RFAL middleware and
 * polling mechanism.
 * @return TS_OK when the function pass, otherwise an error.
 */
ts_t nfc_init(void);

/** @brief Deinitialize NFC driver. */
void nfc_deinit(void);

/**
 * @brief Activates the NFC RFAL state machine to explore the previously
 * registered technologies. The RFAL handles low-level NFC protocols and
 * provides information about the activated device. This function only starts
 * the exploration; you must regularly call nfc_get_event() to continue
 * processing NFC operations.
 * @return TS_OK when the function pass, otherwise an error.
 */
ts_t nfc_start_discovery(void);

/**
 * @brief Deactivate the NFC RFAL state machine (put in IDLE state).
 * @return TS_OK when the function pass, otherwise an error.
 */
ts_t nfc_stop_discovery(void);

/**
 * @brief Continue processing NFC operations. Poll SYSHANDLE_NFC with
 * sysevents_poll() to progress NFC operations.
 *
 * @return true when an event is reported, otherwise false.
 */
bool nfc_get_event(nfc_event_t *event);

/**
 * @brief Get current state of NFC device.
 * @return 'true' when card is connected, else 'false'.
 */
bool nfc_get_state(void);

/**
 * @brief Return general device information of the activated NFC device.
 * @param dev_info [out] Pointer to store current NFC device details.
 * @return TS_OK when the function pass, otherwise an error.
 */
ts_t nfc_get_device_info(nfc_dev_info_t *dev_info);

/**
 * @brief Initiate asynchronous data exchange with the activated NFC device.
 * Poll SYSHANDLE_NFC with sysevents_poll() to progress the exchange. Once it
 * finishes, call nfc_transceive_complete() to get the result.
 *
 * @param cmd [in] Tx data buffer structure, can be reused after return.
 * @return TS_OK when the exchange was started, otherwise an error.
 */
ts_t nfc_transceive_start(const nfc_apdu_message_t *cmd);

/**
 * @brief Start transceiving PSK message over ISO14443-3 customized frame (9-b
 * header, no parity bits, augmented CRC).
 *
 * Behaves like nfc_transceive_start(): the share is copied before the
 * function returns, NFC_EVENT_TRANSCEIVE_DONE is reported when the exchange
 * finishes and the result is picked up with nfc_transceive_complete().
 *
 * @param pcd_psk [in] PSK share to transmit (16 bytes).
 * @param pcd_psk_len [in] Length of the PSK share.
 * @return TS_OK when the exchange was started, otherwise an error.
 */
ts_t nfc_transceive_psk_start(const uint8_t *pcd_psk, size_t pcd_psk_len);

/**
 * @brief Get the result of the exchange started by nfc_transceive_start() or
 * nfc_transceive_psk_start().
 *
 * @param resp [out] Rx data buffer structure
 * @return Result of the exchange, TS_EBUSY if it has not finished yet,
 * TS_ENOSTATE if there is no exchange to complete.
 */
ts_t nfc_transceive_complete(nfc_apdu_message_t *resp);
