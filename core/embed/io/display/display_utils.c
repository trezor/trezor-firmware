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
#include <io/display_utils.h>
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

#ifdef KERNEL_MODE

#if defined(DEBUGLINK) || defined(TREZOR_EMULATOR)

#include "sha2.h"

#ifdef DISPLAY_PANEL_LX250A2401A
// The panel has rounded corners that the GFXMMU leaves unmapped, so the
// recorder masks them to match what hardware reads back.
#include "ltdc_dsi/panels/lx250a2401a/lx250a2401a_corners.h"
#define RECORD_CORNER_MASK 1
#endif

#ifdef TREZOR_EMULATOR
extern void display_clear_save(void);
#endif

typedef struct {
  bool recording;
#ifdef TREZOR_EMULATOR
  uint8_t target_directory[256];
  int refresh_index;
#endif
  // Hashes of distinct screens since the last `display_record_read()`
  uint8_t hashes[DISPLAY_RECORD_MAX_HASHES][DISPLAY_RECORD_HASH_SIZE];
  uint32_t count;
  // Hash of the previously recorded screen, valid when `have_prev`
  uint8_t prev[DISPLAY_RECORD_HASH_SIZE];
  bool have_prev;
  // Running hash over all distinct screens since the recording started
  SHA256_CTX running;
} display_recording_t;

static display_recording_t g_display_recording = {0};

static void record_reset(display_recording_t *rec) {
  rec->count = 0;
  rec->have_prev = false;
  sha256_Init(&rec->running);
}

void display_record_start(uint8_t *target_dir, size_t target_dir_len,
                          int refresh_index) {
  display_recording_t *rec = &g_display_recording;

  rec->recording = true;
  bool fresh = true;

#ifdef TREZOR_EMULATOR
  // Recording into the directory already in use continues the sequence,
  // so the duplicate-frame state and the digest are kept as well.
  fresh = strlen((char *)rec->target_directory) != strlen((char *)target_dir) ||
          strncmp((char *)target_dir, (char *)rec->target_directory,
                  target_dir_len) != 0;
  if (fresh) {
    display_clear_save();
  }

  memset(rec->target_directory, 0, sizeof(rec->target_directory));
  memcpy(rec->target_directory, target_dir,
         MIN(sizeof(rec->target_directory), target_dir_len));
  rec->refresh_index = refresh_index;
#endif

  if (fresh) {
    record_reset(rec);
  }
}

void display_record_stop(void) {
  display_recording_t *rec = &g_display_recording;
  rec->recording = false;
#ifdef TREZOR_EMULATOR
  display_clear_save();
#endif
  record_reset(rec);
}

bool display_is_recording(void) {
  display_recording_t *rec = &g_display_recording;

  return rec->recording;
}

#ifdef FRAMEBUFFER

// Blacks out the pixels of line `y` outside the panel's visible range in a
// converted line of `bpp` bytes per pixel (alpha, if any, stays opaque).
static void record_mask_line(uint32_t y, uint8_t *dst, size_t bpp) {
#ifdef RECORD_CORNER_MASK
  uint32_t first = 0;
  uint32_t last = 0;
  panel_visible_range(y, &first, &last);
  for (uint32_t x = 0; x < DISPLAY_RESX; x++) {
    if (x < first || x > last) {
      memset(dst + x * bpp, 0, 3);
    }
  }
#endif
}

// Converts one framebuffer line into the bytes `Image.tobytes()` yields for
// the emulator's PNG of the same screen (see tests/ui_tests/common.py),
// returns the number of bytes written.
static size_t record_convert_line(uint32_t y, const uint8_t *src,
                                  uint8_t *dst) {
#if defined(DISPLAY_MONO)
  // mono8 -> black/white RGB, the emulator's threshold
  for (int x = 0; x < DISPLAY_RESX; x++) {
    uint8_t v = src[x] > 40 ? 255 : 0;
    dst[3 * x] = v;
    dst[3 * x + 1] = v;
    dst[3 * x + 2] = v;
  }
  record_mask_line(y, dst, 3);
  return DISPLAY_RESX * 3;
#elif defined(UI_COLOR_32BIT)
  // little-endian ARGB8888 (B, G, R, A in memory) -> RGBA, opaque
  for (int x = 0; x < DISPLAY_RESX; x++) {
    dst[4 * x] = src[4 * x + 2];
    dst[4 * x + 1] = src[4 * x + 1];
    dst[4 * x + 2] = src[4 * x];
    dst[4 * x + 3] = 0xFF;
  }
  record_mask_line(y, dst, 4);
  return DISPLAY_RESX * 4;
#else
  // RGB565 -> RGB888 with bit replication, as SDL expands it
  for (int x = 0; x < DISPLAY_RESX; x++) {
    uint16_t v = src[2 * x] | (src[2 * x + 1] << 8);
    uint8_t r = (v >> 11) & 0x1F;
    uint8_t g = (v >> 5) & 0x3F;
    uint8_t b = v & 0x1F;
    dst[3 * x] = (r << 3) | (r >> 2);
    dst[3 * x + 1] = (g << 2) | (g >> 4);
    dst[3 * x + 2] = (b << 3) | (b >> 2);
  }
  record_mask_line(y, dst, 3);
  return DISPLAY_RESX * 3;
#endif
}

#if defined(TREZOR_EMULATOR) && defined(RECORD_CORNER_MASK)
// Paints the unmapped corners opaque black in the emulator's frame buffer,
// so the saved PNG shows what the panel shows and hashes like hardware.
static void record_mask_frame(const display_fb_info_t *fb) {
  for (uint32_t y = 0; y < DISPLAY_RESY; y++) {
    uint32_t first = 0;
    uint32_t last = 0;
    panel_visible_range(y, &first, &last);
    uint32_t *line = (uint32_t *)((uint8_t *)fb->ptr + y * fb->stride);
    for (uint32_t x = 0; x < DISPLAY_RESX; x++) {
      if (x < first || x > last) {
        line[x] = 0xFF000000;
      }
    }
  }
}
#endif

