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
#define _GNU_SOURCE

#include <SDL.h>
#include <SDL_image.h>
#include <math.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "common.h"
#include "display.h"
#include "profile.h"

#include TREZOR_BOARD

#define EMULATOR_BORDER 16

static SDL_Window *WINDOW;
static SDL_Renderer *RENDERER;
static SDL_Surface *BUFFER;
static SDL_Texture *TEXTURE, *BACKGROUND;

static SDL_Surface *PREV_SAVED;

static int DISPLAY_BACKLIGHT = -1;
static int DISPLAY_ORIENTATION = -1;

int sdl_display_res_x = DISPLAY_RESX, sdl_display_res_y = DISPLAY_RESY;
int sdl_touch_offset_x, sdl_touch_offset_y;

// Using RGB565 (16-bit) color format.
typedef uint16_t pixel_color;

// this is just for compatibility with DMA2D using algorithms
uint8_t *const DISPLAY_DATA_ADDRESS = 0;

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

void display_pixeldata(pixel_color c) {
#if !defined USE_RGB_COLORS
  // set to white if highest bits of all R, G, B values are set to 1
  // bin(10000 100000 10000) = hex(0x8410)
  // otherwise set to black
  c = (c & 0x8410) ? 0xFFFF : 0x0000;
#endif
  if (!RENDERER) {
    display_init();
  }
  if (PIXELWINDOW.pos.x <= PIXELWINDOW.end.x &&
      PIXELWINDOW.pos.y <= PIXELWINDOW.end.y) {
    ((pixel_color *)
         BUFFER->pixels)[PIXELWINDOW.pos.x + PIXELWINDOW.pos.y * BUFFER->pitch /
                                                 sizeof(pixel_color)] = c;
  }
  PIXELWINDOW.pos.x++;
  if (PIXELWINDOW.pos.x > PIXELWINDOW.end.x) {
    PIXELWINDOW.pos.x = PIXELWINDOW.start.x;
    PIXELWINDOW.pos.y++;
  }
}

void display_pixeldata_dirty(void) {}

void display_reset_state() {}

void display_init_seq(void) {}

void display_deinit(void) {
  SDL_FreeSurface(PREV_SAVED);
  SDL_FreeSurface(BUFFER);
  if (BACKGROUND != NULL) {
    SDL_DestroyTexture(BACKGROUND);
  }
  if (TEXTURE != NULL) {
    SDL_DestroyTexture(TEXTURE);
  }
  if (RENDERER != NULL) {
    SDL_DestroyRenderer(RENDERER);
  }
  if (WINDOW != NULL) {
    SDL_DestroyWindow(WINDOW);
  }
  SDL_Quit();
}

void display_init(void) {
  if (SDL_Init(SDL_INIT_VIDEO) != 0) {
    printf("%s\n", SDL_GetError());
    error_shutdown("SDL_Init error");
  }
  atexit(display_deinit);

  char *window_title = NULL;
  char *window_title_alloc = NULL;
  if (asprintf(&window_title_alloc, "Trezor^emu: %s", profile_name()) > 0) {
    window_title = window_title_alloc;
  } else {
    window_title = "Trezor^emu";
    window_title_alloc = NULL;
  }

  WINDOW =
      SDL_CreateWindow(window_title, SDL_WINDOWPOS_UNDEFINED,
                       SDL_WINDOWPOS_UNDEFINED, WINDOW_WIDTH, WINDOW_HEIGHT,
#ifdef TREZOR_EMULATOR_RASPI
                       SDL_WINDOW_SHOWN | SDL_WINDOW_FULLSCREEN
#else
                       SDL_WINDOW_SHOWN | SDL_WINDOW_ALLOW_HIGHDPI
#endif
      );
  free(window_title_alloc);
  if (!WINDOW) {
    printf("%s\n", SDL_GetError());
    error_shutdown("SDL_CreateWindow error");
  }
  RENDERER = SDL_CreateRenderer(WINDOW, -1, SDL_RENDERER_SOFTWARE);
  if (!RENDERER) {
    printf("%s\n", SDL_GetError());
    SDL_DestroyWindow(WINDOW);
    error_shutdown("SDL_CreateRenderer error");
  }
  SDL_SetRenderDrawColor(RENDERER, 0, 0, 0, 255);
  SDL_RenderClear(RENDERER);
  BUFFER = SDL_CreateRGBSurface(0, MAX_DISPLAY_RESX, MAX_DISPLAY_RESY, 16,
                                0xF800, 0x07E0, 0x001F, 0x0000);
  TEXTURE = SDL_CreateTexture(RENDERER, SDL_PIXELFORMAT_RGB565,
                              SDL_TEXTUREACCESS_STREAMING, DISPLAY_RESX,
                              DISPLAY_RESY);
  SDL_SetTextureBlendMode(TEXTURE, SDL_BLENDMODE_BLEND);
#ifdef __APPLE__
  // macOS Mojave SDL black screen workaround
  SDL_PumpEvents();
  SDL_SetWindowSize(WINDOW, WINDOW_WIDTH, WINDOW_HEIGHT);
#endif
#include BACKGROUND_FILE
#define CONCAT_LEN_HELPER(name) name##_len
#define CONCAT_LEN(name) CONCAT_LEN_HELPER(name)
  BACKGROUND = IMG_LoadTexture_RW(
      RENDERER, SDL_RWFromMem(BACKGROUND_NAME, CONCAT_LEN(BACKGROUND_NAME)), 0);
  if (BACKGROUND) {
    SDL_SetTextureBlendMode(BACKGROUND, SDL_BLENDMODE_NONE);
    sdl_touch_offset_x = TOUCH_OFFSET_X;
    sdl_touch_offset_y = TOUCH_OFFSET_Y;
  } else {
    SDL_SetWindowSize(WINDOW, DISPLAY_RESX + 2 * EMULATOR_BORDER,
                      DISPLAY_RESY + 2 * EMULATOR_BORDER);
    sdl_touch_offset_x = EMULATOR_BORDER;
    sdl_touch_offset_y = EMULATOR_BORDER;
  }
#if !USE_BACKLIGHT
  // some models do not have backlight capabilities in hardware, so
  // setting its value here for emulator to avoid
  // calling any `set_backlight` functions
  DISPLAY_BACKLIGHT = 255;
#else
  DISPLAY_BACKLIGHT = 0;
#endif
#ifdef TREZOR_EMULATOR_RASPI
  DISPLAY_ORIENTATION = 270;
  SDL_ShowCursor(SDL_DISABLE);
#else
  DISPLAY_ORIENTATION = 0;
#endif
}

