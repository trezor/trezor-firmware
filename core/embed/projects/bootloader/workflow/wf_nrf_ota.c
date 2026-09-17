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

// The nRF image streams as one flat blob and is verified as a whole in
// on_finish, which only stages it; the SMP push is deferred to the next boot
// (nrf_ota_resume_boot) because on a BLE-only device it reboots the link.
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
  return UPLOAD_OK;
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
  return UPLOAD_OK;
}

// Everything the nRF's MCUboot will check that the fold does not cover, so a
// push never erases a working nRF for an image it would refuse. A classic
// image passes trivially.
static secbool nrf_pq_gate(const uint8_t *image, size_t image_len,
                           const merkle_proof_node_t *model_root,
                           const void *boot_header) {
  const boot_header_auth_t *hdr = boot_header_auth_get((uintptr_t)boot_header);
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
  // NRF_STAGING_AREA is not at FIRMWARE_START; use its mapped address.
  const uint8_t *image = (const uint8_t *)flash_area_get_address(
      &NRF_STAGING_AREA, 0, h->image_len);
  if (image == NULL) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "nRF staging address invalid");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER;
  }

  // Founder commitment: the role-bound leaf folds to model_root.
  if (nrf_image_verify_in_tree(image, h->image_len, h->co_path,
                               h->co_path_count, &h->model_root) != sectrue) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "nRF image not in founder tree");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
  }

  // Model-id TLV must name this device (catches misissuance into this tree).
  uint8_t model_id[NRF_IMAGE_MODEL_ID_LEN];
  if (!nrf_image_model_id(image, h->image_len, model_id) ||
      memcmp(model_id, MODEL_INTERNAL_NAME, NRF_IMAGE_MODEL_ID_LEN) != 0) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "nRF image model mismatch");
    return UPLOAD_ERR_INVALID_IMAGE_MODEL;
  }

  // PQ-native gate against the staged header (where model_root came from).
  const void *staged_hdr =
      flash_area_get_address(&STAGING_AREA, 0, sizeof(boot_header_auth_t));
  if (staged_hdr == NULL ||
      nrf_pq_gate(image, h->image_len, &h->model_root, staged_hdr) != sectrue) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "nRF image would be rejected by its bootloader");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
  }

  // Descriptor last, so a half-staged image never presents as valid.
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

// Local operation, no host connection, hence wireless=false.
static void nrf_resume_progress(uint32_t done, uint32_t total) {
  int permille = (total != 0) ? (int)(((uint64_t)done * 1000) / total) : 1000;
  ui_screen_install_progress_upload(permille, false);
}

void nrf_ota_resume_boot(void) {
  uint32_t image_len = 0;
  const merkle_proof_node_t *co_path = NULL;
  size_t co_path_count = 0;
  if (!nrf_staging_read(&image_len, &co_path, &co_path_count)) {
    return;  // nothing staged
  }

  const uint8_t *image = nrf_staging_image(image_len);
  if (image == NULL) {
    nrf_staging_clear();
    return;
  }

  // Recompute the model_root of the installed (boardloader-verified) header.
  const boot_header_auth_t *cur = boot_header_auth_get(BOOTLOADER_START);
  if (cur == NULL) {
    return;  // cannot verify -> keep staged, retry next boot
  }
  merkle_proof_node_t model_root;
  boot_header_calc_merkle_root(cur, BOOTLOADER_START + cur->header_size,
                               &model_root);

  // Only a staging that folds under the running bootloader's tree is acted
  // on; a stale or foreign descriptor is discarded.
  uint8_t model_id[NRF_IMAGE_MODEL_ID_LEN];
  if (nrf_image_verify_in_tree(image, image_len, co_path, co_path_count,
                               &model_root) != sectrue ||
      !nrf_image_model_id(image, image_len, model_id) ||
      memcmp(model_id, MODEL_INTERNAL_NAME, NRF_IMAGE_MODEL_ID_LEN) != 0) {
    nrf_staging_clear();
    return;
  }

  // Re-run the push gate against the installed header; the push is what
  // erases the nRF's only slot.
  if (nrf_pq_gate(image, image_len, &model_root,
                  (const uint8_t *)(uintptr_t)BOOTLOADER_START) != sectrue) {
    nrf_staging_clear();
    return;
  }

  // install_start creates the bar the progress callback updates.
  ui_screen_install_start(false);

  // Idempotent forward-only push over GPIO serial recovery; skipped if the
  // live nRF already matches. MCUboot on the nRF remains the last gate.
  bool ok = true;
  if (nrf_update_required(image, image_len)) {
    ok = nrf_update_with_progress(image, image_len, nrf_resume_progress);
  }

  if (ok == true) {
    nrf_staging_clear();
    return;
  }

  // Keep the staging so a power-cycle re-pushes; do not boot with an
  // incompatible co-processor.
  error_shutdown("nRF update failed");
}

workflow_result_t workflow_nrf_ota_update(
    protob_io_t *iface, const merkle_proof_node_t *model_root,
    const uint8_t *co_path, size_t co_path_len, const uint8_t *image_hash,
    size_t image_hash_len, uint32_t nrf_length) {
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
  // A present hint that is not a SHA-256 is malformed, not absent.
  if (image_hash_len != 0 && image_hash_len != SHA256_DIGEST_LENGTH) {
    return nrf_fail(iface, "Invalid nRF image hash");
  }

  // Key-set cross-check: an nRF declaring a key set other than ours would
  // refuse the pushed image. UNDECLARED (older nRF builds) and an unqueryable
  // nRF fall through to streaming, the safe direction.
#if BOOTLOADER_DEVEL
  const uint8_t want_key_set = NRF_KEY_SET_DEVEL;
#else
  const uint8_t want_key_set = NRF_KEY_SET_PRODUCTION;
#endif
  nrf_info_t info;
  const bool have_info = nrf_get_info(&info);
  if (have_info && info.key_set != NRF_KEY_SET_UNDECLARED &&
      info.key_set != want_key_set) {
    return nrf_fail(iface, "nRF key set does not match this bootloader");
  }

  // Update-required hint: skip the stream if the live nRF already reports
  // this hash. The hint decides whether we stream, so it is fold-verified
  // first; a hint that does not fold rejects the whole upload.
  if (image_hash != NULL && image_hash_len == SHA256_DIGEST_LENGTH) {
    if (nrf_image_verify_hash_in_tree(image_hash,
                                      (const merkle_proof_node_t *)co_path,
                                      co_path_count, model_root) != sectrue) {
      return nrf_fail(iface, "nRF image not in founder tree");
    }
    if (have_info && memcmp(info.hash, image_hash, SHA256_DIGEST_LENGTH) == 0) {
      return WF_OK;  // already up to date
    }
  }

  // Static to keep the co-path copy off the stack; zeroed across retries.
  // Suppresses its own Success (the phase-1 caller sends the single terminal
  // one) and tags requests with NRF_OTA_REQUEST_INDEX.
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
