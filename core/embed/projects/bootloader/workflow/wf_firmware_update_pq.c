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

#ifdef PQ_SECURE_BOOT

// Unofficial firmware is gated on an unlocked bootloader, so PQ needs one.
#ifndef LOCKABLE_BOOTLOADER
#error "PQ_SECURE_BOOT requires LOCKABLE_BOOTLOADER"
#endif

#include <rtl/sizedefs.h>
#include <sec/boot_header.h>
#include <sec/image_hash_conf.h>
#include <sys/bootargs.h>
#include <sys/bootutils.h>
#include <sys/flash.h>
#include <sys/flash_utils.h>
#include <sys/systick.h>

#include <sec/secret.h>
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

#ifdef USE_SMP
#include "sha2.h"
#include "wf_nrf_ota.h"
#endif

// Target transport block size; the block is rounded to a whole number of
// hash chunks, capped by IMAGE_CHUNK_SIZE and floored to FW_MANIFEST_REGION.
// One inline intermediate hash is sent per block (see fwt_on_headers).
#define FW_TRANSPORT_BLOCK_TARGET (64 * 1024)

// The boot header is received into the upload engine's chunk_buffer.
#if BOOT_HEADER_MAXSIZE > IMAGE_CHUNK_SIZE
#error "IMAGE_CHUNK_SIZE too small to receive a boot header"
#endif

// Phase-1 stream of new bootloader code into the staging area, right after
// the staged boot header. Verified as a whole by ucb_stage_verify afterwards.

static upload_status_t blcode_on_headers(image_upload_handler_t *base,
                                         protob_io_t *iface, const uint8_t *buf,
                                         size_t len) {
  (void)base;
  (void)iface;
  (void)buf;
  (void)len;
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
  return UPLOAD_OK;
}

