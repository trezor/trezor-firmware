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

/**
 * @brief Must corespond to RFAL_FEATURE_ISO_DEP_APDU_MAX_LEN in rfal_platform.h
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
  NFCA_T4T,
  NFCA_UNKNOWN_TYPE,
} nfc_nfca_listen_device_type_t;

/** @brief NFC poll events */
typedef enum {
  NFC_NO_EVENT = 0,
  NFC_EVENT_CONNECTED,
  NFC_EVENT_DISCONNECTED,
} nfc_event_t;

/** @brief NFC card details */
typedef struct {
  nfc_dev_type_t type;                     //!< NFC card type
  nfc_nfca_listen_device_type_t tag_type;  //!< NFC-A tag type
  nfc_dev_interface_t interface;           //!< NFC card interface
  char uid[NFC_MAX_UID_BUF_SIZE];          //!< Card UID string
  uint8_t uid_len;
} nfc_dev_info_t;

/** @brief NFC APDU command buffer structure */
typedef struct {
  const uint8_t *data;
  uint16_t data_len;
} nfc_apdu_cmd_t;

/** @brief NFC APDU response buffer pointers */
typedef struct {
  uint8_t *data;       //!< [out] Pointer to the buffer to store received data.
  uint16_t *data_len;  //!< [in/out] Pointer to the length of the buffer.
  // On return,  it will contain the actual length of the received data.
} nfc_apdu_response_t;

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
 * @brief Get current events of NFC device.
 * @param event [out] Pointer to store new event.
 * @return TS_OK when the function pass, otherwise an error.
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
 * @brief Transceive data with the activated NFC device. This is a blocking
 * call.
 * @param cmd [in] Tx data buffer structure
 * @param resp [out] Rx data buffer structure
 * @return TS_OK when the function pass, otherwise an error.
 */
ts_t nfc_transceive(const nfc_apdu_cmd_t cmd, nfc_apdu_response_t resp);


/** 
 * @brief Transceive psk message over ISO14443-3 customized frame (9-b header,
 * no parity bits, augmented CRC).
 * 
 * tx_psk should be an array of 16 bytes, and rx_psk should be of the same size.
 * 
 * @param tx_psk [in] Pointer to the PSK message to transmit.
 * @param tx_psk_buf_len [in] Length of the PSK message to transmit.
 * @param rx_psk [out] Pointer to the buffer to store received PSK message.
 * @param rx_psk_buf_len [in] Capacity of the receive buffer.
 * @param rx_psk_len [in/out] Pointer to the length of the received PSK message.
 * @return TS_OK when the function pass, otherwise an error.
 */
ts_t nfc_transceive_psk(uint8_t *tx_psk, size_t tx_psk_buf_len,
                        uint8_t *rx_psk, size_t rx_psk_buf_len,
                        size_t *rx_psk_len);