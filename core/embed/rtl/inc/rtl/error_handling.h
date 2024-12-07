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

// Checks for an expression and if it is false, shows an error message
// and shuts down the device.
#define ensure(expr, msg) \
  (((expr) == sectrue) ? (void)0 : __fatal_error(msg, __FILE_NAME__, __LINE__))

// Shows WIPE CODE ENTERED screeen and shuts down the device.
void __attribute__((noreturn)) show_wipe_code_screen(void);

// Shows TOO MANY PIN ATTEMPTS screen and shuts down the device.
void __attribute__((noreturn)) show_pin_too_many_screen(void);

// Shows INSTALL RESTRICTED screen and shuts down the device.
void __attribute__((noreturn)) show_install_restricted_screen(void);

#endif  // LIB_ERRORS_H