static upload_status_t blcode_on_finish(image_upload_handler_t *base,
                                        protob_io_t *iface) {
  (void)base;
  (void)iface;
  return UPLOAD_OK;
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

// Send the wire Failure and draw the fail screen; main.c's WF_ERROR path only
// delays and reboots, so every workflow reject must render its own UI.
static workflow_result_t fw_begin_fail(protob_io_t *iface,
                                       const char *message) {
  send_msg_failure(iface, FailureType_Failure_ProcessError, message);
  ui_screen_fail();
  return WF_ERROR;
}

// Phase-1 results returned by value: the preamble receives the header into
// chunk_buffer, which the streams below reuse, so no pointer may outlive it.
typedef struct {
  uint32_t header_size;     // staged header size (stream offset)
  secbool full_bootloader;  // the bootloader code must be streamed
  secbool keep_seed;        // secfalse: storage domain changes, caller erases
} fw_begin_staged_t;

// Every module must be FLASH_BLOCK_SIZE-aligned in addr and size, or the
// per-module segment write asserts mid-install. Lives here rather than in
// firmware_manifest_layout_valid because FLASH_BLOCK_SIZE is MCU-specific;
// called wherever layout_valid is. The CUSTOM variant's app size is not
// founder-authenticated, which is what makes this reachable.
static secbool fwt_manifest_block_aligned(const firmware_manifest_t *manifest) {
  for (size_t i = 0; i < manifest->module_count; i++) {
    const firmware_manifest_entry_t *e = &manifest->entries[i];
    if ((e->addr % FLASH_BLOCK_SIZE) != 0 ||
        (e->size % FLASH_BLOCK_SIZE) != 0) {
      return secfalse;
    }
  }
  return sectrue;
}

// Phase-1 preamble: receive FirmwareBegin, authenticate the boot header and
// the manifest, confirm with the user, stage the boot header. Nothing here is
// destructive. Any result other than WF_OK has already rendered its UI.
// `msg` and `nrf_arg` outlive this call and must not point into chunk_buffer.
static workflow_result_t fw_begin_preamble(protob_io_t *iface,
                                           FirmwareBegin *msg,
                                           firmware_begin_nrf_t *nrf_arg,
                                           fw_begin_staged_t *out) {
  // Manifest region (manifest + proof); same bound as
  // fwt_upload_handler_t.manifest_buf.
  static uint8_t module_headers[FW_MANIFEST_REGION];
  // Boot header scratch borrowed from the upload engine; valid only until
  // the caller starts streaming.
  uint8_t *bh_buf = (uint8_t *)chunk_buffer;
  size_t bh_len = 0;
  size_t mh_len = 0;
  // Host-claimed digest of the incoming bootloader code.
  uint8_t code_hash[IMAGE_HASH_DIGEST_LENGTH] = {0};
  size_t ch_len = 0;
  // The static buffer persists across retries within one boot.
  memset(module_headers, 0, sizeof(module_headers));
  if (sectrue !=
      recv_msg_firmware_begin(iface, msg, bh_buf, BOOT_HEADER_MAXSIZE, &bh_len,
                              module_headers, sizeof(module_headers), &mh_len,
                              code_hash, sizeof(code_hash), &ch_len, nrf_arg)) {
    ui_screen_fail();  // recv already failed, no wire Failure to send
    return WF_ERROR;
  }

  // boot_header_auth_get also enforces hw_model / hw_revision.
  const boot_header_auth_t *hdr = boot_header_auth_get((uintptr_t)bh_buf);
  if (hdr == NULL || hdr->header_size > bh_len) {
    return fw_begin_fail(iface, "Invalid boot header");
  }
  // Bound code_size before hashing that many bytes off BOOTLOADER_START.
  // Subtraction so the sum cannot wrap.
  _Static_assert(BOOTLOADER_MAXSIZE >= SIZE_64K,
                 "bootloader area smaller than the maximum header size");
  if (hdr->code_size > BOOTLOADER_MAXSIZE - hdr->header_size) {
    return fw_begin_fail(iface, "Invalid boot header");
  }

  // Anti-rollback on the header's monotonic_version, before confirming. Same
  // floor as check_bootloader_min_version at boot, ucb_stage_commit and the
  // boardloader.
  if (sectrue != check_bootloader_min_version(hdr->monotonic_version)) {
    return fw_begin_fail(iface, "Firmware downgrade protection");
  }

  // Upgrade floor: the installed bootloader must be >= min_prev_version when
  // set. Enforced only in the bootloader (here and at staging), so a release
  // relying on it must bump monotonic_version as well. An unparseable
  // installed header fails the floor.
  if (boot_header_version_is_set(hdr->min_prev_version)) {
    const boot_header_auth_t *installed =
        boot_header_auth_get(BOOTLOADER_START);
    if (installed == NULL ||
        boot_header_version_compare(installed->version, hdr->min_prev_version) <
            0) {
      return fw_begin_fail(iface, "Unsupported upgrade path");
    }
  }

  // Authenticate the header before anything below uses it. The leaf commits
  // to H(code): if the current on-flash code verifies, the install is
  // header-only; otherwise the host's claimed code_hash must verify, and
  // ucb_stage_verify later binds the delivered code to it.
  // FIH: header-only needs a positive pass; everything else takes the full
  // path, which needs its own positive pass.
  merkle_proof_node_t root;
  boot_header_calc_merkle_root(hdr, BOOTLOADER_START + hdr->header_size, &root);
  const secbool full_bootloader =
      (sectrue == boot_header_check_signature(hdr, &root)) ? secfalse : sectrue;

  if (sectrue == full_bootloader) {
    if (!msg->has_code_length || msg->code_length == 0) {
      return fw_begin_fail(
          iface, "Bootloader code changed; full bootloader not supplied");
    }
    if (ch_len != sizeof(code_hash)) {
      return fw_begin_fail(iface, "Bootloader code hash missing");
    }
    boot_header_calc_merkle_root_from_hash(hdr, code_hash, &root);
    if (sectrue != boot_header_check_signature(hdr, &root)) {
      return fw_begin_fail(iface, "Invalid boot header signature");
    }
  }

#ifdef USE_SMP
  // A device with a co-processor requires every install to carry its image;
  // otherwise arm-last would land on new bootloader + old co-processor.
  // The requirement comes from this build, not the release (an nRF slot is
  // indistinguishable from padding in the co-path). An already-current nRF
  // is still skipped by nrf_update_required.
  if (!msg->has_nrf_length || msg->nrf_length == 0) {
    return fw_begin_fail(iface, "Release carries no co-processor image");
  }
#endif

  // Authenticate the manifest region [manifest || firmware_manifest_proof_t]:
  // the variant leaf folded through the proof must equal firmware_root.
  merkle_proof_node_t firmware_root;
  memcpy(firmware_root.bytes, hdr->firmware_root.bytes,
         sizeof(firmware_root.bytes));
  const firmware_manifest_t *manifest =
      (const firmware_manifest_t *)module_headers;
  if (mh_len < sizeof(firmware_manifest_t) ||
      firmware_manifest_size(manifest) > mh_len) {
    return fw_begin_fail(iface, "Invalid firmware manifest");
  }
  size_t manifest_len = firmware_manifest_size(manifest);
  const merkle_proof_node_t *fw_proof = NULL;
  size_t fw_proof_count = 0;
  if (sectrue != firmware_manifest_read_proof(manifest, mh_len, &fw_proof,
                                              &fw_proof_count)) {
    return fw_begin_fail(iface, "Invalid firmware manifest proof");
  }
  if (sectrue != firmware_manifest_authentic(manifest, manifest_len, fw_proof,
                                             fw_proof_count, &firmware_root)) {
    return fw_begin_fail(iface, "Firmware manifest not authentic");
  }

  // Interaction-less upgrade: the consent digest H(header prefix || manifest)
  // must match the hash firmware left in bootargs under INSTALL_UPGRADE.
  // Consent is one-shot: consumed here, and phase 1 carries no digest into
  // phase 2. FIH: `ilu` flips only on a positive match.
  merkle_proof_node_t consent = {0};
  size_t prefix_len = 0;
  if (sectrue != boot_header_prefix_extent((const uint8_t *)hdr,
                                           hdr->header_size, &prefix_len) ||
      sectrue != boot_header_consent_digest((const uint8_t *)hdr, prefix_len,
                                            module_headers, manifest_len,
                                            &consent)) {
    return fw_begin_fail(iface, "Invalid boot header");
  }
  static bool consent_consumed = false;

  secbool ilu = secfalse;
  if (!consent_consumed &&
      bootargs_get_command() == BOOT_COMMAND_INSTALL_UPGRADE) {
    boot_args_t args = {0};
    bootargs_get_args(&args);
    if (memcmp(args.hash, consent.bytes, sizeof(consent.bytes)) != 0) {
      return fw_begin_fail(iface, "Firmware mismatch");
    }
    // The unattended path installs an upgrade only (as `is_upgrade` in
    // wf_firmware_update.c); a user-confirmed downgrade is still allowed.
    // The installed manifest is read unauthenticated; no manifest means a
    // fresh install, which is not a downgrade.
    const firmware_manifest_t *installed =
        (const firmware_manifest_t *)(uintptr_t)FIRMWARE_START;
    if (installed->magic == FW_MANIFEST_MAGIC &&
        memcmp(manifest->firmware_version, installed->firmware_version,
               sizeof(manifest->firmware_version)) <= 0) {
      // [major, minor, patch, build] byte order is the precedence order.
      return fw_begin_fail(iface, "Not a firmware upgrade");
    }
    consent_consumed = true;
    ilu = sectrue;
  }

  // Validate the module layout before confirming; the same checks run in
  // phase 2 (fwt_on_headers) and at boot (firmware_verify_tree).
  if (sectrue != firmware_manifest_layout_valid(manifest, FIRMWARE_MAXSIZE) ||
      sectrue != fwt_manifest_block_aligned(manifest)) {
    return fw_begin_fail(iface, "Invalid firmware manifest");
  }

  const fw_variant_sec_t variant = manifest->firmware_variant;

  // CUSTOM is a founder-signed slot with the app code_hash zeroed in the
  // leaf: authenticated variant, integrity-only app, storage-isolated via
  // firmware_type, allowed only on an unlocked bootloader.
  secbool is_custom = fw_variant_is_custom(variant);

  // FIH: two independent reads, both must be positively official.
  const secbool official_1 = fw_variant_is_official(variant);
  const secbool official_2 = fw_variant_is_official(manifest->firmware_variant);
  if (official_1 != sectrue || official_2 != sectrue) {
    if (secret_bootloader_locked() != secfalse) {
      return fw_begin_fail(
          iface, "Unlock the bootloader to install unofficial firmware");
    }
  }
  const fw_variant_sec_t firmware_type = variant;

  // FIH: defaults are the safe values (wipe, confirm); each flips only on a
  // positive condition.
  secbool keep_seed = secfalse;
  secbool empty_device = secfalse;
  const boot_header_auth_t *cur = boot_header_auth_get(BOOTLOADER_START);
  const boot_header_unauth_t *cur_unauth =
      (cur != NULL) ? boot_header_unauth_get(cur) : NULL;
  if (cur != NULL && cur_unauth != NULL &&
      cur_unauth->firmware_type == FW_VARIANT_SEC_NONE) {
    // Positively unprovisioned only; an INVALID field is not consent.
    empty_device = sectrue;
  } else if (cur_unauth != NULL && cur_unauth->firmware_type == firmware_type) {
    // Same storage domain (the salt keys off the full firmware_type).
    keep_seed = sectrue;
  }

  // Independent gate: crossing the official<->custom boundary always wipes.
  if (cur_unauth != NULL &&
      fw_variant_is_custom(cur_unauth->firmware_type) != is_custom) {
    keep_seed = secfalse;
  }

  // Storage-format floor: a release below the installed fix_version may not
  // keep the seed. Must match wf_firmware_update.c.
  if (cur != NULL &&
      boot_header_version_compare(hdr->version, cur->fix_version) < 0) {
    keep_seed = secfalse;
  }

  // Confirm unless the device is positively empty and the variant positively
  // official; !keep_seed shows the seed-erase warning.
  // TODO(pq_secure_boot): dedicated tree-install confirm screen.
  size_t vendor_len = 0;
  const secbool install_official = fw_variant_is_official(variant);
  const char *vendor = tree_vendor_str(variant, install_official, &vendor_len);
  // Firmware version from the manifest, not the staged bootloader version.
  const uint32_t fw_version = (uint32_t)manifest->firmware_version[0] |
                              ((uint32_t)manifest->firmware_version[1] << 8) |
                              ((uint32_t)manifest->firmware_version[2] << 16) |
                              ((uint32_t)manifest->firmware_version[3] << 24);
  // Interaction-less skip requires an unchanged storage domain (the erase
  // warning lives on this screen) and an official variant (the running
  // firmware's own confirm is trusted only when it is official). FIH: all
  // three positive.
  const secbool skip_confirm =
      (ilu == sectrue && keep_seed == sectrue && install_official == sectrue)
          ? sectrue
          : secfalse;
  // An empty device auto-confirms only an official variant; "empty" can be
  // created by anyone with physical access. FIH: both positive.
  const secbool skip_empty =
      (empty_device == sectrue && install_official == sectrue) ? sectrue
                                                               : secfalse;
  if (sectrue != skip_empty && sectrue != skip_confirm &&
      CONFIRM != ui_screen_install_confirm_bootloader(
                     fw_version, firmware_root.bytes, keep_seed,
                     /*is_newvendor=*/keep_seed == sectrue ? secfalse : sectrue,
                     vendor, vendor_len)) {
    send_user_abort(iface, "Firmware install cancelled");
    return WF_CANCELLED;
  }
  ui_screen_install_start(iface->wire->wireless);

  // firmware_type lives in the unauth part (outside auth_size, covered by the
  // UCB hash). The firmware Merkle proof rides in the firmware image's
  // manifest region, not here.
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

  out->header_size = header_size;
  out->full_bootloader = full_bootloader;
  out->keep_seed = keep_seed;
  return WF_OK;
}

workflow_result_t workflow_firmware_update_pq(protob_io_t *iface) {
  // nRF OTA fields need stable storage (not chunk_buffer) until the push.
#ifdef USE_SMP
  static uint8_t
      nrf_co_path[MODEL_TREE_MAX_PROOF_NODES * sizeof(merkle_proof_node_t)];
  static uint8_t nrf_image_hash[SHA256_DIGEST_LENGTH];
  memset(nrf_co_path, 0, sizeof(nrf_co_path));
  memset(nrf_image_hash, 0, sizeof(nrf_image_hash));
  firmware_begin_nrf_t nrf_out = {.co_path_buf = nrf_co_path,
                                  .co_path_size = sizeof(nrf_co_path),
                                  .image_hash_buf = nrf_image_hash,
                                  .image_hash_size = sizeof(nrf_image_hash)};
  firmware_begin_nrf_t *nrf_arg = &nrf_out;
#else
  firmware_begin_nrf_t *nrf_arg = NULL;
#endif
  FirmwareBegin msg = {0};

  fw_begin_staged_t staged = {0};
  const workflow_result_t preamble =
      fw_begin_preamble(iface, &msg, nrf_arg, &staged);
  if (preamble != WF_OK) {
    return preamble;
  }
  // chunk_buffer is free for the streams below.
  const uint32_t header_size = staged.header_size;
  const secbool full_bootloader = staged.full_bootloader;
  const secbool keep_seed = staged.keep_seed;

  // Stage the new bootloader and capture the signature-verified model_root
  // (valid for both the header-only and the full path).
  merkle_proof_node_t model_root;
  if (sectrue == full_bootloader) {
    // The stream suppresses its own Success; the single terminal one is below.
    image_upload_handler_t handler = {
        .target_area = &STAGING_AREA,
        .target_offset = header_size,
        .max_size = BOOTLOADER_MAXSIZE,
        .success_result = WF_OK,
        .suppress_success = true,
        .ui = &blcode_upload_ui,
        .on_headers = blcode_on_headers,
        .on_chunk = blcode_on_chunk,
        .on_finish = blcode_on_finish,
    };
    if (WF_OK != run_image_upload(iface, &handler, msg.code_length)) {
      // run_image_upload already showed the failure / abort screen.
      return WF_ERROR;
    }
  }
  // Verify the staged bootloader; the install is not armed yet.
  uint32_t ucb_code_address = 0;
  if (UPLOAD_OK !=
      ucb_stage_verify(&STAGING_AREA,
                       /*header_only=*/(sectrue != full_bootloader), iface,
                       &model_root, &ucb_code_address)) {
    ui_screen_fail();  // ucb_stage_verify sent its own wire Failure
    return WF_ERROR;
  }

#ifdef USE_SMP
  // nRF OTA: delivered and staged now, over the still-compatible link; the
  // SMP push is deferred to the next boot (nrf_ota_resume_boot). The nRF leaf
  // is fold-verified against model_root before arming, so an abort here
  // leaves the UCB unarmed and the old bootloader intact -- but not the
  // firmware, whose region the staging scratch already erased. See
  // docs/core/embed-arch/firmware-merkle-tree.md.
  if (msg.has_nrf_length && msg.nrf_length > 0) {
    workflow_result_t nrf_res = workflow_nrf_ota_update(
        iface, &model_root, nrf_co_path, nrf_out.co_path_len, nrf_image_hash,
        nrf_out.image_hash_len, msg.nrf_length);
    if (nrf_res != WF_OK) {
      // workflow_nrf_ota_update already drew the fail screen + sent Failure.
      return nrf_res;
    }
  }
#endif

  // Erase the seed on a storage-domain change only after ucb_stage_verify
  // has bound the delivered code, and before the reboot into phase 2.
  if (sectrue != keep_seed) {
#ifdef USE_STORAGE_HWKEY
    secret_bhk_regenerate();
#endif
    ensure(erase_storage(NULL), NULL);
#ifdef USE_BACKUP_RAM
    ensure(backup_ram_erase_protected() * sectrue, NULL);
#endif
  }

  // Arm last: before this point an interruption leaves the old bootloader
  // with nothing committed (the firmware body is already erased and phase 2
  // reinstalls it); after it the resume drives forward to new bootloader +
  // new nRF across reboots.
  if (sectrue != ucb_stage_arm(&STAGING_AREA, ucb_code_address)) {
    return fw_begin_fail(iface, "Failed to arm bootloader install");
  }

  // Single terminal Success for phase 1 (sub-streams suppressed theirs).
  ui_screen_install_progress_upload(1000, iface->wire->wireless);
  send_msg_success(iface, NULL);
  systick_delay_ms(500);

  // Reboot into phase 2. CONTINUE_UPGRADE is set atomically with the reset;
  // it is distinct from the firmware-originated INSTALL_UPGRADE because only
  // it may boot past an invalid firmware body, so nothing unprivileged may
  // select it. It carries no arguments and no consent digest (consent is
  // one-shot); phase 2 is constrained by the staged boot header alone. For
  // CUSTOM that pins the variant and placement but not the app hash. Noreturn.
  reboot_and_continue_upgrade();
}

// Phase 2: stream the whole [secmon | kernel+coreapp] image into the firmware
// area under BOOT_COMMAND_CONTINUE_UPGRADE (new boot header already installed
// by the boardloader) and verify it as a tree against firmware_root. No
// re-prompt: confirmed and keep-seed decided in phase 1.

typedef struct {
  image_upload_handler_t base;
  // Manifest authenticated in on_headers, copied out of chunk_buffer.
  uint8_t manifest_buf[FW_MANIFEST_REGION];
  const firmware_manifest_t *manifest;
  // Streaming verify cursor (see fwt_on_chunk).
  size_t cur_module;   // module currently being verified
  uint32_t cur_chunk;  // next chunk index (within cur_module) to verify
  uint8_t
      expected[IMAGE_HASH_DIGEST_LENGTH];  // running hash (starts at code_hash)
} fwt_upload_handler_t;

static upload_status_t fwt_on_headers(image_upload_handler_t *base,
                                      protob_io_t *iface, const uint8_t *buf,
                                      size_t len) {
  fwt_upload_handler_t *h = (fwt_upload_handler_t *)base;

  // The image starts with the firmware manifest (TRZD).
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

  // Authenticate the manifest against the installed firmware_root before
  // anything is written; the per-variant proof follows the manifest.
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

  // firmware_root admits every variant of the release; bind the install to
  // the variant confirmed in phase 1 (the installed firmware_type, trusted
  // because the boot-header region is write-protected from firmware).
  const boot_header_unauth_t *bl_unauth = boot_header_unauth_get(bl);
  if (bl_unauth == NULL) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid boot header");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER;
  }
  if (manifest->firmware_variant != bl_unauth->firmware_type) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Firmware variant mismatch");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER;
  }

  memcpy(h->manifest_buf, buf, manifest_len);
  h->manifest = (const firmware_manifest_t *)h->manifest_buf;

  // Same layout checks as phase 1 and boot, before any erase/write.
  if (sectrue != firmware_manifest_layout_valid(h->manifest, base->max_size) ||
      sectrue != fwt_manifest_block_aligned(h->manifest)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid firmware manifest");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER;
  }
  // Hash chunk size: FLASH_BLOCK_SIZE-aligned, fits the staging buffer, and
  // the same for every module (the transport uses a single block size).
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
  // Transport block: whole hash chunks up to FW_TRANSPORT_BLOCK_TARGET, capped
  // by IMAGE_CHUNK_SIZE, at least the header prefetch (FW_MANIFEST_REGION ==
  // init_chunk_size).
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
  // Inline verification needs one segment per module (+ header); more than
  // the plan holds would fall back to flat streaming, so reject explicitly.
  if ((size_t)h->manifest->module_count + 1 > IMAGE_UPLOAD_MAX_SEGMENTS) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Too many firmware modules");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER;
  }
  h->cur_module = 0;
  h->cur_chunk = 0;
  memcpy(h->expected, h->manifest->entries[0].code_hash.bytes,
         sizeof(h->expected));

  // Pre-confirmed in phase 1.
  ui_screen_install_start(iface->wire->wireless);
  return UPLOAD_OK;
}

