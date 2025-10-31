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

#include <rtl/mini_printf.h>
#include <sys/bootutils.h>
#include <sys/system.h>

#ifdef FANCY_FATAL_ERROR
#include "rust_ui_common.h"
#endif

#ifndef TREZOR_EMULATOR
// Stack check guard value set in startup code.
// This is used if stack protection is enabled.
THREAD_LOCAL uint32_t __stack_chk_guard = 0;
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
  bootutils_wipe_info_t info = {0};

  const char *title = "Wipe code entered";

  mini_snprintf(info.title, sizeof(info.title), "%s", title);
  mini_snprintf(info.message, sizeof(info.message), "%s",
                ALL_DATA_ERASED_MESSAGE);
  mini_snprintf(info.footer, sizeof(info.footer), "%s",
                RECONNECT_DEVICE_MESSAGE);

  reboot_and_wipe(&info);

  while (1)
    ;
}

#ifdef FANCY_FATAL_ERROR
void show_wipe_info(const bootutils_wipe_info_t *info) {
  const char *title = "Device wiped";
  const char *message = ALL_DATA_ERASED_MESSAGE;
  const char *footer = "Please visit trezor.io/rsod";

  if (info->title[0] != '\0') {
    title = info->title;
  }
  if (info->message[0] != '\0') {
    message = info->message;
  }
  if (info->footer[0] != '\0') {
    footer = info->footer;
  }

  display_rsod_rust(title, message, footer);
}
#endif

void __attribute__((noreturn)) show_pin_too_many_screen(void) {
  bootutils_wipe_info_t info = {0};

  const char *title = "Pin attempts exceeded";

  mini_snprintf(info.title, sizeof(info.title), "%s", title);
  mini_snprintf(info.message, sizeof(info.message), "%s",
                ALL_DATA_ERASED_MESSAGE);
  mini_snprintf(info.footer, sizeof(info.footer), "%s",
                RECONNECT_DEVICE_MESSAGE);

  reboot_and_wipe(&info);
  while (1)
    ;
}

void __attribute__((noreturn)) show_install_restricted_screen(void) {
  error_shutdown_ex("Install restricted",
                    "Installation of custom firmware is currently restricted.",
                    "Please visit trezor.io/bootloader");
}
