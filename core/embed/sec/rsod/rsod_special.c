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

#include <rtl/strutils.h>
#include <sec/rsod_special.h>
#include <sys/bootutils.h>
#include <sys/system.h>

#ifdef TREZOR_MODEL_T3W1
// empty message for T3W1 so that it falls to the more appropriate default
#define RECONNECT_DEVICE_MESSAGE ""
#else
#define RECONNECT_DEVICE_MESSAGE "Please reconnect\nthe device"
#endif

void __attribute__((noreturn)) show_wipe_code_screen(void) {
  bootutils_wipe_info_t info = {0};

  const char *title = "Wipe code entered";

  strncpy(info.title, title, sizeof(info.title) - 1);
  strncpy(info.message, ALL_DATA_ERASED_MESSAGE, sizeof(info.message) - 1);
  strncpy(info.footer, RECONNECT_DEVICE_MESSAGE, sizeof(info.footer) - 1);

  reboot_and_wipe(&info);

  while (1)
    ;
}

void __attribute__((noreturn)) show_pin_too_many_screen(void) {
  bootutils_wipe_info_t info = {0};

  const char *title = "Pin attempts exceeded";

  strncpy(info.title, title, sizeof(info.title) - 1);
  strncpy(info.message, ALL_DATA_ERASED_MESSAGE, sizeof(info.message) - 1);
  strncpy(info.footer, RECONNECT_DEVICE_MESSAGE, sizeof(info.footer) - 1);

  reboot_and_wipe(&info);
  while (1)
    ;
}

void __attribute__((noreturn)) show_install_restricted_screen(void) {
  error_shutdown_ex("Install restricted",
                    "Installation of custom firmware is currently restricted.",
                    "Please visit trezor.io/bootloader");
}