// Verify one transport block against the module's hash chain before it is
// written. A block is m = ceil(len/cs) chunks; only a module's final chunk may
// be partial. `prev_hash` is the chain value after the block (the module's
// last block derives it as the seed H(0x01||size) instead). The block is
// folded last->first from that value and must reach `expected`; the
// whole-tree verify in on_finish remains the authoritative backstop.
static upload_status_t fwt_on_chunk(image_upload_handler_t *base,
                                    protob_io_t *iface, uint32_t image_offset,
                                    const uint8_t *data, size_t len,
                                    const uint8_t *prev_hash) {
  fwt_upload_handler_t *h = (fwt_upload_handler_t *)base;
  const firmware_manifest_t *m = h->manifest;

  // The manifest region (segment 0) is authenticated by the leaf fold.
  if (image_offset < m->entries[0].addr) {
    return UPLOAD_OK;
  }

  // Blocks must arrive in strict module/chunk order.
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
  // A non-tail block is whole chunks; the tail block may be any length.
  const bool tail =
      (len == remaining);  // block reaches the module's last chunk
  if (image_offset != e->addr + off || len == 0 || len > remaining ||
      (!tail && (len % cs) != 0)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "vtree: unexpected chunk");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
  }
  const uint32_t mchunks = (len + cs - 1) / cs;  // chunks in this block (ceil)

  // Chain value after this block: derived seed for the tail, inline otherwise.
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
  // Fold last->first; mirrors firmware_module_code_hash.
  uint8_t chain[IMAGE_HASH_DIGEST_LENGTH];
  memcpy(chain, e_end, sizeof(chain));
  for (uint32_t j = mchunks; j-- > 0;) {
    const uint32_t coff = off + j * cs;  // module-relative chunk offset
    const uint32_t clen = (e->size - coff < cs) ? (e->size - coff) : cs;
    firmware_module_chain_step(chain, data + (size_t)j * cs, clen, chain);
  }
  if (memcmp(chain, h->expected, sizeof(chain)) != 0) {
    // Retryable: terminal once the engine's retries are spent.
    return UPLOAD_ERR_INVALID_CHUNK_HASH;
  }

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

