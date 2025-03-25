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

#include <sys/bootargs.h>
#include <sys/systick.h>
#include <util/flash.h>
#include <util/flash_utils.h>

#if USE_OPTIGA || USE_STORAGE_HWKEY
#include <sec/secret.h>
#endif

#include <poll.h>

#include "bootui.h"
#include "protob/protob.h"
#include "version_check.h"
#include "workflow.h"

#ifdef TREZOR_EMULATOR
#include "emulator.h"
#endif

typedef enum {
  UPLOAD_OK = 0,
  UPLOAD_IN_PROGRESS = 1,
  UPLOAD_ERR_INVALID_CHUNK_SIZE = -1,
  UPLOAD_ERR_INVALID_VENDOR_HEADER = -2,
  UPLOAD_ERR_INVALID_VENDOR_HEADER_SIG = -3,
  UPLOAD_ERR_INVALID_VENDOR_HEADER_MODEL = -15,
  UPLOAD_ERR_INVALID_IMAGE_HEADER = -4,
  UPLOAD_ERR_INVALID_IMAGE_MODEL = -5,
  UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG = -6,
  UPLOAD_ERR_INVALID_IMAGE_HEADER_VERSION = -16,
  UPLOAD_ERR_USER_ABORT = -7,
  UPLOAD_ERR_FIRMWARE_TOO_BIG = -8,
  UPLOAD_ERR_INVALID_CHUNK_HASH = -9,
  UPLOAD_ERR_BOOTLOADER_LOCKED = -10,
  UPLOAD_ERR_FIRMWARE_MISMATCH = -11,
  UPLOAD_ERR_NOT_FIRMWARE_UPGRADE = -12,
  UPLOAD_ERR_NOT_FULLTRUST_IMAGE = -13,
  UPLOAD_ERR_INVALID_CHUNK_PADDING = -14,
  UPLOAD_ERR_COMMUNICATION = -17,
} upload_status_t;

#define FIRMWARE_UPLOAD_CHUNK_RETRY_COUNT 2

#ifndef TREZOR_EMULATOR
__attribute__((section(".buf")))
#endif
uint32_t chunk_buffer[IMAGE_CHUNK_SIZE / 4];

typedef struct {
  uint32_t firmware_remaining;          // remaining bytes to upload
  uint32_t firmware_block;              // index of currently processed block
  uint32_t chunk_requested;             // requested chunk size
  uint32_t erase_offset;                // offset of flash memory to erase
  int32_t firmware_upload_chunk_retry;  // retry counter
  size_t headers_offset;                // offset of headers in the first block
  size_t read_offset;   // offset of the next read data in the chunk buffer
  uint32_t chunk_size;  // size of already received chunk data
} firmware_update_ctx_t;

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

static void fw_data_received(size_t len, void *ctx) {
  firmware_update_ctx_t *context = (firmware_update_ctx_t *)ctx;

  context->chunk_size += len;
  // update loader but skip first block
  if (context->firmware_block > 0) {
    ui_screen_install_progress_upload(
        1000 *
        (context->firmware_block * IMAGE_CHUNK_SIZE + context->chunk_size) /
        (context->firmware_block * IMAGE_CHUNK_SIZE +
         context->firmware_remaining));
  }
}