void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1) {
  if (!RENDERER) {
    display_init();
  }
  PIXELWINDOW.start.x = x0;
  PIXELWINDOW.start.y = y0;
  PIXELWINDOW.end.x = x1;
  PIXELWINDOW.end.y = y1;
  PIXELWINDOW.pos.x = x0;
  PIXELWINDOW.pos.y = y0;
}

void display_sync(void) {}

void display_refresh(void) {
  if (!RENDERER) {
    display_init();
  }
  if (BACKGROUND) {
    const SDL_Rect r = {0, 0, WINDOW_WIDTH, WINDOW_HEIGHT};
    SDL_RenderCopy(RENDERER, BACKGROUND, NULL, &r);
  } else {
    SDL_RenderClear(RENDERER);
  }
  // Show the display buffer
  SDL_UpdateTexture(TEXTURE, NULL, BUFFER->pixels, BUFFER->pitch);
#define BACKLIGHT_NORMAL 150
  SDL_SetTextureAlphaMod(TEXTURE,
                         MIN(255, 255 * DISPLAY_BACKLIGHT / BACKLIGHT_NORMAL));
  if (BACKGROUND) {
    const SDL_Rect r = {TOUCH_OFFSET_X, TOUCH_OFFSET_Y, DISPLAY_RESX,
                        DISPLAY_RESY};
    SDL_RenderCopyEx(RENDERER, TEXTURE, NULL, &r, DISPLAY_ORIENTATION, NULL, 0);
  } else {
    const SDL_Rect r = {EMULATOR_BORDER, EMULATOR_BORDER, DISPLAY_RESX,
                        DISPLAY_RESY};
    SDL_RenderCopyEx(RENDERER, TEXTURE, NULL, &r, DISPLAY_ORIENTATION, NULL, 0);
  }
  SDL_RenderPresent(RENDERER);
}

int display_orientation(int degrees) {
  if (degrees != DISPLAY_ORIENTATION) {
#if defined ORIENTATION_NSEW
    if (degrees == 0 || degrees == 90 || degrees == 180 || degrees == 270) {
#elif defined ORIENTATION_NS
    if (degrees == 0 || degrees == 180) {
#else
    if (degrees == 0) {
#endif
      DISPLAY_ORIENTATION = degrees;
      display_refresh();
    }
  }
  return DISPLAY_ORIENTATION;
}

int display_get_orientation(void) { return DISPLAY_ORIENTATION; }

int display_backlight(int val) {
#if !USE_BACKLIGHT
  val = 255;
#endif
  if (DISPLAY_BACKLIGHT != val && val >= 0 && val <= 255) {
    DISPLAY_BACKLIGHT = val;
    display_refresh();
  }
  return DISPLAY_BACKLIGHT;
}

const char *display_save(const char *prefix) {
  if (!RENDERER) {
    display_init();
  }
  static int count;
  static char filename[256];
  // take a cropped view of the screen contents
  const SDL_Rect rect = {0, 0, DISPLAY_RESX, DISPLAY_RESY};
  SDL_Surface *crop = SDL_CreateRGBSurface(
      BUFFER->flags, rect.w, rect.h, BUFFER->format->BitsPerPixel,
      BUFFER->format->Rmask, BUFFER->format->Gmask, BUFFER->format->Bmask,
      BUFFER->format->Amask);
  SDL_BlitSurface(BUFFER, &rect, crop, NULL);
  // compare with previous screen, skip if equal
  if (PREV_SAVED != NULL) {
    if (memcmp(PREV_SAVED->pixels, crop->pixels, crop->pitch * crop->h) == 0) {
      SDL_FreeSurface(crop);
      return filename;
    }
    SDL_FreeSurface(PREV_SAVED);
  }
  // save to png
  snprintf(filename, sizeof(filename), "%s%08d.png", prefix, count++);
  IMG_SavePNG(crop, filename);
  PREV_SAVED = crop;
  return filename;
}

void display_clear_save(void) {
  SDL_FreeSurface(PREV_SAVED);
  PREV_SAVED = NULL;
}

uint8_t *display_get_wr_addr(void) { return (uint8_t *)DISPLAY_DATA_ADDRESS; }

void display_finish_actions(void) {}

void display_reinit(void) {}