// Segment 0 is the manifest region (== init_chunk_size), segments 1.. one per
// module so every block starts on a chunk boundary. Returns 0 (flat stream)
// if the count exceeds `max`. Entry ranges were validated in fwt_on_headers.
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
  // A short stream leaves the cursor behind.
  if (h->cur_module != h->manifest->module_count) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "vtree: incomplete firmware stream");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
  }
  // Authoritative whole-tree verify against the installed firmware_root.
  firmware_tree_info_t info = {0};
  if (sectrue != firmware_verify_tree(&info)) {
    // Diagnostic breakdown: name the failing module, else blame the fold.
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
  // Phase 2 only follows phase 1; a bare FirmwareErase must not erase a valid
  // firmware.
  if (bootargs_get_command() != BOOT_COMMAND_CONTINUE_UPGRADE) {
    return fw_begin_fail(iface,
                         "Firmware update must begin with FirmwareBegin");
  }

  FirmwareErase msg;
  if (sectrue != recv_msg_firmware_erase(iface, &msg)) {
    ui_screen_fail();  // recv already failed (no wire Failure to send)
    return WF_ERROR;
  }

  // Static to keep the manifest copy off the stack; zeroed because it
  // persists across retries within one boot.
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
      // Prefetch only the manifest region; block_size is set in
      // fwt_on_headers.
      .init_chunk_size = FW_MANIFEST_REGION,
  };

  return run_image_upload(iface, &handler.base,
                          msg.has_length ? msg.length : 0);
}

#endif  // PQ_SECURE_BOOT
