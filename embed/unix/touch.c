/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#include <stdint.h>
#ifndef TREZOR_NOUI
#include <SDL2/SDL.h>
#endif

#include "options.h"
#include "touch.h"

void __shutdown(void);

uint32_t touch_read(void)
{
#ifndef TREZOR_NOUI
    SDL_Event event;
    int x, y;
    SDL_PumpEvents();
    if (SDL_PollEvent(&event) > 0) {
        switch (event.type) {
            case SDL_MOUSEBUTTONDOWN:
            case SDL_MOUSEMOTION:
            case SDL_MOUSEBUTTONUP:
                x = event.button.x - DISPLAY_TOUCH_OFFSET_X;
                y = event.button.y - DISPLAY_TOUCH_OFFSET_Y;
                if (x < 0 || y < 0 || x >= DISPLAY_RESX || y >= DISPLAY_RESY) break;
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
            case SDL_KEYUP:
                if (event.key.keysym.sym == SDLK_ESCAPE) {
                    __shutdown();
                }
                break;
            case SDL_QUIT:
                __shutdown();
                break;
        }
    }
#endif
    return 0;
}
