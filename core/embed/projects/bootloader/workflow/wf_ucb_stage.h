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

#ifdef USE_BOOT_UCB

#include <sec/boot_header.h>  // merkle_proof_node_t
#include <sys/flash.h>

#include "protob/protob.h"
#include "wf_image_upload.h"

/**
 * Verify the boot header (+ code for a full update) already staged in
 * `staging_area`: downgrade check, Merkle root, founder signature. Does not
 * arm the UCB; the caller arms last via ucb_stage_arm. A `firmware_type` set
 * in the unauth header is outside `auth_size` and covered by the UCB hash.
 *
 * @param header_only code unchanged; on BOARDLOADER_UCB_ZERO_ADDR_BUG models a
 *                    copy of the current code is staged instead of the 0
 *                    sentinel
 * @param iface       used for failure messages; NULL on the boot path
 * @param out_root    signature-verified modelRoot of the new header
 * @param out_code_address code address for ucb_stage_arm
 * @return UPLOAD_OK, or a negative upload_status_t
 */
upload_status_t ucb_stage_verify(const flash_area_t *staging_area,
                                 bool header_only, protob_io_t *iface,
                                 merkle_proof_node_t *out_root,
                                 uint32_t *out_code_address);

/**
 * Arm the UCB (point of no return); call last, after co-processor updates.
 * `code_address` comes from ucb_stage_verify.
 */
secbool ucb_stage_arm(const flash_area_t *staging_area, uint32_t code_address);

/**
 * Erase the staging area and program `len` bytes of boot header at its start.
 * `data` 4-byte aligned, `len` a multiple of the flash write granularity.
 * Fatal on flash error.
 */
secbool ucb_stage_write_header(const uint8_t *data, uint32_t len);

#endif  // USE_BOOT_UCB
