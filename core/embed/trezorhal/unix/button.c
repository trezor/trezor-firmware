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

#include TREZOR_BOARD

#include <SDL.h>

#include "button.h"
#include "common.h"
#include "platform.h"

static char last_left = 0, last_right = 0;

char button_state_left(void) { return last_left; }

char button_state_right(void) { return last_right; }

uint32_t button_read(void) {
  SDL_Event event;
  SDL_PumpEvents();
  if (SDL_PollEvent(&event) > 0) {
    switch (event.type) {
      case SDL_KEYDOWN:
        if (event.key.repeat) {
          break;
        }
        switch (event.key.keysym.sym) {
          case SDLK_LEFT:
            last_left = 1;
            return BTN_EVT_DOWN | BTN_LEFT;
          case SDLK_RIGHT:
            last_right = 1;
            return BTN_EVT_DOWN | BTN_RIGHT;
        }
        break;
      case SDL_KEYUP:
        if (event.key.repeat) {
          break;
        }
        switch (event.key.keysym.sym) {
          case SDLK_LEFT:
            last_left = 0;
            return BTN_EVT_UP | BTN_LEFT;
          case SDLK_RIGHT:
            last_right = 0;
            return BTN_EVT_UP | BTN_RIGHT;
        }
        break;
    }
  }
  return 0;
}

void button_init(void) {}
