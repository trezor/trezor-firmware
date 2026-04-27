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

/** Structure passed to the next stage of the boot process */
typedef struct {
  /** Version of the structure, used for backward compatibility handling */
  uint32_t version;
  /** Size of payload data in bytes (not including the header) */
  uint32_t size;
  /** Payload passed to the next stage */
  uint8_t data[0];
} startup_args_t;

/**
 * Enum representing system-wide argument types.
 *
 * The actual values and their meaning are defined by the caller; the
 * startup_args module does not interpret them.
 *
 * The enum values are part of the binary interface and must remain stable to
 * preserve compatibility.
 */
typedef enum {
  /** Invalid argument type */
  STARTUP_ARGS_TYPE_INVALID = 0,
  /** MCU device attestation certificate */
  STARTUP_ARGS_TYPE_MCU_DEVICE_CERT = 1,

} startup_args_type_t;

/*
 * @brief Adds an argument into the output buffer to be passed to the next
 * stage of the boot process.
 *
 * @note The output structure is stored in a preallocated global static buffer.
 * If the function is not called at all, the linker will optimize it out and
 * the buffer will not be included in the final binary.
 *
 * @param type Argument type (defined by the caller)
 * @param value Pointer to the argument value
 * @param size Size of the argument value in bytes
 * @return TS_OK on success, or an error code on failure:
 *         TS_ENOMEM if the output buffer does not have enough space
 *         TS_EEXIST if an entry with the same type already exists in the buffer
 *         TS_EBUSY if there is a pending reservation
 */
ts_t startup_args_add(startup_args_type_t type, const void* value, size_t size);

/*
 * @brief Reserves space for an argument in the output buffer to be passed to
 * the next stage of the boot process, and returns a pointer to the reserved
 * space where the caller can write the argument value directly.
 *
 * This function allows the caller to write the argument value directly into the
 * output buffer without needing to copy it from a separate location. The caller
 * must call `startup_args_commit()` after writing the value to finalize the
 * addition of the argument to the output buffer. If the caller decides not to
 * add the argument after reserving space, it must call `startup_args_discard()`
 *
 * @param type Argument type (defined by the caller)
 * @param size Size of the argument value in bytes
 * @param buffer Output pointer to store the address of the reserved space for
 * the argument value. The caller can write the value directly to this address.
 *
 * @return TS_OK on success, or an error code on failure:
 *         TS_ENOMEM if the output buffer does not have enough space
 *         TS_EEXIST if an entry with the same type already exists in the buffer
 *         TS_EBUSY if there is already a pending reservation
 */
ts_t startup_args_reserve(startup_args_type_t type, size_t size, void** buffer);

/*
 * @brief Commits the previously reserved argument in the output buffer.
 *
 * This function must be called after `startup_args_reserve()` to finalize the
 * addition of the argument to the output buffer. It updates the size of the
 * reserved entry to the actual size of the argument value written by the
 * caller, and advances the buffer size to account for the new entry. If this
 * function fails, the reservation remains pending and the caller must either
 * retry with valid arguments or call `startup_args_discard()`.
 *
 * @param size Size of the argument value in bytes (must match or be less than
 * the size used in the previous call to `startup_args_reserve()`)
 *
 * @return TS_OK on success, or an error code on failure:
 *         TS_EINVAL if there is no pending reservation, or if the size is
 *         greater than the size reserved in the previous call to
 *         `startup_args_reserve()`
 */
ts_t startup_args_commit(size_t size);

/*
 * @brief Discards the previously reserved argument in the output buffer.
 *
 * This function must be called if the caller decides not to add the reserved
 * argument to the output buffer. It resets the reservation state, allowing
 * subsequent calls to `startup_args_reserve()` to succeed.
 */
void startup_args_discard(void);

/*
 * @brief Retrieves the pointer to the output arguments structure that can
 * be passed to the next stage of the boot process.
 *
 * @return Pointer to the output arguments structure, or NULL if no arguments
 */
const startup_args_t* startup_args_export(void);

/*
 * @brief Initializes the input buffer used to retrieve arguments passed from
 * the previous stage of the boot process. Call this function before
 * `startup_args_get()`.
 *
 * @param args Pointer to the input arguments structure passed from the previous
 * stage
 * @return Status code indicating success or error
 */
ts_t startup_args_import(const startup_args_t* args);

/*
 * @brief Retrieves an argument from the input buffer initialized from the
 * previous stage of the boot process.
 *
 * @param type Argument type (defined by the caller)
 * @param value Output pointer to store the address of the argument value. May
 * be NULL if the caller is not interested in the value.
 * @param size Output pointer to store the size of the argument value in
 * bytes. May be NULL if the caller is not interested in the size.
 * @return TS_OK on success, or an error code on failure:
 *         TS_ENOINIT if the input buffer has not been initialized
 *         TS_ENOENT if no entry with the specified type exists in the buffer
 */
ts_t startup_args_get(startup_args_type_t type, const void** value,
                      size_t* size);
