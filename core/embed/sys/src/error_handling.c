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

#include "rtl/error_handling.h"
#include "sys/system.h"

void __attribute__((noreturn)) error_shutdown_ex_n(
    const char *title, size_t title_len, const char *message,
    size_t message_len, const char *footer, size_t footer_len) {
  system_exit_error_ex(title, title_len, message, message_len, footer,
                       footer_len);
  for (;;);
}

void __attribute__((noreturn)) __fatal_error_n(const char *msg, size_t msg_len,
                                               const char *file,
                                               size_t file_len, int line) {
  system_exit_fatal_ex(msg, msg_len, file, file_len, line);
  for (;;);
}
