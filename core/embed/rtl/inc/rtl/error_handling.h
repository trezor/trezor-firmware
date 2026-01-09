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

/** Status code type */
typedef struct {
  // Do not access this field directly,
  // use `ts_ok()` and `ts_error()` macros.
  int code;
} ts_t;

/** OK status code (signalling success or no error) */
#define TS_OK ts_make(0)

#define TS_EINVAL ts_make(EINVAL)
#define TS_ENOMEM ts_make(ENOMEM)
#define TS_ENOENT ts_make(ENOENT)
#define TS_EBUSY ts_make(EBUSY)
#define TS_ETIMEDOUT ts_make(ETIMEDOUT)
#define TS_EIO ts_make(EIO)
#define TS_EBADMSG ts_make(EBADMSG)

/** List of Trezor-specific error codes with offset from 2000 to avoid mixing
 * with standard errno codes */
#define TS_ENOINIT ts_make(2000) /* Not initialized */
#define TS_ENOEN ts_make(2001)   /* Not enabled */

/**
 * Extracts the code integer value from status structure.
 *
 * @param status Status structure
 * @return Integer status code
 */
#define ts_code(status) ((status).code)

/**
 * Converts integer to status structure.
 *
 * @param value Integer status code
 * @return Status structure
 */
#define ts_make(value) ((const ts_t){(value)})

/**
 * Check if status code is `TS_OK`.
 *
 * @param status Status structure
 * @return true if status is OK
 */
#define ts_ok(status) (ts_code(status) == ts_code(TS_OK))

/**
 * Checks if status code is not `TS_OK`.
 *
 * @param status Status structure
 * @return true if status is an error
 */
#define ts_error(status) (ts_code(status) != ts_code(TS_OK))

/**
 * Checks if both status codes are equal.
 *
 * @param status1 First status structure
 * @param status2 Second status structure
 * @return true if both status codes are equal
 */
#define ts_eq(status1, status2) (ts_code(status1) == ts_code(status2))

/**
 * Returns a string representation of the status code.
 *
 * TS_OK -> "OK"
 * TS_Exxx -> "Exxx"
 *
 * @param status Status structure
 * @return String representation of the status code
 */
const char *ts_string(ts_t status);

/**
 * Ensures that status code is `TS_OK`. If not, it shows an error message
 * and shuts down the device.
 *
 * @param status Status structure
 * @param msg Error message to show if status is not OK
 */
#define ensure_ok(status, msg)                     \
  do {                                             \
    if (!ts_ok(status)) {                          \
      __fatal_error(msg, __FILE_NAME__, __LINE__); \
    }                                              \
  } while (0)

/**
 * Ensures that condition is evaluated as `true`. If not, it shows
 * an error message and shuts down the device.
 *
 * @param cond Condition to check
 * @param msg Error message to show if condition is not true
 */
#define ensure_true(cond, msg)                     \
  do {                                             \
    if (!(cond)) {                                 \
      __fatal_error(msg, __FILE_NAME__, __LINE__); \
    }                                              \
  } while (0)

/**
 * Ensures that condition is evaluated as `sectrue`. If not, it shows
 * an error message and shuts down the device.
 *
 * @param seccond Security condition to check
 * @param msg Error message to show if condition is not sectrue
 */
#define ensure(seccond, msg)                       \
  do {                                             \
    if ((seccond) != sectrue) {                    \
      __fatal_error(msg, __FILE_NAME__, __LINE__); \
    }                                              \
  } while (0)

/**
 * Shows an error message and shuts down the device.
 *
 * @param title Title of the error message (defaults to
 *  "INTERNAL ERROR" if NULL)
 * @param message Main error message (defaults to no message if NULL)
 * @param footer Footer of the error message (defaults to
 *  "PLEASE VISIT TREZOR.IO/RSOD" if NULL)
 */
void __attribute__((noreturn))
error_shutdown_ex(const char *title, const char *message, const char *footer);

/**
 * Shows an error message and shuts down the device.
 *
 * @param message Main error message (defaults to no message if NULL)
 */
void __attribute__((noreturn)) error_shutdown(const char *message);

/**
 * Shows a fatal error message with file and line information,
 * and shuts down the device.
 *
 * Do not use this function directly, use the `ensure_xxx() or
 * assert() macros instead.
 *
 * @param msg Error message
 * @param file Source file name where the error occurred
 * @param line Line number in the source file where the error occurred
 */
void __attribute__((noreturn))
__fatal_error(const char *msg, const char *file, int line);

/*
 * TSH_DECLARE, TSH_RETURN and TSH_CHECK_xxx() macros define
 * a simple error handling mechanism
 *
 * Example:
 *
 * // Preferably use `__wur` attribute to ensure that the return value
 * // is not ignored
 * ts_t __wur my_function(int arg) {
 *   // Initialize verify mechanism
 *   TSH_DECLARE;
 *
 *   // Check arguments
 *   TSH_CHECK_ARG(arg > 0);
 *
 *   ts_t status;
 *
 *   // Verify success
 *   status = some_function();
 *   TSH_CHECK_OK(status);
 *
 *   // Verify condition
 *   TSH_CHECK(another_function() != 0, TS_ERROR_IO);
 *
 *  cleanup:
 *
 *   // clean up code comes here
 *
 *   TSH_RETURN;
 * }
 */

/**
 * Declares a status variable and initializes it to `TS_OK`.
 *
 * The defined variable is in subsequent macros used to track the
 * status within a function.
 */
#define TSH_DECLARE __attribute__((unused)) ts_t __status = TS_OK;

/**
 * Returns the most recently stored status value.
 */
#define TSH_RETURN   \
  do {               \
    return __status; \
  } while (0)

/**
 * Checks the status, if it indicates an error, set
 * status variable and jumps to `cleanup` label.
 *
 * @param status status value to check
 */
#define TSH_CHECK_OK(status) \
  do {                       \
    ts_t _status = status;   \
    if (ts_error(_status)) { \
      __status = _status;    \
      goto cleanup;          \
    }                        \
  } while (0)

/**
 * Checks the condition, if it is not `true`, set status variable
 * and jumps to `cleanup` label.
 *
 * @param cond Condition to check
 * @param status status value to set if condition is not true
 */
#define TSH_CHECK(cond, status) \
  do {                          \
    if (!(cond)) {              \
      __status = status;        \
      goto cleanup;             \
    }                           \
  } while (0)

/**
 * Checks the condition, if it is not `true`, set status variable
 * to `TS_EINVAL` and jumps to `cleanup` label.
 *
 * @param cond Condition to check
 */
#define TSH_CHECK_ARG(cond) \
  do {                      \
    if (!(cond)) {          \
      __status = TS_EINVAL; \
      goto cleanup;         \
    }                       \
  } while (0)

/**
 * Checks the (secbool) condition, if it is not `sectrue`, set
 * status variable and jumps to `cleanup` label.
 *
 * @param seccond Security condition to check
 * @param status status value to set if condition is not sectrue
 */
#define TSH_CHECK_SEC(seccond, status) \
  do {                                 \
    if ((seccond) != sectrue) {        \
      __status = status;               \
      goto cleanup;                    \
    }                                  \
  } while (0)
