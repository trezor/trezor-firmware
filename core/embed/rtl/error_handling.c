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

#include <sys/system.h>

#ifndef TREZOR_EMULATOR
// Stack check guard value set in startup code.
// This is used if stack protection is enabled.
uint32_t __stack_chk_guard = 0;
#endif

#define ALL_DATA_ERASED_MESSAGE "All data has been erased from the device"

#ifdef TREZOR_MODEL_T3W1
// empty message for T3W1 so that it falls to the more appropriate default
#define RECONNECT_DEVICE_MESSAGE ""
#else
#define RECONNECT_DEVICE_MESSAGE "Please reconnect\nthe device"
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
  error_shutdown_ex("Wipe code entered", ALL_DATA_ERASED_MESSAGE,
                    RECONNECT_DEVICE_MESSAGE);
}

void __attribute__((noreturn)) show_pin_too_many_screen(void) {
  error_shutdown_ex("Pin attempts exceeded", ALL_DATA_ERASED_MESSAGE,
                    RECONNECT_DEVICE_MESSAGE);
}

void __attribute__((noreturn)) show_install_restricted_screen(void) {
  error_shutdown_ex("Install restricted",
                    "Installation of custom firmware is currently restricted.",
                    "Please visit trezor.io/bootloader");
}
