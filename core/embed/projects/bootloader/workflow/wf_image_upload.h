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

#pragma once

#include <trezor_types.h>

#include <sys/flash.h>

#include "protob/protob.h"
#include "workflow_common.h"

/**
 * Status of a single step of the chunked image upload.
 *
 * Values are shared between the generic upload engine and the per-image-type
 * handlers, and are kept identical to the historical firmware-update codes so
 * that wire behaviour and logs do not change.
 */
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
  UPLOAD_ERR_INVALID_SECMON_HEADER = -18,
  UPLOAD_ERR_INVALID_SECMON_HEADER_SIG = -19,
  UPLOAD_ERR_INVALID_SECMON_MODEL = -20,
  UPLOAD_ERR_INVALID_SECMON_HASH = -21,
  UPLOAD_ERR_INVALID_SECMON_VERSION = -23,
  UPLOAD_ERR_SECMON_TOO_BIG = -22,
} upload_status_t;

// Single staging buffer shared by the upload engine (one IMAGE_CHUNK_SIZE
// chunk). Exposed so a pre-upload step can reuse it as scratch before any
// streaming starts.
extern uint32_t chunk_buffer[];

typedef struct image_upload_handler image_upload_handler_t;

/**
 * Type-specific UI callbacks for an image upload.
 *
 * The engine never draws screens itself; it only signals progress, success and
 * failure, and each image type renders its own UI.
 */
typedef struct {
  /**
   * Renders upload / installation progress.
   *
   * @param permille Progress in the range 0..1000.
   * @param wireless True if the transport is wireless (BLE).
   */
  void (*progress)(int permille, bool wireless);

  /**
   * Renders the success / completion sequence after the image is installed.
   *
   * @param wireless True if the transport is wireless (BLE).
   */
  void (*success)(bool wireless);

  /**
   * Renders the failure screen for a terminal upload status. May be noreturn
   * for some statuses (e.g. a locked-bootloader restriction screen).
   *
   * @param status The terminal status that aborted the upload.
   */
  void (*fail)(upload_status_t status);
} image_upload_ui_t;

/**
 * Per-image-type strategy plugged into the generic upload engine.
 *
 * The engine owns the transport (erase/length handshake, chunk request/receive
 * loop, retries, timeout, progress UI) and the flash erase+write into
 * `target_area`. The handler owns everything type-specific: header parsing and
 * signature/version/model validation, user confirmation and policy, per-chunk
 * integrity, and finalization.
 *
 * Failure-message contract:
 *  - `on_headers` and `on_finish` send their own specific failure / abort
 *    message before returning a negative status.
 *  - `on_chunk` returns UPLOAD_ERR_INVALID_CHUNK_HASH *without* sending a
 *    message (the engine may retry the block and only reports failure once the
 *    retry budget is exhausted). For any other negative status, `on_chunk`
 *    sends its own message first.
 */
struct image_upload_handler {
  /** Destination flash area the image is written to. */
  const flash_area_t *target_area;
  /** Base byte offset within `target_area` to write the image at (default 0).
   *  The image is written to `target_offset + <image offset>`; the host-facing
   *  chunk offsets (FirmwareRequest) remain image-relative (0-based). Used to
   *  stage an image after an already-written prefix (e.g. new bootloader code
   *  placed right after a staged boot header). */
  uint32_t target_offset;
  /** Upper bound on the declared image size, in bytes. */
  uint32_t max_size;
  /** Workflow result returned on a successful upload. */
  workflow_result_t success_result;
  /** Type-specific UI callbacks. */
  const image_upload_ui_t *ui;

  /**
   * Validates the image headers and runs user confirmation / policy.
   *
   * Called once with the first IMAGE_INIT_CHUNK_SIZE bytes, which contain all
   * headers. On success the engine fetches the remainder of the image.
   *
   * @param self Handler instance.
   * @param iface Protobuf I/O interface used to send failure / abort messages.
   * @param buf Buffer holding the first received chunk.
   * @param len Number of valid bytes in @p buf.
   * @return UPLOAD_OK on success, a negative upload_status_t otherwise.
   */
  upload_status_t (*on_headers)(image_upload_handler_t *self,
                                protob_io_t *iface, const uint8_t *buf,
                                size_t len);

  /**
   * Verifies a fully-received chunk before it is written to flash.
   *
   * @param self Handler instance.
   * @param iface Protobuf I/O interface used to send failure messages.
   * @param block_idx Zero-based index of the chunk within the image.
   * @param data Buffer holding the received chunk.
   * @param len Number of valid bytes in @p data.
   * @return UPLOAD_OK on success; UPLOAD_ERR_INVALID_CHUNK_HASH to let the
   *         engine retry the block; another negative upload_status_t to fail.
   */
  upload_status_t (*on_chunk)(image_upload_handler_t *self, protob_io_t *iface,
                              uint32_t block_idx, const uint8_t *data,
                              size_t len);

  /**
   * Finalizes the upload after the last chunk is verified and written.
   *
   * @param self Handler instance.
   * @param iface Protobuf I/O interface used to send failure messages.
   * @return UPLOAD_OK on success, a negative upload_status_t otherwise.
   */
  upload_status_t (*on_finish)(image_upload_handler_t *self,
                               protob_io_t *iface);
};

/**
 * Runs the chunked image upload driven by @p handler.
 *
 * Streams and writes the image to the handler's target area, and drives
 * per-chunk verification and finalization. The caller is responsible for the
 * type-specific erase/length handshake and passes the declared image size in.
 *
 * @param iface Protobuf I/O interface to communicate with the host.
 * @param handler Per-image-type handler describing validation and destination.
 * @param image_size Declared total image size, in bytes.
 * @return The workflow result.
 */
workflow_result_t run_image_upload(protob_io_t *iface,
                                   image_upload_handler_t *handler,
                                   uint32_t image_size);
