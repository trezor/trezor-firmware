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

/**
 * @file ble.h
 * @brief BLE (Bluetooth Low Energy) functionality interface
 *
 * This module provides interface to BLE (Bluetooth Low Energy) functionality.
 * It allows the device to advertise itself, connect to other devices, and
 * exchange data over BLE.
 */

#include <trezor_types.h>

#define BLE_RX_PACKET_SIZE 244
#define BLE_TX_PACKET_SIZE 244

#define BLE_ADV_NAME_LEN 20
#define BLE_PAIRING_CODE_LEN 6

#define BLE_MAX_BONDS 8

/**
 * @brief BLE operating modes
 */
typedef enum {
  BLE_MODE_OFF, /**< BLE is disabled; no advertising or connections */
  BLE_MODE_KEEP_CONNECTION, /**< Keep current connection if present; do not
                               start new advertising */
  BLE_MODE_CONNECTABLE,     /**< Advertise and accept connections from bonded
                               devices */
  BLE_MODE_PAIRING,         /**< Advertise, accept new pairing requests */
  BLE_MODE_DFU,             /**< Used for updating nRF firmware */
} ble_mode_t;

/**
 * @brief BLE TX power levels
 */
typedef enum {
  BLE_TX_POWER_PLUS_4_DBM = 4,
  BLE_TX_POWER_PLUS_0_DBM = 0,
  BLE_TX_POWER_MINUS_4_DBM = -4,
  BLE_TX_POWER_MINUS_8_DBM = -8,
  BLE_TX_POWER_MINUS_12_DBM = -12,
  BLE_TX_POWER_MINUS_16_DBM = -16,
} ble_tx_power_level_t;

/*
 * Address types:
 * BT_ADDR_LE_PUBLIC       0x00
 * BT_ADDR_LE_RANDOM       0x01
 * BT_ADDR_LE_PUBLIC_ID    0x02
 * BT_ADDR_LE_RANDOM_ID    0x03
 * BT_ADDR_LE_UNRESOLVED   0xFE
 * BT_ADDR_LE_ANONYMOUS    0xFF
 */
typedef struct {
  uint8_t type;
  uint8_t addr[6]; /**< 6-byte address */
} bt_le_addr_t;

/**
 * @brief BLE wakeup parameters structure
 */
typedef struct {
  bool accept_msgs;            /**< Accept incoming messages */
  bool reboot_on_resume;       /**< Reboot device on resume */
  bool high_speed;             /**< Use high speed connection */
  uint8_t peer_count;          /**< Number of paired peers */
  ble_mode_t mode_requested;   /**< Requested BLE mode */
  bt_le_addr_t connected_addr; /**< Connected device address */
  bool restart_adv_on_disconnect;
  bool next_adv_with_disconnect;
  uint8_t name[BLE_ADV_NAME_LEN]; /**< Advertising name */
  bool static_mac;                /**< Use static MAC address */
} ble_wakeup_params_t;

/**
 * @brief BLE event types
 */
typedef enum {
  BLE_NONE = 0,               /**< No event */
  BLE_CONNECTED = 1,          /**< Connected to a device */
  BLE_DISCONNECTED = 2,       /**< Disconnected from a device */
  BLE_PAIRING_REQUEST = 3,    /**< Pairing request received */
  BLE_PAIRING_CANCELLED = 4,  /**< Pairing was canceled by host */
  BLE_PAIRING_COMPLETED = 5,  /**< Pairing was completed successfully */
  BLE_PAIRING_NOT_NEEDED = 6, /**< Pairing is not needed */
  BLE_CONNECTION_CHANGED =
      7, /**< Connection change (e.g. different device connected) */
} ble_event_type_t;

/**
 * @brief BLE event structure
 */
typedef struct {
  ble_event_type_t type; /**< Event type */
  int connection_id;     /**< Connection ID */
  uint8_t data_len;      /**< Data length */
  uint8_t data[6];       /**< Event data */
} ble_event_t;

/**
 * @brief BLE state structure
 */
typedef struct {
  bool connected;              /**< Device is connected */
  bool connectable;            /**< Device is in connectable mode */
  bool pairing;                /**< Device is in pairing mode */
  bool pairing_requested;      /**< Pairing has been requested */
  bool state_known;            /**< State is known/valid */
  uint8_t peer_count;          /**< Number of paired peers */
  bt_le_addr_t connected_addr; /**< Address of connected device */
} ble_state_t;

/**
 * @brief Initializes the BLE module
 *
 * Sets up the BLE hardware and software resources,
 * preparing the module for operation.
 * The function has no effect if the module was already initialized.
 *
 * @return true if initialization was successful, false otherwise
 */
bool ble_init(void);

/**
 * @brief Deinitializes the BLE module
 *
 * Releases resources allocated during initialization
 * and shuts down the BLE module.
 */
void ble_deinit(void);

/**
 * @brief Suspends the BLE module
 *
 * @param wakeup_params Pointer to structure to store wakeup parameters
 */
void ble_suspend(ble_wakeup_params_t *wakeup_params);

/**
 * @brief Resumes the BLE module
 *
 * @param wakeup_params Pointer to wakeup parameters structure
 * @return true if resume was successful, false otherwise
 */
bool ble_resume(const ble_wakeup_params_t *wakeup_params);

