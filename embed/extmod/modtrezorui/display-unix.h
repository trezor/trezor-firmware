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

#include <stdlib.h>
#ifndef TREZOR_EMULATOR_NOUI
#include <SDL2/SDL.h>
#include <SDL2/SDL_image.h>

#define EMULATOR_BORDER 16

#if TREZOR_MODEL == T

#define WINDOW_WIDTH    400
#define WINDOW_HEIGHT   600
#define TOUCH_OFFSET_X  80
#define TOUCH_OFFSET_Y  110

#elif TREZOR_MODEL == 1

#define WINDOW_WIDTH    200
#define WINDOW_HEIGHT   340
#define TOUCH_OFFSET_X  36
#define TOUCH_OFFSET_Y  92

#else
#error Unknown TREZOR Model
#endif

static SDL_Renderer *RENDERER;
static SDL_Surface *BUFFER;
static SDL_Texture *TEXTURE, *BACKGROUND;

int sdl_display_res_x = DISPLAY_RESX, sdl_display_res_y = DISPLAY_RESX;
int sdl_touch_offset_x, sdl_touch_offset_y;

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
#if TREZOR_MODEL == 1
    // set to white if highest bits of all R, G, B values are set to 1
    // bin(10000 100000 10000) = hex(0x8410)
    // otherwise set to black
    c = (c & 0x8410) ? 0xFFFF : 0x0000;
#endif
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
#ifndef TREZOR_EMULATOR_NOUI
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
    RENDERER = SDL_CreateRenderer(win, -1, SDL_RENDERER_SOFTWARE);
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
    BACKGROUND = IMG_LoadTexture(RENDERER, "../embed/unix/background_" XSTR(TREZOR_MODEL) ".jpg");
    if (BACKGROUND) {
        SDL_SetTextureBlendMode(BACKGROUND, SDL_BLENDMODE_NONE);
        sdl_touch_offset_x = TOUCH_OFFSET_X;
        sdl_touch_offset_y = TOUCH_OFFSET_Y;
    } else {
        SDL_SetWindowSize(win, DISPLAY_RESX + 2 * EMULATOR_BORDER, DISPLAY_RESY + 2 * EMULATOR_BORDER);
        sdl_touch_offset_x = EMULATOR_BORDER;
        sdl_touch_offset_y = EMULATOR_BORDER;
    }
    DISPLAY_BACKLIGHT = 0;
    DISPLAY_ORIENTATION = 0;
#endif
}

static void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1)
{
#ifndef TREZOR_EMULATOR_NOUI
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
#ifndef TREZOR_EMULATOR_NOUI
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
    if (BACKGROUND) {
        const SDL_Rect r = {TOUCH_OFFSET_X, TOUCH_OFFSET_Y, DISPLAY_RESX, DISPLAY_RESY};
        SDL_RenderCopyEx(RENDERER, TEXTURE, NULL, &r, DISPLAY_ORIENTATION, NULL, 0);
    } else {
        const SDL_Rect r = {EMULATOR_BORDER, EMULATOR_BORDER, DISPLAY_RESX, DISPLAY_RESY};
        SDL_RenderCopyEx(RENDERER, TEXTURE, NULL, &r, DISPLAY_ORIENTATION, NULL, 0);
    }
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

void display_save(const char *prefix)
{
#ifndef TREZOR_EMULATOR_NOUI
    if (!RENDERER) {
        display_init();
    }
    static uint32_t cnt = 0;
    char fname[256];
    snprintf(fname, sizeof(fname), "%s%08d.png", prefix, cnt);
    const SDL_Rect rect = {0, 0, DISPLAY_RESX, DISPLAY_RESY};
    SDL_Surface *crop = SDL_CreateRGBSurface(BUFFER->flags, rect.w, rect.h, BUFFER->format->BitsPerPixel, BUFFER->format->Rmask, BUFFER->format->Gmask, BUFFER->format->Bmask, BUFFER->format->Amask);
    SDL_BlitSurface(BUFFER, &rect, crop, NULL);
    IMG_SavePNG(crop, fname);
    SDL_FreeSurface(crop);
    fprintf(stderr, "Saved screenshot to %s\n", fname);
    cnt++;
#endif
}