static upload_status_t process_msg_FirmwareUpload(protob_io_t *iface,
                                                  firmware_update_ctx_t *ctx) {
  FirmwareUpload msg;

  const secbool r =
      recv_msg_firmware_upload(iface, &msg, ctx, fw_data_received,
                               &((uint8_t *)chunk_buffer)[ctx->read_offset],
                               sizeof(chunk_buffer) - ctx->read_offset);

  if (sectrue != r ||
      ctx->chunk_size != (ctx->chunk_requested + ctx->read_offset)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid chunk size");
    return UPLOAD_ERR_INVALID_CHUNK_SIZE;
  }

  static image_header hdr;

  if (ctx->firmware_block == 0) {
    if (ctx->headers_offset == 0) {
      // first block and headers are not yet parsed
      vendor_header vhdr;

      if (sectrue != read_vendor_header((uint8_t *)chunk_buffer, &vhdr)) {
        send_msg_failure(iface, FailureType_Failure_ProcessError,
                         "Invalid vendor header");
        return UPLOAD_ERR_INVALID_VENDOR_HEADER;
      }

      if (sectrue != check_vendor_header_model(&vhdr)) {
        send_msg_failure(iface, FailureType_Failure_ProcessError,
                         "Wrong model");
        return UPLOAD_ERR_INVALID_VENDOR_HEADER_MODEL;
      }

      if (sectrue != check_vendor_header_keys(&vhdr)) {
        send_msg_failure(iface, FailureType_Failure_ProcessError,
                         "Invalid vendor header signature");
        return UPLOAD_ERR_INVALID_VENDOR_HEADER_SIG;
      }

      const image_header *received_hdr =
          read_image_header((uint8_t *)chunk_buffer + vhdr.hdrlen,
                            FIRMWARE_IMAGE_MAGIC, FIRMWARE_MAXSIZE);

      if (received_hdr !=
          (const image_header *)((uint8_t *)chunk_buffer + vhdr.hdrlen)) {
        send_msg_failure(iface, FailureType_Failure_ProcessError,
                         "Invalid firmware header");
        return UPLOAD_ERR_INVALID_IMAGE_HEADER;
      }

      if (sectrue != check_image_model(received_hdr)) {
        send_msg_failure(iface, FailureType_Failure_ProcessError,
                         "Wrong firmware model");
        return UPLOAD_ERR_INVALID_IMAGE_MODEL;
      }

      if (sectrue != check_image_header_sig(received_hdr, vhdr.vsig_m,
                                            vhdr.vsig_n, vhdr.vpub)) {
        send_msg_failure(iface, FailureType_Failure_ProcessError,
                         "Invalid firmware signature");
        return UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG;
      }

      if (sectrue != check_firmware_min_version(received_hdr->monotonic)) {
        send_msg_failure(iface, FailureType_Failure_ProcessError,
                         "Firmware downgrade protection");
        return UPLOAD_ERR_INVALID_IMAGE_HEADER_VERSION;
      }

      memcpy(&hdr, received_hdr, sizeof(hdr));

      vendor_header current_vhdr;

      secbool is_new = secfalse;

      if (sectrue !=
          read_vendor_header((const uint8_t *)FIRMWARE_START, &current_vhdr)) {
        is_new = sectrue;
      }

      const image_header *current_hdr = NULL;

      if (is_new == secfalse) {
        current_hdr = read_image_header(
            (const uint8_t *)FIRMWARE_START + current_vhdr.hdrlen,
            FIRMWARE_IMAGE_MAGIC, FIRMWARE_MAXSIZE);

        if (current_hdr !=
            (const image_header *)(void *)(FIRMWARE_START +
                                           current_vhdr.hdrlen)) {
          is_new = sectrue;
        }
      }

      secbool should_keep_seed = secfalse;
      secbool is_newvendor = secfalse;
      secbool is_upgrade = secfalse;
      if (is_new == secfalse) {
        detect_installation(&current_vhdr, current_hdr, &vhdr, &hdr, &is_new,
                            &should_keep_seed, &is_newvendor, &is_upgrade);
      }

      secbool is_ilu = secfalse;  // interaction-less update

      if (bootargs_get_command() == BOOT_COMMAND_INSTALL_UPGRADE) {
        IMAGE_HASH_CTX ctx;
        uint8_t hash[IMAGE_HASH_DIGEST_LENGTH];
        IMAGE_HASH_INIT(&ctx);
        IMAGE_HASH_UPDATE(&ctx, (uint8_t *)chunk_buffer,
                          vhdr.hdrlen + received_hdr->hdrlen);
        IMAGE_HASH_FINAL(&ctx, hash);

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

#if defined USE_OPTIGA
      if (secfalse != secret_optiga_present() &&
          ((vhdr.vtrust & VTRUST_SECRET_MASK) != VTRUST_SECRET_ALLOW)) {
        send_msg_failure(iface, FailureType_Failure_ProcessError,
                         "Install restricted");
        return UPLOAD_ERR_BOOTLOADER_LOCKED;
      }
#endif

      ui_result_t response = UI_RESULT_CANCEL;
      if (((vhdr.vtrust & VTRUST_NO_WARNING) == VTRUST_NO_WARNING) &&
          (sectrue == is_new || sectrue == is_ilu)) {
        // new installation or interaction less updated - auto confirm
        // only allowed for full-trust images
        response = UI_RESULT_CONFIRM;
      } else {
        if (sectrue != is_new) {
          int version_cmp = version_compare(hdr.version, current_hdr->version);
          response = ui_screen_install_confirm(
              &vhdr, &hdr, should_keep_seed, is_newvendor, is_new, version_cmp);
        } else {
          response = ui_screen_install_confirm(&vhdr, &hdr, sectrue,
                                               is_newvendor, is_new, 0);
        }
      }

      if (UI_RESULT_CONFIRM != response) {
        send_user_abort(iface, "Firmware install cancelled");
        return UPLOAD_ERR_USER_ABORT;
      }

      ui_screen_install_start();

      // if firmware is not upgrade, erase storage
      if (sectrue != should_keep_seed) {
#ifdef USE_STORAGE_HWKEY
        secret_bhk_regenerate();
#endif
        ensure(erase_storage(NULL), NULL);
      }

      ctx->headers_offset = IMAGE_HEADER_SIZE + vhdr.hdrlen;
      ctx->read_offset = IMAGE_INIT_CHUNK_SIZE;

      // request the rest of the first chunk
      uint32_t chunk_limit = (ctx->firmware_remaining > IMAGE_CHUNK_SIZE)
                                 ? IMAGE_CHUNK_SIZE
                                 : ctx->firmware_remaining;
      ctx->chunk_requested = chunk_limit - ctx->read_offset;

      if (sectrue != send_msg_request_firmware(iface, ctx->read_offset,
                                               ctx->chunk_requested)) {
        return UPLOAD_ERR_COMMUNICATION;
      }

      ctx->firmware_remaining -= ctx->read_offset;
      if (ctx->firmware_remaining > 0) {
        return UPLOAD_IN_PROGRESS;
      }
      return UPLOAD_OK;
    } else {
      // first block with the headers parsed -> the first chunk is now complete
      ctx->read_offset = 0;
    }
  }

  // should not happen, but double-check
  if (flash_area_get_address(
          &FIRMWARE_AREA, ctx->firmware_block * IMAGE_CHUNK_SIZE, 0) == NULL) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Firmware too big");
    return UPLOAD_ERR_FIRMWARE_TOO_BIG;
  }

  if (sectrue !=
      check_single_hash(hdr.hashes + ctx->firmware_block * 32,
                        (uint8_t *)chunk_buffer + ctx->headers_offset,
                        ctx->chunk_size - ctx->headers_offset)) {
    if (ctx->firmware_upload_chunk_retry > 0) {
      --ctx->firmware_upload_chunk_retry;

      // clear chunk buffer
      memset((uint8_t *)&chunk_buffer, 0xFF, IMAGE_CHUNK_SIZE);
      ctx->chunk_size = 0;

      if (sectrue != send_msg_request_firmware(
                         iface, ctx->firmware_block * IMAGE_CHUNK_SIZE,
                         ctx->chunk_requested)) {
        return UPLOAD_ERR_COMMUNICATION;
      }
      if (ctx->firmware_remaining > 0) {
        return UPLOAD_IN_PROGRESS;
      }
      return UPLOAD_OK;
    }

    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid chunk hash");
    return UPLOAD_ERR_INVALID_CHUNK_HASH;
  }

  // buffer with the received data
  const uint32_t *src = (const uint32_t *)chunk_buffer;
  // number of received bytes
  uint32_t bytes_remaining = ctx->chunk_size;
  // offset into the FIRMWARE_AREA part of the flash
  uint32_t write_offset = ctx->firmware_block * IMAGE_CHUNK_SIZE;

  ensure((ctx->chunk_size % FLASH_BLOCK_SIZE == 0) * sectrue, NULL);

  while (bytes_remaining > 0) {
    // erase flash before writing
    uint32_t bytes_erased = 0;

    if (write_offset >= ctx->erase_offset) {
      // erase the next flash section
      ensure(flash_area_erase_partial(&FIRMWARE_AREA, ctx->erase_offset,
                                      &bytes_erased),
             NULL);
      ctx->erase_offset += bytes_erased;
    } else {
      // some erased space left from the previous round => use it
      bytes_erased = ctx->erase_offset - write_offset;
    }

    // write the received data
    uint32_t bytes_to_write = MIN(bytes_erased, bytes_remaining);
    ensure(flash_unlock_write(), NULL);
    ensure(flash_area_write_data(&FIRMWARE_AREA, write_offset, src,
                                 bytes_to_write),
           NULL);
    ensure(flash_lock_write(), NULL);

    write_offset += bytes_to_write;
    src += bytes_to_write / sizeof(uint32_t);

    bytes_remaining -= bytes_to_write;
  }

  ctx->firmware_remaining -= ctx->chunk_requested;

  if (ctx->firmware_remaining == 0) {
    // erase the rest (unused part) of the FIRMWARE_AREA
    uint32_t bytes_erased = 0;
    do {
      ensure(flash_area_erase_partial(&FIRMWARE_AREA, ctx->erase_offset,
                                      &bytes_erased),
             NULL);
      ctx->erase_offset += bytes_erased;
    } while (bytes_erased > 0);
  }

  ctx->headers_offset = 0;
  ctx->firmware_block++;
  ctx->firmware_upload_chunk_retry = FIRMWARE_UPLOAD_CHUNK_RETRY_COUNT;

  if (ctx->firmware_remaining > 0) {
    ctx->chunk_requested = (ctx->firmware_remaining > IMAGE_CHUNK_SIZE)
                               ? IMAGE_CHUNK_SIZE
                               : ctx->firmware_remaining;

    // clear chunk buffer
    ctx->chunk_size = 0;
    memset((uint8_t *)&chunk_buffer, 0xFF, IMAGE_CHUNK_SIZE);
    if (sectrue !=
        send_msg_request_firmware(iface, ctx->firmware_block * IMAGE_CHUNK_SIZE,
                                  ctx->chunk_requested)) {
      return UPLOAD_ERR_COMMUNICATION;
    }
  } else {
    send_msg_success(iface, NULL);
  }

  if (ctx->firmware_remaining > 0) {
    return UPLOAD_IN_PROGRESS;
  }
  return UPLOAD_OK;
}

