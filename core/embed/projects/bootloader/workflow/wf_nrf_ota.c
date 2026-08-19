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

#if defined(PQ_SECURE_BOOT) && defined(USE_SMP)

#include <io/nrf.h>
#include <io/nrf_image.h>
#include <sec/boot_header.h>
#include <sys/flash.h>

#include "sha2.h"

#include "bootui.h"
#include "nrf_staging.h"
#include "wf_image_upload.h"
#include "wf_nrf_ota.h"

// The nRF image streams as one flat blob (no header at the start): the founder
// check (fold + model id) runs as a whole in on_finish, mirroring the
// bootloader-code stream (blcode_* in wf_firmware_update_pq.c). Per-chunk hooks
// are therefore no-ops.
//
// on_finish STAGES ONLY: it validates the image and persists its descriptor
// (co-path) via nrf_staging.*; the actual SMP push to the nRF is DEFERRED to
// the next bootloader boot's resume driver. On a BLE-only device the push
// reboots the nRF into DFU (= the BLE link), so it cannot run during this host
// connection; deferring it is also what makes an interrupted update resumable.
// See nrf_staging.h / the coproc-ota design.
typedef struct {
  image_upload_handler_t base;
  merkle_proof_node_t model_root;  // signed root (copied in)
  merkle_proof_node_t co_path[MODEL_TREE_MAX_PROOF_NODES];  // nRF leaf -> root
  size_t co_path_count;
  uint32_t image_len;  // actual streamed size (base->max_size is only the cap)
} nrf_upload_handler_t;

static upload_status_t nrf_on_headers(image_upload_handler_t *base,
                                      protob_io_t *iface, const uint8_t *buf,
                                      size_t len) {
  (void)base;
  (void)iface;
  (void)buf;
  (void)len;
  return UPLOAD_OK;  // validated as a whole in on_finish
}

static upload_status_t nrf_on_chunk(image_upload_handler_t *base,
                                    protob_io_t *iface, uint32_t image_offset,
                                    const uint8_t *data, size_t len,
                                    const uint8_t *prev_hash) {
  (void)base;
  (void)iface;
  (void)image_offset;
  (void)data;
  (void)len;
  (void)prev_hash;
  return UPLOAD_OK;  // fold + model-id verified in on_finish
}

// Run the PQ-native push gate against the boot header at `header_address` (the
// one whose modelRoot we folded against). A classic image passes trivially; a
// PQ-native one must additionally carry this release's founder signature
// records, an image-side Merkle proof that folds, and no rogue TLVs --
// otherwise its own MCUboot would reject it AFTER we had already erased the
// only slot. See nrf_image_verify_for_push.
static secbool nrf_pq_gate(const uint8_t *image, size_t image_len,
                           const merkle_proof_node_t *model_root,
                           uint32_t header_address) {
  const boot_header_auth_t *hdr = boot_header_auth_get(header_address);
  if (hdr == NULL) {
    return secfalse;
  }
  const boot_header_unauth_t *unauth = boot_header_unauth_get(hdr);
  if (unauth == NULL) {
    return secfalse;
  }
  return nrf_image_verify_for_push(
      image, image_len, model_root, unauth->slh_signature[0],
      unauth->slh_signature[1], unauth->ec_signature[0],
      unauth->ec_signature[1]);
}

