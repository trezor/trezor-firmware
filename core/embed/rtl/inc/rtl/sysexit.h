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

/**
 *  Terminates the current task with an error message.
 *
 * To avoid circular dependencies, this function is declared here
 * in rtl but implemented in sys/task.
 *
 * See the notes for `system_exit` regarding the behavior of the error handler
 *
 * @param title Title of the error message
 * @param message Main error message
 * @param footer Footer of the error message
 */
void system_exit_error(const char *title, const char *message,
                       const char *footer);

/**
 * Terminates the current task with a fatal error message.
 * To avoid circular dependencies, this function is declared here
 * in rtl but implemented in sys/task.
 *
 * See the notes for `system_exit` regarding the behavior of the error handler
 *
 * @param message Fatal error message
 * @param file Source file name where the fatal error occurred
 * @param line Line number in the source file where the fatal error occurred
 */
void system_exit_fatal(const char *message, const char *file, int line);
