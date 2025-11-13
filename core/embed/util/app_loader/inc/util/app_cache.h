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

#include <sys/systask.h>

// 32-byte application hash serving as application identifier
typedef struct {
  uint8_t bytes[32];
} app_hash_t;

// Handle to an application image in the cache
typedef struct app_cache_image app_cache_image_t;

#ifdef KERNEL_MODE

/**
 * Initializes the app cache subsystem.
 *
 * @return true on success, false on failure.
 */
bool app_cache_init(void);

#endif

/**
 * Allocates a space for an application image and returns a handle to it.
 *
 * Caller is responsible for writing the application image data
 * using `app_cache_write_image()` and unlocking the image when done using
 * `app_cache_unlock_image()`.
 *
 * @param hash The application image hash.
 * @param size The size of the application image to create.
 *
 * @return A handle to the allocated application image, or
 *         NULL on failure.
 */
app_cache_image_t* app_cache_create_image(const app_hash_t* hash, size_t size);

/**
 * Writes application image data to the allocated space.
 *
 * app_image_write() fails if the app image was verified and is now read-only.
 *
 * @param image The application image handle.
 * @param offset The offset within the application image to write to.
 * @param data Pointer to the data to write.
 * @param size The size of the data to write.
 *
 * @return true on success, false on failure.
 */
bool app_cache_write_image(app_cache_image_t* image, uintptr_t offset,
                           const void* data, size_t size);

/**
 * Finalizes loading of the application image. If `accept` is true,
 * the image is marked as loaded and will be available for execution.
 * If `accept` is false, the image is discarded.
 *
 * @param image The application image handle.
 * @param accept If true, the image is marked as loaded; if false,
 *               the image is discarded.
 * @return true on success, false on failure.
 */

bool app_cache_finalize_image(app_cache_image_t* image, bool accept);

#ifdef KERNEL_MODE

/**
 * Locks the application image in memory for access.
 *
 * @param image The application image handle.
 * @param ptr Pointer to store the address of the application image.
 * @param size Pointer to store the size of the application image.
 *
 * @return true on success, false on failure.
 */

app_cache_image_t* app_cache_lock_image(const app_hash_t* hash, void** ptr,
                                        size_t* size);

/**
 * Unlocks the application image previously locked with `app_cache_lock()`.
 *
 * @param image The application image handle.
 */
void app_cache_unlock_image(app_cache_image_t* image);

#endif  // KERNEL_MODE

#ifdef TREZOR_EMULATOR

/**
 * Loads an application image from a file into the app cache.
 *
 * This function is only available in the emulator build.
 *
 * @param hash The application hash.
 * @param filename The path to the file containing the application image.
 *
 * @return true on success, false on failure.
 */
bool app_cache_load_file(const app_hash_t* hash, const char* filename);

#endif  // TREZOR_EMULATOR
