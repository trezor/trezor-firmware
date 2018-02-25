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

static SDL_Renderer *RENDERER;
static SDL_Surface *BUFFER;
static SDL_Texture *TEXTURE, *BACKGROUND;

static struct {
    struct {
        uint16_t x, y;
    } start;
    struct {
        uint16_t x, y;
    } end;
    struct {
        uint16_t x, y;
    } pos;
} PIXELWINDOW;

void PIXELDATA(uint16_t c) {
    if (!RENDERER) {
        display_init();
    }
    if (PIXELWINDOW.pos.x <= PIXELWINDOW.end.x && PIXELWINDOW.pos.y <= PIXELWINDOW.end.y) {
        ((uint16_t *)BUFFER->pixels)[PIXELWINDOW.pos.x + PIXELWINDOW.pos.y * BUFFER->pitch / sizeof(uint16_t)] = c;
    }
    PIXELWINDOW.pos.x++;
    if (PIXELWINDOW.pos.x > PIXELWINDOW.end.x) {
        PIXELWINDOW.pos.x = PIXELWINDOW.start.x;
        PIXELWINDOW.pos.y++;
    }
}
#else
#define PIXELDATA(X) (void)(X)
#endif

void display_init(void)
{
#ifndef TREZOR_NOUI
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        printf("%s\n", SDL_GetError());
        ensure(secfalse, "SDL_Init error");
    }
    atexit(SDL_Quit);
    SDL_Window *win = SDL_CreateWindow("TREZOR Emulator", SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED, WINDOW_WIDTH, WINDOW_HEIGHT, SDL_WINDOW_SHOWN);
    if (!win) {
        printf("%s\n", SDL_GetError());
        ensure(secfalse, "SDL_CreateWindow error");
    }
    RENDERER = SDL_CreateRenderer(win, -1, SDL_RENDERER_ACCELERATED);
    if (!RENDERER) {
        printf("%s\n", SDL_GetError());
        SDL_DestroyWindow(win);
        ensure(secfalse, "SDL_CreateRenderer error");
    }
    SDL_SetRenderDrawColor(RENDERER, 0, 0, 0, 255);
    SDL_RenderClear(RENDERER);
    BUFFER = SDL_CreateRGBSurface(0, MAX_DISPLAY_RESX, MAX_DISPLAY_RESY, 16, 0xF800, 0x07E0, 0x001F, 0x0000);
    TEXTURE = SDL_CreateTexture(RENDERER, SDL_PIXELFORMAT_RGB565, SDL_TEXTUREACCESS_STREAMING, DISPLAY_RESX, DISPLAY_RESY);
    SDL_SetTextureBlendMode(TEXTURE, SDL_BLENDMODE_BLEND);
    // TODO: find better way how to embed/distribute background image
    BACKGROUND = IMG_LoadTexture(RENDERER, "../embed/unix/background.jpg");
    if (BACKGROUND) {
        SDL_SetTextureBlendMode(BACKGROUND, SDL_BLENDMODE_NONE);
    }
    DISPLAY_BACKLIGHT = 0;
    DISPLAY_ORIENTATION = 0;
#endif
}

static void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1)
{
#ifndef TREZOR_NOUI
    if (!RENDERER) {
        display_init();
    }
    PIXELWINDOW.start.x = x0; PIXELWINDOW.start.y = y0;
    PIXELWINDOW.end.x = x1; PIXELWINDOW.end.y = y1;
    PIXELWINDOW.pos.x = x0; PIXELWINDOW.pos.y = y0;
#endif
}

void display_refresh(void)
{
#ifndef TREZOR_NOUI
    if (!RENDERER) {
        display_init();
    }
    if (BACKGROUND) {
        SDL_RenderCopy(RENDERER, BACKGROUND, NULL, NULL);
    } else {
        SDL_RenderClear(RENDERER);
    }
    SDL_UpdateTexture(TEXTURE, NULL, BUFFER->pixels, BUFFER->pitch);
#define BACKLIGHT_NORMAL 150
    SDL_SetTextureAlphaMod(TEXTURE, MIN(255, 255 * DISPLAY_BACKLIGHT / BACKLIGHT_NORMAL));
    const SDL_Rect r = {DISPLAY_TOUCH_OFFSET_X, DISPLAY_TOUCH_OFFSET_Y, DISPLAY_RESX, DISPLAY_RESY};
    SDL_RenderCopyEx(RENDERER, TEXTURE, NULL, &r, DISPLAY_ORIENTATION, NULL, 0);
    SDL_RenderPresent(RENDERER);
#endif
}

static void display_set_orientation(int degrees)
{
    display_refresh();
}

static void display_set_backlight(int val)
{
    display_refresh();
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
