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
 */
ts_t startup_args_add(startup_args_type_t type, const void* value, size_t size);

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
