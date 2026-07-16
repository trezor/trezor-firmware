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

#pragma once

#include <stddef.h>

/**
 * @brief Terminates the current task normally with the given exit code.
 *
 * If the current task is the kernel task, the error handler is called with the
 * postmortem information. If the task is not the kernel task, the task is
 * terminated immediately and the kernel task is scheduled.
 *
 * @param exitcode Exit code returned by the terminating task.
 */
void __attribute__((noreturn)) system_exit(int exitcode);

/**
 * @brief Terminates the current task with an error message.
 *
 * See the notes for `system_exit` regarding the behavior of the error handler
 *
 * @param title Title of the error.
 * @param message Main error message.
 * @param footer Footer text for the error display.
 */
void __attribute__((noreturn)) system_exit_error(const char* title,
                                                 const char* message,
                                                 const char* footer);

/**
 * @brief Like `system_exit_error`, but with explicit lengths for the strings.
 *
 * @param title Title of the error.
 * @param title_len Length of the title.
 * @param message Main error message.
 * @param message_len Length of the message.
 * @param footer Footer text for the error display.
 * @param footer_len Length of the footer.
 */
void __attribute__((noreturn)) system_exit_error_ex(
    const char* title, size_t title_len, const char* message,
    size_t message_len, const char* footer, size_t footer_len);

/**
 * @brief Terminates the current task with a fatal error message.
 *
 * See the notes for `system_exit` regarding the behavior of the error handler
 *
 * @param message Fatal error message.
 * @param file Source file where the fatal error occurred.
 * @param line Line number in the source file.
 */
void __attribute__((noreturn)) system_exit_fatal(const char* message,
                                                 const char* file, int line);

/**
 * @brief Like `system_exit_fatal`, but with explicit lengths for the strings.
 *
 * @param message Fatal error message.
 * @param message_len Length of the message.
 * @param file Source file where the fatal error occurred.
 * @param file_len Length of the file string.
 * @param line Line number in the source file.
 */
void __attribute__((noreturn)) system_exit_fatal_ex(const char* message,
                                                    size_t message_len,
                                                    const char* file,
                                                    size_t file_len, int line);
