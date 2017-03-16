/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <SDL2/SDL.h>

#include "options.h"

uint32_t touch_read(void)
{
    SDL_Event event;
    int x, y;
    SDL_PumpEvents();
    if (SDL_PollEvent(&event) > 0) {
        switch (event.type) {
            case SDL_MOUSEBUTTONDOWN:
            case SDL_MOUSEMOTION:
            case SDL_MOUSEBUTTONUP:
                x = event.button.x - DISPLAY_BORDER;
                y = event.button.y - DISPLAY_BORDER;
                if (x < 0 || y < 0 || x >= DISPLAY_RESX || y >= DISPLAY_RESY) break;
                switch (event.type) {
                    case SDL_MOUSEBUTTONDOWN:
                        return (0x00 << 24) | (0x01 << 16) | (x << 8) | y; // touch_start
                        break;
                    case SDL_MOUSEMOTION:
                        // remove other SDL_MOUSEMOTION events from queue
                        SDL_FlushEvent(SDL_MOUSEMOTION);
                        if (event.motion.state) {
                            return (0x00 << 24) | (0x02 << 16) | (x << 8) | y; // touch_move
                        }
                        break;
                    case SDL_MOUSEBUTTONUP:
                        return (0x00 << 24) | (0x04 << 16) | (x << 8) | y; // touch_end
                        break;
                }
                break;
            case SDL_KEYUP:
                if (event.key.keysym.sym == SDLK_ESCAPE) {
                    exit(3);
                }
                break;
            case SDL_QUIT:
                exit(3);
                break;
        }
    }
    return 0;
}
