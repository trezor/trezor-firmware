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

// Must sit at TOP LEVEL, not inside any #ifdef: it #undefs the model's flash
// address constants so they resolve to the emulator's mapped addresses, and a
// use further down the file that is NOT under the same condition would silently
// get the device constant back -- a pointer to nothing on the host.
#ifdef TREZOR_EMULATOR
#include "../emulator.h"
#endif

#ifdef USE_BOOT_UCB

#include <sec/boot_header.h>
#include <sec/boot_ucb.h>
#include <sys/flash.h>

#include "protob/protob.h"
#include "wf_image_upload.h"  // chunk_buffer
#include "wf_ucb_stage.h"

// Report a staging failure to the host, if there is one. `ucb_stage_verify` is
// also reached from the bootloader's own boot path, where nobody is listening
// and `iface` is NULL -- MSG_SEND would dereference it.
static void stage_report_failure(protob_io_t *iface, const char *msg) {
  if (iface != NULL) {
    send_msg_failure(iface, FailureType_Failure_ProcessError, msg);
  }
}

// The UCB records DEVICE flash addresses: the boardloader reads the block from
// flash on the next boot and dereferences them, so they must mean something to
// it and not to us. On the MCU a pointer into flash IS that address and this is
// the identity. On the emulator flash is an mmap of `trezor.flash`, so the two
// are unrelated -- harmless there, since no boardloader ever reads the block,
// but written out explicitly so the one place where "pointer" and "flash
// address" stop being the same thing is visible rather than implied.
static uint32_t ucb_flash_address(const void *flash_ptr) {
  return (uint32_t)(uintptr_t)flash_ptr;
}

#ifdef BOARDLOADER_UCB_ZERO_ADDR_BUG
// Copy `len` bytes of the currently installed bootloader code into the staging
// area at `offset` (i.e. right after the staged header). Source is the running
// bootloader's own code in flash; the destination is a distinct flash region.
// Only needed for the code_address==0 sentinel workaround below (its sole
// caller), so it is compiled only when that workaround is active.
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
#endif  // BOARDLOADER_UCB_ZERO_ADDR_BUG

upload_status_t ucb_stage_verify(const flash_area_t *staging_area,
                                 bool header_only, protob_io_t *iface,
                                 merkle_proof_node_t *out_root,
                                 uint32_t *out_code_address) {
  // The boot header is staged at the start of the staging area.
  const uint8_t *staged =
      flash_area_get_address(staging_area, 0, sizeof(boot_header_auth_t));

  const boot_header_auth_t *hdr = boot_header_auth_get(staged);
  if (hdr == NULL) {
    stage_report_failure(iface, "Invalid bootloader header");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER;
  }

  const boot_header_auth_t *cur =
      boot_header_auth_get((const uint8_t *)(uintptr_t)BOOTLOADER_START);
  if (cur != NULL && hdr->monotonic_version < cur->monotonic_version) {
    stage_report_failure(iface, "Bootloader downgrade protection");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_VERSION;
  }

  // Resolve where the code to verify lives (`verify_code`) and what the
  // UCB records (`ucb_code_address`; 0 is the "header-only -- reuse the current
  // code" sentinel). For a full update the new code is already staged after the
  // header. For header-only, the bootloader code is unchanged (the caller has
  // verified the new header signs over the current code).
  const void *verify_code;
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
      stage_report_failure(iface, "Staging failed");
      return UPLOAD_ERR_COMMUNICATION;
    }
    verify_code = staged + hdr->header_size;
    ucb_code_address = ucb_flash_address(verify_code);
#else
    // Fixed boardloader: reuse the in-place current code (nothing to stage) --
    // verify the new header against it and hand the boardloader the 0 sentinel.
    verify_code =
        (const uint8_t *)(uintptr_t)BOOTLOADER_START + hdr->header_size;
    ucb_code_address = 0;
#endif
  } else {
    verify_code = staged + hdr->header_size;
    ucb_code_address = ucb_flash_address(verify_code);
  }

  // Verify: the Merkle root over the authenticated header + code, then the
  // signature over that root. (firmware_type is outside auth_size, so a
  // device-set firmware_type does not affect this check.)
  merkle_proof_node_t merkle_root;
  boot_header_calc_merkle_root(hdr, verify_code, &merkle_root);

  if (sectrue != boot_header_check_signature(hdr, &merkle_root)) {
    stage_report_failure(iface, "Invalid bootloader signature");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
  }

  // Hand the signature-verified modelRoot back (the root the new boot header
  // commits to): co-processor images are peer leaves under it, so this is what
  // the caller folds them against -- valid for BOTH header-only (current code)
  // and full (staged new code), always after the signature check above.
  if (out_root != NULL) {
    memcpy(out_root->bytes, merkle_root.bytes, sizeof(out_root->bytes));
  }
  // The code address the UCB must record. The install itself is NOT armed here:
  // the caller arms it (ucb_stage_arm) only AFTER any co-processor updates
  // succeed, so a partial update can never leave the new bootloader installed
  // against an old, possibly-incompatible co-processor (a brick). See
  // wf_firmware_update_pq.
  *out_code_address = ucb_code_address;
  return UPLOAD_OK;
}

secbool ucb_stage_arm(const flash_area_t *staging_area, uint32_t code_address) {
  // Arm the boot update control block: the boardloader re-verifies and installs
  // the staged bootloader on the next boot. This is the point of no return for
  // the bootloader swap -- call it LAST, after co-processors are updated.
  const void *staged =
      flash_area_get_address(staging_area, 0, sizeof(boot_header_auth_t));
  return boot_ucb_write(staged, code_address);
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

#ifdef PQ_SECURE_BOOT
secbool ucb_stage_clear_firmware_type(void) {
  const boot_header_auth_t *installed =
      boot_header_auth_get((const uint8_t *)(uintptr_t)BOOTLOADER_START);
  if (installed == NULL) {
    return secfalse;
  }
  const uint32_t header_size = installed->header_size;
  if (header_size == 0 || header_size > IMAGE_CHUNK_SIZE) {
    return secfalse;
  }

  // Copy the installed header verbatim, then clear the one byte. Everything
  // authenticated is preserved bit for bit, so the founder signature over it
  // still verifies below; firmware_type is outside auth_size.
  uint8_t *staged = (uint8_t *)chunk_buffer;
  memcpy(staged, (const void *)(uintptr_t)BOOTLOADER_START, header_size);

  boot_header_auth_t *hdr = (boot_header_auth_t *)boot_header_auth_get(staged);
  if (hdr == NULL) {
    return secfalse;
  }
  boot_header_unauth_t *unauth =
      (boot_header_unauth_t *)(uintptr_t)boot_header_unauth_get(hdr);
  if (unauth == NULL) {
    return secfalse;
  }
  if (unauth->firmware_type == 0) {
    // Already unprovisioned -- nothing to install, and arming the UCB for a
    // no-op change would spend a boardloader install for nothing.
    return sectrue;
  }
  unauth->firmware_type = 0;

  if (sectrue != ucb_stage_write_header(staged, header_size)) {
    return secfalse;
  }

  // No iface: this runs from the bootloader's own boot path, not a host
  // workflow, so a failure has nobody to report to over the wire.
  uint32_t code_address = 0;
  if (UPLOAD_OK != ucb_stage_verify(&STAGING_AREA, /*header_only=*/true, NULL,
                                    NULL, &code_address)) {
    return secfalse;
  }
  return ucb_stage_arm(&STAGING_AREA, code_address);
}
#endif  // PQ_SECURE_BOOT

#endif  // USE_BOOT_UCB
