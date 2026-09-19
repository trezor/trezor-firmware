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

#include <sec/rsod_special.h>
#include <sys/bootargs.h>
#include <sys/bootutils.h>
#include <sys/flash.h>
#include <sys/flash_utils.h>
#include <sys/systick.h>

#if defined(LOCKABLE_BOOTLOADER) || USE_STORAGE_HWKEY
#include <sec/secret.h>
#endif

#ifdef USE_BACKUP_RAM
#include <sec/backup_ram.h>
#endif

#include "bootui.h"
#include "protob/protob.h"
#include "version_check.h"
#include "wf_image_upload.h"
#include "workflow.h"

#ifdef TREZOR_EMULATOR
#include "emulator.h"
#endif

// Firmware-specific upload handler. Embeds the generic handler vtable plus the
// state that the firmware validation needs to carry across chunks.
typedef struct {
  image_upload_handler_t base;
  image_header hdr;       // copy of the received firmware header
  size_t headers_offset;  // offset of the code within the first block
                          // (vhdr.hdrlen + IMAGE_HEADER_SIZE)
#ifdef USE_SECMON_VERIFICATION
  size_t secmon_code_offset;  // offset of the secmon code in the current block
  size_t secmon_code_size;    // size of the secmon code
  size_t secmon_code_processed;  // size of the processed secmon code
  uint8_t expected_secmon_hash[IMAGE_HASH_DIGEST_LENGTH];  // expected hash of
                                                           // the secmon code
  // todo should be IMAGE_HASH_CTX, but due to limitations of the hash_processor
  //  driver implementation, we can't run two hash calculations in parallel so
  //  temporarily we use SW hashing for secmon code during update.
  //  As secmon is only used on U5 MCUs where also SHA256is used for image
  //  hashes, this works, but should be fixed by improving the hash_processor
  SHA256_CTX secmon_hash_ctx;
#endif
} fw_upload_handler_t;

static int version_compare(uint32_t vera, uint32_t verb) {
  /* Explicit casts so that we control how compiler does the unsigned shift
   * and correctly then promote uint8_t to int without possibility of
   * having implementation-defined right shift on negative int
   * in case compiler promoted the wrong unsigned int
   */
  int a, b;
  a = (uint8_t)vera & 0xFF;
  b = (uint8_t)verb & 0xFF;
  if (a != b) return a - b;
  a = (uint8_t)(vera >> 8) & 0xFF;
  b = (uint8_t)(verb >> 8) & 0xFF;
  if (a != b) return a - b;
  a = (uint8_t)(vera >> 16) & 0xFF;
  b = (uint8_t)(verb >> 16) & 0xFF;
  if (a != b) return a - b;
  a = (uint8_t)(vera >> 24) & 0xFF;
  b = (uint8_t)(verb >> 24) & 0xFF;
  return a - b;
}

static void detect_installation(const vendor_header *current_vhdr,
                                const image_header *current_hdr,
                                const vendor_header *const new_vhdr,
                                const image_header *const new_hdr,
                                secbool *is_new, secbool *keep_seed,
                                secbool *is_newvendor, secbool *is_upgrade) {
  *is_new = secfalse;
  *keep_seed = secfalse;
  *is_newvendor = secfalse;
  *is_upgrade = secfalse;
  if (sectrue != check_vendor_header_keys(current_vhdr)) {
    *is_new = sectrue;
    return;
  }
  if (sectrue != check_image_model(current_hdr)) {
    *is_new = sectrue;
    return;
  }
  if (sectrue != check_firmware_min_version(current_hdr->monotonic)) {
    *is_new = sectrue;
    return;
  }
  if (sectrue != check_image_header_sig(current_hdr, current_vhdr->vsig_m,
                                        current_vhdr->vsig_n,
                                        current_vhdr->vpub)) {
    *is_new = sectrue;
    return;
  }
  uint8_t hash1[32], hash2[32];
  vendor_header_hash(new_vhdr, hash1);
  vendor_header_hash(current_vhdr, hash2);
  if (0 != memcmp(hash1, hash2, 32)) {
    *is_newvendor = sectrue;
    return;
  }
  if (version_compare(new_hdr->version, current_hdr->fix_version) < 0) {
    return;
  }
  if (version_compare(new_hdr->version, current_hdr->version) > 0) {
    *is_upgrade = sectrue;
  }

  *keep_seed = sectrue;
}

