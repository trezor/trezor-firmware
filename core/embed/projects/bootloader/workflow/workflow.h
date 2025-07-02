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

#include <sys/sysevent.h>
#include <util/image.h>

#include "protob/protob.h"
#include "rust_ui_bootloader.h"

typedef enum {
  WF_ERROR_FATAL = 0,
  WF_ERROR = 0x11223344,
  WF_OK = 0x7ABBCCDD,
  WF_OK_REBOOT_SELECTED = 0x68A4DABF,
  WF_OK_FIRMWARE_INSTALLED = 0x04D9D07F,
  WF_OK_DEVICE_WIPED = 0x30DC3841,
  WF_OK_BOOTLOADER_UNLOCKED = 0x23FCBD03,
  WF_OK_UI_ACTION = 0xAABBCCEE,
  WF_OK_PAIRING_COMPLETED = 0xAABBCCEF,
  WF_OK_PAIRING_FAILED = 0xAABBCCF0,
  WF_CANCELLED = 0x55667788,
} workflow_result_t;

workflow_result_t workflow_firmware_update(protob_io_t *iface);

workflow_result_t workflow_wipe_device(protob_io_t *iface);

#ifdef LOCKABLE_BOOTLOADER
workflow_result_t workflow_unlock_bootloader(protob_io_t *iface);
#endif

workflow_result_t workflow_ping(protob_io_t *iface);

workflow_result_t workflow_initialize(protob_io_t *iface,
                                      const vendor_header *const vhdr,
                                      const image_header *const hdr);

workflow_result_t workflow_get_features(protob_io_t *iface,
                                        const vendor_header *const vhdr,
                                        const image_header *const hdr);

workflow_result_t workflow_menu(const vendor_header *const vhdr,
                                const image_header *const hdr,
                                protob_ios_t *ios);

workflow_result_t workflow_bootloader(const vendor_header *const vhdr,
                                      const image_header *const hdr,
                                      secbool firmware_present);

workflow_result_t workflow_empty_device(void);

workflow_result_t workflow_host_control(const vendor_header *const vhdr,
                                        const image_header *const hdr,
                                        c_layout_t *wait_layout,
                                        uint32_t *ui_action_result,
                                        protob_ios_t *ios);

workflow_result_t workflow_auto_update(const vendor_header *const vhdr,
                                       const image_header *const hdr);

#ifdef USE_BLE
workflow_result_t workflow_ble_pairing_request(const vendor_header *const vhdr,
                                               const image_header *const hdr);

workflow_result_t workflow_wireless_setup(const vendor_header *const vhdr,
                                          const image_header *const hdr,
                                          protob_ios_t *ios);
#endif

void workflow_ifaces_init(secbool usb21_landing, protob_ios_t *ios);

void workflow_ifaces_deinit(protob_ios_t *ios);

void workflow_ifaces_pause(protob_ios_t *ios);

void workflow_ifaces_resume(protob_ios_t *ios);
