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
 * @brief Performs a fade effect on the display backlight
 * @param start Starting backlight level (0-255)
 * @param end Target backlight level (0-255)
 * @param delay Total duration of the fade effect in milliseconds
 */
void display_fade(int start, int end, int delay);

/**
 * @brief Starts recording the display output to files
 * @param target_dir Directory where the screen captures will be saved
 * @param target_dir_len Length of the target directory path
 * @param refresh_index Index used for the refresh sequence in filenames
 * @note Only available in emulator builds
 */
void display_record_start(uint8_t *target_dir, size_t target_dir_len,
                          int refresh_index);

/**
 * @brief Stops the display recording
 * @note Only available in emulator builds
 */
void display_record_stop(void);

/**
 * @brief Checks if the display recording is currently active
 * @return true if recording is in progress, false otherwise
 * @note Only available in emulator builds
 */
bool display_is_recording(void);

/**
 * @brief Captures and saves the current screen content
 * @details Saves the current screen content to a file if recording is active
 * @note Only available in emulator builds
 */
void display_record_screen(void);
