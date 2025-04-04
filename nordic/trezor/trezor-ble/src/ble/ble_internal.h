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

#include <stdbool.h>

#include <zephyr/types.h>

#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/bluetooth/uuid.h>

#include <trz_comm/trz_comm.h>

/** @brief UUID of the NUS Service. **/
#define BT_UUID_TRZ_VAL \
  BT_UUID_128_ENCODE(0x8c000001, 0xa59b, 0x4d58, 0xa9ad, 0x073df69fa1b1)

/** @brief UUID of the TX Characteristic. **/
#define BT_UUID_TRZ_TX_VAL \
  BT_UUID_128_ENCODE(0x8c000003, 0xa59b, 0x4d58, 0xa9ad, 0x073df69fa1b1)

/** @brief UUID of the RX Characteristic. **/
#define BT_UUID_TRZ_RX_VAL \
  BT_UUID_128_ENCODE(0x8c000002, 0xa59b, 0x4d58, 0xa9ad, 0x073df69fa1b1)

#define BT_UUID_TRZ_SERVICE BT_UUID_DECLARE_128(BT_UUID_TRZ_VAL)
#define BT_UUID_TRZ_RX BT_UUID_DECLARE_128(BT_UUID_TRZ_RX_VAL)
#define BT_UUID_TRZ_TX BT_UUID_DECLARE_128(BT_UUID_TRZ_TX_VAL)

#define BLE_PAIRING_CODE_LEN 6
#define BLE_ADV_NAME_LEN 20

typedef struct {
  uint8_t msg_id;
  uint8_t connected;
  uint8_t advertising;
  uint8_t advertising_whitelist;

  uint8_t peer_count;
  uint8_t reserved[2];
  uint8_t sd_version_number;

  uint16_t sd_company_id;
  uint16_t sd_subversion_number;

  uint32_t app_version;
  uint32_t bld_version;

} event_status_msg_t;

typedef enum {
  INTERNAL_EVENT_STATUS = 0x01,
  INTERNAL_EVENT_SUCCESS = 0x02,
  INTERNAL_EVENT_FAILURE = 0x03,
  INTERNAL_EVENT_PAIRING_REQUEST = 0x04,
  INTERNAL_EVENT_PAIRING_CANCELLED = 0x05,
  INTERNAL_EVENT_MAC = 0x06,
} internal_event_t;

typedef enum {
  INTERNAL_CMD_SEND_STATE = 0x00,
  INTERNAL_CMD_ADVERTISING_ON = 0x01,
  INTERNAL_CMD_ADVERTISING_OFF = 0x02,
  INTERNAL_CMD_ERASE_BONDS = 0x03,
  INTERNAL_CMD_DISCONNECT = 0x04,
  INTERNAL_CMD_ACK = 0x05,
  INTERNAL_CMD_ALLOW_PAIRING = 0x06,
  INTERNAL_CMD_REJECT_PAIRING = 0x07,
  INTERNAL_CMD_UNPAIR = 0x08,
  INTERNAL_CMD_GET_MAC = 0x09,
} internal_cmd_t;

typedef struct {
  uint8_t cmd_id;
  uint8_t whitelist;
  uint8_t color;
  uint8_t static_addr;
  uint32_t device_code;
  uint8_t name[BLE_ADV_NAME_LEN];
} cmd_advertising_on_t;

typedef struct {
  uint8_t cmd_id;
  uint8_t code[BLE_PAIRING_CODE_LEN];
} cmd_allow_pairing_t;

// BLE management functions
// Initialization
void ble_management_init(void);
// Send status event
void ble_management_send_status_event(void);
// Send Pairing Request event, data is the pairing code
void ble_management_send_pairing_request_event(uint8_t *data, uint16_t len);
// Send Pairing Cancelled event
void ble_management_send_pairing_cancelled_event(void);

// Bonds
// Erase all bonds
bool bonds_erase_all(void);
// Get number of bonded devices
int bonds_get_count(void);
// Erase current bond
bool bonds_erase_current(void);

// Advertising functions
// Initialization
void advertising_init(void);
// Start advertising, with or without whitelist
void advertising_start(bool wl, uint8_t color, uint32_t device_code,
                       bool static_addr, char *name, int name_len);
// Stop advertising
void advertising_stop(void);
// Check if advertising is active
bool advertising_is_advertising(void);
// Check if advertising is active with whitelist
bool advertising_is_advertising_whitelist(void);
// Get current MAC address
void advertising_get_mac(uint8_t *mac, uint16_t max_len);

// Connection functions
// Initialization
bool connection_init(void);
// Disconnect current connection
void connection_disconnect(void);
// Check if there is an active connection
bool connection_is_connected(void);
// Get current connection
struct bt_conn *connection_get_current(void);

// Pairing functions
// Initialization
bool pairing_init(void);
// Reset pairing process
void pairing_reset(void);
// Respond to pairing request
void pairing_num_comp_reply(bool accept, uint8_t *code);

// Service functions
// Callback definition for received data
typedef void (*service_received_cb)(struct bt_conn *conn,
                                    const uint8_t *const data, uint16_t len);
// Initialize of the BLE service
int service_init(service_received_cb callbacks);
// Send data to the connected device
int service_send(struct bt_conn *conn, trz_packet_t *data);
