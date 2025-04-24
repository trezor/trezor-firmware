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

#include <trezor_model.h>
#include <trezor_types.h>

typedef enum {
  BACKUP_RAM_OK = 0,
  BACKUP_RAM_ERROR,
} backup_ram_status_t;

// Fuel gauge backup storage definition
typedef struct {
  float soc;  // Captured state of charge <0, 1>
  // Captures RTC time at which SOC was captured
  uint32_t last_capture_timestamp;
} fuel_gauge_backup_storage_t;

typedef union {
  uint8_t bytes[BACKUP_RAM_SIZE];
  struct {
    volatile fuel_gauge_backup_storage_t fg;
    // < Room for other data structures >
  } data;
} backup_ram_data_t;

// Initialize backup RAM driver
backup_ram_status_t backup_ram_init(void);

// Deinitialize backup RAM driver
backup_ram_status_t backup_ram_deinit(void);

// Erase backup ram
backup_ram_status_t backup_ram_erase(void);

// Erase unused space in backup ram
// This function clears the remaining part of the backup ram not alocated by
// data struct.
backup_ram_status_t backup_ram_erase_unused(void);

// Store fuel gauge state in backup ram
backup_ram_status_t backup_ram_store_fuel_gauge_state(
    const fuel_gauge_backup_storage_t* fg_state);

// Read fuel gauge state from backup ram
backup_ram_status_t backup_ram_read_fuel_gauge_state(
    fuel_gauge_backup_storage_t* fg_state);
