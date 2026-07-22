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

#ifdef PQ_SECURE_BOOT

#include <sec/boot_header.h>
#include <sys/bootargs.h>
#include <sys/bootutils.h>
#include <sys/flash.h>
#include <sys/flash_utils.h>
#include <sys/systick.h>

#if defined(USE_STORAGE_HWKEY) || defined(LOCKABLE_BOOTLOADER)
#include <sec/secret.h>
#endif
#ifdef USE_BACKUP_RAM
#include <sec/backup_ram.h>
#endif

#include <sys/systick.h>

#include "bootui.h"
#include "fw_check.h"
#include "protob/protob.h"
#include "version_check.h"
#include "wf_image_upload.h"
#include "wf_ucb_stage.h"
#include "workflow.h"

// Buffer for the received firmware manifest ("firmware directory") in the
// FirmwareBegin preamble (generous headroom).
#define FW_TREE_MODULE_HEADERS_MAX 2048

// --- Phase-1 new-bootloader-code streaming (full bootloader update) ----------
// When FirmwareBegin carries a new bootloader code_length, the code is
// streamed into the staging area right after the already-staged boot header
// (engine target_offset = header_size). The header arrived (with the resolved
// firmware_type) in the message and was written first; the whole staged
// [header|code] is then verified + handed to the boardloader in on_finish.

static upload_status_t blcode_on_headers(image_upload_handler_t *base,
                                         protob_io_t *iface, const uint8_t *buf,
                                         size_t len) {
  (void)base;
  (void)iface;
  (void)buf;
  (void)len;
  // Raw bootloader code (no header at the start); already confirmed in the
  // preamble, so nothing to validate here.
  return UPLOAD_OK;
}

static upload_status_t blcode_on_chunk(image_upload_handler_t *base,
                                       protob_io_t *iface, uint32_t block_idx,
                                       const uint8_t *data, size_t len) {
  (void)base;
  (void)iface;
  (void)block_idx;
  (void)data;
  (void)len;
  // Integrity is verified as a whole (Merkle root + signature) in on_finish.
  return UPLOAD_OK;
}

static upload_status_t blcode_on_finish(image_upload_handler_t *base,
                                        protob_io_t *iface) {
  // The new bootloader [header|code] is fully staged; verify it and hand it to
  // the boardloader via the UCB (code_address = staged header + header_size).
  return ucb_stage_commit(base->target_area, /*header_only=*/false, iface);
}

static void blcode_ui_progress(int permille, bool wireless) {
  ui_screen_install_progress_upload(permille, wireless);
}

static void blcode_ui_success(bool wireless) {
  ui_screen_install_progress_upload(1000, wireless);
}

static void blcode_ui_fail(upload_status_t status) {
  (void)status;
  ui_screen_fail();
}

static const image_upload_ui_t blcode_upload_ui = {
    .progress = blcode_ui_progress,
    .success = blcode_ui_success,
    .fail = blcode_ui_fail,
};

