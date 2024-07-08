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

#ifndef LIB_ERROR_HANDLING_H
#define LIB_ERROR_HANDLING_H

#include <stdint.h>

// Suppresses the intellisense error in VSCode
#ifndef __FILE_NAME__
#define __FILE_NAME__ __FILE__
#endif

// Status code type
typedef struct {
  // Do not access this field directly,
  // use `ts_ok()` and `ts_error()` macros.
  uint32_t code;
} ts_t;

// Build status code from any 16-bit value.
//
// Status codes are hardened against fault injections
// by storing the same value in the upper 16 bits.
#define TS_BUILD(code) ((const ts_t){(code) | ((code) << 16)})

// OK status code (signalling success or no error)
#define TS_OK TS_BUILD(0)

// This offset ensures at lest 16bit hamming distance
// between `TS_OK` and other status codes.
#define TS_ERROR_OFFSET 0xFF00

// Build error status code from any 8-bit value
//
// The code should be in range 0 to 255 to ensure
// 16-bit hamming distance to `TS_OK`
#define TS_ERROR_BUILD(code) TS_BUILD(TS_ERROR_OFFSET + (code))

// Error status codes
#define TS_ERROR TS_ERROR_BUILD(0)
#define TS_ERROR_BUSY TS_ERROR_BUILD(1)
#define TS_ERROR_TIMEOUT TS_ERROR_BUILD(2)
#define TS_ERROR_NOTINIT TS_ERROR_BUILD(3)
#define TS_ERROR_ARG TS_ERROR_BUILD(4)
#define TS_ERROR_IO TS_ERROR_BUILD(5)

// Extracts the status code integer value.
#define ts_code(status) ((status).code)

// Converts status code to 32-bit unsigned integer.
#define ts_to_u32(status) ((status).code);

// Converts 32-bit unsigned integer to status code.
#define ts_from_u32(u32) ((const ts_t){u32})

// Check status code consistency and returns its value.
// If invalid status code is detected, it will call `__fatal_error()`.
#define _ts_checked(status)                                          \
  ({                                                                 \
    ts_t _checked = (status);                                        \
    if ((ts_code(_checked) & 0xFFFF) != (ts_code(_checked) >> 16)) { \
      __fatal_error("ts check error", __FILE_NAME__, __LINE__);      \
    }                                                                \
    _checked;                                                        \
  })

// Returns `true` if status code is `TS_OK`
#define ts_ok(status) (ts_code(_ts_checked(status)) == ts_code(TS_OK))

// Returns `true` if status code is NOT `TS_OK`
#define ts_error(status) (ts_code(_ts_checked(status)) != ts_code(TS_OK))

// Returns `true` if both status codes are equal
#define ts_eq(status1, status2) (ts_code(status1) == ts_code(status2))

// Returns a string representation of the status code.
//
// TS_OK -> "OK"
// TS_ERROR -> "ERROR"
// ...
const char *ts_string(ts_t status);

// ----------------------------------------------------
// TS_INIT, TS_RETURN and VERIFY_XXX() macros define
// a simple error handling mechanism
//
// Example:
//
// ts_t my_function(int arg) {
//   // initialize verify mechanism
//   TS_INIT;
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
#define TS_INIT __attribute__((unused)) ts_t __status = TS_OK;

// Returns the current status.
#define TS_RETURN return __status;

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

// Do not use this function directly, use the `ensure()` macro instead.
void __attribute__((noreturn))
__fatal_error(const char *msg, const char *file, int line);

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

// Shows WIPE CODE ENTERED screeen and shuts down the device.
void __attribute__((noreturn)) show_wipe_code_screen(void);

// Shows TOO MANY PIN ATTEMPTS screen and shuts down the device.
void __attribute__((noreturn)) show_pin_too_many_screen(void);

// Shows INSTALL RESTRICTED screen and shuts down the device.
void __attribute__((noreturn)) show_install_restricted_screen(void);

#endif  // LIB_ERRORS_H
