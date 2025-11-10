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

#define NFC_BACKUP_STORAGE_MAGIC 0xA5
#define NFC_BACKUP_STORAGE_VERSION 0x01
#define NFC_BACKUP_STORAGE_MAX_SIZE 64

typedef enum {
  NFC_BACKUP_CONNECTED,
  NFC_BACKUP_DISCONNECTED,
} nfc_backup_event_t;

typedef struct {
  uint8_t magic;
  uint8_t version;
  uint8_t bytes[NFC_BACKUP_STORAGE_MAX_SIZE];  // Adjust size as needed
  uint16_t
      crc;  // CRC16 for data integrity, replace with repairable code if needed
} nfc_backup_data_t;

typedef struct {
  uint8_t uid[8];
  uint8_t dsfid;
  uint8_t afi;
  uint16_t memory_size;
  uint8_t ic_reference;
} nfc_backup_system_info_t;

typedef struct {
  bool connected;
  bool system_info_available;
} nfc_backup_state_t;

bool nfc_backup_init();

void nfc_backup_deinit();

bool nfc_backup_read_system_info(nfc_backup_system_info_t *system_info);

bool nfc_backup_configure_discrete_mode();

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

bool nfc_backup_store_data(const uint8_t *data, size_t data_size);

void nfc_backup_worker(nfc_backup_state_t *state);

bool nfc_backup_read_data(uint8_t *data, size_t data_size);

void nfc_backup_get_state(nfc_backup_state_t *state);