workflow_result_t workflow_firmware_update_pq(protob_io_t *iface) {
  // --- Preamble: boot header (reuse the big chunk_buffer as scratch) + the
  //     firmware manifest ("firmware directory") blob. ---
  static uint8_t module_headers[FW_TREE_MODULE_HEADERS_MAX];
  uint8_t *bh_buf = (uint8_t *)chunk_buffer;
  size_t bh_len = 0;
  size_t mh_len = 0;
  FirmwareBegin msg = {0};
  if (sectrue != recv_msg_firmware_begin(iface, &msg, bh_buf, IMAGE_CHUNK_SIZE,
                                         &bh_len, module_headers,
                                         sizeof(module_headers), &mh_len)) {
    return WF_ERROR;
  }

  // --- Validate the new boot header (structure + model). ---
  const boot_header_auth_t *hdr =
      boot_header_auth_get((uint32_t)(uintptr_t)bh_buf);
  if (hdr == NULL || hdr->header_size > bh_len) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid boot header");
    return WF_ERROR;
  }
  if (hdr->hw_model != HW_MODEL) {
    send_msg_failure(iface, FailureType_Failure_ProcessError, "Wrong model");
    return WF_ERROR;
  }

  // --- Anti-rollback (reject a downgrade UP FRONT, before confirming). ---
  //     The tree couples the bootloader + firmware into ONE signed unit: the
  //     boot header carries firmware_root, so the header's single-byte
  //     monotonic_version is the anti-rollback axis for the whole coupled
  //     release. (The manifest firmware_version is authenticated but
  //     DISPLAY-ONLY; the monotonic byte is what a security release bumps.)
  //     This is the SAME floor enforced at boot (check_bootloader_min_version)
  //     and again at staging (ucb_stage_commit) and by the boardloader;
  //     checking it here just avoids asking the user to confirm an install that
  //     would be rejected anyway.
  if (sectrue != check_bootloader_min_version(hdr->monotonic_version)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Firmware downgrade protection");
    return WF_ERROR;
  }

  // --- The DEVICE decides whether the bootloader CODE must be streamed. ---
  //     Compute the boot header's Merkle root over the CURRENT on-flash
  //     bootloader code and check the signature. If it passes, the new header
  //     already signs the current code (unchanged) -> header-only, stream
  //     nothing. If it fails, the code differs and must be streamed (full
  //     update); the new code's signature -- and hence trust in firmware_root
  //     -- is then verified after staging (ucb_stage_commit / boardloader), so
  //     a bad header/root is still rejected before anything is installed. Until
  //     then the confirm + module-header authentication below run against a
  //     not-yet-signature-verified root; that is safe (nothing is installed on
  //     rejection). The host always makes the code available (code_length set);
  //     we request it only when we actually need it, so the client no longer
  //     guesses with a --full-bootloader flag.
  merkle_proof_node_t root;
  boot_header_calc_merkle_root(hdr, BOOTLOADER_START + hdr->header_size, &root);
  const bool code_conforms =
      (sectrue == boot_header_check_signature(hdr, &root));
  const bool have_code = msg.has_code_length && msg.code_length > 0;
  const bool full_bootloader = !code_conforms;

  if (full_bootloader && !have_code) {
    // The bootloader code must change, but the host supplied only a header.
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Bootloader code changed; full bootloader not supplied");
    return WF_ERROR;
  }

  // --- Authenticate the firmware manifest against the new firmware_root. ---
  //     The preamble blob is the firmware image's manifest region:
  //     [manifest || firmware_manifest_proof_t] -- the manifest ("firmware
  //     directory") followed by the per-variant Merkle proof (co-path variant
  //     leaf -> firmware_root), the exact bytes baked at the firmware image
  //     start. Authenticate header-only (no bodies yet): the variant leaf,
  //     folded through the proof, must equal firmware_root. A single-variant
  //     firmware has an empty proof (variant leaf == firmware_root).
  merkle_proof_node_t firmware_root;
  memcpy(firmware_root.bytes, hdr->firmware_root.bytes,
         sizeof(firmware_root.bytes));
  const firmware_manifest_t *manifest =
      (const firmware_manifest_t *)module_headers;
  if (mh_len < sizeof(firmware_manifest_t) ||
      firmware_manifest_size(manifest) > mh_len) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid firmware manifest");
    return WF_ERROR;
  }
  size_t manifest_len = firmware_manifest_size(manifest);
  const merkle_proof_node_t *fw_proof = NULL;
  size_t fw_proof_count = 0;
  if (sectrue != firmware_manifest_read_proof(manifest, mh_len, &fw_proof,
                                              &fw_proof_count) ||
      sectrue != firmware_manifest_authentic(manifest, manifest_len, fw_proof,
                                             fw_proof_count, &firmware_root)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid firmware manifest");
    return WF_ERROR;
  }

  // --- Resolve the (authenticated) variant -> firmware_type. ---
  uint32_t variant = manifest->firmware_variant;

  // Custom firmware is the authenticated FW_VARIANT_CUSTOM slot: its manifest
  // leaf was founder-signed with the kernel+coreapp code_hash zeroed (see
  // firmware_manifest_authentic above), so the variant field is authenticated
  // and the app is founder-unbound (integrity-only). A custom install runs
  // unprivileged, is storage-isolated (firmware_type == the variant feeds the
  // storage salt), and is allowed ONLY on an UNLOCKED bootloader. FIH: gate on
  // the POSITIVE is_official check -- anything not positively official (custom /
  // none / unknown) requires an unlocked bootloader.
  secbool is_custom = firmware_type_is_custom((uint8_t)variant);
  if (firmware_type_is_official((uint8_t)variant) != sectrue) {
#ifdef LOCKABLE_BOOTLOADER
    if (secret_bootloader_locked() != secfalse) {
      send_msg_failure(iface, FailureType_Failure_ProcessError,
                       "Unlock the bootloader to install unofficial firmware");
      return WF_ERROR;
    }
#else
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Unofficial firmware not supported");
    return WF_ERROR;
#endif
  }
  uint8_t firmware_type = firmware_type_compose(variant);

  // FIH: default to the SAFE behaviour -- WIPE (keep_seed secfalse) and treat
  // the device as NOT empty (require confirmation). Each flips to the
  // permissive value only when its condition is POSITIVELY met, so a
  // skipped/glitched check leaves the safe path (confirm shown, seed wiped),
  // never a silent install or a seed kept across storage domains.
  secbool keep_seed = secfalse;
  secbool empty_device = secfalse;
  const boot_header_auth_t *cur = boot_header_auth_get(BOOTLOADER_START);
  const boot_header_unauth_t *cur_unauth =
      (cur != NULL) ? boot_header_unauth_get(cur) : NULL;
  if (cur == NULL || cur_unauth == NULL || cur_unauth->firmware_type == 0) {
    // Positively unprovisioned (matches fw_check's header_present == secfalse).
    empty_device = sectrue;
  } else if (cur_unauth->firmware_type == firmware_type) {
    // Same storage domain: BOTH the variant AND the official/custom flag match
    // (the salt keys off the full firmware_type). An official<->custom switch
    // at the same variant changes firmware_type -> different salt -> wipe.
    keep_seed = sectrue;
  }

  // Defense-in-depth for the official<->custom boundary: crossing it MUST wipe
  // the seed, so switching to unofficial firmware (and back) can never recover
  // a wallet provisioned under the other privilege level. This is an
  // INDEPENDENT gate -- on a real transition the firmware_type equality above
  // already left keep_seed false, but re-deriving the custom flag from the
  // current header and forcing a wipe on mismatch means a single glitched
  // equality cannot preserve the seed across the boundary. (Safe direction: any
  // doubt -> wipe.)
  if (cur_unauth != NULL &&
      firmware_type_is_custom(cur_unauth->firmware_type) != is_custom) {
    keep_seed = secfalse;
  }

  // --- Confirm -- UNLESS the device is (positively) empty. Like legacy, a
  // fresh
  //     install onto an empty device needs no consent (even though setup erases
  //     storage). A provisioned device always confirms; a variant
  //     (storage-domain) change passes !keep_seed so the single install-confirm
  //     screen shows the "SEED WILL BE ERASED!" warning, so the user is never
  //     surprised by losing their wallet. The confirm shows the firmware
  //     variant (vendor string) and the firmware version (from the
  //     authenticated manifest). TODO(pq_secure_boot): a dedicated tree-install
  //     confirm screen; reuse the bootloader one for now. ---
  // Vendor identity shown on the confirm: the variant name for an official
  // install, or the loud UNSAFE marker for a custom one. FIH: official only on
  // the POSITIVE is_official allow-list.
  size_t vendor_len = 0;
  const secbool install_official = firmware_type_is_official((uint8_t)variant);
  const char *vendor = tree_vendor_str(variant, install_official, &vendor_len);
  // Firmware version from the (authenticated) manifest, packed for format_ver.
  // This is the FIRMWARE version, not the staged bootloader's TRZQ version.
  const uint32_t fw_version = (uint32_t)manifest->firmware_version[0] |
                              ((uint32_t)manifest->firmware_version[1] << 8) |
                              ((uint32_t)manifest->firmware_version[2] << 16) |
                              ((uint32_t)manifest->firmware_version[3] << 24);
  if (sectrue != empty_device &&
      CONFIRM != ui_screen_install_confirm_bootloader(
                     fw_version, firmware_root.bytes, keep_seed,
                     /*is_newvendor=*/keep_seed == sectrue ? secfalse : sectrue,
                     vendor, vendor_len)) {
    send_user_abort(iface, "Firmware install cancelled");
    return WF_CANCELLED;
  }
  ui_screen_install_start(iface->wire->wireless);

  // --- Erase the seed only on a storage-domain (variant) change. ---
  if (sectrue != keep_seed) {
#ifdef USE_STORAGE_HWKEY
    secret_bhk_regenerate();
#endif
    ensure(erase_storage(NULL), NULL);
#ifdef USE_BACKUP_RAM
    ensure(backup_ram_erase_protected() * sectrue, NULL);
#endif
  }

  // --- Set the resolved firmware_type into the (unauth) header, then stage it.
  //     firmware_type is outside auth_size (does not affect the signature) and
  //     the UCB hash covers it so it survives install. The firmware Merkle proof
  //     is NOT written here -- it rides in the firmware image's manifest region
  //     (installed in phase 2), so this write-protected header carries only the
  //     storage-domain identity. ---
  boot_header_unauth_t *unauth =
      (boot_header_unauth_t *)(uintptr_t)boot_header_unauth_get(hdr);
  if (unauth == NULL) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid boot header");
    return WF_ERROR;
  }
  unauth->firmware_type = firmware_type;

  uint32_t header_size = hdr->header_size;
  if (sectrue != ucb_stage_write_header(bh_buf, header_size)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError, "Staging failed");
    return WF_ERROR;
  }

  if (full_bootloader) {
    // --- Stream the new bootloader code into the staging area right after the
    //     staged header, then verify the whole [header|code] + write the UCB
    //     (on_finish). NOTE: run_image_upload reuses chunk_buffer (== bh_buf),
    //     so the header/module data there must not be needed past this point --
    //     firmware_root is already copied out, the header is staged in flash.
    //     ---
    image_upload_handler_t handler = {
        .target_area = &STAGING_AREA,
        .target_offset = header_size,
        .max_size = BOOTLOADER_MAXSIZE,
        .success_result = WF_OK_BOOTLOADER_UPDATED,
        .ui = &blcode_upload_ui,
        .on_headers = blcode_on_headers,
        .on_chunk = blcode_on_chunk,
        .on_finish = blcode_on_finish,
    };
    workflow_result_t r = run_image_upload(iface, &handler, msg.code_length);
    if (r != WF_OK_BOOTLOADER_UPDATED) {
      // run_image_upload already showed the failure / abort screen.
      return r;
    }
    // run_image_upload already sent Success to the host.
  } else {
    // --- Header-only: reuse (a copy of) the current bootloader code and hand
    //     the staged header to the boardloader via the UCB. ---
    if (UPLOAD_OK !=
        ucb_stage_commit(&STAGING_AREA, /*header_only=*/true, iface)) {
      return WF_ERROR;
    }
    ui_screen_install_progress_upload(1000, iface->wire->wireless);
    // Tell the host phase 1 succeeded before we reboot (this path does not go
    // through run_image_upload, which is what sends Success otherwise); give
    // the transfer a moment to reach the host.
    send_msg_success(iface, NULL);
    systick_delay_ms(500);
  }

  // Reboot into the auto-update that installs the firmware modules (phase 2).
  // reboot_and_upgrade sets BOOT_COMMAND_INSTALL_UPGRADE atomically as part of
  // the reset (a plain reboot_device would overwrite it with
  // BOOT_COMMAND_REBOOT via its own bootargs_set), carrying firmware_root as
  // the pre-confirmed identity. Noreturn.
  reboot_and_upgrade(firmware_root.bytes);
}

