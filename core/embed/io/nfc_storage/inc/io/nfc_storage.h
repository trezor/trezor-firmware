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

/**
 * @brief NFC storage device types
 */
typedef enum {
  NFC_STORAGE_NO_DEVICE = -1,
  NFC_STORAGE_ST25TV = 0,
  NFC_STORAGE_MAX_TYPES,
} nfc_storage_type_t;

/**
 * @brief NFC storage state
 */
typedef struct {
  bool connected;
} nfc_storage_state_t;

/**
 * @brief NFC storage events
 */
typedef enum {
  NFC_STORAGE_DEVICE_CONNECTED,
  NFC_STORAGE_DEVICE_DISCONNECTED,
} nfc_storage_event_t;

/**
 * @brief NFC storage memory structure
 */
typedef struct {
  uint32_t total_size_bytes;
  uint32_t start_address;
  uint32_t end_address;
} nfc_storage_mem_struct_t;

/**
 * @brief Initialize NFC storage driver
 *
 * @return true on success, false on failure
 */
bool nfc_storage_init();

/**
 * @brief Deinitialize NFC storage driver
 */
void nfc_storage_deinit();

/**
 * @brief Register NFC storage device type for discovery
 *
 * @param type NFC storage device type to register
 * @return true on success, false on failure
 */
bool nfc_storage_register_device(nfc_storage_type_t type);

/**
 * @brief Activate NFC and start discovery poller
 *
 * @return true on success, false on failure
 */
bool nfc_storage_start_discovery();

/**
 * @brief Stop NFC discovery
 */
void nfc_storage_stop_discovery();

/**
 * @brief Get pending NFC storage events
 *
 * @param events Pointer to nfc_storage_event_t to store events
 * @return true on success, false on failure
 */
bool nfc_storage_get_events(nfc_storage_event_t *events);

/**
 * @brief Get current NFC storage state
 *
 * @param state Pointer to nfc_storage_state_t to store state
 */
bool nfc_storage_get_state(nfc_storage_state_t *state);

/**
 * @brief Get memory structure of the connected NFC storage device
 *
 * @param mem_struct Pointer to nfc_storage_mem_struct_t to store memory
 * structure
 * @return true on success, false on failure
 */
bool nfc_storage_device_get_mem_struct(nfc_storage_mem_struct_t *mem_struct);

/**
 * @brief Read data from the connected NFC storage device
 *
 * Reads data from then NFC storage device starting from specified address.
 * Memory structure giving the available address range should be obtained by
 * calling nfc_storage_device_get_mem_struct() function.
 *
 * @param block_number data start address to read from
 * @param data Pointer to buffer to store read data
 * @param data_size Size of data to read in bytes
 * @return true on success, false on failure
 */
bool nfc_storage_device_read_data(uint32_t addr, uint8_t *data,
                                  size_t data_size);

/**
 * @brief Write data to the connected NFC storage device
 *
 * Writes data to NFC storage device starting from specified address. Memory
 * structure giving the available address range should be obtained by
 * calling nfc_storage_device_get_mem_struct() function.
 *
 * @param block_number Starting block number to write to
 * @param data Pointer to data to write
 * @param data_size Size of data to write in bytes
 * @return true on success, false on failure
 */
bool nfc_storage_device_write_data(uint32_t addr, const uint8_t *data,
                                   size_t data_size);

/**
 * @brief Wipe memory of the connected NFC storage device
 *
 * @return true on success, false on failure
 */
bool nfc_storage_device_wipe_memory();
