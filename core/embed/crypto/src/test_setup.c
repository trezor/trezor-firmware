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

#include <stdio.h>
#include <stdlib.h>

void system_exit_error(const char *title, const char *message,
                       const char *footer) {
  printf("Error: %s\n", message);
  if (title != NULL && *title != '\0') {
    printf("Title: %s\n", title);
  }

  if (footer != NULL && *footer != '\0') {
    printf("Footer: %s\n", footer);
  }

  exit(1);
}

void system_exit_fatal(const char *message, const char *file, int line) {
  printf("Fatal error: %s", message);
  if (file != NULL && *file != '\0') {
    printf(" at %s:%d", file, line);
  }
  printf("\n");

  exit(1);
}
