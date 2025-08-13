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

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/display.h>
#include <io/unix/sdl_display.h>

#include <SDL.h>
#include <SDL_image.h>

#include "profile.h"

#define EMULATOR_BORDER 16

#ifdef UI_COLOR_32BIT

#define PIXEL_FORMAT SDL_PIXELFORMAT_ARGB8888
#define COLOR_DEPTH 32
#define COLOR_MASK_A 0xFF000000
#define COLOR_MASK_R 0x00FF0000
#define COLOR_MASK_G 0x0000FF00
#define COLOR_MASK_B 0x000000FF
#define PIXEL_SIZE 4

#else

#define PIXEL_FORMAT SDL_PIXELFORMAT_RGB565
#define COLOR_DEPTH 16
#define COLOR_MASK_R 0xF800
#define COLOR_MASK_G 0x07E0
#define COLOR_MASK_B 0x001F
#define COLOR_MASK_A 0x0000
#define PIXEL_SIZE 2

#endif

typedef struct {
  // Set if the driver is initialized
  bool initialized;
  // Current display orientation (0 or 180)
  int orientation_angle;
  // Current backlight level ranging from 0 to 255
  int backlight_level;

  SDL_Window *window;
  SDL_Renderer *renderer;
  SDL_Surface *buffer;
  SDL_Texture *texture;
  SDL_Texture *background;
  SDL_Surface *prev_saved;

#if DISPLAY_MONO
  // SDL2 does not support 8bit surface/texture
  // and we have to simulate it
  uint8_t mono_framebuf[DISPLAY_RESX * DISPLAY_RESY];
#endif

#ifdef USE_RGB_LED
  // Color of the RGB LED
  uint32_t led_color;
#endif

#ifdef USE_HAPTIC
  uint32_t haptic_color;
  uint32_t haptic_expire_time;
#endif /* USE_HAPTIC */

} display_driver_t;

static display_driver_t g_display_driver = {
    .initialized = false,
};

//!@# TODO get rid of this...
int sdl_display_res_x = DISPLAY_RESX, sdl_display_res_y = DISPLAY_RESY;
int sdl_touch_offset_x, sdl_touch_offset_y;
int sdl_touch_x = -1, sdl_touch_y = -1;

static void display_exit_handler(void) {
  display_deinit(DISPLAY_RESET_CONTENT);
}