// ---------------------------------------------------------------------------
// Phase 2: install the firmware modules into the firmware area.
//
// Runs in the freshly-booted bootloader (new boot header / firmware_root
// already installed by the boardloader), auto-continued via
// BOOT_COMMAND_INSTALL_UPGRADE. The whole [secmon | kernel+coreapp] image is
// streamed to the firmware area and then verified as a tree against the
// installed firmware_root. It was already confirmed (and keep-seed decided) in
// phase 1, so this installs without re-prompting. Authenticity is guaranteed by
// the final firmware_verify_tree: modules that do not reduce to the signed
// firmware_root are rejected.
// ---------------------------------------------------------------------------

typedef struct {
  image_upload_handler_t base;
  // The firmware manifest, authenticated against firmware_root in on_headers
  // and copied here (chunk_buffer, where it arrives, is reused for later
  // chunks). Its trusted entries drive the incremental per-module verification
  // below.
  uint8_t manifest_buf[FW_MANIFEST_REGION];
  const firmware_manifest_t *manifest;
  uintptr_t firmware_base;  // firmware region start (manifest addr base)
  size_t next_module;       // next directory entry to verify incrementally
} fwt_upload_handler_t;

// Verify every manifest module whose code is now fully on flash
// ([addr, addr+size) within [0, bytes_on_flash)) against its authenticated
// directory entry: H(code) == entry->code_hash. Advances next_module so each
// module is verified exactly once, the moment it lands -- early rejection
// instead of waiting for the whole image. entry->addr is the module code
// offset and entry->size its code size, so the module ends at addr + size.
static upload_status_t fwt_verify_ready_modules(fwt_upload_handler_t *h,
                                                protob_io_t *iface,
                                                uint32_t bytes_on_flash) {
  const firmware_manifest_t *m = h->manifest;
  while (h->next_module < m->module_count) {
    const firmware_manifest_entry_t *e = &m->entries[h->next_module];
    // Every module -- including a custom variant's kernel+coreapp -- carries a
    // real code_hash in the (authenticated) manifest, so each is verified
    // against it the moment its bytes land. For the custom app that hash is the
    // creator's (corruption check); the secmon's is founder-signed.
    uint32_t module_end = e->addr + e->size;
    if (module_end > bytes_on_flash) {
      break;  // not fully written yet
    }
    if (sectrue != firmware_verify_manifest_entry(e, h->firmware_base)) {
      send_msg_failure(iface, FailureType_Failure_ProcessError,
                       e->module_type == FW_MODULE_SECMON
                           ? "vtree: secmon verify failed (incremental)"
                           : "vtree: module verify failed (incremental)");
      return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
    }
    h->next_module++;
  }
  return UPLOAD_OK;
}

