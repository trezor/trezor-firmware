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

// PQ secure boot only supports lockable-bootloader models: unofficial
// (custom / unknown-variant) firmware is permitted ONLY behind an unlockable
// bootloader, so a PQ build without LOCKABLE_BOOTLOADER would have no safe gate
// for it. Enforce the invariant at compile time and assume it below.
#ifndef LOCKABLE_BOOTLOADER
#error "PQ_SECURE_BOOT requires LOCKABLE_BOOTLOADER"
#endif

#include <sec/boot_header.h>
#include <sec/image_hash_conf.h>
#include <sys/bootargs.h>
#include <sys/bootutils.h>
#include <sys/flash.h>
#include <sys/flash_utils.h>
#include <sys/systick.h>

#include <sec/secret.h>  // secret_bootloader_locked() -- always present under PQ
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

// Target OTA transport block size in bytes. The actual block is the largest
// WHOLE number of smart-hashing HASH chunks that fits this (T = n * chunk_size,
// n = target / chunk_size), capped by the staging buffer (IMAGE_CHUNK_SIZE) and
// floored to cover the header prefetch (FW_MANIFEST_REGION). Expressing the
// lever in bytes (not a chunk count) keeps the transport block ~constant
// regardless of the hash chunk size, which is what actually matters (RAM,
// round-trips, early- reject granularity are all byte-denominated). Decouples
// the transport/reject/ round-trip granularity (the block) from the hash chunk
// (the commitment): one inline intermediate is sent per block, so a larger
// target => fewer intermediates
// + round-trips but coarser early-reject. See fwt_on_chunk / fwt_on_headers.
#define FW_TRANSPORT_BLOCK_TARGET (64 * 1024)

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
                                       protob_io_t *iface,
                                       uint32_t image_offset,
                                       const uint8_t *data, size_t len,
                                       const uint8_t *prev_hash) {
  (void)base;
  (void)iface;
  (void)image_offset;
  (void)data;
  (void)len;
  (void)prev_hash;
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

// Firmware-update rejection exit: send the wire Failure AND draw the fail
// screen, then return WF_ERROR. The bootloader's WF_ERROR path (main.c) only
// delays ~10s and reboots -- it does NOT draw anything -- so a workflow MUST
// render its own error UI first (as the phase-2 upload engine does via
// ui->fail); otherwise the current screen just sits frozen through the delay.
// Use this for every validation reject (both phases) so the user sees a failure
// instead of a freeze.
static workflow_result_t fw_begin_fail(protob_io_t *iface,
                                       const char *message) {
  send_msg_failure(iface, FailureType_Failure_ProcessError, message);
  ui_screen_fail();
  return WF_ERROR;
}

workflow_result_t workflow_firmware_update_pq(protob_io_t *iface) {
  // --- Preamble: boot header (reuse the big chunk_buffer as scratch) + the
  //     firmware manifest ("firmware directory") blob. ---
  // Receive buffer for the manifest region (manifest + firmware Merkle proof)
  // -- the same object phase 2 stores in fwt_upload_handler_t.manifest_buf, so
  // it is bounded by the canonical FW_MANIFEST_REGION, not an ad-hoc size.
  static uint8_t module_headers[FW_MANIFEST_REGION];
  uint8_t *bh_buf = (uint8_t *)chunk_buffer;
  size_t bh_len = 0;
  size_t mh_len = 0;
  // Defense-in-depth: this static buffer persists across retries within one
  // boot, so zero it before each receive. Consumers are already length-bounded
  // (mh_len) and cryptographically authenticated (firmware_root), so this only
  // guarantees any stale attacker bytes from a prior call read back as zero.
  memset(module_headers, 0, sizeof(module_headers));
  FirmwareBegin msg = {0};
  if (sectrue != recv_msg_firmware_begin(iface, &msg, bh_buf, IMAGE_CHUNK_SIZE,
                                         &bh_len, module_headers,
                                         sizeof(module_headers), &mh_len)) {
    ui_screen_fail();  // recv already failed (no wire Failure to send); see
                       // main.c
    return WF_ERROR;
  }

  // --- Validate the new boot header (structure + model). ---
  //     boot_header_auth_get() also enforces hw_model/hw_revision, so a
  //     model mismatch is already rejected here as "Invalid boot header".
  const boot_header_auth_t *hdr =
      boot_header_auth_get((uint32_t)(uintptr_t)bh_buf);
  if (hdr == NULL || hdr->header_size > bh_len) {
    return fw_begin_fail(iface, "Invalid boot header");
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
    return fw_begin_fail(iface, "Firmware downgrade protection");
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
    return fw_begin_fail(
        iface, "Bootloader code changed; full bootloader not supplied");
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
    // malformed: too short for the fixed header, or entries run past the blob
    return fw_begin_fail(iface, "Invalid firmware manifest");
  }
  size_t manifest_len = firmware_manifest_size(manifest);
  const merkle_proof_node_t *fw_proof = NULL;
  size_t fw_proof_count = 0;
  if (sectrue != firmware_manifest_read_proof(manifest, mh_len, &fw_proof,
                                              &fw_proof_count)) {
    // malformed proof region (too many nodes, or runs past the blob)
    return fw_begin_fail(iface, "Invalid firmware manifest proof");
  }
  if (sectrue != firmware_manifest_authentic(manifest, manifest_len, fw_proof,
                                             fw_proof_count, &firmware_root)) {
    // structurally valid, but the variant leaf does not fold to firmware_root
    return fw_begin_fail(iface, "Firmware manifest not authentic");
  }

  // --- Validate the module layout NOW, before confirming + rebooting. ---
  //     The same check runs in phase 2 (fwt_on_headers), but doing it here
  //     means a malformed / hostile manifest (notably a CUSTOM variant's
  //     unauthenticated app size, which folds fine but could run past the
  //     firmware area) is rejected before the user is asked to confirm and
  //     before the boot header is staged + the device reboots. The SAME shared
  //     check also runs in phase 2 and at every boot (firmware_verify_tree).
  //     ---
  if (sectrue != firmware_manifest_layout_valid(manifest, FIRMWARE_MAXSIZE)) {
    return fw_begin_fail(iface, "Invalid firmware manifest");
  }

  // --- Resolve the (authenticated) variant -> firmware_type. ---
  uint32_t variant = manifest->firmware_variant;

  // Custom firmware is the authenticated FW_VARIANT_CUSTOM slot: its manifest
  // leaf was founder-signed with the kernel+coreapp code_hash zeroed (see
  // firmware_manifest_authentic above), so the variant field is authenticated
  // and the app is founder-unbound (integrity-only). A custom install runs
  // unprivileged, is storage-isolated (firmware_type == the variant feeds the
  // storage salt), and is allowed ONLY on an UNLOCKED bootloader. FIH: gate on
  // the POSITIVE is_official check -- anything not positively official (custom
  // / none / unknown) requires an unlocked bootloader.
  secbool is_custom = firmware_type_is_custom((uint8_t)variant);
  if (firmware_type_is_official((uint8_t)variant) != sectrue) {
    // Unofficial firmware is allowed only on an UNLOCKED bootloader (guaranteed
    // lockable under PQ -- see the LOCKABLE_BOOTLOADER static check above).
    if (secret_bootloader_locked() != secfalse) {
      return fw_begin_fail(
          iface, "Unlock the bootloader to install unofficial firmware");
    }
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
  //     the UCB hash covers it so it survives install. The firmware Merkle
  //     proof is NOT written here -- it rides in the firmware image's manifest
  //     region (installed in phase 2), so this write-protected header carries
  //     only the storage-domain identity. ---
  boot_header_unauth_t *unauth =
      (boot_header_unauth_t *)(uintptr_t)boot_header_unauth_get(hdr);
  if (unauth == NULL) {
    return fw_begin_fail(iface, "Invalid boot header");
  }
  unauth->firmware_type = firmware_type;

  uint32_t header_size = hdr->header_size;
  if (sectrue != ucb_stage_write_header(bh_buf, header_size)) {
    return fw_begin_fail(iface, "Staging failed");
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
      ui_screen_fail();  // ucb_stage_commit sent its own wire Failure
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
  // chunks). Its trusted entries + chunk_size drive the streaming per-chunk
  // verification.
  uint8_t manifest_buf[FW_MANIFEST_REGION];
  const firmware_manifest_t *manifest;
  // Smart-hashing verify cursor (variant A, forward). Each module streams as
  // its own segment in transport blocks of block_size (a whole number of hash
  // chunks); each block's FirmwareUpload carries ONE inline H_prev (its
  // trailing chunk's; the module's last block derives the seed), from which the
  // device reverse-folds the block to verify -- so no hash blob is buffered,
  // the cursor just tracks where in the manifest the next arriving block
  // belongs.
  size_t cur_module;   // module currently being verified
  uint32_t cur_chunk;  // next chunk index (within cur_module) to verify
  uint8_t
      expected[IMAGE_HASH_DIGEST_LENGTH];  // running hash (starts at code_hash)
} fwt_upload_handler_t;

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
  // embedded in the streamed image's manifest region (right after the
  // manifest); fold the variant leaf through it to firmware_root. Its
  // (now-trusted) entries then drive the per-module verification as the modules
  // stream in.
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
  if (sectrue !=
          firmware_manifest_read_proof(manifest, len, &proof, &proof_count) ||
      sectrue != firmware_manifest_authentic(manifest, manifest_len, proof,
                                             proof_count, &root)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid firmware manifest");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
  }

  // Keep the authenticated manifest and arm the streaming per-chunk verify.
  memcpy(h->manifest_buf, buf, manifest_len);
  h->manifest = (const firmware_manifest_t *)h->manifest_buf;

  // Validate the module layout (same shared check as phase 1 and boot; re-run
  // here as defense-in-depth on the streamed manifest, before any erase/write).
  // Bounds the CUSTOM variant's unauthenticated app size to the firmware area +
  // chunk alignment. See firmware_manifest_layout_valid.
  if (sectrue != firmware_manifest_layout_valid(h->manifest, base->max_size)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid firmware manifest");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER;
  }
  // Transport sizing (streaming only, so NOT part of the shared layout check).
  // The per-module HASH chunk size `cs` is the commitment/padding granularity;
  // it must be FLASH_BLOCK_SIZE-aligned (write granularity) and fit the staging
  // buffer. chunk_size is PER MODULE, but the transport uses a SINGLE block
  // size, so for now every module must share one chunk_size -- reject a
  // mixed-size manifest (per-module transport cadence is a future addition).
  const uint32_t cs = h->manifest->entries[0].chunk_size;
  if (cs == 0 || cs > IMAGE_CHUNK_SIZE || (cs % FLASH_BLOCK_SIZE) != 0) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid firmware manifest");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER;
  }
  for (size_t i = 1; i < h->manifest->module_count; i++) {
    if (h->manifest->entries[i].chunk_size != cs) {
      send_msg_failure(iface, FailureType_Failure_ProcessError,
                       "Mixed module chunk sizes not supported");
      return UPLOAD_ERR_INVALID_IMAGE_HEADER;
    }
  }
  // The TRANSPORT block is the largest WHOLE number of hash chunks that fits
  // the byte target FW_TRANSPORT_BLOCK_TARGET, capped by the staging buffer and
  // at least the header prefetch (FW_MANIFEST_REGION == the engine's
  // init_chunk_size, which block_size must cover). This decouples the
  // download/reject/round-trip granularity (the block) from the hash chunk
  // `cs`: the host sends ONE inline intermediate per block (its trailing
  // chunk's H_prev; the module's last block derives the seed) and the device
  // reverse-folds the block's chunks to verify, so wire intermediates +
  // round-trips drop ~(target/cs)-fold while the commitment stays at the small
  // hash chunk cs.
  const uint32_t max_chunks =
      IMAGE_CHUNK_SIZE / cs;  // >= 1 (cs <= IMAGE_CHUNK_SIZE)
  uint32_t block_chunks =
      FW_TRANSPORT_BLOCK_TARGET / cs;  // whole chunks per target
  if (block_chunks < 1) block_chunks = 1;
  if (block_chunks > max_chunks) block_chunks = max_chunks;
  while (block_chunks * cs < FW_MANIFEST_REGION && block_chunks < max_chunks) {
    block_chunks++;  // ensure the block covers the header prefetch
  }
  base->block_size = block_chunks * cs;
  // Inline per-chunk verification relies on the per-module segment plan (header
  // segment + one per module), so the engine requests every chunk at its
  // module-relative offset (block k == chunk k). More modules than the plan can
  // hold would fall back to flat streaming, which cannot deliver chunk-aligned
  // hashes -- reject explicitly rather than fail cryptically per chunk. (This
  // is a streaming-capacity limit, hence not part of the shared layout check.)
  if ((size_t)h->manifest->module_count + 1 > IMAGE_UPLOAD_MAX_SEGMENTS) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Too many firmware modules");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER;
  }
  // Init the per-chunk cursor at module 0 (expected = its code_hash).
  h->cur_module = 0;
  h->cur_chunk = 0;
  memcpy(h->expected, h->manifest->entries[0].code_hash.bytes,
         sizeof(h->expected));

  // Pre-confirmed in phase 1 -> auto-accept.
  ui_screen_install_start(iface->wire->wireless);
  return UPLOAD_OK;
}

