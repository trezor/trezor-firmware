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
 * @brief Status codes for backup RAM operations
 */
typedef enum {
  BACKUP_RAM_OK = 0,
  BACKUP_RAM_OK_STORAGE_INITIALIZED,
  BACKUP_RAM_ERROR,
  BACKUP_RAM_HEADER_CHECK_ERROR,
  BACKUP_RAM_VERSION_CHECK_ERROR,
  BACKUP_RAM_CRC_CHECK_ERROR,
  BACKUP_RAM_DATA_CHECK_ERROR,
} backup_ram_status_t;

/**
 * @brief Structure for power management data stored in backup RAM
 *
 * This structure contains critical power management information that needs to
 * persist across power cycles and resets. It stores battery state of charge
 * (SOC), timing information, and system state data required for proper power
 * management. The data is stored in battery-backed RAM to ensure availability
 * after power loss.
 */
typedef struct {
  float soc;  // Captured state of charge <0, 1>
  bool bat_crittical;
  // Captures RTC time at which SOC was captured
  uint32_t last_capture_timestamp;
  // Captures power manager state at bootloader exit so it could be correctly
  // restored in the firwmare.
  uint32_t bootloader_exit_state;
} backup_ram_power_manager_data_t;

/**
 * @brief Initialize backup RAM driver
 *
 * @return backup_ram_status_t BACKUP_RAM_OK if the operation was successful or
 *                             backup allready initialized.
 */
backup_ram_status_t backup_ram_init(void);

/**
 * @brief Deinitialize backup RAM driver
 */
void backup_ram_deinit(void);

/**
 * @brief Erase backup RAM completely.
 *
 * @return backup_ram_status_t BACKUP_RAM_OK if the operation was successful.
 */
backup_ram_status_t backup_ram_erase(void);

/**
 * @brief Erase unused space of the backup RAM (everything unallocated by the
 *        defined storage structure).
 *
 * @return backup_ram_status_t BACKUP_RAM_OK if the operation was successful.
 */
backup_ram_status_t backup_ram_erase_unused(void);

/**
 * @brief Store power manager data in backup RAM.
 *
 * @param fg_state Pointer to the structure containing the data to be stored
 * @return backup_ram_status_t BACKUP_RAM_OK if the operation was successful.
 */
backup_ram_status_t backup_ram_store_power_manager_data(
    const backup_ram_power_manager_data_t* pm_data);

/**
 * @brief Read power manager data from backup RAM.
 *
 * @param fg_state Pointer to the structure where the data will be stored
 * @return backup_ram_status_t BACKUP_RAM_OK if the operation was successful.
 */
backup_ram_status_t backup_ram_read_power_manager_data(
    backup_ram_power_manager_data_t* pm_data);
