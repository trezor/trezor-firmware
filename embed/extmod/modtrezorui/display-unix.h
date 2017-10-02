/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <stdlib.h>
#ifndef TREZOR_NOUI
#include <SDL2/SDL.h>
#include <SDL2/SDL_image.h>

#define DISPLAY_BORDER 16

static SDL_Renderer *RENDERER;
static SDL_Surface *BUFFER;
static SDL_Texture *TEXTURE;
static int DATAODD;
static int POSX, POSY, SX, SY, EX, EY;

void DATA(uint8_t x) {
    if (!RENDERER) {
        display_init();
    }
    if (POSX <= EX && POSY <= EY) {
        ((uint8_t *)BUFFER->pixels)[POSX * 2 + POSY * BUFFER->pitch + (DATAODD ^ 1)] = x;
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
#else
#define DATA(X) (void)(X);
#endif

int display_init(void)
{
#ifndef TREZOR_NOUI
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        printf("SDL_Init Error: %s\n", SDL_GetError());
    }
    SDL_Window *win = SDL_CreateWindow("TREZOR", SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED, DISPLAY_RESX + 2 * DISPLAY_BORDER, DISPLAY_RESY + 2 * DISPLAY_BORDER, SDL_WINDOW_SHOWN);
    if (!win) {
        printf("SDL_CreateWindow Error: %s\n", SDL_GetError());
        SDL_Quit();
    }
    RENDERER = SDL_CreateRenderer(win, -1, SDL_RENDERER_ACCELERATED);
    if (!RENDERER) {
        printf("SDL_CreateRenderer Error: %s\n", SDL_GetError());
        SDL_DestroyWindow(win);
        SDL_Quit();
    }
    SDL_SetRenderDrawColor(RENDERER, DISPLAY_BACKLIGHT, DISPLAY_BACKLIGHT, DISPLAY_BACKLIGHT, 255);
    SDL_RenderClear(RENDERER);
    BUFFER = SDL_CreateRGBSurface(0, MAX_DISPLAY_RESX, MAX_DISPLAY_RESY, 16, 0xF800, 0x07E0, 0x001F, 0x0000);
    TEXTURE = SDL_CreateTexture(RENDERER, SDL_PIXELFORMAT_RGB565, SDL_TEXTUREACCESS_STREAMING, DISPLAY_RESX, DISPLAY_RESY);
    SDL_SetTextureBlendMode(TEXTURE, SDL_BLENDMODE_NONE);
    SDL_SetTextureAlphaMod(TEXTURE, 0);

    DISPLAY_BACKLIGHT = 0;
    DISPLAY_ORIENTATION = 0;
#endif
    return 0;
}

static void display_set_window_raw(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1)
{
#ifndef TREZOR_NOUI
    if (!RENDERER) {
        display_init();
    }
    SX = x0; SY = y0;
    EX = x1; EY = y1;
    POSX = SX; POSY = SY;
    DATAODD = 0;
#endif
}

static void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1)
{
    display_set_window_raw(x0, y0, x1, y1);
}

void display_refresh(void)
{
#ifndef TREZOR_NOUI
    if (!RENDERER) {
        display_init();
    }
    SDL_RenderClear(RENDERER);
    SDL_UpdateTexture(TEXTURE, NULL, BUFFER->pixels, BUFFER->pitch);
    const SDL_Rect r = {DISPLAY_BORDER, DISPLAY_BORDER, DISPLAY_RESX, DISPLAY_RESY};
    SDL_RenderCopyEx(RENDERER, TEXTURE, NULL, &r, DISPLAY_ORIENTATION, NULL, 0);
    SDL_RenderPresent(RENDERER);
#endif
}

static void display_set_orientation(int degrees)
{
}

static void display_set_backlight(int val)
{
#ifndef TREZOR_NOUI
    if (!RENDERER) {
        display_init();
    }
    SDL_SetRenderDrawColor(RENDERER, val, val, val, 255);
#endif
}

void display_save(const char *filename)
{
#ifndef TREZOR_NOUI
    if (!RENDERER) {
        display_init();
    }
    IMG_SavePNG(BUFFER, filename);
#endif
}
