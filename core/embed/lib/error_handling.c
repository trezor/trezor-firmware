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

#include "common.h"
#include "display.h"
#include "error_handling.h"
#include "mini_printf.h"
#ifdef FANCY_FATAL_ERROR
#include "rust_ui.h"
#else
#include "terminal.h"
#endif

#ifdef RGB16
#define COLOR_FATAL_ERROR RGB16(0x7F, 0x00, 0x00)
#else
#define COLOR_FATAL_ERROR COLOR_BLACK
#endif

void __attribute__((noreturn))
error_shutdown_ex(const char *title, const char *message, const char *footer) {
  if (title == NULL) {
    title = "INTERNAL ERROR";
  }
  if (footer == NULL) {
    footer = "PLEASE VISIT\nTREZOR.IO/RSOD";
  }

#ifdef FANCY_FATAL_ERROR
  error_shutdown_rust(title, message, footer);
#else
  display_orientation(0);
  term_set_color(COLOR_WHITE, COLOR_FATAL_ERROR);
  term_printf("%s\n", title);
  if (message) {
    term_printf("%s\n", message);
  }
  term_printf("\n%s\n", footer);
  display_backlight(255);
  trezor_shutdown();
#endif
}

void __attribute__((noreturn)) error_shutdown(const char *message) {
  error_shutdown_ex(NULL, message, NULL);
}

void __attribute__((noreturn))
__fatal_error(const char *msg, const char *file, int line) {
#ifdef FANCY_FATAL_ERROR
  if (msg == NULL) {
    char buf[128] = {0};
    mini_snprintf(buf, sizeof(buf), "%s:%d", file, line);
    msg = buf;
  }
  error_shutdown(msg);
#else
  display_orientation(0);
  term_set_color(COLOR_WHITE, COLOR_FATAL_ERROR);
  term_printf("\nINTERNAL ERROR:\n");
  if (msg) {
    term_printf("msg : %s\n", msg);
  }
  if (file) {
    term_printf("file: %s:%d\n", file, line);
  }
#ifdef SCM_REVISION
  const uint8_t *rev = (const uint8_t *)SCM_REVISION;
  term_printf("rev : %02x%02x%02x%02x%02x\n", rev[0], rev[1], rev[2], rev[3],
              rev[4]);
#endif
  term_printf("\nPlease contact Trezor support.\n");
  display_backlight(255);
  trezor_shutdown();
#endif
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