static upload_status_t fw_on_headers(image_upload_handler_t *base,
                                     protob_io_t *iface, const uint8_t *buf,
                                     size_t len) {
  fw_upload_handler_t *self = (fw_upload_handler_t *)base;
  (void)len;

  vendor_header vhdr;

  if (sectrue != read_vendor_header(buf, IMAGE_CHUNK_SIZE, &vhdr)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid vendor header");
    return UPLOAD_ERR_INVALID_VENDOR_HEADER;
  }

  if (sectrue != check_vendor_header_model(&vhdr)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError, "Wrong model");
    return UPLOAD_ERR_INVALID_VENDOR_HEADER_MODEL;
  }

  if (sectrue != check_vendor_header_keys(&vhdr)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid vendor header signature");
    return UPLOAD_ERR_INVALID_VENDOR_HEADER_SIG;
  }

  const image_header *received_hdr = read_image_header(
      buf + vhdr.hdrlen, FIRMWARE_IMAGE_MAGIC, FIRMWARE_MAXSIZE);

  if (received_hdr != (const image_header *)(buf + vhdr.hdrlen)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid firmware header");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER;
  }

  if (sectrue != check_image_model(received_hdr)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Wrong firmware model");
    return UPLOAD_ERR_INVALID_IMAGE_MODEL;
  }

  if (sectrue != check_image_header_sig(received_hdr, vhdr.vsig_m, vhdr.vsig_n,
                                        vhdr.vpub)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid firmware signature");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
  }

  if (sectrue != check_firmware_min_version(received_hdr->monotonic)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Firmware downgrade protection");
    return UPLOAD_ERR_INVALID_IMAGE_HEADER_VERSION;
  }

#ifdef USE_SECMON_VERIFICATION
  size_t secmon_start_offset =
      (size_t)IMAGE_CODE_ALIGN(vhdr.hdrlen + IMAGE_HEADER_SIZE);
  size_t secmon_start = (size_t)buf + secmon_start_offset;
  const secmon_header_t *secmon_hdr =
      read_secmon_header((const uint8_t *)secmon_start, FIRMWARE_MAXSIZE);

  if (secmon_hdr != NULL) {
    self->secmon_code_offset =
        IMAGE_CODE_ALIGN(vhdr.hdrlen + IMAGE_HEADER_SIZE) + SECMON_HEADER_SIZE;
  }

  if (secmon_hdr != (const secmon_header_t *)secmon_start) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid secmon header");
    return UPLOAD_ERR_INVALID_SECMON_HEADER;
  }

  if (sectrue != check_secmon_model(secmon_hdr)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Wrong secmon model");
    return UPLOAD_ERR_INVALID_SECMON_MODEL;
  }

  if (sectrue != check_secmon_header_sig(secmon_hdr)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid secmon signature");
    return UPLOAD_ERR_INVALID_SECMON_HEADER_SIG;
  }

  if (sectrue != check_secmon_min_version(secmon_hdr->monotonic)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Secmon downgrade protection");
    return UPLOAD_ERR_INVALID_SECMON_VERSION;
  }

  self->secmon_code_size = secmon_hdr->codelen;

  memcpy(self->expected_secmon_hash, secmon_hdr->hash,
         IMAGE_HASH_DIGEST_LENGTH);
