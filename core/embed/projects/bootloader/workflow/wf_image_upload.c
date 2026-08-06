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

/* A build with no segment-planning handler streams the image as ONE segment, so
 * the plan collapses to constants and the crossing logic cannot fire. Spelling
 * that out lets the compiler drop it -- it matters on a model whose bootloader
 * region has no room for generality it never uses (T3T1). */
#ifdef PQ_SECURE_BOOT
#define SEG_BEGIN(e) ((e)->segments[(e)->seg_idx].offset)
#define SEG_END(e) \
  ((e)->segments[(e)->seg_idx].offset + (e)->segments[(e)->seg_idx].length)
#else
#define SEG_BEGIN(e) (0u)
#define SEG_END(e) ((e)->image_total)
#endif

/* Only the PQ firmware handler lowers the initial prefetch below the default, so
 * every other build reads a field that is always zero. */
#ifdef PQ_SECURE_BOOT
#define HANDLER_INIT_CHUNK(h) ((h)->init_chunk_size)
#else
#define HANDLER_INIT_CHUNK(h) (0u)
#endif

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
  uint32_t chunk_requested;  // requested chunk size
  uint32_t erase_offset;     // offset of flash memory to erase
  int32_t chunk_retry;       // retry counter
  size_t read_offset;        // offset of the next read data in the chunk buffer
  uint32_t chunk_size;       // size of already received chunk data
  bool headers_parsed;      // true once the first chunk's headers are validated
  bool confirmed;           // true once the upload is confirmed by the user
  bool wireless_transport;  // whether the transport is over BLE
  image_upload_handler_t *handler;  // active image-type handler
  // Bytes requested + written per block. Defaults to IMAGE_CHUNK_SIZE (the full
  // staging buffer); a handler may lower it in on_headers (adopted below) to
  // stream at a finer granularity. Always <= IMAGE_CHUNK_SIZE.
  uint32_t block_size;
  // Size of the first (header) prefetch. Defaults to IMAGE_INIT_CHUNK_SIZE; a
  // handler may lower it via handler->init_chunk_size (resolved at start,
  // before on_headers). <= block_size.
  uint32_t init_chunk_size;
  // Segment plan (see handler->plan_segments). The image is streamed as one or
  // more segments, each with its OWN block cadence (blocks from
  // segments[seg_idx].offset). With no plan the whole image is a single segment
  // (flat streaming). stream_offset is the absolute image offset of the current
  // block start within the current segment.
#ifdef PQ_SECURE_BOOT
  image_segment_t segments[IMAGE_UPLOAD_MAX_SEGMENTS];
  size_t seg_count;
  size_t seg_idx;
#endif
  uint32_t stream_offset;
  uint32_t image_total;  // declared image size (validation + progress)
} upload_engine_t;

