/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <stdlib.h>
#include <SDL2/SDL.h>

#define DISPLAY_BORDER 16

static SDL_Renderer *RENDERER = 0;
static SDL_Surface  *BUFFER   = 0;
static SDL_Texture  *TEXTURE  = 0;
static int DATAODD = 0;
static int POSX, POSY, SX, SY, EX, EY = 0;

#define CMD(X) (void)(X);

void DATA(uint8_t x) {
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

void display_init(void)
{
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
    SDL_SetRenderDrawColor(RENDERER, BACKLIGHT, BACKLIGHT, BACKLIGHT, 255);
    SDL_RenderClear(RENDERER);
    BUFFER = SDL_CreateRGBSurface(0, DISPLAY_RESX, DISPLAY_RESY, 16, 0xF800, 0x07E0, 0x001F, 0x0000);
    TEXTURE = SDL_CreateTexture(RENDERER, SDL_PIXELFORMAT_RGB565, SDL_TEXTUREACCESS_STREAMING, DISPLAY_RESX, DISPLAY_RESY);
    SDL_SetTextureBlendMode(TEXTURE, SDL_BLENDMODE_NONE);
    SDL_SetTextureAlphaMod(TEXTURE, 0);
}

static void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1)
{
    SX = x0; SY = y0;
    EX = x1; EY = y1;
    POSX = SX; POSY = SY;
    DATAODD = 0;
}

void display_refresh(void)
{
    SDL_RenderClear(RENDERER);
    SDL_UpdateTexture(TEXTURE, NULL, BUFFER->pixels, BUFFER->pitch);
    const SDL_Rect r = {DISPLAY_BORDER, DISPLAY_BORDER, DISPLAY_RESX, DISPLAY_RESY};
    SDL_RenderCopyEx(RENDERER, TEXTURE, NULL, &r, ORIENTATION, NULL, 0);
    SDL_RenderPresent(RENDERER);
}

static void display_set_orientation(int degrees)
{
}

static void display_set_backlight(int val)
{
    SDL_SetRenderDrawColor(RENDERER, val, val, val, 255);
}
