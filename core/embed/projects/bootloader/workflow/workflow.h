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

#include <util/image.h>

#include "protob/protob.h"

typedef enum {
  WF_WIPE_AND_SHUTDOWN = 0,
  WF_SHUTDOWN = 0x11223344,
  WF_CONTINUE_TO_FIRMWARE = 0xAABBCCDD,
  WF_RETURN = 0x55667788,
  WF_STAY = 0xEEFF0011,
} workflow_result_t;

workflow_result_t workflow_firmware_update(protob_iface_t *iface,
                                           uint32_t msg_size, uint8_t *buf);

workflow_result_t workflow_wipe_device(protob_iface_t *iface, uint32_t msg_size,
                                       uint8_t *buf);

#ifdef USE_OPTIGA
workflow_result_t workflow_unlock_bootloader(protob_iface_t *iface,
                                             uint32_t msg_size, uint8_t *buf);
#endif

workflow_result_t workflow_ping(protob_iface_t *iface, uint32_t msg_size,
                                uint8_t *buf);

workflow_result_t workflow_initialize(protob_iface_t *iface, uint32_t msg_size,
                                      uint8_t *buf,
                                      const vendor_header *const vhdr,
                                      const image_header *const hdr);

workflow_result_t workflow_get_features(protob_iface_t *iface,
                                        uint32_t msg_size, uint8_t *buf,
                                        const vendor_header *const vhdr,
                                        const image_header *const hdr);

workflow_result_t workflow_bootloader(const vendor_header *const vhdr,
                                      const image_header *const hdr,
                                      secbool firmware_present);

workflow_result_t workflow_empty_device(void);

workflow_result_t workflow_host_control(const vendor_header *const vhdr,
                                        const image_header *const hdr,
                                        void (*redraw_wait_screen)(void));

workflow_result_t workflow_auto_update(const vendor_header *const vhdr,
                                       const image_header *const hdr);

secbool workflow_is_jump_allowed_1(void);
secbool workflow_is_jump_allowed_2(void);
