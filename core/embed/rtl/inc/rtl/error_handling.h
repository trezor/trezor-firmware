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

#include <errno.h>

// Suppresses the intellisense error in VSCode
#ifndef __FILE_NAME__
#define __FILE_NAME__ __FILE__
#endif

// Status code type
typedef struct {
  // Do not access this field directly,
  // use `ts_ok()` and `ts_error()` macros.
  int code;
} ts_t;

// OK status code (signalling success or no error)
#define TS_OK ts_make(0)

#define TS_EINVAL ts_make(EINVAL)
#define TS_ENOMEM ts_make(ENOMEM)
#define TS_ENOENT ts_make(ENOENT)
#define TS_EBUSY ts_make(EBUSY)
#define TS_ETIMEDOUT ts_make(ETIMEDOUT)
#define TS_EIO ts_make(EIO)
#define TS_EBADMSG ts_make(EBADMSG)

// #define TS_SPECIFIC_BASE 1000
// #define TS_ERROR ts_make(TS_SPECIFIC_BASE + 0) // Generic error

// Extracts the code integer value from status structure.
#define ts_code(status) ((status).code)

// Converts integer to status structure.
#define ts_make(value) ((const ts_t){(value)})

// Returns `true` if status code is `TS_OK`
#define ts_ok(status) (ts_code(status) == ts_code(TS_OK))

// Returns `true` if status code is NOT `TS_OK`
#define ts_error(status) (ts_code(status) != ts_code(TS_OK))

// Returns `true` if both status codes are equal
#define ts_eq(status1, status2) (ts_code(status1) == ts_code(status2))

// Returns a string representation of the status code.
//
// TS_OK -> "OK"
// TS_ERROR -> "ERROR"
// ...
const char *ts_string(ts_t status);

// Ensures that status code is `TS_OK`.
// If not, it shows an error message and shuts down the device.
#define ensure_ok(status, msg)                     \
  do {                                             \
    if (!ts_ok(status)) {                          \
      __fatal_error(msg, __FILE_NAME__, __LINE__); \
    }                                              \
  } while (0)

// Ensures that condition is evaluated as `true`.
// If not, it shows an error message and shuts down the device.
#define ensure_true(cond, msg)                     \
  do {                                             \
    if (!(cond)) {                                 \
      __fatal_error(msg, __FILE_NAME__, __LINE__); \
    }                                              \
  } while (0)

// Ensures that condition is evaluated as `sectrue`.
// If not, it shows an error message and shuts down the device.
#define ensure(seccond, msg)                       \
  do {                                             \
    if ((seccond) != sectrue) {                    \
      __fatal_error(msg, __FILE_NAME__, __LINE__); \
    }                                              \
  } while (0)

// Shows an error message and shuts down the device.
//
// If the title is NULL, it will be set to "INTERNAL ERROR".
// If the message is NULL, it will be ignored.
// If the footer is NULL, it will be set to "PLEASE VISIT TREZOR.IO/RSOD".
void __attribute__((noreturn))
error_shutdown_ex(const char *title, const char *message, const char *footer);

// Shows an error message and shuts down the device.
//
// Same as `error_shutdown_ex()` but with a default header and footer.
void __attribute__((noreturn)) error_shutdown(const char *message);

// Do not use this function directly, use the `ensure()` macro instead.
void __attribute__((noreturn))
__fatal_error(const char *msg, const char *file, int line);

// ----------------------------------------------------
// TS_INIT, TS_RETURN and VERIFY_XXX() macros define
// a simple error handling mechanism
//
// Example:
//
// ts_t my_function(int arg) {
//   // initialize verify mechanism
//   TS_DECLARE;
//
//   // check arguments
//   TS_CHECK_ARG(arg > 0);
//
//   ts_t status;
//
//   // verify success
//   status = some_function();
//   TS_CHECK_OK(status);
//
//   // verify condition
//   TS_CHECK(another_function() != 0, TS_ERROR_IO);
//
//  cleanup:
//
//   // clean up code comes here
//
//   TS_RETURN;
// }

// Declares a status variable and initializes it to `TS_OK`.
// This variable is used to store the status
#define TS_DECLARE __attribute__((unused)) ts_t __status = TS_OK;

// Returns the current status.
#define TS_RETURN    \
  do {               \
    return __status; \
  } while (0)

// Jumps to `error` label if status is not `TS_OK`.
#define TS_CHECK_OK(status)  \
  do {                       \
    ts_t _status = status;   \
    if (ts_error(_status)) { \
      __status = _status;    \
      goto cleanup;          \
    }                        \
  } while (0)

// Jumps to `error` label if the condition is not `true`.
#define TS_CHECK(cond, status) \
  do {                         \
    if (!(cond)) {             \
      __status = status;       \
      goto cleanup;            \
    }                          \
  } while (0)

// Jumps to `error` label if the condition is not `true`.
// Sets the status to `TS_ERROR_ARG`.
#define TS_CHECK_ARG(cond)     \
  do {                         \
    if (!(cond)) {             \
      __status = TS_ERROR_ARG; \
      goto cleanup;            \
    }                          \
  } while (0)

// Jumps to `error` label if the condition is not `sectrue`.
#define TS_CHECK_SEC(seccond, status) \
  do {                                \
    if ((seccond) != sectrue) {       \
      __status = status;              \
      goto cleanup;                   \
    }                                 \
  } while (0)