static upload_status_t nrf_on_finish(image_upload_handler_t *base,
                                     protob_io_t *iface) {
  nrf_upload_handler_t *h = (nrf_upload_handler_t *)base;
  // The image was streamed into NRF_STAGING_AREA at offset 0; read it back
  // through its memory-mapped address (it is at the FRONT of the firmware
  // region, past the secmon -- do NOT assume FIRMWARE_START).
  const uint8_t *image = (const uint8_t *)flash_area_get_address(
      &NRF_STAGING_AREA, 0, h->image_len);
  if (image == NULL) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "nRF staging address invalid");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER;
  }

  // 1. Founder commitment: leaf = H(0x00 || image) folds through the co-path to
  //    the signature-verified modelRoot.
  if (nrf_image_verify_in_tree(image, h->image_len, h->co_path,
                               h->co_path_count, &h->model_root) != sectrue) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "nRF image not in founder tree");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
  }

  // 2. Cross-model guard: the image's model-id TLV must be THIS device (every
  //    model's nRF shares modelRoot, so the fold alone does not pin the model).
  uint8_t model_id[NRF_IMAGE_MODEL_ID_LEN];
  if (!nrf_image_model_id(image, h->image_len, model_id) ||
      memcmp(model_id, MODEL_INTERNAL_NAME, NRF_IMAGE_MODEL_ID_LEN) != 0) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "nRF image model mismatch");
    return UPLOAD_ERR_INVALID_IMAGE_MODEL;
  }

  // 3. PQ-native gate: everything MCUboot will check that the fold above does
  // not
  //    cover -- the image-side Merkle proof, this release's signature records,
  //    and the absence of rogue TLVs. Checked against the STAGED boot header,
  //    since that is the header h->model_root came from (ucb_stage_verify). A
  //    classic image passes trivially. Rejecting here means we never erase a
  //    working nRF for an image its own MCUboot would refuse.
  uint32_t staged_hdr = (uint32_t)(uintptr_t)flash_area_get_address(
      &STAGING_AREA, 0, sizeof(boot_header_auth_t));
  if (staged_hdr == 0 ||
      nrf_pq_gate(image, h->image_len, &h->model_root, staged_hdr) != sectrue) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "nRF image would be rejected by its bootloader");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
  }

  // 4. Persist the descriptor (co-path) as the FINAL staging commit. The push
  //    itself is deferred to the boot-time resume driver (see the file header);
  //    writing the descriptor last means a half-staged image never presents as
  //    valid. The nRF's own MCUboot Ed25519 check remains the authoritative
  //    gate at push time.
  if (nrf_staging_write_desc(h->image_len, h->co_path, h->co_path_count) !=
      sectrue) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "nRF staging descriptor write failed");
    return UPLOAD_ERR_COMMUNICATION;
  }
  return UPLOAD_OK;
}

static void nrf_ui_progress(int permille, bool wireless) {
  ui_screen_install_progress_upload(permille, wireless);
}

static void nrf_ui_success(bool wireless) {
  ui_screen_install_progress_upload(1000, wireless);
}

static void nrf_ui_fail(upload_status_t status) {
  (void)status;
  ui_screen_fail();
}

static const image_upload_ui_t nrf_upload_ui = {
    .progress = nrf_ui_progress,
    .success = nrf_ui_success,
    .fail = nrf_ui_fail,
};

static workflow_result_t nrf_fail(protob_io_t *iface, const char *message) {
  send_msg_failure(iface, FailureType_Failure_ProcessError, message);
  ui_screen_fail();
  return WF_ERROR;
}

// Progress of the STM->nRF SMP push during the autonomous boot-time resume ->
// the install progress bar. `wireless` is false: this runs before any host
// connection, so it is a local operation, not a host transfer.
static void nrf_resume_progress(uint32_t done, uint32_t total) {
  int permille = (total != 0) ? (int)(((uint64_t)done * 1000) / total) : 1000;
  ui_screen_install_progress_upload(permille, false);
}

void nrf_ota_resume_boot(void) {
  uint32_t image_len = 0;
  const merkle_proof_node_t *co_path = NULL;
  size_t co_path_count = 0;
  if (!nrf_staging_read(&image_len, &co_path, &co_path_count)) {
    return;  // nothing staged -> normal boot (the common case)
  }

  const uint8_t *image = nrf_staging_image(image_len);
  if (image == NULL) {
    nrf_staging_clear();
    return;
  }

  // Recompute the modelRoot the INSTALLED boot header commits to (mirrors
  // ucb_stage_verify's fixed-boardloader path). The boardloader already
  // authenticated this header+code before running us, so recomputation is
  // trusted.
  const boot_header_auth_t *cur = boot_header_auth_get(BOOTLOADER_START);
  if (cur == NULL) {
    return;  // cannot verify -> keep staged, retry next boot
  }
  merkle_proof_node_t model_root;
  boot_header_calc_merkle_root(cur, BOOTLOADER_START + cur->header_size,
                               &model_root);

  // Founder commitment + cross-model guard against the INSTALLED root. A
  // stale/aborted/foreign descriptor (e.g. staged for a bootloader we did NOT
  // end up installing) will not fold -> discard and boot normally. This fold is
  // the coupling between the two durable flags (UCB armed / staging valid):
  // only a staging that matches the running bootloader's tree is acted on.
  uint8_t model_id[NRF_IMAGE_MODEL_ID_LEN];
  if (nrf_image_verify_in_tree(image, image_len, co_path, co_path_count,
                               &model_root) != sectrue ||
      !nrf_image_model_id(image, image_len, model_id) ||
      memcmp(model_id, MODEL_INTERNAL_NAME, NRF_IMAGE_MODEL_ID_LEN) != 0) {
    nrf_staging_clear();
    return;
  }

  // PQ-native gate, now against the INSTALLED boot header (the swap has
  // happened, so this is the release the staged nRF belongs to). Re-checked
  // here and not just trusted from staging time: this runs after a reboot, and
  // the push is what actually erases the nRF's only slot.
  if (nrf_pq_gate(image, image_len, &model_root, BOOTLOADER_START) != sectrue) {
    nrf_staging_clear();
    return;
  }

  // Set up the install progress screen before the (potentially ~30 s) push --
  // ui_screen_install_progress_upload only updates a bar that install_start
  // created; without this the push runs against a blank screen. `wireless` is
  // false: this is an autonomous local operation, not a host transfer.
  ui_screen_install_start(false);

  // Idempotent, forward-only push over the link-independent GPIO
  // serial-recovery path. Skip if the live nRF already matches (resume after a
  // push that completed before the staging was cleared);
  // nrf_update_with_progress retries internally and the nRF's own MCUboot
  // Ed25519 check is the authoritative gate.
  bool ok = true;
  if (nrf_update_required(image, image_len)) {
    ok = nrf_update_with_progress(image, image_len, nrf_resume_progress);
  }

  if (ok == true) {
    nrf_staging_clear();
    return;
  }

  // Persistent failure: do NOT clear the staging (a power-cycle re-enters this
  // driver and re-pushes) and do NOT continue -- proceeding would boot with an
  // incompatible co-processor and, on a BLE-only device, a dead host link.
  error_shutdown("nRF update failed");
}

