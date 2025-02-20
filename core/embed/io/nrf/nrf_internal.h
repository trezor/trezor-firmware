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
  MGMT_CMD_SYSTEM_OFF = 0x00,
  MGMT_CMD_INFO = 0x01,
} management_cmd_t;

typedef enum {
  MGMT_RESP_INFO = 0,
} management_resp_t;

void nrf_dfu_comm_send(const uint8_t *data, uint32_t len);
uint32_t nrf_dfu_comm_receive(uint8_t *data, uint32_t len);

void nrf_int_send(const uint8_t *data, uint32_t len);
uint32_t nrf_int_receive(uint8_t *data, uint32_t len);

bool nrf_firmware_running(void);

bool nrf_reboot(void);
bool nrf_reboot_to_bootloader(void);

void nrf_signal_running(void);
void nrf_signal_off(void);

void nrf_stay_in_bootloader(bool set);
bool nrf_in_reserved_gpio(void);
