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
#include "memzero.h"

void __attribute__((noreturn)) trezor_shutdown(void) {
  printf("SHUTDOWN\n");

  // Wait some time to let the user see the displayed
  // message before shutting down
  hal_delay(3000);

  exit(3);
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
      exit(3);
      return 0;
    case SDL_KEYUP:
      if (event->key.repeat) {
        return 0;
      }
      switch (event->key.keysym.sym) {
        case SDLK_ESCAPE:
          exit(3);
          return 0;
        case SDLK_p:
          display_save("emu");
          return 0;
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