// Verify THIS transport block against the smart-hashing chain, BEFORE it is
// written to flash. A block carries m = ceil(len/cs) HASH chunks (cs = this
// module's chunk_size); all are cs bytes except a module's final chunk, which
// may be partial (modules are not padded to a whole chunk). Blocks arrive in
// strict module/chunk order, tracked by the cursor (cur_module, cur_chunk,
// `expected` = the running chain value the block's first chunk must fold to;
// starts at the module's code_hash).
//
// The host sends ONE inline intermediate per block: `prev_hash` = the value
// AFTER the block (the trailing chunk's H_prev). For the module's LAST block
// (which reaches the innermost chunk) that value is the derived seed
// H(0x01||size), so no prev_hash is sent. From it the device reconstructs the
// block's starting expected by folding the block's chunks LAST->FIRST
// (E = step(E, C_j) for j = m-1..0), then checks E == `expected`. A single
// check verifies all m chunks; `expected` then advances to the sent value for
// the next block. Anchored at both ends (code_hash at the first block, seed at
// the last; each sent intermediate is re-verified by the next block's fold), so
// a forged intermediate can't pass without a hash collision. Rejects at block
// granularity; the whole-tree verify in on_finish is the authoritative
// backstop.
static upload_status_t fwt_on_chunk(image_upload_handler_t *base,
                                    protob_io_t *iface, uint32_t image_offset,
                                    const uint8_t *data, size_t len,
                                    const uint8_t *prev_hash) {
  fwt_upload_handler_t *h = (fwt_upload_handler_t *)base;
  const firmware_manifest_t *m = h->manifest;

  // The manifest/header region [0, entries[0].addr) is authenticated by the
  // leaf fold in on_headers, not chain-verified. It is segment 0 (a single
  // block at offset 0), so let it through untouched.
  if (image_offset < m->entries[0].addr) {
    return UPLOAD_OK;
  }

  // Every remaining block is one or more module chunks. It must land exactly
  // where the cursor expects (the engine drives strict segment/chunk order) and
  // be a whole number of chunks within the current module; anything else is a
  // protocol/stream error -> fail closed.
  if (h->cur_module >= m->module_count) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "vtree: unexpected chunk");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
  }
  const firmware_manifest_entry_t *e = &m->entries[h->cur_module];
  const uint32_t cs = e->chunk_size;  // != 0 (validated in on_headers)
  const uint32_t n =
      (e->size + cs - 1) / cs;             // chunk count (last may be partial)
  const uint32_t off = h->cur_chunk * cs;  // module-relative block start
  const uint32_t remaining =
      e->size - off;  // bytes left (cur_chunk < n => > 0)
  // The block must land where the cursor expects and stay within the module. It
  // is whole hash chunks EXCEPT the block that reaches the module end, whose
  // last chunk may be partial (size % cs != 0, since modules are no longer
  // padded to a whole chunk). So a non-tail block must be a whole number of
  // chunks; the tail block may be any length up to `remaining`.
  const bool tail =
      (len == remaining);  // block reaches the module's last chunk
  if (image_offset != e->addr + off || len == 0 || len > remaining ||
      (!tail && (len % cs) != 0)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "vtree: unexpected chunk");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
  }
  const uint32_t mchunks = (len + cs - 1) / cs;  // chunks in this block (ceil)

  // E_end = the chain value AFTER this block. The tail block reaches the
  // module's innermost chunk, so E_end is the derived seed (binds the module
  // length); otherwise the host sends it inline as prev_hash (the trailing
  // chunk H_prev).
  uint8_t e_end[IMAGE_HASH_DIGEST_LENGTH];
  if (tail) {
    firmware_module_chain_seed(e->size, e_end);
  } else {
    if (prev_hash == NULL) {
      send_msg_failure(iface, FailureType_Failure_ProcessError,
                       "vtree: missing chunk hash");
      return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
    }
    memcpy(e_end, prev_hash, sizeof(e_end));
  }
  // Reconstruct the block's starting expected: fold its chunks LAST->FIRST from
  // E_end (chain_step is in-place safe). Each chunk is cs bytes except the
  // module's final chunk, which may be partial (clen = the module tail) --
  // mirrors firmware_module_code_hash.
  uint8_t chain[IMAGE_HASH_DIGEST_LENGTH];
  memcpy(chain, e_end, sizeof(chain));
  for (uint32_t j = mchunks; j-- > 0;) {
    const uint32_t coff = off + j * cs;  // module-relative chunk offset
    const uint32_t clen = (e->size - coff < cs) ? (e->size - coff) : cs;
    firmware_module_chain_step(chain, data + (size_t)j * cs, clen, chain);
  }
  if (memcmp(chain, h->expected, sizeof(chain)) != 0) {
    // Retryable (no message): a transient transport corruption of the block
    // then recovers; a genuinely bad block fails terminally once retries are
    // spent.
    return UPLOAD_ERR_INVALID_CHUNK_HASH;
  }

  // Block verified: advance the running expected to E_end and the cursor by
  // mchunks; at the module end move to the next module (expected = its
  // code_hash).
  memcpy(h->expected, e_end, sizeof(h->expected));
  h->cur_chunk += mchunks;
  if (h->cur_chunk >= n) {
    h->cur_module++;
    h->cur_chunk = 0;
    if (h->cur_module < m->module_count) {
      memcpy(h->expected, m->entries[h->cur_module].code_hash.bytes,
             sizeof(h->expected));
    }
  }
  return UPLOAD_OK;
}