bool display_init(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (drv->initialized) {
    return true;
  }

  if (SDL_Init(SDL_INIT_VIDEO) != 0) {
    printf("%s\n", SDL_GetError());
    error_shutdown("SDL_Init error");
  }
  atexit(display_exit_handler);

  char *window_title = NULL;
  char *window_title_alloc = NULL;
  if (asprintf(&window_title_alloc, "Trezor^emu: %s", profile_name()) > 0) {
    window_title = window_title_alloc;
  } else {
    window_title = "Trezor^emu";
    window_title_alloc = NULL;
  }

  drv->window =
      SDL_CreateWindow(window_title, SDL_WINDOWPOS_UNDEFINED,
                       SDL_WINDOWPOS_UNDEFINED, WINDOW_WIDTH, WINDOW_HEIGHT,
#ifdef TREZOR_EMULATOR_RASPI
                       SDL_WINDOW_SHOWN | SDL_WINDOW_FULLSCREEN
#else
                       SDL_WINDOW_SHOWN
#endif
      );
  free(window_title_alloc);
  if (!drv->window) {
    printf("%s\n", SDL_GetError());
    error_shutdown("SDL_CreateWindow error");
  }
  drv->renderer = SDL_CreateRenderer(drv->window, -1, SDL_RENDERER_SOFTWARE);
  if (!drv->renderer) {
    printf("%s\n", SDL_GetError());
    SDL_DestroyWindow(drv->window);
    error_shutdown("SDL_CreateRenderer error");
  }
  SDL_SetRenderDrawColor(drv->renderer, 0, 0, 0, 255);
  SDL_RenderClear(drv->renderer);

  drv->buffer = SDL_CreateRGBSurface(0, DISPLAY_RESX, DISPLAY_RESY, COLOR_DEPTH,
                                     COLOR_MASK_R, COLOR_MASK_G, COLOR_MASK_B,
                                     COLOR_MASK_A);
  drv->texture = SDL_CreateTexture(drv->renderer, PIXEL_FORMAT,
                                   SDL_TEXTUREACCESS_STREAMING, DISPLAY_RESX,
                                   DISPLAY_RESY);
  SDL_SetTextureBlendMode(drv->texture, SDL_BLENDMODE_BLEND);
#ifdef __APPLE__
  // macOS Mojave SDL black screen workaround
  SDL_PumpEvents();
  SDL_SetWindowSize(drv->window, WINDOW_WIDTH, WINDOW_HEIGHT);
#endif
#ifdef BACKGROUND_FILE
#include BACKGROUND_FILE
#define CONCAT_LEN_HELPER(name) name##_len
#define CONCAT_LEN(name) CONCAT_LEN_HELPER(name)
  drv->background = IMG_LoadTexture_RW(
      drv->renderer,
      SDL_RWFromMem(BACKGROUND_NAME, CONCAT_LEN(BACKGROUND_NAME)), 0);
#endif
  if (drv->background) {
    SDL_SetTextureBlendMode(drv->background, SDL_BLENDMODE_NONE);
    sdl_touch_offset_x = TOUCH_OFFSET_X;
    sdl_touch_offset_y = TOUCH_OFFSET_Y;
  } else {
    SDL_SetWindowSize(drv->window, DISPLAY_RESX + 2 * EMULATOR_BORDER,
                      DISPLAY_RESY + 2 * EMULATOR_BORDER);
    sdl_touch_offset_x = EMULATOR_BORDER;
    sdl_touch_offset_y = EMULATOR_BORDER;
  }
#if !USE_BACKLIGHT
  // some models do not have backlight capabilities in hardware, so
  // setting its value here for emulator to avoid
  // calling any `set_backlight` functions
  drv->backlight_level = 255;
#else
  drv->backlight_level = 0;
#endif
#ifdef TREZOR_EMULATOR_RASPI
  drv->orientation_angle = 270;
  SDL_ShowCursor(SDL_DISABLE);
#else
  drv->orientation_angle = 0;
#endif
#ifdef USE_RGB_LED
  drv->led_color = 0;
#endif

#ifdef USE_HAPTIC
  drv->haptic_color = 0;
  drv->haptic_expire_time = 0;
#endif /* USE_HAPTIC */

  gfx_bitblt_init();

  drv->initialized = true;
  return true;
}

void display_deinit(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  gfx_bitblt_deinit();

  SDL_FreeSurface(drv->prev_saved);
  SDL_FreeSurface(drv->buffer);
  if (drv->background != NULL) {
    SDL_DestroyTexture(drv->background);
  }
  if (drv->texture != NULL) {
    SDL_DestroyTexture(drv->texture);
  }
  if (drv->renderer != NULL) {
    SDL_DestroyRenderer(drv->renderer);
  }
  if (drv->window != NULL) {
    SDL_DestroyWindow(drv->window);
  }
  SDL_Quit();

  drv->initialized = false;
}

int display_set_backlight(int level) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

#if !USE_BACKLIGHT
  level = 255;
#endif

  if (drv->backlight_level != level && level >= 0 && level <= 255) {
    drv->backlight_level = level;
    display_refresh();
  }

  return drv->backlight_level;
}

int display_get_backlight(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  return drv->backlight_level;
}

