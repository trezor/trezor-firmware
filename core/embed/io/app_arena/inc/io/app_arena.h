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

#include <rtl/crypto_helpers.h>
#include <sys/systask.h>

#define APP_IMAGE_HANDLE_INVALID 0

#define APP_IMAGE_MAX_ID_LEN 32
#define APP_IMAGE_MAX_NAME_LEN 32
#define APP_IMAGE_MAX_VENDOR_LEN 32

/** Handle for a loaded application image. */
typedef uint32_t app_image_handle_t;

/** Information about a loaded application image. */
typedef struct {
  /** Set if image was fully loaded and verified */
  bool ready;
  /** Set if image is currently running. */
  bool running;
  /** Unique identification of the application. */
  char id[APP_IMAGE_MAX_ID_LEN];
  /** Name of the loaded application. */
  char name[APP_IMAGE_MAX_NAME_LEN];
  /** Vendor of the loaded application. */
  char vendor[APP_IMAGE_MAX_VENDOR_LEN];
  /** Version of the application. */
  uint32_t version;
  /** ID of the running task  (or 0 if not running). */
  systask_id_t task_id;
  /** Size of the image payload in bytes. */
  size_t image_size;
  /** Size of each chunk of the payload in bytes */
  size_t chunk_size;
  /** Calculated hash of the image header */
  sha256_digest_t header_hash;
} app_image_info_t;

/** Information about the application arena. */
typedef struct {
  /** Total size of the arena in bytes. */
  size_t total_size;
  /** Size of unused space in the arena in bytes. */
  size_t free_size;
  /** Number of images currently loaded in the arena. */
  size_t image_count;
} app_arena_info_t;

/**
 * @brief Initialize the application arena.
 *
 * This function must be called before any other functions in this module.
 *
 * @return TS_OK on success, or an error code on failure.
 */
ts_t app_arena_init(void);

/**
 * @brief Returns run-time information about the application arena.
 *
 * @param info Pointer to a structure to receive the arena info.
 * @return TS_OK on success, or an error code on failure.
 */
ts_t app_arena_get_info(app_arena_info_t *info);

/**
 * @brief Clears the pending read event on SYSHANDLE_APP_ARENA, if any.
 *
 * app_arena signals stopped/killed task by signaling read readiness
 * on SYSHANDLE_APP_ARENA. This event remains pending until the task
 * that receives it calls this function.
 *
 * @return TS_OK on success, or an error code on failure.
 */
ts_t app_arena_clear_event(void);

/**
 * @brief Creates a new empty image in the application arena.
 *
 * @param header Pointer to the image header data.
 * @param header_size Size of the image header data in bytes.
 * @param proof Pointer to the Merkle proof data for signature
 * verification.
 * @param proof_len Number of sha256_digest_t elements in the proof array.
 * @param handle Pointer to store the handle of the newly allocated image.
 *
 * @return TS_OK on success, or an error code on failure.
 *         TS_EBADMSG if the header is invalid or verification failed.
 *         TS_ENOMEM if there is not enough memory to allocate a new image.
 */
ts_t app_arena_create_image(const void *header, size_t header_size,
                            const sha256_digest_t *proof, size_t proof_len,
                            app_image_handle_t *handle);

/**
 * @brief Returns a handle of a loaded image by its index.
 *
 * @param idx Index of the loaded image to retrieve. Valid range is [0,
 * image_count-1].
 * @param handle Pointer to store the handle of the retrieved image. Set to
 * APP_IMAGE_HANDLE_INVALID if idx is out of range.
 * @return TS_OK on success, or an error code on failure.
 */
ts_t app_arena_get_image_by_index(size_t idx, app_image_handle_t *handle);

/**
 * @brief Returns information about a loaded application image.
 *
 * @param handle Handle of the image to query.
 * @param info Pointer to a structure to receive the image information.
 * @return TS_OK on success, or an error code on failure.
 *         TS_ENOENT if the image handle is invalid.
 */
ts_t app_image_get_info(app_image_handle_t handle, app_image_info_t *info);

/**
 * @brief Writes image data to a loaded application image.
 *
 * This function can be used to load the application image data into the arena.
 * The image must be in the APP_IMAGE_STATE_LOADING state before calling this
 * function.
 *
 * @param handle Handle of the image to write to.
 * @param data Pointer to the data to write.
 * @param size Size of the data in bytes.
 * @param hash Pointer to the SHA-256 hash of the chunk chain
 * @return TS_OK on success, or an error code on failure.
 *         TS_ENOENT if the image handle is invalid.
 *         TS_ENOMEM if there is not enough memory to write the data.
 *         TS_EBADMSG if the verification failed.
 */
ts_t app_image_write_chunk(app_image_handle_t handle, const void *data,
                           size_t size, const sha256_digest_t *hash);

/**
 * @brief Deletes a loaded application image.
 *
 * If the image is currently running, it will be stopped before being deleted.
 *
 * @param handle Handle of the image to delete.
 * @return TS_OK on success, or an error code on failure.
 *         TS_ENOENT if the image handle is invalid.
 */
ts_t app_image_delete(app_image_handle_t handle);

/**
 * @brief Runs a loaded application image.
 *
 * If the image is fully loaded and verified, this function starts
 * executing, otherwise it returns an error code.
 * If the image is already running, it returns TS_OK without doing
 * anything.
 *
 * @param handle Handle of the image to run.
 * @param task_id Pointer to store the ID of the created task running the image.
 * @return TS_OK on success, or an error code on failure.
 *         TS_ENOENT if the image handle is invalid.
 *         TS_EINVAL invalid argument or state (e.g. image is not ready to run).
 *         TS_EBADMSG if the image is invalid and can't be run.
 */
ts_t app_image_run(app_image_handle_t handle, systask_id_t *task_id);

/**
 * @brief Stops a running application image.
 *
 * If the image is currently running, this function stops its execution and
 * transitions it back to the ready state. If the image is not running, it
 * returns TS_OK without doing anything.
 *
 * @param handle Handle of the image to stop.
 * @return TS_OK on success, or an error code on failure.
 *         TS_ENOENT if the image handle is invalid.
 */
ts_t app_image_stop(app_image_handle_t handle);

/**
 * @brief Gets postmortem information for a stopped application image.
 *
 * If the image is still running, the info structure will be invalid.
 *
 * @param handle Handle of the image to query.
 * @param pinfo Pointer to a structure to receive postmortem information.
 * @return TS_OK on success, or an error code on failure.
 *         TS_ENOENT if the image handle is invalid.
 */
ts_t app_image_get_pminfo(app_image_handle_t handle,
                          systask_postmortem_t *pminfo);
