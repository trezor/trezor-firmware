/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
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
                x = event.button.x - DISPLAY_BORDER;
                y = event.button.y - DISPLAY_BORDER;
                if (x < 0 || y < 0 || x >= DISPLAY_RESX || y >= DISPLAY_RESY) break;
                switch (event.type) {
                    case SDL_MOUSEBUTTONDOWN:
                        return TOUCH_START | (x << 12) | y;
                    case SDL_MOUSEMOTION:
                        // remove other SDL_MOUSEMOTION events from queue
                        SDL_FlushEvent(SDL_MOUSEMOTION);
                        if (event.motion.state) {
                            return TOUCH_MOVE | (x << 12) | y;
                        }
                        break;
                    case SDL_MOUSEBUTTONUP:
                        return TOUCH_END | (x << 12) | y;
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