int display_set_orientation(int angle) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  if (angle != drv->orientation_angle) {
#if defined ORIENTATION_NSEW
    if (angle == 0 || angle == 90 || angle == 180 || angle == 270) {
#elif defined ORIENTATION_NS
    if (angle == 0 || angle == 180) {
#else
    if (angle == 0) {
#endif
      drv->orientation_angle = angle;
      display_refresh();
    }
  }
  return drv->orientation_angle;
}

int display_get_orientation(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  return drv->orientation_angle;
}

#ifdef FRAMEBUFFER
bool display_get_frame_buffer(display_fb_info_t *fb) {
  display_driver_t *drv = &g_display_driver;

  memset(fb, 0, sizeof(display_fb_info_t));

  if (!drv->initialized) {
    return false;
  }

#ifdef DISPLAY_MONO
  fb->ptr = drv->mono_framebuf;
  fb->stride = DISPLAY_RESX;
  fb->size = DISPLAY_RESX * DISPLAY_RESY;
#else
  fb->ptr = drv->buffer->pixels;
  fb->stride = DISPLAY_RESX * PIXEL_SIZE;
  fb->size = DISPLAY_RESX * DISPLAY_RESY * PIXEL_SIZE;
#endif
  return true;
}

#else  // FRAMEBUFFER

void display_wait_for_sync(void) {
  // not implemented in the emulator
}
#endif

#ifdef DISPLAY_MONO
// Copies driver's monochromatic framebuffer into the RGB framebuffer used by
// SDL
static void copy_mono_framebuf(display_driver_t *drv) {
  for (int y = 0; y < DISPLAY_RESY; y++) {
    uint16_t *dst =
        (uint16_t *)((uint8_t *)drv->buffer->pixels + drv->buffer->pitch * y);
    uint8_t *src = &drv->mono_framebuf[y * DISPLAY_RESX];
    for (int x = 0; x < DISPLAY_RESX; x++) {
      uint8_t lum = src[x] > 40 ? 255 : 0;
      dst[x] = gfx_color16_rgb(lum, lum, lum);
    }
  }
}
#endif

#ifdef USE_RGB_LED

void display_rgb_led(uint32_t color) {
  display_driver_t *drv = &g_display_driver;
  if (!drv->initialized) {
    return;
  }
  // Store color for future display refreshes
  drv->led_color = color;
  display_refresh();
}

void draw_rgb_led() {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  const uint32_t color = drv->led_color;

  if (color == 0) {
    return;  // No LED color set
  }

  // Extract RGB components
  uint32_t r = (color >> 16) & 0xFF;
  uint32_t g = (color >> 8) & 0xFF;
  uint32_t b = color & 0xFF;

  // Define LED circle properties
  const int radius = 5;
  int center_x = DISPLAY_RESX / 2;
  int center_y = 0;

  // Position based on background
  if (drv->background) {
    center_x += TOUCH_OFFSET_X;
    center_y = TOUCH_OFFSET_Y / 2;
  } else {
    center_x += EMULATOR_BORDER;
    center_y = EMULATOR_BORDER / 2;
  }

  // Draw the LED
  SDL_SetRenderDrawColor(drv->renderer, r, g, b, 255);
  for (int y = -radius; y <= radius; y++) {
    for (int x = -radius; x <= radius; x++) {
      if (x * x + y * y <= radius * radius) {
        SDL_RenderDrawPoint(drv->renderer, center_x + x, center_y + y);
      }
    }
  }
  SDL_SetRenderDrawColor(drv->renderer, 0, 0, 0, 255);
}
#endif  // USE_RGB_LED

#ifdef USE_HAPTIC

void display_haptic_effect(haptic_effect_t effect) {
  display_driver_t *drv = &g_display_driver;
  if (!drv->initialized) {
    return;
  }

  switch (effect) {
    case HAPTIC_BUTTON_PRESS:
      drv->haptic_color = 0xFF0000;                    // Red
      drv->haptic_expire_time = SDL_GetTicks() + 200;  // 200 ms duration
      break;
    case HAPTIC_HOLD_TO_CONFIRM:
      drv->haptic_color = 0xFF00;                      // Green
      drv->haptic_expire_time = SDL_GetTicks() + 500;  // 500 ms duration
      break;
    case HAPTIC_BOOTLOADER_ENTRY:
      drv->haptic_color = 0x0000FF;                    // Blue
      drv->haptic_expire_time = SDL_GetTicks() + 500;  // 500 ms duration
      break;
    default:
      drv->haptic_color = 0x0;
      break;
  }

  display_refresh();
}

void display_custom_effect(uint32_t duration_ms) {
  display_driver_t *drv = &g_display_driver;
  if (!drv->initialized) {
    return;
  }

  drv->haptic_color = 0xFFA500;  // Orange
  drv->haptic_expire_time = SDL_GetTicks() + duration_ms;
  display_refresh();
}

void draw_haptic() {
  display_driver_t *drv = &g_display_driver;
  if (!drv->initialized) {
    return;
  }

  if (SDL_GetTicks() > drv->haptic_expire_time) {
    drv->haptic_color = 0;  // Clear
    return;
  }

  const uint32_t color = drv->haptic_color;

  if (color == 0) {
    return;  // No LED color set
  }

  // Extract RGB components
  uint32_t r = (color >> 16) & 0xFF;
  uint32_t g = (color >> 8) & 0xFF;
  uint32_t b = color & 0xFF;

  // Define touch circle properties
  const int radius = 5;

#ifdef USE_TOUCH
  int center_x = sdl_touch_x;
  int center_y = sdl_touch_y;
#else
  int center_x = DISPLAY_RESX / 2;
  int center_y = DISPLAY_RESY + 20;
#endif /* USE_TOUCH */

  // Position based on background
  if (drv->background) {
    center_x += TOUCH_OFFSET_X;
    center_y += TOUCH_OFFSET_Y;
  } else {
    center_x += EMULATOR_BORDER;
    center_y += EMULATOR_BORDER;
  }

  // // Draw the touch circle
  SDL_SetRenderDrawColor(drv->renderer, r, g, b, 255);

  for (int y = -radius; y <= radius; y++) {
    for (int x = -radius; x <= radius; x++) {
      if (x * x + y * y <= radius * radius) {
        SDL_RenderDrawPoint(drv->renderer, center_x + x, center_y + y);
      }
    }
  }
  SDL_SetRenderDrawColor(drv->renderer, 0, 0, 0, 255);
}
#endif /* USE_HAPTIC */

void display_refresh(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

#ifdef DISPLAY_MONO
  copy_mono_framebuf(drv);
#endif

  if (drv->background) {
    const SDL_Rect r = {0, 0, WINDOW_WIDTH, WINDOW_HEIGHT};
    SDL_RenderCopy(drv->renderer, drv->background, NULL, &r);
  } else {
    SDL_RenderClear(drv->renderer);
  }
  // Show the display buffer
  SDL_UpdateTexture(drv->texture, NULL, drv->buffer->pixels,
                    drv->buffer->pitch);
#define BACKLIGHT_NORMAL 150
  SDL_SetTextureAlphaMod(
      drv->texture, MIN(255, 255 * drv->backlight_level / BACKLIGHT_NORMAL));
  if (drv->background) {
    const SDL_Rect r = {TOUCH_OFFSET_X, TOUCH_OFFSET_Y, DISPLAY_RESX,
                        DISPLAY_RESY};
    SDL_RenderCopyEx(drv->renderer, drv->texture, NULL, &r,
                     drv->orientation_angle, NULL, 0);
  } else {
    const SDL_Rect r = {EMULATOR_BORDER, EMULATOR_BORDER, DISPLAY_RESX,
                        DISPLAY_RESY};
    SDL_RenderCopyEx(drv->renderer, drv->texture, NULL, &r,
                     drv->orientation_angle, NULL, 0);
  }
#ifdef USE_RGB_LED
  draw_rgb_led();
#endif

#ifdef USE_HAPTIC
  draw_haptic();
#endif

  SDL_RenderPresent(drv->renderer);
}

#ifndef DISPLAY_MONO

void display_fill(const gfx_bitblt_t *bb) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row =
      (uint8_t *)drv->buffer->pixels + (drv->buffer->pitch * bb_new.dst_y);
  bb_new.dst_stride = drv->buffer->pitch;

#ifdef UI_COLOR_32BIT
  gfx_rgba8888_fill(&bb_new);
#else
  gfx_rgb565_fill(&bb_new);
#endif
}