static upload_status_t fwt_on_headers(image_upload_handler_t *base,
                                      protob_io_t *iface, const uint8_t *buf,
                                      size_t len) {
  fwt_upload_handler_t *h = (fwt_upload_handler_t *)base;

  // The image begins with the firmware manifest ("firmware directory", TRZD) at
  // the firmware region start.
  const firmware_manifest_t *manifest = (const firmware_manifest_t *)buf;
  if (len < sizeof(firmware_manifest_t) ||
      manifest->magic != FW_MANIFEST_MAGIC) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid firmware image");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER;
  }
  size_t manifest_len = firmware_manifest_size(manifest);
  if (manifest_len > FW_MANIFEST_REGION || manifest_len > len) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid firmware manifest");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER;
  }

  // Authenticate the streamed manifest against the firmware_root in our
  // boardloader-verified boot header BEFORE writing anything -- the earliest
  // possible rejection of a wrong/corrupt manifest. The per-variant proof is
  // embedded in the streamed image's manifest region (right after the manifest);
  // fold the variant leaf through it to firmware_root. Its (now-trusted) entries
  // then drive the per-module verification as the modules stream in.
  const boot_header_auth_t *bl = boot_header_auth_get(BOOTLOADER_START);
  if (bl == NULL) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid boot header");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER;
  }
  merkle_proof_node_t root;
  memcpy(root.bytes, bl->firmware_root.bytes, sizeof(root.bytes));
  const merkle_proof_node_t *proof = NULL;
  size_t proof_count = 0;
  if (sectrue != firmware_manifest_read_proof(manifest, len, &proof,
                                              &proof_count) ||
      sectrue != firmware_manifest_authentic(manifest, manifest_len, proof,
                                             proof_count, &root)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid firmware manifest");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
  }

  // Keep the authenticated manifest and arm the incremental per-module verify.
  memcpy(h->manifest_buf, buf, manifest_len);
  h->manifest = (const firmware_manifest_t *)h->manifest_buf;
  h->firmware_base = (uintptr_t)flash_area_get_address(base->target_area, 0, 0);
  h->next_module = 0;

  // Pre-confirmed in phase 1 -> auto-accept.
  ui_screen_install_start(iface->wire->wireless);
  return UPLOAD_OK;
}

