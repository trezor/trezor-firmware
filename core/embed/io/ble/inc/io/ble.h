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

// This module provides interface to BLE (Bluetooth Low Energy) functionality.
// It allows the device to advertise itself, connect to other devices, and
// exchange data over BLE.

#include <trezor_types.h>

#define BLE_RX_PACKET_SIZE 244
#define BLE_TX_PACKET_SIZE 64

#define BLE_ADV_NAME_LEN 20
#define BLE_PAIRING_CODE_LEN 6

typedef enum {
  BLE_SWITCH_OFF = 0,      // Turn off BLE advertising, disconnect
  BLE_SWITCH_ON = 1,       // Turn on BLE advertising
  BLE_PAIRING_MODE = 2,    // Enter pairing mode
  BLE_DISCONNECT = 3,      // Disconnect from the connected device
  BLE_ERASE_BONDS = 4,     // Erase all bonding information
  BLE_ALLOW_PAIRING = 5,   // Accept pairing request
  BLE_REJECT_PAIRING = 6,  // Reject pairing request
  BLE_UNPAIR = 7,          // Erase bond for currently connected device
} ble_command_type_t;

typedef struct {
  uint8_t name[BLE_ADV_NAME_LEN];
  bool static_mac;
} ble_adv_start_cmd_data_t;

typedef union {
  uint8_t raw[32];
  ble_adv_start_cmd_data_t adv_start;
  uint8_t pairing_code[BLE_PAIRING_CODE_LEN];
} ble_command_data_t;

typedef struct {
  ble_command_type_t cmd_type;
  uint8_t data_len;
  ble_command_data_t data;
} ble_command_t;

typedef enum {
  BLE_NONE = 0,               // No event
  BLE_CONNECTED = 1,          // Connected to a device
  BLE_DISCONNECTED = 2,       // Disconnected from a device
  BLE_PAIRING_REQUEST = 3,    // Pairing request received
  BLE_PAIRING_CANCELLED = 4,  // Pairing was cancelled by host
} ble_event_type_t;

typedef struct {
  ble_event_type_t type;
  int connection_id;
  uint8_t data_len;
  uint8_t data[6];
} ble_event_t;

typedef struct {
  bool connected;
  bool connectable;
  bool pairing;
  bool pairing_requested;
  bool state_known;
  uint8_t peer_count;
} ble_state_t;

// Initializes the BLE module
//
// Sets up the BLE hardware and software resources,
// preparing the module for operation.
// The function has no effect if the module was already initialized.
bool ble_init(void);

// Deinitializes the BLE module
//
// Releases resources allocated during initialization
// and shuts down the BLE module.
void ble_deinit(void);

// Starts BLE operations
//
// Enables reception of messages over BLE
void ble_start(void);

// Stops BLE operations
//
// Disables reception of messages over BLE
// Flushes any queued messages
void ble_stop(void);

// Issues a command to the BLE module
//
// Sends a specific command to the BLE module for execution.
//
// Returns `true` if the command was successfully issued.
bool ble_issue_command(ble_command_t *command);

// Reads an event from the BLE module
//
// Retrieves the next event from the BLE module's event queue.
//
// Returns `true` if an event was successfully read, `false` if no event is
// available.
bool ble_get_event(ble_event_t *event);

// Retrieves the current state of the BLE module
//
// Obtains the current operational state of the BLE module.
void ble_get_state(ble_state_t *state);

// Check if write is possible
bool ble_can_write(void);

// Writes data to a connected BLE device
//
// Sends data over an established BLE connection.
bool ble_write(const uint8_t *data, uint16_t len);

// Check if read is possible
bool ble_can_read(void);

// Reads data from a connected BLE device
//
// max_len indicates the maximum number of bytes to read. Rest of the data
// will be discarded.
//
// Returns the number of bytes actually read.
uint32_t ble_read(uint8_t *data, uint16_t max_len);

// Read MAC address of the device
//
// When not using static address, the address is random and may not correspond
// to what is actually used for advertising
bool ble_get_mac(uint8_t *mac, size_t max_len);
