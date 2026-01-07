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

#include <trezor_rtl.h>

#include <sys/bootutils.h>
#include <sys/system.h>

#ifndef TREZOR_EMULATOR
// Stack check guard value set in startup code.
// This is used if stack protection is enabled.
THREAD_LOCAL uint32_t __stack_chk_guard = 0;
#endif

// Calls to this function are inserted by the compiler
// when stack protection is enabled.
void __attribute__((noreturn, used)) __stack_chk_fail(void) {
  error_shutdown("(SS)");
}

const char *ts_string(ts_t status) {
  if (ts_eq(status, TS_OK)) {
    return "OK";
  } else if (ts_eq(status, TS_EINVAL)) {
    return "EINVAL";
  } else if (ts_eq(status, TS_ENOMEM)) {
    return "ENOMEM";
  } else if (ts_eq(status, TS_ENOENT)) {
    return "ENOENT";
  } else if (ts_eq(status, TS_EBUSY)) {
    return "EBUSY";
  } else if (ts_eq(status, TS_ETIMEDOUT)) {
    return "ETIMEDOUT";
  } else if (ts_eq(status, TS_EIO)) {
    return "EIO";
  } else if (ts_eq(status, TS_EBADMSG)) {
    return "EBADMSG";
    // Trezor-specific error codes
  } else if (ts_eq(status, TS_ENOINIT)) {
    return "ENOINIT";
  } else if (ts_eq(status, TS_ENOEN)) {
    return "ENOEN";
  } else {
    return "?ERROR";
  }
}

void __attribute__((noreturn))
error_shutdown_ex(const char *title, const char *message, const char *footer) {
  system_exit_error(title, message, footer);
  while (1)
    ;
}

void __attribute__((noreturn)) error_shutdown(const char *message) {
  error_shutdown_ex(NULL, message, NULL);
}

void __attribute__((noreturn))
__fatal_error(const char *msg, const char *file, int line) {
  system_exit_fatal(msg, file, line);
  while (1)
    ;
}
