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

#include <sys/flash.h>
#include <sys/flash_utils.h>
#include <sys/sysevent.h>
#include <sys/systick.h>

#include "protob/protob.h"
#include "wf_image_upload.h"
#include "workflow.h"

#define MESSAGE_RX_TIMEOUT 10000

#define FIRMWARE_UPLOAD_CHUNK_RETRY_COUNT 2

// Single staging buffer shared by the upload engine. One IMAGE_CHUNK_SIZE chunk
// is received here, verified by the handler, and then written to flash.
#ifndef TREZOR_EMULATOR
__attribute__((section(".buf")))
#endif
uint32_t chunk_buffer[IMAGE_CHUNK_SIZE / 4];

// Transport-level state of an in-progress upload. Everything here is
// image-type-agnostic; type-specific state lives in the handler.
typedef struct {
  uint32_t remaining;        // remaining bytes to upload
  uint32_t block;            // index of currently processed block
  uint32_t chunk_requested;  // requested chunk size
  uint32_t erase_offset;     // offset of flash memory to erase
  int32_t chunk_retry;       // retry counter
  size_t read_offset;        // offset of the next read data in the chunk buffer
  uint32_t chunk_size;       // size of already received chunk data
  bool headers_parsed;      // true once the first chunk's headers are validated
  bool confirmed;           // true once the upload is confirmed by the user
  bool wireless_transport;  // whether the transport is over BLE
  image_upload_handler_t *handler;  // active image-type handler
} upload_engine_t;

static void upload_data_received(size_t len, void *ctx) {
  upload_engine_t *e = (upload_engine_t *)ctx;

  e->chunk_size += len;
  // update loader only after the update is confirmed
  if (e->confirmed) {
    e->handler->ui->progress(1000 *
                                 (e->block * IMAGE_CHUNK_SIZE + e->chunk_size) /
                                 (e->block * IMAGE_CHUNK_SIZE + e->remaining),
                             e->wireless_transport);
  }
}

static upload_status_t process_upload_chunk(protob_io_t *iface,
                                            image_upload_handler_t *handler,
                                            upload_engine_t *e) {
  FirmwareUpload msg;

  const secbool r =
      recv_msg_firmware_upload(iface, &msg, e, upload_data_received,
                               &((uint8_t *)chunk_buffer)[e->read_offset],
                               sizeof(chunk_buffer) - e->read_offset);

  if (sectrue != r || e->chunk_size != (e->chunk_requested + e->read_offset)) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid chunk size");
    return UPLOAD_ERR_INVALID_CHUNK_SIZE;
  }

  if (e->block == 0) {
    if (!e->headers_parsed) {
      // first block and headers are not yet parsed -> let the handler validate
      // all headers, signatures, versions and run user confirmation / policy
      upload_status_t s = handler->on_headers(
          handler, iface, (const uint8_t *)chunk_buffer, e->chunk_size);
      if (s != UPLOAD_OK) {
        // handler has already sent the failure / abort message
        return s;
      }

      e->headers_parsed = true;
      e->confirmed = true;

      e->read_offset = IMAGE_INIT_CHUNK_SIZE;

      // request the rest of the first chunk
      uint32_t chunk_limit =
          (e->remaining > IMAGE_CHUNK_SIZE) ? IMAGE_CHUNK_SIZE : e->remaining;
      e->chunk_requested = chunk_limit - e->read_offset;

      if (sectrue != send_msg_request_firmware(iface, e->read_offset,
                                               e->chunk_requested)) {
        return UPLOAD_ERR_COMMUNICATION;
      }

      e->remaining -= e->read_offset;
      if (e->remaining > 0) {
        return UPLOAD_IN_PROGRESS;
      }
      return UPLOAD_OK;
    } else {
      // first block with the headers parsed -> the first chunk is now complete
      e->read_offset = 0;
    }
  }

  // should not happen, but double-check
  if (flash_area_get_address(
          handler->target_area,
          handler->target_offset + e->block * IMAGE_CHUNK_SIZE, 0) == NULL) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Firmware too big");
    return UPLOAD_ERR_FIRMWARE_TOO_BIG;
  }

  // type-specific per-chunk integrity verification
  upload_status_t cs = handler->on_chunk(
      handler, iface, e->block, (const uint8_t *)chunk_buffer, e->chunk_size);

  if (cs == UPLOAD_ERR_INVALID_CHUNK_HASH) {
    if (e->chunk_retry > 0) {
      --e->chunk_retry;

      // clear chunk buffer
      memset((uint8_t *)&chunk_buffer, 0xFF, IMAGE_CHUNK_SIZE);
      e->chunk_size = 0;

      if (sectrue != send_msg_request_firmware(iface,
                                               e->block * IMAGE_CHUNK_SIZE,
                                               e->chunk_requested)) {
        return UPLOAD_ERR_COMMUNICATION;
      }
      if (e->remaining > 0) {
        return UPLOAD_IN_PROGRESS;
      }
      return UPLOAD_OK;
    }

    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid chunk hash");
    return UPLOAD_ERR_INVALID_CHUNK_HASH;
  } else if (cs != UPLOAD_OK) {
    // handler has already sent its own failure message
    return cs;
  }

  // buffer with the received data
  const uint32_t *src = (const uint32_t *)chunk_buffer;
  // number of received bytes
  uint32_t bytes_remaining = e->chunk_size;
  // offset into the target area part of the flash (after the base
  // target_offset)
  uint32_t write_offset = handler->target_offset + e->block * IMAGE_CHUNK_SIZE;

  ensure((e->chunk_size % FLASH_BLOCK_SIZE == 0) * sectrue, NULL);

  while (bytes_remaining > 0) {
    // erase flash before writing
    uint32_t bytes_erased = 0;

    if (write_offset >= e->erase_offset) {
      // erase the next flash section
      ensure(flash_area_erase_partial(handler->target_area, e->erase_offset,
                                      &bytes_erased),
             NULL);
      e->erase_offset += bytes_erased;
    } else {
      // some erased space left from the previous round => use it
      bytes_erased = e->erase_offset - write_offset;
    }

    // write the received data
    uint32_t bytes_to_write = MIN(bytes_erased, bytes_remaining);
    ensure(flash_unlock_write(), NULL);
    ensure(flash_area_write_data(handler->target_area, write_offset, src,
                                 bytes_to_write),
           NULL);
    ensure(flash_lock_write(), NULL);

    write_offset += bytes_to_write;
    src += bytes_to_write / sizeof(uint32_t);

    bytes_remaining -= bytes_to_write;
  }

  e->remaining -= e->chunk_requested;

  if (e->remaining == 0) {
    // erase the rest (unused part) of the target area
    uint32_t bytes_erased = 0;
    do {
      ensure(flash_area_erase_partial(handler->target_area, e->erase_offset,
                                      &bytes_erased),
             NULL);
      e->erase_offset += bytes_erased;
    } while (bytes_erased > 0);
  }

  e->block++;
  e->chunk_retry = FIRMWARE_UPLOAD_CHUNK_RETRY_COUNT;

  if (e->remaining > 0) {
    e->chunk_requested =
        (e->remaining > IMAGE_CHUNK_SIZE) ? IMAGE_CHUNK_SIZE : e->remaining;

    // clear chunk buffer
    e->chunk_size = 0;
    memset((uint8_t *)&chunk_buffer, 0xFF, IMAGE_CHUNK_SIZE);
    if (sectrue != send_msg_request_firmware(iface, e->block * IMAGE_CHUNK_SIZE,
                                             e->chunk_requested)) {
      return UPLOAD_ERR_COMMUNICATION;
    }
  } else {
    upload_status_t fs = handler->on_finish(handler, iface);
    if (fs != UPLOAD_OK) {
      // handler has already sent its own failure message
      return fs;
    }
    send_msg_success(iface, NULL);
  }

  if (e->remaining > 0) {
    return UPLOAD_IN_PROGRESS;
  }
  return UPLOAD_OK;
}

