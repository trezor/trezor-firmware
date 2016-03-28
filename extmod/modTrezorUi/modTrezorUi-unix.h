/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#include <SDL2/SDL.h>

static int SDL_inited = 0;
static SDL_Renderer *RENDERER = 0;
static SDL_Surface  *SCREEN   = 0;
static SDL_Texture  *TEXTURE  = 0;
static int DATAODD = 0;
static int POSX, POSY, SX, SY, EX, EY = 0;

#define DATA(X) DATAfunc((X))

static void DATAfunc(uint8_t x) {
    if (!SDL_inited) return;
    if (POSX <= EX && POSY <= EY) {
        ((uint8_t *)SCREEN->pixels)[POSX * 2 + POSY * SCREEN->pitch + (DATAODD ^ 1)] = x;
    }
    DATAODD = !DATAODD;
    if (DATAODD == 0) {
        POSX++;
        if (POSX > EX) {
            POSX = SX;
            POSY++;
        }
    }
}

static void display_init(void)
{
    if (SDL_inited) return;
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        printf("SDL_Init Error: %s\n", SDL_GetError());
    }
    SDL_Window *win = SDL_CreateWindow("TREZOR", SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED, RESX, RESY, SDL_WINDOW_SHOWN);
    if (!win) {
        printf("SDL_CreateWindow Error: %s\n", SDL_GetError());
        SDL_Quit();
    }
    RENDERER = SDL_CreateRenderer(win, -1, SDL_RENDERER_SOFTWARE);
    if (!RENDERER) {
        printf("SDL_CreateRenderer Error: %s\n", SDL_GetError());
        SDL_DestroyWindow(win);
        SDL_Quit();
    }
    SDL_RenderClear(RENDERER);
    SCREEN = SDL_CreateRGBSurface(0, RESX, RESY, 16, 0xF800, 0x07E0, 0x001F, 0x0000);
    TEXTURE = SDL_CreateTexture(RENDERER, SDL_PIXELFORMAT_RGB565, SDL_TEXTUREACCESS_STREAMING, RESX, RESY);
    SDL_inited = 1;
}

static void display_set_window(uint8_t x, uint8_t y, uint8_t w, uint8_t h) {
    if (!SDL_inited) return;
    SX = x; SY = y;
    EX = x + w - 1; EY = y + h - 1;
    POSX = SX; POSY = SY;
    DATAODD = 0;
}

static void display_update(void)
{
    if (!SDL_inited) return;
    SDL_UpdateTexture(TEXTURE, NULL, SCREEN->pixels, SCREEN->pitch);
    SDL_RenderCopy(RENDERER, TEXTURE, NULL, NULL);
    SDL_RenderPresent(RENDERER);
}
