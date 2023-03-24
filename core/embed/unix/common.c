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

#include <SDL.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <unistd.h>

#include "common.h"
#include "display.h"
#ifdef FANCY_FATAL_ERROR
#include "rust_ui.h"
#endif
#include "memzero.h"

extern void main_clean_exit();
extern float DISPLAY_GAMMA;

void __attribute__((noreturn)) trezor_shutdown(void) {
  printf("SHUTDOWN\n");
  main_clean_exit(3);
  for (;;)
    ;
}

#ifdef RGB16
#define COLOR_FATAL_ERROR RGB16(0x7F, 0x00, 0x00)
#else
// black on monochromatic displays
#define COLOR_FATAL_ERROR 0x0000
#endif

void __attribute__((noreturn))
__fatal_error(const char *expr, const char *msg, const char *file, int line,
              const char *func) {
  display_orientation(0);
  display_backlight(255);

#ifdef FANCY_FATAL_ERROR
  char buf[256] = {0};
  snprintf(buf, sizeof(buf), "%s: %d", file, line);
  screen_fatal_error_c(msg, buf);
  display_refresh();
#else
  display_print_color(COLOR_WHITE, COLOR_FATAL_ERROR);
  display_printf("\nFATAL ERROR:\n");
  printf("\nFATAL ERROR:\n");
  if (expr) {
    display_printf("expr: %s\n", expr);
    printf("expr: %s\n", expr);
  }
  if (msg) {
    display_printf("msg : %s\n", msg);
    printf("msg : %s\n", msg);
  }
  if (file) {
    display_printf("file: %s:%d\n", file, line);
    printf("file: %s:%d\n", file, line);
  }
  if (func) {
    display_printf("func: %s\n", func);
    printf("func: %s\n", func);
  }
#ifdef SCM_REVISION
  const uint8_t *rev = (const uint8_t *)SCM_REVISION;
  display_printf("rev : %02x%02x%02x%02x%02x\n", rev[0], rev[1], rev[2], rev[3],
                 rev[4]);
  printf("rev : %02x%02x%02x%02x%02x\n", rev[0], rev[1], rev[2], rev[3],
         rev[4]);
#endif
  display_printf("\n\n\nHint:\nIsn't the emulator already running?\n");
  printf("Hint:\nIsn't the emulator already running?\n");
#endif
  hal_delay(3000);
  trezor_shutdown();
}

void __attribute__((noreturn))
error_shutdown(const char *label, const char *msg) {
#ifdef FANCY_FATAL_ERROR
  screen_error_shutdown_c(label, msg);
  display_refresh();
#else
  display_clear();
  display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_FATAL_ERROR);
  int y = 32;
  if (label) {
    display_text(8, y, label, -1, FONT_NORMAL, COLOR_WHITE, COLOR_FATAL_ERROR);
    printf("%s\n", label);
    y += 32;
  }
  if (msg) {
    display_text(8, y, msg, -1, FONT_NORMAL, COLOR_WHITE, COLOR_FATAL_ERROR);
    printf("%s\n", msg);
    y += 32;
  }
  y += 32;
  display_text(8, y, "Please unplug the device.", -1, FONT_NORMAL, COLOR_WHITE,
               COLOR_FATAL_ERROR);
  printf("\nPlease unplug the device.\n");
#endif
  display_backlight(255);
  hal_delay(5000);
  exit(4);
}

void hal_delay(uint32_t ms) { usleep(1000 * ms); }

uint32_t hal_ticks_ms() {
  struct timeval tv;
  gettimeofday(&tv, NULL);
  return tv.tv_sec * 1000 + tv.tv_usec / 1000;
}

static int SDLCALL emulator_event_filter(void *userdata, SDL_Event *event) {
  switch (event->type) {
    case SDL_QUIT:
      trezor_shutdown();
      return 0;
    case SDL_KEYUP:
      if (event->key.repeat) {
        return 0;
      }
      switch (event->key.keysym.sym) {
        case SDLK_ESCAPE:
          trezor_shutdown();
          return 0;
        case SDLK_p:
          display_save("emu");
          return 0;
#if defined TREZOR_MODEL_T
        // Left and right arrows controlling display gamma
        // Only for TT (in button models, arrows do different things)
        case SDLK_LEFT:
          DISPLAY_GAMMA = fmaxf(0.0f, DISPLAY_GAMMA - 0.05f);
          printf("DISPLAY_GAMMA: %0.2f\n", DISPLAY_GAMMA);
          display_refresh();
          return 0;
        case SDLK_RIGHT:
          DISPLAY_GAMMA = fminf(8.0f, DISPLAY_GAMMA + 0.05f);
          printf("DISPLAY_GAMMA: %0.2f\n", DISPLAY_GAMMA);
          display_refresh();
          return 0;
#endif
      }
      break;
  }
  return 1;
}

void emulator_poll_events(void) {
  SDL_PumpEvents();
  SDL_FilterEvents(emulator_event_filter, NULL);
}

uint8_t HW_ENTROPY_DATA[HW_ENTROPY_LEN];

void collect_hw_entropy(void) { memzero(HW_ENTROPY_DATA, HW_ENTROPY_LEN); }

void show_wipe_code_screen(void) {
  error_shutdown(
      "DEVICE WIPED!",
      "You have entered the wipe code. All private data has been erased.");
}
void show_pin_too_many_screen(void) {
  error_shutdown("DEVICE WIPED!",
                 "Too many wrong PIN attempts. Storage has been wiped.");
}
