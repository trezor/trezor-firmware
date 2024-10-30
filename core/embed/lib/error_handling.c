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

#include <stddef.h>
#include <stdint.h>

#include "error_handling.h"
#include "system.h"

#ifndef TREZOR_EMULATOR
// Stack check guard value set in startup code.
// This is used if stack protection is enabled.
uint32_t __stack_chk_guard = 0;
#endif

// Calls to this function are inserted by the compiler
// when stack protection is enabled.
void __attribute__((noreturn, used)) __stack_chk_fail(void) {
  error_shutdown("(SS)");
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

void __attribute__((noreturn)) show_wipe_code_screen(void) {
  error_shutdown_ex("WIPE CODE ENTERED",
                    "All data has been erased from the device",
                    "PLEASE RECONNECT\nTHE DEVICE");
}

void __attribute__((noreturn)) show_pin_too_many_screen(void) {
  error_shutdown_ex("TOO MANY PIN ATTEMPTS",
                    "All data has been erased from the device",
                    "PLEASE RECONNECT\nTHE DEVICE");
}

void __attribute__((noreturn)) show_install_restricted_screen(void) {
  error_shutdown_ex("INSTALL RESTRICTED",
                    "Installation of custom firmware is currently restricted.",
                    "Please visit\ntrezor.io/bootloader");
}
