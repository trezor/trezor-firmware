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

#include <sec/image.h>

#include "protob/protob.h"
#include "workflow_common.h"

workflow_result_t workflow_firmware_update(protob_io_t *iface);

workflow_result_t workflow_wipe_device(protob_io_t *iface);

#ifdef LOCKABLE_BOOTLOADER
workflow_result_t workflow_unlock_bootloader(protob_io_t *iface);
#endif

workflow_result_t workflow_ping(protob_io_t *iface);

workflow_result_t workflow_initialize(protob_io_t *iface, const fw_info_t *fw);

workflow_result_t workflow_get_features(protob_io_t *iface,
                                        const fw_info_t *fw);

workflow_result_t workflow_menu(const fw_info_t *fw, protob_ios_t *ios);

workflow_result_t workflow_bootloader(const fw_info_t *fw);

workflow_result_t workflow_empty_device(void);

workflow_result_t workflow_auto_update(const fw_info_t *fw);

#ifdef USE_BLE

bool wipe_bonds(protob_io_t *iface);

workflow_result_t workflow_ble_pairing_request(const fw_info_t *fw);

workflow_result_t workflow_wireless_setup(const fw_info_t *fw,
                                          protob_ios_t *ios);
#endif

void workflow_ifaces_init(secbool usb21_landing, protob_ios_t *ios);

void workflow_ifaces_deinit(protob_ios_t *ios);

void workflow_ifaces_pause(protob_ios_t *ios);

void workflow_ifaces_resume(protob_ios_t *ios);