void display_copy_rgb565(const gfx_bitblt_t *bb) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row =
      (uint8_t *)drv->buffer->pixels + (drv->buffer->pitch * bb_new.dst_y);
  bb_new.dst_stride = drv->buffer->pitch;

#ifdef UI_COLOR_32BIT
  gfx_rgba8888_copy_rgb565(&bb_new);
#else
  gfx_rgb565_copy_rgb565(&bb_new);
#endif
}

void display_copy_mono1p(const gfx_bitblt_t *bb) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row =
      (uint8_t *)drv->buffer->pixels + (drv->buffer->pitch * bb_new.dst_y);
  bb_new.dst_stride = drv->buffer->pitch;

#ifdef UI_COLOR_32BIT
  gfx_rgba8888_copy_mono1p(&bb_new);
#else
  gfx_rgb565_copy_mono1p(&bb_new);
#endif
}

#else  // DISPLAY_MONO

void display_fill(const gfx_bitblt_t *bb) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = drv->mono_framebuf + (DISPLAY_RESX * bb_new.dst_y);
  bb_new.dst_stride = DISPLAY_RESX;

  gfx_mono8_fill(&bb_new);
}

void display_copy_mono1p(const gfx_bitblt_t *bb) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = drv->mono_framebuf + (DISPLAY_RESX * bb_new.dst_y);
  bb_new.dst_stride = DISPLAY_RESX;

  gfx_mono8_copy_mono1p(&bb_new);
}

