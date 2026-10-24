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

// Must stay at top level: it #undefs the model's flash address constants.
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

// `iface` is NULL on the bootloader's own boot path.
static void stage_report_failure(protob_io_t *iface, const char *msg) {
  if (iface != NULL) {
    send_msg_failure(iface, FailureType_Failure_ProcessError, msg);
  }
}

// The UCB records device flash addresses for the boardloader; on the MCU a
// flash pointer is that address (on the emulator it is not, but nothing
// reads the block there).
static uint32_t ucb_flash_address(const void *flash_ptr) {
  return (uint32_t)(uintptr_t)flash_ptr;
}

#ifdef BOARDLOADER_UCB_ZERO_ADDR_BUG
// Copy the installed bootloader code into the staging area at `offset`.
static secbool stage_copy_current_code(uint32_t offset, uint32_t len) {
  const uint8_t *src = (const uint8_t *)(uintptr_t)(BOOTLOADER_START + offset);
  uint32_t remaining = len;
  uint32_t pos = offset;

  while (remaining > 0) {
    uint32_t bytes_erased = 0;
    ensure(flash_area_erase_partial(&STAGING_AREA, pos, &bytes_erased), NULL);

    uint32_t chunk = MIN(bytes_erased, remaining);
    // Quad-word aligned writes; the extra source bytes past the code are
    // never hashed or compared.
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
  const uint8_t *staged =
      flash_area_get_address(staging_area, 0, sizeof(boot_header_auth_t));

  const boot_header_auth_t *hdr = boot_header_auth_get((uintptr_t)staged);
  if (hdr == NULL) {
    stage_report_failure(iface, "Invalid bootloader header");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER;
  }

  const boot_header_auth_t *cur = boot_header_auth_get(BOOTLOADER_START);
  if (cur != NULL && hdr->monotonic_version < cur->monotonic_version) {
    stage_report_failure(iface, "Bootloader downgrade protection");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_VERSION;
  }

  // Upgrade floor, re-checked on the staged header; must match phase 1
  // (fw_begin_preamble). Set => must be positively satisfied.
  if (boot_header_version_is_set(hdr->min_prev_version) &&
      (cur == NULL ||
       boot_header_version_compare(cur->version, hdr->min_prev_version) < 0)) {
    stage_report_failure(iface, "Unsupported bootloader upgrade path");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_VERSION;
  }

  // Code to verify against, and the address the UCB records (0 = reuse the
  // current code).
  const void *verify_code;
  uint32_t ucb_code_address;
  if (header_only) {
#ifdef BOARDLOADER_UCB_ZERO_ADDR_BUG
    // The field boardloader mangles the 0 sentinel (adjust_to_secure_flash
    // before the sentinel check), so stage a copy and record a real address.
    if (sectrue != stage_copy_current_code(hdr->header_size, hdr->code_size)) {
      stage_report_failure(iface, "Staging failed");
      return UPLOAD_ERR_COMMUNICATION;
    }
    verify_code = staged + hdr->header_size;
    ucb_code_address = ucb_flash_address(verify_code);
#else
    verify_code =
        (const uint8_t *)(uintptr_t)BOOTLOADER_START + hdr->header_size;
    ucb_code_address = 0;
#endif
  } else {
    verify_code = staged + hdr->header_size;
    ucb_code_address = ucb_flash_address(verify_code);
  }

  // firmware_type is outside auth_size and does not affect this check.
  merkle_proof_node_t merkle_root;
  boot_header_calc_merkle_root(hdr, (uintptr_t)verify_code, &merkle_root);

  if (sectrue != boot_header_check_signature(hdr, &merkle_root)) {
    stage_report_failure(iface, "Invalid bootloader signature");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
  }

  // Signature-verified modelRoot; co-processor leaves fold against it.
  if (out_root != NULL) {
    memcpy(out_root->bytes, merkle_root.bytes, sizeof(out_root->bytes));
  }
  // Not armed here; the caller arms last (ucb_stage_arm).
  *out_code_address = ucb_code_address;
  return UPLOAD_OK;
}

secbool ucb_stage_arm(const flash_area_t *staging_area, uint32_t code_address) {
  // Point of no return for the bootloader swap.
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
  const boot_header_auth_t *installed = boot_header_auth_get(BOOTLOADER_START);
  if (installed == NULL) {
    return secfalse;
  }
  const uint32_t header_size = installed->header_size;
  if (header_size == 0 || header_size > IMAGE_CHUNK_SIZE) {
    return secfalse;
  }

  // Verbatim copy; the authenticated part stays bit for bit.
  uint8_t *staged = (uint8_t *)chunk_buffer;
  memcpy(staged, (const void *)(uintptr_t)BOOTLOADER_START, header_size);

  boot_header_auth_t *hdr =
      (boot_header_auth_t *)boot_header_auth_get((uintptr_t)staged);
  if (hdr == NULL) {
    return secfalse;
  }
  boot_header_unauth_t *unauth =
      (boot_header_unauth_t *)(uintptr_t)boot_header_unauth_get(hdr);
  if (unauth == NULL) {
    return secfalse;
  }
  if (unauth->firmware_type == FW_VARIANT_SEC_NONE) {
    return sectrue;  // already the canonical unprovisioned value
  }
  // INVALID is normalised too: the empty-device auto-confirm requires a
  // positive NONE.
  unauth->firmware_type = FW_VARIANT_SEC_NONE;

  if (sectrue != ucb_stage_write_header(staged, header_size)) {
    return secfalse;
  }

  // No iface: boot path, nobody to report to.
  uint32_t code_address = 0;
  if (UPLOAD_OK != ucb_stage_verify(&STAGING_AREA, /*header_only=*/true, NULL,
                                    NULL, &code_address)) {
    return secfalse;
  }
  return ucb_stage_arm(&STAGING_AREA, code_address);
}
#endif  // PQ_SECURE_BOOT

#endif  // USE_BOOT_UCB
