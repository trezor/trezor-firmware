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

#include <io/ble.h>

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
  INTERNAL_EVENT_PAIRING_REQUEST = 0x04,
  INTERNAL_EVENT_PAIRING_CANCELLED = 0x05,
} internal_event_t;

typedef enum {
  INTERNAL_CMD_PING = 0x00,
  INTERNAL_CMD_ADVERTISING_ON = 0x01,
  INTERNAL_CMD_ADVERTISING_OFF = 0x02,
  INTERNAL_CMD_ERASE_BONDS = 0x03,
  INTERNAL_CMD_DISCONNECT = 0x04,
  INTERNAL_CMD_ACK = 0x05,
  INTERNAL_CMD_ALLOW_PAIRING = 0x06,
  INTERNAL_CMD_REJECT_PAIRING = 0x07,
} internal_cmd_t;

typedef struct {
  uint8_t cmd_id;
  uint8_t whitelist;
  uint8_t color;
  uint8_t name[BLE_ADV_NAME_LEN];
} cmd_advertising_on_t;
