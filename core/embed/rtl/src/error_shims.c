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

// Provide definitions of the system exit functions so that they can be
// called without linking the sys crate. This is needed when compiling the
// tests for the crates that don't depend on sys, such as the crypto crate.

#include <rtl/sysexit.h>

#include <stdio.h>
#include <stdlib.h>

static void print_rust_string(const char* str, size_t len) {
  if (str != NULL && len > 0) {
    fwrite(str, len, 1, stdout);
  }
}

void system_exit_error_ex(const char* title, size_t title_len,
                          const char* message, size_t message_len,
                          const char* footer, size_t footer_len) {
  printf("====== ERROR ======\n");
  if (title != NULL && title_len > 0) {
    printf("Title: ");
    print_rust_string(title, title_len);
    printf("\n");
  }
  printf("Error: ");
  print_rust_string(message, message_len);
  printf("\n");
  if (footer != NULL && footer_len > 0) {
    printf("Footer: ");
    print_rust_string(footer, footer_len);
    printf("\n");
  }
  exit(1);
}

void system_exit_fatal_ex(const char* message, size_t message_len,
                          const char* file, size_t file_len, int line) {
  printf("====== FATAL ERROR ======\n");
  printf("Fatal error: ");
  print_rust_string(message, message_len);
  printf("\n");
  if (file != NULL && file_len > 0) {
    printf(" at ");
    print_rust_string(file, file_len);
    printf(":%d", line);
  }
  printf("\n");
  exit(1);
}