workflow_result_t workflow_nrf_ota_update(
    protob_io_t *iface, const merkle_proof_node_t *model_root,
    const uint8_t *co_path, size_t co_path_len, const uint8_t *image_hash,
    size_t image_hash_len, uint32_t nrf_length) {
  // --- Validate the offered co-path + size up front. ---
  if (co_path == NULL || (co_path_len % sizeof(merkle_proof_node_t)) != 0) {
    return nrf_fail(iface, "Invalid nRF co-path");
  }
  const size_t co_path_count = co_path_len / sizeof(merkle_proof_node_t);
  if (co_path_count > MODEL_TREE_MAX_PROOF_NODES) {
    return nrf_fail(iface, "nRF co-path too long");
  }
  if (nrf_length == 0 || nrf_length > nrf_staging_image_capacity()) {
    return nrf_fail(iface, "nRF image size invalid");
  }

  // --- Update-required hint: if the running nRF already reports this image's
  //     hash, skip the stream entirely. Best-effort optimization, NOT a trust
  //     input: a wrong hash only changes whether we stream, never what we
  //     accept (on_finish still folds to modelRoot). If the nRF cannot be
  //     queried, fall through and stream. ---
  if (image_hash != NULL && image_hash_len == SHA256_DIGEST_LENGTH) {
    nrf_info_t info;
    if (nrf_get_info(&info) &&
        memcmp(info.hash, image_hash, SHA256_DIGEST_LENGTH) == 0) {
      return WF_OK;  // already up to date -> nothing to push
    }
  }

  // --- Stream into NRF_STAGING_AREA, then fold + model-id + persist descriptor
  //     (push deferred to the boot-time resume driver). ---
  // static: keeps the co-path copy + handler off the stack and stable across
  // the streaming loop (run_image_upload reuses chunk_buffer, not this). Zero
  // first (defense-in-depth across retries within one boot). Suppresses its own
  // Success and tags its FirmwareRequests with NRF_OTA_REQUEST_INDEX so the
  // host serves the nRF image (vs the bootloader code at index 0); the single
  // terminal Success is sent by the phase-1 caller.
  static nrf_upload_handler_t handler;
  memset(&handler, 0, sizeof(handler));
  memcpy(&handler.model_root, model_root, sizeof(handler.model_root));
  memcpy(handler.co_path, co_path, co_path_len);
  handler.co_path_count = co_path_count;
  handler.image_len = nrf_length;
  handler.base = (image_upload_handler_t){
      .target_area = &NRF_STAGING_AREA,
      .target_offset = 0,
      .max_size = nrf_staging_image_capacity(),
      .request_index = NRF_OTA_REQUEST_INDEX,
      .success_result = WF_OK,
      .suppress_success = true,
      .ui = &nrf_upload_ui,
      .on_headers = nrf_on_headers,
      .on_chunk = nrf_on_chunk,
      .on_finish = nrf_on_finish,
  };
  return run_image_upload(iface, &handler.base, nrf_length);
}

#endif  // PQ_SECURE_BOOT && USE_SMP