#if defined(DISPLAY_MONO)
#define RECORD_MODE "RGB"
#define RECORD_LINE_SIZE (DISPLAY_RESX * 3)
#elif defined(UI_COLOR_32BIT)
#define RECORD_MODE "RGBA"
#define RECORD_LINE_SIZE (DISPLAY_RESX * 4)
#else
#define RECORD_MODE "RGB"
#define RECORD_LINE_SIZE (DISPLAY_RESX * 3)
#endif

// Hashes the frame about to be displayed into `digest`, feeding the same
// bytes into `running`. Returns false if the frame buffer is unavailable.
static bool record_hash_screen(SHA256_CTX *running,
                               uint8_t digest[DISPLAY_RECORD_HASH_SIZE]) {
  display_fb_info_t fb;
  if (!display_get_frame_buffer(&fb)) {
    return false;
  }

  static uint8_t line[DISPLAY_RESX * 4];
  SHA256_CTX frame;
  sha256_Init(&frame);

#if defined(TREZOR_EMULATOR) && defined(RECORD_CORNER_MASK)
  record_mask_frame(&fb);
#endif

  for (int y = 0; y < DISPLAY_RESY; y++) {
    const uint8_t *src = (const uint8_t *)fb.ptr + y * fb.stride;
    size_t len = record_convert_line(y, src, line);
    sha256_Update(&frame, line, len);
    sha256_Update(running, line, len);
  }

  sha256_Final(&frame, digest);
  return true;
}

#endif  // FRAMEBUFFER

void display_record_screen(void) {
  display_recording_t *rec = &g_display_recording;

  if (!rec->recording) {
    return;
  }

#ifdef FRAMEBUFFER
  SHA256_CTX running = rec->running;
  uint8_t digest[DISPLAY_RECORD_HASH_SIZE];
  if (!record_hash_screen(&running, digest)) {
    return;
  }

  if (rec->have_prev && memcmp(rec->prev, digest, sizeof(digest)) == 0) {
    // Same screen as the previous one, the emulator would not save it either
    return;
  }

  memcpy(rec->prev, digest, sizeof(digest));
  rec->have_prev = true;
  rec->running = running;
  if (rec->count == DISPLAY_RECORD_MAX_HASHES) {
    // Not read for too long, keep the newest
    memmove(rec->hashes[0], rec->hashes[1],
            (DISPLAY_RECORD_MAX_HASHES - 1) * DISPLAY_RECORD_HASH_SIZE);
    rec->count--;
  }
  memcpy(rec->hashes[rec->count], digest, sizeof(digest));
  rec->count++;
#endif

#ifdef TREZOR_EMULATOR
  char prefix[512];
  snprintf(prefix, sizeof(prefix), "%.255s/refresh%02d-", rec->target_directory,
           rec->refresh_index);

  display_save(prefix);
#endif
}

void display_record_read(display_record_info_t *info) {
  display_recording_t *rec = &g_display_recording;

  memset(info, 0, sizeof(*info));
  memcpy(info->hashes, rec->hashes, rec->count * DISPLAY_RECORD_HASH_SIZE);
  info->count = rec->count;
  rec->count = 0;

  SHA256_CTX running = rec->running;
  sha256_Final(&running, info->digest);
}

size_t display_record_read_screen(display_record_screen_t *info, size_t offset,
                                  uint8_t *buf, size_t len) {
  display_recording_t *rec = &g_display_recording;

  memset(info, 0, sizeof(*info));
  info->width = DISPLAY_RESX;
  info->height = DISPLAY_RESY;
  strncpy(info->mode, RECORD_MODE, sizeof(info->mode) - 1);
  if (rec->have_prev) {
    memcpy(info->hash, rec->prev, sizeof(info->hash));
  }

#ifdef FRAMEBUFFER
  display_fb_info_t fb;
  if (!display_get_displayed_frame_buffer(&fb)) {
    return 0;
  }

  size_t total = (size_t)RECORD_LINE_SIZE * DISPLAY_RESY;
  info->total = total;
  if (offset >= total) {
    return 0;
  }
  len = MIN(len, total - offset);

  static uint8_t line[DISPLAY_RESX * 4];
  size_t copied = 0;
  while (copied < len) {
    size_t pos = offset + copied;
    size_t y = pos / RECORD_LINE_SIZE;
    size_t x = pos % RECORD_LINE_SIZE;
    const uint8_t *src = (const uint8_t *)fb.ptr + y * fb.stride;
    size_t line_len = record_convert_line(y, src, line);
    size_t n = MIN(line_len - x, len - copied);
    memcpy(buf + copied, line + x, n);
    copied += n;
  }
  return copied;
#else
  return 0;
#endif
}

#else  // DEBUGLINK || TREZOR_EMULATOR

void display_record_start(uint8_t *target_dir, size_t target_dir_len,
                          int refresh_index) {}
void display_record_stop(void) {}
bool display_is_recording(void) { return false; }
void display_record_screen(void) {}
void display_record_read(display_record_info_t *info) {
  memset(info, 0, sizeof(*info));
}
size_t display_record_read_screen(display_record_screen_t *info, size_t offset,
                                  uint8_t *buf, size_t len) {
  memset(info, 0, sizeof(*info));
  return 0;
}

#endif  // DEBUGLINK || TREZOR_EMULATOR

#endif  // KERNEL_MODE