#endif

void display_save(const char *prefix) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

#ifdef DISPLAY_MONO
  copy_mono_framebuf(drv);
#endif

  static int count;
  static char filename[256];
  // take a cropped view of the screen contents
  const SDL_Rect rect = {0, 0, DISPLAY_RESX, DISPLAY_RESY};
  SDL_Surface *crop = SDL_CreateRGBSurface(
      drv->buffer->flags, rect.w, rect.h, drv->buffer->format->BitsPerPixel,
      drv->buffer->format->Rmask, drv->buffer->format->Gmask,
      drv->buffer->format->Bmask, drv->buffer->format->Amask);
  SDL_BlitSurface(drv->buffer, &rect, crop, NULL);

#ifdef USE_HAPTIC
  // === Static haptic dots ===
  if (SDL_GetTicks() < drv->haptic_expire_time) {
    uint32_t color = drv->haptic_color;

    if (color != 0) {
      // Extract RGB components
      uint32_t r = (color >> 16) & 0xFF;
      uint32_t g = (color >> 8) & 0xFF;
      uint32_t b = color & 0xFF;
      // Draw a one-pixel dot
      if (sdl_touch_x >= 0 && sdl_touch_x < rect.w && sdl_touch_y >= 0 &&
          sdl_touch_y < rect.h) {
        Uint8 *pixel_ptr = (Uint8 *)crop->pixels + (sdl_touch_y * crop->pitch) +
                           (sdl_touch_x * crop->format->BytesPerPixel);
        *(Uint32 *)pixel_ptr = SDL_MapRGBA(crop->format, r, g, b, 255);
      }
    }
  }
#endif  // USE_HAPTIC

  // compare with previous screen, skip if equal
  if (drv->prev_saved != NULL) {
    if (memcmp(drv->prev_saved->pixels, crop->pixels, crop->pitch * crop->h) ==
        0) {
      SDL_FreeSurface(crop);
      return;
    }
    SDL_FreeSurface(drv->prev_saved);
  }
  // save to png
  snprintf(filename, sizeof(filename), "%s%08d.png", prefix, count++);
  IMG_SavePNG(crop, filename);
  drv->prev_saved = crop;
}

void display_clear_save(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  SDL_FreeSurface(drv->prev_saved);
  drv->prev_saved = NULL;
}
