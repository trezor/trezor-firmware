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

#include <trezor_model.h>
#include <trezor_rtl.h>

#ifdef USE_BOOT_UCB

#include <sec/boot_header.h>
#include <sec/boot_ucb.h>
#include <sys/flash.h>

#include "protob/protob.h"
#include "wf_ucb_stage.h"

// Copy `len` bytes of the currently installed bootloader code into the staging
// area at `offset` (i.e. right after the staged header). Source is the running
// bootloader's own code in flash; the destination is a distinct flash region.
static secbool stage_copy_current_code(uint32_t offset, uint32_t len) {
  const uint8_t *src = (const uint8_t *)(uintptr_t)(BOOTLOADER_START + offset);
  uint32_t remaining = len;
  uint32_t pos = offset;

  while (remaining > 0) {
    uint32_t bytes_erased = 0;
    ensure(flash_area_erase_partial(&STAGING_AREA, pos, &bytes_erased), NULL);

    uint32_t chunk = MIN(bytes_erased, remaining);
    // Flash writes are quad-word aligned; round the tail up. The extra source
    // bytes past the code are don't-care -- only code_size bytes are ever
    // hashed (Merkle root) or compared (bootloader_area_needs_update).
    uint32_t wlen = (chunk + 15u) & ~15u;
    if (wlen > bytes_erased) {
      wlen = bytes_erased;
    }
    ensure(flash_unlock_write(), NULL);
    ensure(flash_area_write_data(&STAGING_AREA, pos, src, wlen), NULL);
    ensure(flash_lock_write(), NULL);

    pos += chunk;
    src += chunk;
    remaining -= chunk;
  }
  return sectrue;
}

upload_status_t ucb_stage_commit(const flash_area_t *staging_area,
                                 bool header_only, protob_io_t *iface) {
  // The boot header is staged at the start of the staging area.
  uint32_t staged = (uint32_t)(uintptr_t)flash_area_get_address(
      staging_area, 0, sizeof(boot_header_auth_t));

  const boot_header_auth_t *hdr = boot_header_auth_get(staged);
  if (hdr == NULL) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid bootloader header");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER;
  }

  const boot_header_auth_t *cur = boot_header_auth_get(BOOTLOADER_START);
  if (cur != NULL && hdr->monotonic_version < cur->monotonic_version) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Bootloader downgrade protection");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_VERSION;
  }

  // Resolve where the code to verify lives (`verify_code_address`) and what the
  // UCB records (`ucb_code_address`; 0 is the "header-only -- reuse the current
  // code" sentinel). For a full update the new code is already staged after the
  // header. For header-only, the bootloader code is unchanged (the caller has
  // verified the new header signs over the current code).
  uint32_t verify_code_address;
  uint32_t ucb_code_address;
  if (header_only) {
#ifdef BOARDLOADER_UCB_ZERO_ADDR_BUG
    // This model's field boardloader mangles the code_address == 0 sentinel:
    // its boot_ucb_read() runs adjust_to_secure_flash() on code_address BEFORE
    // the sentinel is checked, turning 0 into (FLASH_BASE_S - FLASH_BASE_NS)
    // which is then rejected as out of range (see BOARDLOADER_UCB_ZERO_ADDR_BUG
    // in the model header). Work around it: stage a copy of the current code
    // and hand the boardloader a real, in-range address instead of the
    // sentinel.
    if (sectrue != stage_copy_current_code(hdr->header_size, hdr->code_size)) {
      send_msg_failure(iface, FailureType_Failure_ProcessError,
                       "Staging failed");
      return UPLOAD_ERR_COMMUNICATION;
    }
    verify_code_address = staged + hdr->header_size;
    ucb_code_address = verify_code_address;
#else
    // Fixed boardloader: reuse the in-place current code (nothing to stage) --
    // verify the new header against it and hand the boardloader the 0 sentinel.
    verify_code_address = BOOTLOADER_START + hdr->header_size;
    ucb_code_address = 0;
#endif
  } else {
    verify_code_address = staged + hdr->header_size;
    ucb_code_address = verify_code_address;
  }

  // Verify: the Merkle root over the authenticated header + code, then the
  // signature over that root. (firmware_type is outside auth_size, so a
  // device-set firmware_type does not affect this check.)
  merkle_proof_node_t merkle_root;
  boot_header_calc_merkle_root(hdr, verify_code_address, &merkle_root);

  if (sectrue != boot_header_check_signature(hdr, &merkle_root)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid bootloader signature");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
  }

  // Hand off to the boardloader: it re-verifies and installs on the next boot.
  if (sectrue != boot_ucb_write(staged, ucb_code_address)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Failed to write boot UCB");
    return UPLOAD_ERR_COMMUNICATION;
  }

  return UPLOAD_OK;
}

secbool ucb_stage_write_header(const uint8_t *data, uint32_t len) {
  const uint32_t *src = (const uint32_t *)(const void *)data;
  uint32_t remaining = len;
  uint32_t write_offset = 0;
  uint32_t erase_offset = 0;

  while (remaining > 0) {
    uint32_t bytes_erased = 0;
    ensure(flash_area_erase_partial(&STAGING_AREA, erase_offset, &bytes_erased),
           NULL);
    erase_offset += bytes_erased;

    uint32_t to_write = MIN(bytes_erased, remaining);
    ensure(flash_unlock_write(), NULL);
    ensure(flash_area_write_data(&STAGING_AREA, write_offset, src, to_write),
           NULL);
    ensure(flash_lock_write(), NULL);

    write_offset += to_write;
    src += to_write / sizeof(uint32_t);
    remaining -= to_write;
  }

  return sectrue;
}

#endif  // USE_BOOT_UCB