// Plan the segments (called by the engine right after fwt_on_headers): segment
// 0 is the manifest/header region [0, FW_MANIFEST_REGION) -- streamed + written
// like any block but NOT chain-verified (on_chunk finds no module inside it; it
// is authenticated by the leaf fold). Its length equals init_chunk_size, so the
// engine's header prefetch fills it exactly. Segments 1.. are one per module,
// each streamed from its own addr in transport blocks of block_size (a whole
// number of hash chunks), so every block starts on a chunk boundary -- what the
// per-block reverse-fold verify in fwt_on_chunk needs. Returns 0 (=> a single
// whole-image segment, flat) if the count would exceed `max`. The engine calls
// this only after fwt_on_headers succeeds, which has already validated every
// entry's addr/size (ascending, non-overlapping, chunk-aligned, within the
// firmware area) -- so the ranges below are safe even for a custom manifest
// whose app size is not founder-authenticated.
static size_t fwt_plan_segments(image_upload_handler_t *base,
                                uint32_t image_size, image_segment_t *out,
                                size_t max) {
  (void)image_size;
  const fwt_upload_handler_t *h = (const fwt_upload_handler_t *)base;
  const firmware_manifest_t *m = h->manifest;
  size_t n = (size_t)m->module_count + 1;  // +1 for the header region
  if (m->module_count == 0 || n > max) {
    return 0;
  }
  out[0].offset = 0;
  out[0].length = FW_MANIFEST_REGION;
  for (size_t i = 0; i < m->module_count; i++) {
    out[i + 1].offset = m->entries[i].addr;
    out[i + 1].length = m->entries[i].size;
  }
  return n;
}

