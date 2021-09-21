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

#include <SDL2/SDL.h>
#include <stdbool.h>
#include <stdint.h>

extern void __shutdown(void);
extern const char *display_save(const char *prefix);

static bool handle_emulator_events(const SDL_Event *event) {
  switch (event->type) {
    case SDL_KEYUP:
      if (event->key.repeat) {
        break;
      }
      switch (event->key.keysym.sym) {
        case SDLK_ESCAPE:
          __shutdown();
          return true;
        case SDLK_p:
          display_save("emu");
          return true;
      }
      break;
    case SDL_QUIT:
      __shutdown();
      return true;
  }
  return false;
}

#if TREZOR_MODEL == T

#include "touch.h"

extern int sdl_display_res_x, sdl_display_res_y;
extern int sdl_touch_offset_x, sdl_touch_offset_y;

uint32_t touch_read(void) {
  SDL_Event event;
  SDL_PumpEvents();
  if (SDL_PollEvent(&event) > 0) {
    if (handle_emulator_events(&event)) {
      return 0;
    }
    switch (event.type) {
      case SDL_MOUSEBUTTONDOWN:
      case SDL_MOUSEMOTION:
      case SDL_MOUSEBUTTONUP: {
        const int x = event.button.x - sdl_touch_offset_x;
        const int y = event.button.y - sdl_touch_offset_y;
        if (x < 0 || y < 0 || x >= sdl_display_res_x ||
            y >= sdl_display_res_y) {
          if (event.motion.state) {
            const int clamp_x =
                (x < 0)
                    ? 0
                    : ((x >= sdl_display_res_x) ? sdl_display_res_x - 1 : x);
            const int clamp_y =
                (y < 0)
                    ? 0
                    : ((y >= sdl_display_res_y) ? sdl_display_res_y - 1 : y);
            return TOUCH_END | touch_pack_xy(clamp_x, clamp_y);
          } else {
            break;
          }
        }
        switch (event.type) {
          case SDL_MOUSEBUTTONDOWN:
            return TOUCH_START | touch_pack_xy(x, y);
          case SDL_MOUSEMOTION:
            // remove other SDL_MOUSEMOTION events from queue
            SDL_FlushEvent(SDL_MOUSEMOTION);
            if (event.motion.state) {
              return TOUCH_MOVE | touch_pack_xy(x, y);
            }
            break;
          case SDL_MOUSEBUTTONUP:
            return TOUCH_END | touch_pack_xy(x, y);
        }
        break;
      }
    }
  }
  return 0;
}

#elif TREZOR_MODEL == 1

#include "button.h"

uint32_t button_read(void) {
  SDL_Event event;
  SDL_PumpEvents();
  if (SDL_PollEvent(&event) > 0) {
    if (handle_emulator_events(&event)) {
      return 0;
    }
    switch (event.type) {
      case SDL_KEYDOWN:
        if (event.key.repeat) {
          break;
        }
        switch (event.key.keysym.sym) {
          case SDLK_LEFT:
            return BTN_EVT_DOWN | BTN_LEFT;
          case SDLK_RIGHT:
            return BTN_EVT_DOWN | BTN_RIGHT;
        }
        break;
      case SDL_KEYUP:
        if (event.key.repeat) {
          break;
        }
        switch (event.key.keysym.sym) {
          case SDLK_LEFT:
            return BTN_EVT_UP | BTN_LEFT;
          case SDLK_RIGHT:
            return BTN_EVT_UP | BTN_RIGHT;
        }
        break;
    }
  }
  return 0;
}

#else
#error Unknown Trezor model
#endif