static void upload_data_received(size_t len, void *ctx) {
  upload_engine_t *e = (upload_engine_t *)ctx;

  e->chunk_size += len;
  // update loader only after the update is confirmed
  if (e->confirmed) {
    // absolute stream position (incl. the current partial) over the total image
    uint32_t done = e->stream_offset + e->chunk_size;
    uint32_t permille = e->image_total ? (1000 * done / e->image_total) : 1000;
    e->handler->ui->progress(permille, e->wireless_transport);
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

  if (!e->headers_parsed) {
    // FIRST message: the init prefetch (init_chunk_size bytes at image offset
    // 0) holds all headers. Validate them, adopt a handler transport block
    // size, and plan the segments; then finish filling segment 0's first block
    // if the prefetch did not already cover it.
    upload_status_t s = handler->on_headers(
        handler, iface, (const uint8_t *)chunk_buffer, e->chunk_size);
    if (s != UPLOAD_OK) {
      // handler has already sent the failure / abort message
      return s;
    }
    e->headers_parsed = true;
    e->confirmed = true;

    // Adopt a handler-chosen transport block size (set in on_headers). Clamp to
    // [init_chunk_size, IMAGE_CHUNK_SIZE]: never larger than the staging
    // buffer, never smaller than the header prefetch already read. 0 keeps the
    // default.
    if (e->handler->block_size != 0) {
      uint32_t bs = e->handler->block_size;
      if (bs > IMAGE_CHUNK_SIZE) {
        bs = IMAGE_CHUNK_SIZE;
      }
      if (bs >= e->init_chunk_size) {
        e->block_size = bs;
      }
    }

    // Plan the segments to stream. A handler may split the image into segments
    // (e.g. a header region + one per image sub-region), each streamed with its
    // OWN block cadence -- blocks requested from segments[i].offset, so block k
    // of a segment == chunk k. With no plan the whole image is ONE segment;
    // flat streaming is just that degenerate case. Segment 0 always starts at
    // offset 0 -- its head is the init prefetch just received.
#ifdef PQ_SECURE_BOOT
    if (handler->plan_segments != NULL) {
      e->seg_count = handler->plan_segments(
          handler, e->image_total, e->segments, IMAGE_UPLOAD_MAX_SEGMENTS);
    } else {
      e->seg_count = 1;
      e->segments[0].offset = 0;
      e->segments[0].length = e->image_total;
    }
    e->seg_idx = 0;
#endif
    e->stream_offset = SEG_BEGIN(e);  // == 0

    // Finish segment 0's first block: its head (the init prefetch) is buffered;
    // request the remainder if the block is larger. If the whole first block
    // fit in the prefetch (a small segment 0, e.g. a fixed-size header region),
    // fall straight through to write it.
    uint32_t seg0_end = SEG_END(e);
    uint32_t block_target = MIN(e->block_size, seg0_end - e->stream_offset);
    if (e->chunk_size < block_target) {
      e->read_offset = e->chunk_size;
      e->chunk_requested = block_target - e->chunk_size;
      if (sectrue !=
          send_msg_request_firmware(iface, e->stream_offset + e->read_offset,
                                    e->chunk_requested)) {
        return UPLOAD_ERR_COMMUNICATION;
      }
      return UPLOAD_IN_PROGRESS;
    }
    e->read_offset = 0;
  } else if (e->read_offset != 0) {
    // Second message of the first block: its head was the init prefetch and the
    // remainder just arrived; reset the buffer offset for subsequent blocks.
    e->read_offset = 0;
  }

  // Absolute image offset of this block's start (== bytes already on flash).
  const uint32_t image_off = e->stream_offset;

  // should not happen, but double-check
  if (flash_area_get_address(handler->target_area,
                             handler->target_offset + image_off, 0) == NULL) {
    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Firmware too big");
    return UPLOAD_ERR_FIRMWARE_TOO_BIG;
  }

  // type-specific per-chunk integrity verification (image_off = bytes already
  // on flash before this block).
  upload_status_t cs =
      handler->on_chunk(handler, iface, image_off, (const uint8_t *)chunk_buffer,
                        e->chunk_size);

  if (cs == UPLOAD_ERR_INVALID_CHUNK_HASH) {
    if (e->chunk_retry > 0) {
      --e->chunk_retry;

      // clear chunk buffer
      memset((uint8_t *)&chunk_buffer, 0xFF, IMAGE_CHUNK_SIZE);
      e->chunk_size = 0;

      if (sectrue !=
          send_msg_request_firmware(iface, image_off, e->chunk_requested)) {
        return UPLOAD_ERR_COMMUNICATION;
      }
      return UPLOAD_IN_PROGRESS;
    }

    send_msg_failure(iface, FailureType_Failure_ProcessError,
                     "Invalid chunk hash");
    return UPLOAD_ERR_INVALID_CHUNK_HASH;
  } else if (cs != UPLOAD_OK) {
    // handler has already sent its own failure message
    return cs;
  }

  // erase (rolling cursor) + write this block
  const uint32_t *src = (const uint32_t *)chunk_buffer;
  uint32_t bytes_remaining = e->chunk_size;
  uint32_t write_offset = handler->target_offset + image_off;

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

  // Advance the stream cursor within the current segment; cross into the next
  // when consumed. Inter-segment padding was erased by the rolling cursor above
  // but not written.
  e->stream_offset += e->chunk_size;
  e->chunk_retry = FIRMWARE_UPLOAD_CHUNK_RETRY_COUNT;
  bool all_done = false;
  if (e->stream_offset >= SEG_END(e)) {
#ifdef PQ_SECURE_BOOT
    e->seg_idx++;
    if (e->seg_idx >= e->seg_count) {
      all_done = true;
    } else {
      e->stream_offset = e->segments[e->seg_idx].offset;
    }
#else
    all_done = true;
#endif
  }

  if (!all_done) {
    uint32_t next_end = SEG_END(e);
    e->chunk_requested = MIN(e->block_size, next_end - e->stream_offset);
    e->chunk_size = 0;
    memset((uint8_t *)&chunk_buffer, 0xFF, IMAGE_CHUNK_SIZE);
    if (sectrue != send_msg_request_firmware(iface, e->stream_offset,
                                             e->chunk_requested)) {
      return UPLOAD_ERR_COMMUNICATION;
    }
    return UPLOAD_IN_PROGRESS;
  }

  // All segments streamed: erase the tail beyond the last one, then finalize
  // (whole-image / whole-tree verify) and report success.
  uint32_t bytes_erased = 0;
  do {
    ensure(flash_area_erase_partial(handler->target_area, e->erase_offset,
                                    &bytes_erased),
           NULL);
    e->erase_offset += bytes_erased;
  } while (bytes_erased > 0);
  upload_status_t fs = handler->on_finish(handler, iface);
  if (fs != UPLOAD_OK) {
    // handler has already sent its own failure message
    return fs;
  }
  send_msg_success(iface, NULL);
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
      // Full staging buffer by default; a handler may shrink it in on_headers.
      .block_size = IMAGE_CHUNK_SIZE,
      // Header prefetch size; a handler may shrink it (used before on_headers).
      .init_chunk_size = HANDLER_INIT_CHUNK(handler)
                             ? HANDLER_INIT_CHUNK(handler)
                             : IMAGE_INIT_CHUNK_SIZE,
      .image_total = image_size,
  };

  e.wireless_transport = iface->wire->wireless;

  if ((image_size > 0) && ((image_size % sizeof(uint32_t)) == 0) &&
      (image_size <= handler->max_size)) {
    // clear chunk buffer
    memset((uint8_t *)&chunk_buffer, 0xFF, IMAGE_CHUNK_SIZE);
    e.chunk_size = 0;

    // request the header prefetch (segment 0's head)
    e.chunk_requested =
        (image_size > e.init_chunk_size) ? e.init_chunk_size : image_size;
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
