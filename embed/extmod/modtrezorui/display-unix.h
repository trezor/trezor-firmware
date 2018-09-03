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

#define DISPLAY_EMULATOR_BORDER 16

#define DISPLAY_TOUCH_OFFSET_X 180
#define DISPLAY_TOUCH_OFFSET_Y 120

#define WINDOW_WIDTH 600
#define WINDOW_HEIGHT 800

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
    RENDERER = SDL_CreateRenderer(win, -1, 0);
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
        sdl_touch_offset_x = DISPLAY_TOUCH_OFFSET_X;
        sdl_touch_offset_y = DISPLAY_TOUCH_OFFSET_Y;
    } else {
        SDL_SetWindowSize(win, DISPLAY_RESX + 2 * DISPLAY_EMULATOR_BORDER, DISPLAY_RESY + 2 * DISPLAY_EMULATOR_BORDER);
        sdl_touch_offset_x = DISPLAY_EMULATOR_BORDER;
        sdl_touch_offset_y = DISPLAY_EMULATOR_BORDER;
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
        const SDL_Rect r = {DISPLAY_TOUCH_OFFSET_X, DISPLAY_TOUCH_OFFSET_Y, DISPLAY_RESX, DISPLAY_RESY};
        SDL_RenderCopyEx(RENDERER, TEXTURE, NULL, &r, DISPLAY_ORIENTATION, NULL, 0);
    } else {
        const SDL_Rect r = {DISPLAY_EMULATOR_BORDER, DISPLAY_EMULATOR_BORDER, DISPLAY_RESX, DISPLAY_RESY};
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