/**
 * @brief Starts BLE operations
 *
 * Enables reception of messages over BLE
 */
void ble_start(void);

/**
 * @brief Stops BLE operations
 *
 * Disables reception of messages over BLE
 * Flushes any queued messages
 */
void ble_stop(void);

/**
 * @brief Turns off BLE advertising and disconnects from devices
 *
 * @return true if the command was successfully executed, false otherwise
 */
bool ble_switch_off(void);

/**
 * @brief Turns on BLE advertising
 *
 * @return true if the command was successfully executed, false otherwise
 */
bool ble_switch_on(void);

/**
 * @brief Enters pairing mode
 *
 * @param name Advertising name to use
 * @param name_len Length of the advertising name
 * @return true if the command was successfully executed, false otherwise
 */
bool ble_enter_pairing_mode(const uint8_t *name, size_t name_len);

/**
 * @brief Disconnects from the currently connected device
 *
 * @return true if the command was successfully executed, false otherwise
 */
bool ble_disconnect(void);

/**
 * @brief Erases all bonding information
 *
 * @return true if the command was successfully executed, false otherwise
 */
bool ble_erase_bonds(void);

/**
 * @brief Accepts a pairing request with the provided pairing code
 *
 * @param pairing_code Pointer to pairing code array
 * @return true if the command was successfully executed, false otherwise
 */
bool ble_allow_pairing(const uint8_t *pairing_code);

/**
 * @brief Rejects a pairing request
 *
 * @return true if the command was successfully executed, false otherwise
 */
bool ble_reject_pairing(void);

/**
 * @brief Keeps connection to the connected device but stops advertising
 *
 * @return true if the command was successfully executed, false otherwise
 */
bool ble_keep_connection(void);

/**
 * @brief Set static BLE MAC address flag
 *
 * @param static_mac Enable/disable static MAC address
 * @return true if the command was successfully executed, false otherwise
 */
bool ble_set_static_mac(bool static_mac);

/**
 * @brief Sets the BLE advertising name, but does not affect advertising
 *
 * @param name Pointer to name string
 * @param len Length of the name
 */
void ble_set_name(const uint8_t *name, size_t len);

/**
 * @brief Reads an event from the BLE module
 *
 * Retrieves the next event from the BLE module's event queue.
 *
 * @param event Pointer to event structure to fill
 * @return true if an event was successfully read, false if no event is
 * available
 */
bool ble_get_event(ble_event_t *event);

/**
 * @brief Retrieves the current state of the BLE module
 *
 * Obtains the current operational state of the BLE module.
 *
 * @param state Pointer to state structure to fill
 */
void ble_get_state(ble_state_t *state);

/**
 * @brief Retrieves last set advertising name
 *
 * @param name Pointer to buffer for the name
 * @param max_len Maximum length of the buffer
 */
void ble_get_advertising_name(char *name, size_t max_len);

/**
 * @brief Check if write is possible
 *
 * @return true if write is possible, false otherwise
 */
bool ble_can_write(void);

/**
 * @brief Unpair device
 *
 * Unpairs currently connected device if addr is NULL.
 *
 * @param addr Pointer to address of device to unpair, or NULL for current
 * device
 * @return true if successful, false otherwise
 */
bool ble_unpair(const bt_le_addr_t *addr);

/**
 * @brief Writes data to a connected BLE device
 *
 * Sends data over an established BLE connection.
 *
 * @param data Pointer to data to send
 * @param len Length of data to send
 * @return true if successful, false otherwise
 */
bool ble_write(const uint8_t *data, uint16_t len);

/**
 * @brief Check if read is possible
 *
 * @return true if read is possible, false otherwise
 */
bool ble_can_read(void);

/**
 * @brief Get bond list
 *
 * @param bonds Pointer to array to fill with bonded addresses
 * @param count Maximum number of bonds to retrieve
 * @return Number of bonds actually retrieved
 */
uint8_t ble_get_bond_list(bt_le_addr_t *bonds, size_t count);

/**
 * @brief Reads data from a connected BLE device
 *
 * max_len indicates the maximum number of bytes to read. Rest of the data
 * will be discarded.
 *
 * @param data Pointer to buffer for received data
 * @param max_len Maximum number of bytes to read
 * @return Number of bytes actually read
 */
uint32_t ble_read(uint8_t *data, uint16_t max_len);

/**
 * @brief Read MAC address of the device
 *
 * When not using static address, the address is random and may not correspond
 * to what is actually used for advertising
 *
 * @param addr Pointer to address structure to fill
 * @return true if successful, false otherwise
 */
bool ble_get_mac(bt_le_addr_t *addr);

/**
 * @brief Set high speed connection
 *
 * When enabled, the connection parameters will be set to achieve
 * higher data throughput, at the cost of increased power consumption.
 *
 * @param enable Enable/disable high speed mode
 */
void ble_set_high_speed(bool enable);

/**
 * @brief Set TX power
 *
 * Set TX power level.
 *
 * @param level Transmit power level to set
 */
void ble_set_tx_power(ble_tx_power_level_t level);

/**
 * @brief BLE notify
 *
 * Sends notification to host over BLE.
 *
 * @param data Pointer to data to notify
 * @param len Length of data
 */
void ble_notify(const uint8_t *data, size_t len);