#endif

  memcpy(&self->hdr, received_hdr, sizeof(self->hdr));

  vendor_header current_vhdr;

  secbool is_new = secfalse;

  if (sectrue != read_vendor_header((const uint8_t *)FIRMWARE_START,
                                    VENDOR_HEADER_MAX_SIZE, &current_vhdr)) {
    is_new = sectrue;
  }

  const image_header *current_hdr = NULL;

  if (is_new == secfalse) {
    current_hdr =
        read_image_header((const uint8_t *)FIRMWARE_START + current_vhdr.hdrlen,
                          FIRMWARE_IMAGE_MAGIC, FIRMWARE_MAXSIZE);

    if (current_hdr !=
        (const image_header *)(void *)(FIRMWARE_START + current_vhdr.hdrlen)) {
      is_new = sectrue;
    }
  }

  secbool should_keep_seed = secfalse;
  secbool is_newvendor = secfalse;
  secbool is_upgrade = secfalse;
  if (is_new == secfalse) {
    detect_installation(&current_vhdr, current_hdr, &vhdr, &self->hdr, &is_new,
                        &should_keep_seed, &is_newvendor, &is_upgrade);
  }

  secbool is_ilu = secfalse;  // interaction-less update

  if (bootargs_get_command() == BOOT_COMMAND_INSTALL_UPGRADE) {
    IMAGE_HASH_CTX ilu_ctx;
    uint8_t hash[IMAGE_HASH_DIGEST_LENGTH];
    IMAGE_HASH_INIT(&ilu_ctx);
    IMAGE_HASH_UPDATE(&ilu_ctx, buf, vhdr.hdrlen + received_hdr->hdrlen);
    IMAGE_HASH_FINAL(&ilu_ctx, hash);

    // the firmware must be the same as confirmed by the user
    boot_args_t args = {0};
    bootargs_get_args(&args);

    if (memcmp(args.hash, hash, sizeof(hash)) != 0) {
      send_msg_failure(iface, FailureType_Failure_ProcessError,
                       "Firmware mismatch");
      return UPLOAD_ERR_FIRMWARE_MISMATCH;
    }

    // the firmware must be from the same vendor
    // the firmware must be newer
    if (is_upgrade != sectrue || is_newvendor != secfalse) {
      send_msg_failure(iface, FailureType_Failure_ProcessError,
                       "Not a firmware upgrade");
      return UPLOAD_ERR_NOT_FIRMWARE_UPGRADE;
    }

    if ((vhdr.vtrust & VTRUST_NO_WARNING) != VTRUST_NO_WARNING) {
      send_msg_failure(iface, FailureType_Failure_ProcessError,
                       "Not a full-trust image");
      return UPLOAD_ERR_NOT_FULLTRUST_IMAGE;
    }

    // upload the firmware without confirmation
    is_ilu = sectrue;
  }

#if defined LOCKABLE_BOOTLOADER
  if (secfalse != secret_bootloader_locked() &&
      ((vhdr.vtrust & VTRUST_SECRET_MASK) != VTRUST_SECRET_ALLOW)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Install restricted");
    return UPLOAD_ERR_BOOTLOADER_LOCKED;
  }
#endif

#ifdef USE_SECMON_VERIFICATION
  if (self->secmon_code_size >
      ((self->hdr.codelen + IMAGE_HEADER_SIZE + vhdr.hdrlen) -
       self->secmon_code_offset)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Secmon code too big");
    return UPLOAD_ERR_SECMON_TOO_BIG;
  }
#endif

  confirm_result_t response = CANCEL;
  if (((vhdr.vtrust & VTRUST_NO_WARNING) == VTRUST_NO_WARNING) &&
      (sectrue == is_new || sectrue == is_ilu)) {
    // new installation or interaction less updated - auto confirm
    // only allowed for full-trust images
    response = CONFIRM;
  } else {
    if (sectrue != is_new) {
      int version_cmp =
          version_compare(self->hdr.version, current_hdr->version);
      response = ui_screen_install_confirm(&vhdr, &self->hdr, should_keep_seed,
                                           is_newvendor, is_new, version_cmp);
    } else {
      response = ui_screen_install_confirm(&vhdr, &self->hdr, sectrue,
                                           is_newvendor, is_new, 0);
    }
  }

  if (CONFIRM != response) {
    send_user_abort(iface, "Firmware install cancelled");
    return UPLOAD_ERR_USER_ABORT;
  }

  ui_screen_install_start(iface->wire->wireless);

  // if firmware is not upgrade, erase storage
  if (sectrue != should_keep_seed) {
#ifdef USE_STORAGE_HWKEY
    secret_bhk_regenerate();
#endif
    ensure(erase_storage(NULL), NULL);
#ifdef USE_BACKUP_RAM
    ensure(backup_ram_erase_protected() * sectrue, NULL);
#endif
  }

  self->headers_offset = IMAGE_HEADER_SIZE + vhdr.hdrlen;

  return UPLOAD_OK;
}

