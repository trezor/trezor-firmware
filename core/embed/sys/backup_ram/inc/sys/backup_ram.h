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

/** Global keys for items stored in the backup RAM */
#define BACKUP_RAM_KEY_PM_RECOVERY 0x0001   // Power management recovery data
#define BACKUP_RAM_KEY_BLE_SETTINGS 0x0002  // BLE settings
#define BACKUP_RAM_KEY_TELEMETRY 0x0003  // Telemetry data (min/max temps etc.)

/** Maximum size of data stored under a single key in backup RAM */
#define BACKUP_RAM_MAX_KEY_DATA_SIZE 512

typedef enum {
  BACKUP_RAM_ITEM_PUBLIC =
      0, /**< Public data - will be preserved on device wipe */
  BACKUP_RAM_ITEM_PROTECTED =
      1, /**< Protected data - will be erased on device wipe */
} backup_ram_item_type_t;

/**
 * @brief Initializes backup RAM driver
 *
 * This function initializes the backup RAM driver, checks the consistency of
 * the backup RAM storage, and initializes it if necessary.
 *
 * @return true if the operation was successful
 *
 */
bool backup_ram_init(void);

/**
 * @brief Deinitialize backup RAM driver
 *
 * The function does not erase the backup RAM, it just deinitializes
 * the driver.
 */
void backup_ram_deinit(void);

/**
 * @brief Erases the backup RAM content
 *
 * @return true if the operation was successful, false otherwise.
 */

bool backup_ram_erase(void);

/**
 * @brief Erases protected backup RAM content
 *
 * @return true if the operation was successful, false otherwise.
 */
bool backup_ram_erase_protected(void);

/**
 * @brief Erases a single item in backup RAM by its key.
 *
 * If the item with the given key does not exist, the function does nothing.
 *
 * @param key Key of the item to erase
 *
 * @return true if the operation was successful, false otherwise.
 */
bool backup_ram_erase_item(uint16_t key);

#define BACKUP_RAM_INVALID_KEY 0xFFFF

/**
 * @brief Finds the first key in backup RAM that is greater than or equal to
 * min_key.
 *
 * @param min_key Minimum key to search for
 *
 * @return The first key found that is greater than or equal to min_key, or
 *         BACKUP_RAM_INVALID_KEY if no such key exists.
 */
uint16_t backup_ram_search(uint16_t min_key);

/**
 * @brief Writes key-value data in backup RAM.
 *
 * @param key Key to identify the data
 * @param data Pointer to the data to be stored
 * @param type Type of the data being stored
 * @param data_size Size of the data in bytes. If the key does not exist, this
 * value will be set to 0. If data_size == 0, the item will be removed.
 *
 * @return true if the operation was successful, false otherwise.
 */
bool backup_ram_write(uint16_t key, backup_ram_item_type_t type,
                      const void* data, size_t data_size);

/**
 * @brief Reads key-value data from backup RAM.
 *
 * Writes key-value data in backup RAM. If the value with the give key
 * exists, it will be overwritten with the new data. If the data_size is
 * zero, the key will be removed from the backup RAM.
 *
 * @param key Key to identify the data
 * @param buffer Pointer to the buffer where the data will be stored
 * @param buffer_size Size of the buffer in bytes
 * @param data_size Pointer to a variable where the size of the data
 *
 * If data_size is NULL, the size will not be retrieved. If buffer is NULL,
 * the data will not be copied, but the size will still be retrieved.
 *
 * @return backup_ram_status_t BACKUP_RAM_OK if the operation was
 * successful.
 */
bool backup_ram_read(uint16_t key, void* buffer, size_t buffer_size,
                     size_t* data_size);

/**
 * @brief Determines if a key is accessible by the kernel.
 * @param key Key to check
 * @return true if the key is accessible by the kernel, false otherwise
 */
bool backup_ram_kernel_accessible(uint16_t key);
