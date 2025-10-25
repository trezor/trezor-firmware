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

#include <sys/systask.h>
#include <sys/system.h>

#ifdef KERNEL_MODE

void system_exit(int exitcode) { systask_exit(NULL, exitcode); }

void system_exit_error_ex(const char* title, size_t title_len,
                          const char* message, size_t message_len,
                          const char* footer, size_t footer_len) {
  systask_exit_error(NULL, title, title_len, message, message_len, footer,
                     footer_len);
}

void system_exit_fatal_ex(const char* message, size_t message_len,
                          const char* file, size_t file_len, int line) {
  systask_exit_fatal(NULL, message, message_len, file, file_len, line);
}

#endif  // KERNEL_MODE

void system_exit_error(const char* title, const char* message,
                       const char* footer) {
  size_t title_len = title != NULL ? strlen(title) : 0;
  size_t message_len = message != NULL ? strlen(message) : 0;
  size_t footer_len = footer != NULL ? strlen(footer) : 0;

  system_exit_error_ex(title, title_len, message, message_len, footer,
                       footer_len);
}

void system_exit_fatal(const char* message, const char* file, int line) {
  size_t message_len = message != NULL ? strlen(message) : 0;
  size_t file_len = file != NULL ? strlen(file) : 0;
  system_exit_fatal_ex(message, message_len, file, file_len, line);
}