static upload_status_t fw_on_chunk(image_upload_handler_t *base,
                                   protob_io_t *iface, uint32_t block_idx,
                                   const uint8_t *data, size_t len) {
  fw_upload_handler_t *self = (fw_upload_handler_t *)base;

  size_t skip = (block_idx == 0) ? self->headers_offset : 0;

  if (sectrue != check_single_hash(self->hdr.hashes + block_idx * 32,
                                   data + skip, len - skip)) {
    // engine handles retry; do not send a failure message here
    return UPLOAD_ERR_INVALID_CHUNK_HASH;
  }

#ifdef USE_SECMON_VERIFICATION
  // validate secmon code hash
  if (self->secmon_code_size > 0) {
    if (self->secmon_code_processed == 0) {
      // todo SW SHA256, see comment in fw_upload_handler_t
      sha256_Init(&self->secmon_hash_ctx);
    }

    size_t secmon_code_remaining =
        self->secmon_code_size - self->secmon_code_processed;

    size_t secmon_code_to_process = IMAGE_CHUNK_SIZE - self->secmon_code_offset;

    secmon_code_to_process = MIN(secmon_code_to_process, secmon_code_remaining);

    sha256_Update(&self->secmon_hash_ctx, data + self->secmon_code_offset,
                  secmon_code_to_process);

    self->secmon_code_processed += secmon_code_to_process;
    self->secmon_code_offset = 0;

    if (self->secmon_code_processed >= self->secmon_code_size) {
      // secmon code is fully processed
      uint8_t secmon_hash[IMAGE_HASH_DIGEST_LENGTH];
      sha256_Final(&self->secmon_hash_ctx, secmon_hash);

      if (memcmp(secmon_hash, self->expected_secmon_hash,
                 IMAGE_HASH_DIGEST_LENGTH) != 0) {
        send_msg_failure(iface, FailureType_Failure_ProcessError,
                         "Invalid secmon hash");
        return UPLOAD_ERR_INVALID_SECMON_HASH;
      }
      self->secmon_code_size = 0;  // reset secmon code size to prevent
      // reprocessing in the next chunk
    }
  }
#endif

  return UPLOAD_OK;
}

static upload_status_t fw_on_finish(image_upload_handler_t *base,
                                    protob_io_t *iface) {
  (void)base;
  (void)iface;
  // The firmware image is now live in FIRMWARE_AREA; nothing else to do.
  return UPLOAD_OK;
}

static void fw_ui_progress(int permille, bool wireless) {
  ui_screen_install_progress_upload(permille, wireless);
}

static void fw_ui_success(bool wireless) {
  ui_screen_install_progress_upload(1000, wireless);
  ui_screen_done(4, sectrue);
  ui_screen_done(3, secfalse);
  systick_delay_ms(1000);
  ui_screen_done(2, secfalse);
  systick_delay_ms(1000);
  ui_screen_done(1, secfalse);
  systick_delay_ms(1000);
}

static void fw_ui_fail(upload_status_t status) {
  if (status == UPLOAD_ERR_BOOTLOADER_LOCKED) {
    // This function does not return
    show_install_restricted_screen();
  } else {
    ui_screen_fail();
  }
}

static const image_upload_ui_t fw_upload_ui = {
    .progress = fw_ui_progress,
    .success = fw_ui_success,
    .fail = fw_ui_fail,
};

workflow_result_t workflow_firmware_update(protob_io_t *iface) {
  FirmwareErase msg;
  if (sectrue != recv_msg_firmware_erase(iface, &msg)) {
    return WF_ERROR;
  }

  fw_upload_handler_t handler = {
      .base =
          {
              .target_area = &FIRMWARE_AREA,
              .max_size = FIRMWARE_MAXSIZE,
              .success_result = WF_OK_FIRMWARE_INSTALLED,
              .ui = &fw_upload_ui,
              .on_headers = fw_on_headers,
              .on_chunk = fw_on_chunk,
              .on_finish = fw_on_finish,
          },
  };

  return run_image_upload(iface, &handler.base,
                          msg.has_length ? msg.length : 0);
}