static upload_status_t fwt_on_chunk(image_upload_handler_t *base,
                                    protob_io_t *iface, uint32_t block_idx,
                                    const uint8_t *data, size_t len) {
  (void)data;
  (void)len;
  fwt_upload_handler_t *h = (fwt_upload_handler_t *)base;
  // On entry, blocks [0, block_idx) are already on flash (this block is written
  // after we return), i.e. block_idx * IMAGE_CHUNK_SIZE bytes. Verify every
  // module now fully present against its authenticated manifest entry -- fails
  // at the first bad module instead of after a full image write. The whole-tree
  // verify in on_finish remains the authoritative backstop.
  return fwt_verify_ready_modules(h, iface, block_idx * IMAGE_CHUNK_SIZE);
}

static upload_status_t fwt_on_finish(image_upload_handler_t *base,
                                     protob_io_t *iface) {
  fwt_upload_handler_t *h = (fwt_upload_handler_t *)base;
  // Verify any trailing module not yet covered incrementally (everything is on
  // flash now).
  upload_status_t s = fwt_verify_ready_modules(h, iface, UINT32_MAX);
  if (s != UPLOAD_OK) {
    return s;
  }
  // Authoritative whole-tree verify against the installed firmware_root
  // (manifest fold + per-module code integrity), independent of the
  // incremental checks -- the backstop.
  firmware_tree_info_t info = {0};
  if (sectrue != firmware_verify_tree(&info)) {
    // Granular breakdown (prototype diagnostic): re-run the per-module checks
    // the way firmware_verify_tree does, so the failure names the culprit -- a
    // module (secmon/kernel) vs the manifest fold/authenticity.
    const firmware_manifest_t *man =
        (const firmware_manifest_t *)(uintptr_t)FIRMWARE_START;
    for (size_t i = 0; man->magic == FW_MANIFEST_MAGIC && i < man->module_count;
         i++) {
      const firmware_manifest_entry_t *e = &man->entries[i];
      if (sectrue != firmware_verify_manifest_entry(e, FIRMWARE_START)) {
        send_msg_failure(iface, FailureType_Failure_ProcessError,
                         e->module_type == FW_MODULE_SECMON
                             ? "vtree: secmon module bad"
                             : "vtree: app/module bad");
        return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
      }
    }
    // Every module passes individually -> the manifest fold/authenticity (or
    // the installed firmware_root) is the mismatch.
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "vtree: fold/authenticity failed");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
  }
  // Update installed; clear the auto-continue command.
  bootargs_set(BOOT_COMMAND_NONE, NULL, 0);
  return UPLOAD_OK;
}