static upload_status_t fwt_on_finish(image_upload_handler_t *base,
                                     protob_io_t *iface) {
  fwt_upload_handler_t *h = (fwt_upload_handler_t *)base;
  // Every module chunk was chain-verified inline as it streamed; the cursor
  // must have consumed exactly all modules. A short stream (fewer chunks than
  // the manifest declares) leaves it behind -> fail closed before the
  // whole-tree verify.
  if (h->cur_module != h->manifest->module_count) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "vtree: incomplete firmware stream");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
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
    return fw_begin_fail(iface,
                         "Firmware update must begin with FirmwareBegin");
  }

  FirmwareErase msg;
  if (sectrue != recv_msg_firmware_erase(iface, &msg)) {
    ui_screen_fail();  // recv already failed (no wire Failure to send)
    return WF_ERROR;
  }

  // static: carries the copied manifest (FW_MANIFEST_REGION) and the per-chunk
  // verify cursor; keeps it off the bootloader stack. The smart-hashing
  // intermediate hashes are no longer buffered here -- each arrives inline on
  // its chunk's FirmwareUpload (see fwt_on_chunk).
  //
  // Defense-in-depth: this static singleton persists across retries within one
  // boot, so zero the WHOLE struct up front -- manifest_buf and the verify
  // cursor -- clearing any stale (attacker-supplied) bytes from a prior call.
  // Every consumer is already length-bounded and cryptographically
  // authenticated (firmware_root / code_hash chain), so this is
  // belt-and-suspenders; on_headers re-initializes the mutable state.
  static fwt_upload_handler_t handler;
  memset(&handler, 0, sizeof(handler));
  handler.base = (image_upload_handler_t){
      .target_area = &FIRMWARE_AREA,
      .max_size = FIRMWARE_MAXSIZE,
      .success_result = WF_OK_FIRMWARE_INSTALLED,
      .ui = &fwt_upload_ui,
      .on_headers = fwt_on_headers,
      .on_chunk = fwt_on_chunk,
      .on_finish = fwt_on_finish,
      .plan_segments = fwt_plan_segments,
      // The header prefetch only needs the manifest region (manifest + proof),
      // a fixed size -- so don't over-prefetch into the first module (keeps it
      // skippable later). block_size is set from chunk_size in fwt_on_headers.
      .init_chunk_size = FW_MANIFEST_REGION,
  };

  return run_image_upload(iface, &handler.base,
                          msg.has_length ? msg.length : 0);
}

#endif  // PQ_SECURE_BOOT