workflow_result_t workflow_firmware_update(protob_io_t *iface) {
  firmware_update_ctx_t ctx = {
      .firmware_upload_chunk_retry = FIRMWARE_UPLOAD_CHUNK_RETRY_COUNT,
  };

  FirmwareErase msg;
  secbool res = recv_msg_firmware_erase(iface, &msg);

  if (res != sectrue) {
    return WF_ERROR;
  }

  ctx.firmware_remaining = msg.has_length ? msg.length : 0;
  if ((ctx.firmware_remaining > 0) &&
      ((ctx.firmware_remaining % sizeof(uint32_t)) == 0) &&
      (ctx.firmware_remaining <= FIRMWARE_MAXSIZE)) {
    // clear chunk buffer
    memset((uint8_t *)&chunk_buffer, 0xFF, IMAGE_CHUNK_SIZE);
    ctx.chunk_size = 0;

    // request new firmware
    ctx.chunk_requested = (ctx.firmware_remaining > IMAGE_INIT_CHUNK_SIZE)
                              ? IMAGE_INIT_CHUNK_SIZE
                              : ctx.firmware_remaining;
    if (sectrue != send_msg_request_firmware(iface, 0, ctx.chunk_requested)) {
      ui_screen_fail();
      return WF_ERROR;
    }
  } else {
    // invalid firmware size
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Wrong firmware size");
    return WF_ERROR;
  }

  upload_status_t s = UPLOAD_IN_PROGRESS;

  while (true) {
    uint16_t ifaces[1] = {protob_get_iface_flag(iface) | MODE_READ};
    poll_event_t e = {0};
    uint8_t i = poll_events(ifaces, 1, &e, 100);

    if (e.type == EVENT_NONE || i != protob_get_iface_flag(iface)) {
      continue;
    }

    uint16_t msg_id = 0;

    if (sectrue != protob_get_msg_header(iface, &msg_id)) {
      // invalid header -> discard
      return WF_ERROR;
    }
    s = process_msg_FirmwareUpload(iface, &ctx);

    if (s < 0 && s != UPLOAD_ERR_USER_ABORT) {  // error, but not user abort
      if (s == UPLOAD_ERR_BOOTLOADER_LOCKED) {
        // This function does not return
        show_install_restricted_screen();
      } else {
        ui_screen_fail();
      }
      return WF_ERROR;
    } else if (s == UPLOAD_ERR_USER_ABORT) {
      systick_delay_ms(100);
      return WF_CANCELLED;
    } else if (s == UPLOAD_OK) {  // last chunk received
      ui_screen_install_progress_upload(1000);
      ui_screen_done(4, sectrue);
      ui_screen_done(3, secfalse);
      systick_delay_ms(1000);
      ui_screen_done(2, secfalse);
      systick_delay_ms(1000);
      ui_screen_done(1, secfalse);
      systick_delay_ms(1000);
      return WF_OK_FIRMWARE_INSTALLED;
    }
  }
}