workflow_result_t run_image_upload(protob_io_t *iface,
                                   image_upload_handler_t *handler,
                                   uint32_t image_size) {
  upload_engine_t e = {
      .chunk_retry = FIRMWARE_UPLOAD_CHUNK_RETRY_COUNT,
      .handler = handler,
      // Start erasing at the base offset so an already-written prefix (e.g. a
      // staged boot header) is preserved.
      .erase_offset = handler->target_offset,
  };

  e.wireless_transport = iface->wire->wireless;

  e.remaining = image_size;
  if ((e.remaining > 0) && ((e.remaining % sizeof(uint32_t)) == 0) &&
      (e.remaining <= handler->max_size)) {
    // clear chunk buffer
    memset((uint8_t *)&chunk_buffer, 0xFF, IMAGE_CHUNK_SIZE);
    e.chunk_size = 0;

    // request new image
    e.chunk_requested = (e.remaining > IMAGE_INIT_CHUNK_SIZE)
                            ? IMAGE_INIT_CHUNK_SIZE
                            : e.remaining;
    if (sectrue != send_msg_request_firmware(iface, 0, e.chunk_requested)) {
      handler->ui->fail(UPLOAD_ERR_COMMUNICATION);
      return WF_ERROR;
    }
  } else {
    // invalid image size
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Wrong firmware size");
    return WF_ERROR;
  }

  upload_status_t s = UPLOAD_IN_PROGRESS;

  uint32_t msg_deadline = ticks_timeout(MESSAGE_RX_TIMEOUT);

  while (true) {
    sysevents_t awaited = {0};
    sysevents_t signalled = {0};

    awaited.read_ready = 1 << protob_get_iface_flag(iface);

    sysevents_poll(&awaited, &signalled, ticks_timeout(100));

    if (awaited.read_ready != signalled.read_ready) {
      if (ticks_expired(msg_deadline)) {
        // timeout
        handler->ui->fail(UPLOAD_ERR_COMMUNICATION);
        return WF_ERROR;
      }
      continue;
    }

    uint16_t msg_id = 0;

    if (sectrue != protob_get_msg_header(iface, &msg_id)) {
      // invalid header -> discard
      return WF_ERROR;
    }
    s = process_upload_chunk(iface, handler, &e);

    msg_deadline = ticks_timeout(MESSAGE_RX_TIMEOUT);

    if (s < 0 && s != UPLOAD_ERR_USER_ABORT) {  // error, but not user abort
      // the handler decides which failure screen to show (and may not return,
      // e.g. for a locked-bootloader restriction)
      handler->ui->fail(s);
      return WF_ERROR;
    } else if (s == UPLOAD_ERR_USER_ABORT) {
      systick_delay_ms(100);
      return WF_CANCELLED;
    } else if (s == UPLOAD_OK) {  // last chunk received
      handler->ui->success(e.wireless_transport);
      return handler->success_result;
    }
  }
}
