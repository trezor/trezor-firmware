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

typedef enum {
  WF_ERROR_FATAL = 0,
  WF_ERROR = 0x11223344,
  WF_OK = 0x7ABBCCDD,
  WF_OK_REBOOT_SELECTED = 0x68A4DABF,
  WF_OK_FIRMWARE_INSTALLED = 0x04D9D07F,
  WF_OK_DEVICE_WIPED = 0x30DC3841,
  WF_OK_BOOTLOADER_UNLOCKED = 0x23FCBD03,
  WF_OK_UI_ACTION = 0x5ABBCCEE,
  WF_OK_PAIRING_COMPLETED = 0x5ABBCCEF,
  WF_OK_PAIRING_FAILED = 0x3ABBCCF0,
  WF_CANCELLED = 0x55667788,
} workflow_result_t;

workflow_result_t bootloader_process_usb(void);

workflow_result_t bootloader_process_ble(void);
