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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "common.h"

void __shutdown(void) {
  printf("SHUTDOWN\n");
  exit(3);
}

void __fatal_error(const char *expr, const char *msg, const char *file,
                   int line, const char *func) {
  printf("\nFATAL ERROR:\n");
  if (expr) {
    printf("expr: %s\n", expr);
  }
  if (msg) {
    printf("msg : %s\n", msg);
  }
  if (file) {
    printf("file: %s:%d\n", file, line);
  }
  if (func) {
    printf("func: %s\n", func);
  }
  __shutdown();
}

void error_shutdown(const char *line1, const char *line2, const char *line3,
                    const char *line4) {
  // For testing do not treat pin_fails_check_max as a fatal error.
  (void)line1;
  (void)line2;
  (void)line3;
  (void)line4;
  return;
}
