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

#include <io/display.h>
#include <sys/systick.h>

void display_fade(uint8_t start, uint8_t end, int delay) {
#ifdef USE_BACKLIGHT
  if (display_get_backlight() == end) {
    return;
  }
  for (int i = 0; i < 100; i++) {
    display_set_backlight(start + i * (end - start) / 100);
    hal_delay(delay / 100);
  }
  display_set_backlight(end);
#endif
}

#ifdef TREZOR_EMULATOR

extern void display_clear_save(void);

typedef struct {
  // Screen recording status
  bool recording;
  uint8_t target_directory[256];
  int refresh_index;

} display_recording_t;

static display_recording_t g_display_recording = {0};

void display_record_start(uint8_t *target_dir, size_t target_dir_len,
                          int refresh_index) {
  display_recording_t *rec = &g_display_recording;

  rec->recording = true;

  if (strlen((char *)rec->target_directory) != strlen((char *)target_dir) ||
      strncmp((char *)target_dir, (char *)rec->target_directory,
              target_dir_len) != 0) {
    // If the target directory is not set, we assume the recording is not
    // started yet.
    display_clear_save();
  }

  memset(rec->target_directory, 0, sizeof(rec->target_directory));
  memcpy(rec->target_directory, target_dir,
         MIN(sizeof(rec->target_directory), target_dir_len));
  rec->refresh_index = refresh_index;
}

void display_record_stop(void) {
  display_recording_t *rec = &g_display_recording;
  rec->recording = false;
  display_clear_save();
}

bool display_is_recording(void) {
  display_recording_t *rec = &g_display_recording;

  return rec->recording;
}

void display_record_screen(void) {
  display_recording_t *rec = &g_display_recording;

  if (!rec->recording) {
    return;
  }

  char prefix[512];
  snprintf(prefix, sizeof(prefix), "%s/refresh%02d-", rec->target_directory,
           rec->refresh_index);

  display_save(prefix);
}

#else
void display_record_start(uint8_t *target_dir, size_t target_dir_len,
                          int refresh_index) {}
void display_record_stop(void) {}
bool display_is_recording(void) { return false; }
void display_record_screen(void) {}

#endif
