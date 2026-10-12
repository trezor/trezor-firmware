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
void display_fade(uint8_t start, uint8_t end, int delay);

// Number of per-screen hashes kept between two `display_record_read()` calls
#define DISPLAY_RECORD_MAX_HASHES 32
#define DISPLAY_RECORD_HASH_SIZE 32

typedef struct {
  // Hashes of distinct screens painted since the previous read, oldest first
  uint8_t hashes[DISPLAY_RECORD_MAX_HASHES][DISPLAY_RECORD_HASH_SIZE];
  uint32_t count;
  // Running hash over all distinct screens since the recording started
  uint8_t digest[DISPLAY_RECORD_HASH_SIZE];
} display_record_info_t;

/**
 * @brief Starts screen recording
 * @details Every distinct painted screen is hashed in the byte layout the
 * emulator's recorded PNG decodes to (see `display_record_screen`), so
 * hardware runs compare directly against emulator fixtures. The emulator
 * additionally saves each screen as a PNG.
 * @param target_dir Directory for the PNGs (emulator only, ignored elsewhere)
 * @param target_dir_len Length of the target directory path
 * @param refresh_index Index used for the refresh sequence in filenames
 * @note Debug-link and emulator builds only; a no-op otherwise
 */
void display_record_start(uint8_t *target_dir, size_t target_dir_len,
                          int refresh_index);

/**
 * @brief Stops the display recording
 */
void display_record_stop(void);

/**
 * @brief Checks if the display recording is currently active
 * @return true if recording is in progress, false otherwise
 */
bool display_is_recording(void);

/**
 * @brief Records the screen that is about to be displayed
 * @details Must be called after rendering and before `display_refresh()`.
 * Hashes the frame (and saves it on the emulator) unless it is identical to
 * the previously recorded one. Does nothing if recording is not active.
 */
void display_record_screen(void);

/**
 * @brief Reads the hashes recorded since the previous read and forgets them
 * @param info Receives the hashes and the running digest
 */
void display_record_read(display_record_info_t *info);

// Largest chunk `display_record_read_screen()` copies at once
#define DISPLAY_RECORD_CHUNK_SIZE 4096

typedef struct {
  uint32_t width;
  uint32_t height;
  // Total size of the converted screen in bytes
  uint32_t total;
  // Pixel layout of the converted bytes, as PIL names it ("RGB"/"RGBA")
  char mode[8];
  // Hash of the last recorded screen, which is the displayed one unless
  // something was painted since; the host checks it against the data
  uint8_t hash[DISPLAY_RECORD_HASH_SIZE];
} display_record_screen_t;

/**
 * @brief Reads a chunk of the displayed screen
 * @details The screen is converted into the same bytes the hashes are
 * computed over, so the host can verify the capture by hashing it.
 * @param info Receives the screen geometry and the hash of the last recorded
 * screen
 * @param offset Offset into the converted screen
 * @param buf Receives the bytes
 * @param len Number of bytes requested, at most DISPLAY_RECORD_CHUNK_SIZE
 * @return Number of bytes copied, 0 if the screen is unavailable
 */
size_t display_record_read_screen(display_record_screen_t *info, size_t offset,
                                  uint8_t *buf, size_t len);
