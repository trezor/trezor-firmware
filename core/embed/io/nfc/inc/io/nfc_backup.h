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

typedef enum {
  NFC_BACKUP_CONNECTED,
  NFC_BACKUP_DISCONNECTED,
} nfc_backup_event_t;

typedef struct {
  bool connected;
} nfc_backup_state_t;

typedef struct {
  uint8_t uid[8];
  uint8_t dsfid;
  uint8_t afi;
  uint8_t mem_block_size;
  uint8_t mem_block_count;
  uint8_t ic_reference;
} nfc_backup_system_info_t;

/**
 * @brief Initialize NFC backup driver
 *
 * @return true on success, false on failure
 */
bool nfc_backup_init();

/**
 * @brief Deinitialize NFC backup driver
 */
void nfc_backup_deinit();

/**
 * @brief Activate NFC and start discovery poller
 *
 * @return true on success, false on failure
 */
bool nfc_backup_start_discovery();

/**
 * @brief Stop NFC discovery
 */
void nfc_backup_stop_discovery();

/**
 * @brief Get pending NFC backup events
 *
 * @param events Pointer to nfc_backup_event_t to store events
 * @return true on success, false on failure
 */
bool nfc_backup_get_events(nfc_backup_event_t *events);

/**
 * @brief Get current NFC backup state
 *
 * @param state Pointer to nfc_backup_state_t to store state
 */
void nfc_backup_get_state(nfc_backup_state_t *state);

/**
 * @brief Read system info from the connected NFC tag
 *
 * @param system_info Pointer to nfc_backup_system_info_t structure to store
 *                    the system info
 * @return true on success, false on failure
 */
bool nfc_backup_read_system_info(nfc_backup_system_info_t *system_info);

/**
 * @brief Enable or disable silent mode on the connected NFC tag
 *
 * @param enable true to enable silent mode, false to disable
 * @return true on success, false on failure
 */
bool nfc_backup_set_silent_mode(bool enable);

/**
 * @brief Write data to the connected NFC tag
 *
 * Writes data to the NFC tag starting from the specified block number. Number
 * of available blocks and their size can be obtained from the NFC tag system
 * info acquired by nfc_backup_read_system_info() function.
 *
 * @param block_number Starting block number to write to
 * @param data Pointer to data to write
 * @param data_size Size of data to write in bytes
 * @return true on success, false on failure
 */
bool nfc_backup_write_data(uint16_t block_number, const uint8_t *data,
                           size_t data_size);

/**
 * @brief Wipe memory of the connected NFC tag
 *
 * @return true on success, false on failure
 */
bool nfc_backup_wipe_memory();

/**
 * @brief Read data from the connected NFC tag
 *
 * Reads data from the NFC tag starting from the specified block number. Number
 * of available blocks and their size can be obtained from the NFC tag system
 * info acquired by nfc_backup_read_system_info() function.
 *
 * @param block_number Starting block number to read from
 * @param data Pointer to buffer to store read data
 * @param data_size Size of data to read in bytes
 * @return true on success, false on failure
 */
bool nfc_backup_read_data(uint16_t block_number, uint8_t *data,
                          size_t data_size);
