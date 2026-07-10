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

#include <sys/flash.h>

#include "protob/protob.h"
#include "wf_image_upload.h"

/**
 * Verify the boot-header image already staged in `staging_area` and arm the
 * boot update control block (UCB) so the boardloader installs it on the next
 * reboot. (This does NOT write to the staging area -- see
 * `ucb_stage_write_header` for that; here the header, and for a full update the
 * code, are already staged.)
 *
 * Runs the downgrade check, recomputes the Merkle root over the authenticated
 * header + code, verifies the founder signature over that root, and writes the
 * UCB (`boot_ucb_write`). Sends its own failure message on any error.
 *
 * A caller may set `firmware_type` in the staged (unauth) header before calling
 * this; that field is outside `auth_size` so it does not affect the signature
 * check, and it is covered by the UCB hash computed here.
 *
 * `header_only` means the bootloader code is unchanged (the caller has verified
 * the new header signs over the current code). On models whose field
 * boardloader mangles the code_address == 0 sentinel
 * (BOARDLOADER_UCB_ZERO_ADDR_BUG) a copy of the current code is staged and a
 * real code address recorded (the workaround); otherwise nothing is staged and
 * the UCB records the 0 sentinel (reuse current code). For a full update the
 * new code is expected staged right after the header.
 *
 * @param staging_area Flash area holding the staged boot header (+ code).
 * @param header_only Bootloader code unchanged (reuse current code).
 * @param iface Protobuf I/O used to send failure messages.
 * @return UPLOAD_OK on success, a negative upload_status_t otherwise.
 */
upload_status_t ucb_stage_commit(const flash_area_t *staging_area,
                                 bool header_only, protob_io_t *iface);

/**
 * Write `len` bytes of a boot header from `data` to the start of the staging
 * area (erase + program). For the case where the boot header arrives whole (in
 * a message) rather than through the chunk stream, so it must be staged up
 * front. `data` must be 4-byte aligned and `len` a multiple of the flash write
 * granularity (the boot header's 8K-aligned `header_size` satisfies this).
 * Fatal on flash error.
 */
secbool ucb_stage_write_header(const uint8_t *data, uint32_t len);

#endif  // USE_BOOT_UCB