static void fwt_ui_progress(int permille, bool wireless) {
  ui_screen_install_progress_upload(permille, wireless);
}

static void fwt_ui_success(bool wireless) {
  ui_screen_install_progress_upload(1000, wireless);
  ui_screen_done(4, sectrue);
  ui_screen_done(3, secfalse);
  systick_delay_ms(1000);
  ui_screen_done(2, secfalse);
  systick_delay_ms(1000);
  ui_screen_done(1, secfalse);
  systick_delay_ms(1000);
}

static void fwt_ui_fail(upload_status_t status) {
  (void)status;
  ui_screen_fail();
}

static const image_upload_ui_t fwt_upload_ui = {
    .progress = fwt_ui_progress,
    .success = fwt_ui_success,
    .fail = fwt_ui_fail,
};

workflow_result_t workflow_firmware_update(protob_io_t *iface) {
  // Phase 2 only ever follows phase 1 (which armed INSTALL_UPGRADE and
  // installed the new firmware_root). Reject a bare install so a stray
  // FirmwareErase does not erase a valid firmware.
  if (bootargs_get_command() != BOOT_COMMAND_INSTALL_UPGRADE) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Firmware update must begin with FirmwareBegin");
    return WF_ERROR;
  }

  FirmwareErase msg;
  if (sectrue != recv_msg_firmware_erase(iface, &msg)) {
    return WF_ERROR;
  }

  // static: carries the copied manifest (FW_MANIFEST_REGION) + verify cursor;
  // keeps it off the bootloader stack. on_headers resets the mutable state.
  static fwt_upload_handler_t handler;
  handler.base = (image_upload_handler_t){
      .target_area = &FIRMWARE_AREA,
      .max_size = FIRMWARE_MAXSIZE,
      .success_result = WF_OK_FIRMWARE_INSTALLED,
      .ui = &fwt_upload_ui,
      .on_headers = fwt_on_headers,
      .on_chunk = fwt_on_chunk,
      .on_finish = fwt_on_finish,
  };

  return run_image_upload(iface, &handler.base,
                          msg.has_length ? msg.length : 0);
}

#endif  // PQ_SECURE_BOOT
