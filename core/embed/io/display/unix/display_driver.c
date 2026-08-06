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
#include <sys/logging.h>
#include <sys/profile.h>
#include <sys/systask.h>

#include <SDL3/SDL.h>
#include <SDL3/SDL_blendmode.h>
#include <SDL3/SDL_render.h>
#include <SDL3_image/SDL_image.h>
#include <stdlib.h>

#ifdef USE_POWER_MANAGER
#include "suspend_overlay.h"
#endif

LOG_DECLARE(display_driver)

#define EMULATOR_BORDER 16

// Limits for the emulator window scale factor. Factors below 1 shrink the
// window, which is useful for the models with a large window.
#define EMULATOR_MIN_SCALE 0.25f
#define EMULATOR_MAX_SCALE 16.0f

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
  uint8_t backlight_level;

  SDL_Window *window;
  SDL_Renderer *renderer;
  SDL_Surface *buffer;
  SDL_Texture *texture;
  SDL_Texture *background;
  SDL_Texture *foreground;
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
} display_driver_t;

static display_driver_t g_display_driver = {
    .initialized = false,
};

int sdl_display_res_x = DISPLAY_RESX, sdl_display_res_y = DISPLAY_RESY;
int sdl_touch_offset_x, sdl_touch_offset_y;

#ifndef TREZOR_EMULATOR_RASPI
// Returns the factor by which the emulator window is scaled, as requested
// through `TREZOR_EMULATOR_SCALE`. Returns 1, i.e. no scaling, when the
// variable is unset or does not hold a valid value.
static float emulator_scale(void) {
  const char *env_scale = getenv("TREZOR_EMULATOR_SCALE");
  if (env_scale == NULL || env_scale[0] == '\0') {
    return 1.0f;
  }

  char *end = NULL;
  const float scale = strtof(env_scale, &end);
  // Negated comparisons so that NaN, which compares false either way, is
  // rejected as well.
  if (end == NULL || *end != '\0' || !(scale >= EMULATOR_MIN_SCALE) ||
      !(scale <= EMULATOR_MAX_SCALE)) {
    LOG_WARN("ignoring out-of-range TREZOR_EMULATOR_SCALE '%s'", env_scale);
    return 1.0f;
  }

  return scale;
}
#endif

bool display_init(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (drv->initialized) {
    return true;
  }

  if (!SDL_Init(SDL_INIT_VIDEO | SDL_INIT_HAPTIC | SDL_INIT_EVENTS)) {
    LOG_ERR("%s", SDL_GetError());
    error_shutdown("SDL_Init error");
  }

  char *window_title = NULL;
  char *window_title_alloc = NULL;
  if (asprintf(&window_title_alloc, "Trezor^emu: %s", profile_name()) > 0) {
    window_title = window_title_alloc;
  } else {
    window_title = "Trezor^emu";
    window_title_alloc = NULL;
  }

  Uint32 window_flags =
#ifdef TREZOR_EMULATOR_RASPI
      SDL_WINDOW_FULLSCREEN;
#else
      // Windows are visible by default in SDL3. Keep this one hidden until its
      // final size is known, otherwise it is mapped at the unscaled size first
      // and visibly resized once the scale factor has been applied below.
      SDL_WINDOW_HIDDEN;
#endif

  // SDL3 renderer creation can fail on Wayland.
  // On failure falls back to X11 via XWayland.
  for (int attempt = 1; attempt <= 2; attempt++) {
    if (attempt == 2) {
      // Second attempt: tear down Wayland, reinit with X11
      LOG_WARN("Renderer failed on Wayland (%s), retrying with X11",
               SDL_GetError());
      SDL_DestroyWindow(drv->window);
      drv->window = NULL;
      SDL_QuitSubSystem(SDL_INIT_VIDEO);

      SDL_SetHintWithPriority(SDL_HINT_VIDEO_DRIVER, "x11", SDL_HINT_OVERRIDE);
      if (!SDL_InitSubSystem(SDL_INIT_VIDEO)) {
        free(window_title_alloc);
        LOG_ERR("X11 fallback: %s", SDL_GetError());
        error_shutdown("SDL_Init error");
      }
    }

    drv->window = SDL_CreateWindow(window_title, WINDOW_WIDTH, WINDOW_HEIGHT,
                                   window_flags);
    if (!drv->window) {
      break;
    }

    drv->renderer = SDL_CreateRenderer(drv->window, NULL);
    if (drv->renderer) {
      break;  // success
    }

    // Retry if we're on Wayland and this is the first attempt
    const char *video_driver = SDL_GetCurrentVideoDriver();
    if (attempt == 1 && video_driver && strcmp(video_driver, "wayland") == 0) {
      continue;  // try fallback with x11
    }
    break;  // no fallback possible
  }

  free(window_title_alloc);

  if (!drv->window) {
    LOG_ERR("%s", SDL_GetError());
    error_shutdown("SDL_CreateWindow error");
  }

  if (!drv->renderer) {
    LOG_ERR("%s", SDL_GetError());
    SDL_DestroyWindow(drv->window);
    error_shutdown("SDL_CreateRenderer error");
  }

  SDL_SetRenderDrawColor(drv->renderer, 0, 0, 0, 255);
  SDL_RenderClear(drv->renderer);

  drv->buffer = SDL_CreateSurface(
      DISPLAY_RESX, DISPLAY_RESY,
      SDL_GetPixelFormatForMasks(COLOR_DEPTH, COLOR_MASK_R, COLOR_MASK_G,
                                 COLOR_MASK_B, COLOR_MASK_A));
  drv->texture = SDL_CreateTexture(drv->renderer, PIXEL_FORMAT,
                                   SDL_TEXTUREACCESS_STREAMING, DISPLAY_RESX,
                                   DISPLAY_RESY);
  SDL_SetTextureBlendMode(drv->texture, SDL_BLENDMODE_BLEND);
  SDL_SetTextureScaleMode(drv->texture, SDL_SCALEMODE_NEAREST);
#ifdef __APPLE__
  // macOS Mojave SDL black screen workaround
  SDL_PumpEvents();
  SDL_SetWindowSize(drv->window, WINDOW_WIDTH, WINDOW_HEIGHT);
#endif
#define CONCAT_LEN_HELPER(name) name##_len
#define CONCAT_LEN(name) CONCAT_LEN_HELPER(name)
#ifdef BACKGROUND_FILE
#include BACKGROUND_FILE
  drv->background = IMG_LoadTexture_IO(
      drv->renderer,
      SDL_IOFromMem(BACKGROUND_NAME, CONCAT_LEN(BACKGROUND_NAME)), true);
#endif
#ifdef FOREGROUND_FILE
#include FOREGROUND_FILE
  drv->foreground = IMG_LoadTexture_IO(
      drv->renderer,
      SDL_IOFromMem(FOREGROUND_NAME, CONCAT_LEN(FOREGROUND_NAME)), true);
  if (drv->foreground) {
    SDL_SetTextureBlendMode(drv->foreground, SDL_BLENDMODE_BLEND);
    // check that foreground dimensions match the window size which is important
    // for cutouts
    float fw, fh;
    if (SDL_GetTextureSize(drv->foreground, &fw, &fh)) {
      if ((int)fw != WINDOW_WIDTH || (int)fh != WINDOW_HEIGHT) {
        LOG_ERR(
            "Foreground texture size (%dx%d) does not match window size "
            "(%dx%d)",
            (int)fw, (int)fh, WINDOW_WIDTH, WINDOW_HEIGHT);
        error_shutdown("Foreground texture size mismatch");
      }
    } else {
      LOG_ERR("SDL_GetTextureSize failed: %s", SDL_GetError());
      error_shutdown("SDL_GetTextureSize error");
    }
  }
#endif
  if (drv->background) {
    SDL_SetTextureBlendMode(drv->background, SDL_BLENDMODE_NONE);
  }
  // Size of the coordinate space all drawing is done in, and the window size at
  // the default scale of 1.
  int logical_width;
  int logical_height;

  if (drv->background || drv->foreground) {
    logical_width = WINDOW_WIDTH;
    logical_height = WINDOW_HEIGHT;
    sdl_touch_offset_x = TOUCH_OFFSET_X;
    sdl_touch_offset_y = TOUCH_OFFSET_Y;
  } else {
    logical_width = DISPLAY_RESX + 2 * EMULATOR_BORDER;
    logical_height = DISPLAY_RESY + 2 * EMULATOR_BORDER;
    sdl_touch_offset_x = EMULATOR_BORDER;
    sdl_touch_offset_y = EMULATOR_BORDER;
  }

#ifdef TREZOR_EMULATOR_RASPI
  // The window is fullscreen on the Raspberry Pi display, so scaling it would
  // have no effect there.
  const float scale = 1.0f;
#else
  const float scale = emulator_scale();
#endif

  // The requested factor is turned into a window size in whole pixels right
  // away, so everything below reasons about integers only. Comparing the result
  // against the unscaled size also avoids testing the factor itself for
  // equality with 1.
  const int window_width = (int)(logical_width * scale + 0.5f);
  const int window_height = (int)(logical_height * scale + 0.5f);

  // The window was created at `WINDOW_WIDTH` x `WINDOW_HEIGHT`, so it only
  // needs resizing when the final size differs from that.
  if (window_width != WINDOW_WIDTH || window_height != WINDOW_HEIGHT) {
    SDL_SetWindowSize(drv->window, window_width, window_height);
  }

  if (window_width != logical_width || window_height != logical_height) {
    // Keep drawing in unscaled display coordinates and let SDL scale the
    // result to the window. Letterboxing keeps the aspect ratio intact when
    // rounding to whole pixels does not divide evenly, and it also lets
    // `sdl_display_window_to_display()` map input coordinates back.
    SDL_SetRenderLogicalPresentation(drv->renderer, logical_width,
                                     logical_height,
                                     SDL_LOGICAL_PRESENTATION_LETTERBOX);
    // Nearest-neighbour sampling, set when the texture was created, keeps
    // whole-number enlarging crisp. Any other factor needs interpolation,
    // otherwise rows and columns of pixels are dropped outright.
    if (window_width % logical_width != 0 ||
        window_height % logical_height != 0) {
      SDL_SetTextureScaleMode(drv->texture, SDL_SCALEMODE_LINEAR);
    }
  }

  // The window size is final, so it is safe to map it now. Present the cleared
  // renderer first so that the window does not appear with undefined contents.
  // A no-op on the Raspberry Pi, where the window was never hidden.
  SDL_RenderClear(drv->renderer);
  SDL_RenderPresent(drv->renderer);
  SDL_ShowWindow(drv->window);

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
  SDL_HideCursor();
#else
  drv->orientation_angle = 0;
#endif
#ifdef USE_RGB_LED
  drv->led_color = 0;
#endif

  gfx_bitblt_init();

  drv->initialized = true;
  return true;
}

void sdl_display_window_to_display(float window_x, float window_y,
                                   int *display_x, int *display_y) {
  display_driver_t *drv = &g_display_driver;

  float x = window_x;
  float y = window_y;

  // Undoes the window scaling; a no-op when the window is not scaled.
  if (drv->initialized) {
    SDL_RenderCoordinatesFromWindow(drv->renderer, window_x, window_y, &x, &y);
  }

  *display_x = (int)x;
  *display_y = (int)y;
}

void display_deinit(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  gfx_bitblt_deinit();

  SDL_DestroySurface(drv->prev_saved);
  drv->prev_saved = NULL;
  SDL_DestroySurface(drv->buffer);
  if (drv->background != NULL) {
    SDL_DestroyTexture(drv->background);
  }
  if (drv->foreground != NULL) {
    SDL_DestroyTexture(drv->foreground);
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

bool display_set_backlight(uint8_t level) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return false;
  }

#if !USE_BACKLIGHT
  level = 255;
#endif

  if (drv->backlight_level != level) {
    drv->backlight_level = level;
    display_refresh();
  }

  return true;
}

uint8_t display_get_backlight(void) {
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

  // Position based on background/foreground
  if (drv->background || drv->foreground) {
    center_x += TOUCH_OFFSET_X;
#ifdef LED_OFFSET_Y
    center_y = TOUCH_OFFSET_Y + LED_OFFSET_Y;
#else
    center_y = TOUCH_OFFSET_Y;
#endif
  } else {
    center_x += EMULATOR_BORDER;
    center_y = EMULATOR_BORDER / 2;
  }

  // Draw the LED
  SDL_SetRenderDrawColor(drv->renderer, r, g, b, 255);
  for (int y = -radius; y <= radius; y++) {
    for (int x = -radius; x <= radius; x++) {
      if (x * x + y * y <= radius * radius) {
        SDL_RenderPoint(drv->renderer, center_x + x, center_y + y);
      }
    }
  }
  SDL_SetRenderDrawColor(drv->renderer, 0, 0, 0, 255);
}
#endif  // USE_RGB_LED

static SDL_FRect screen_rect(void) {
  display_driver_t *drv = &g_display_driver;
  if (drv->background || drv->foreground) {
    return (SDL_FRect){TOUCH_OFFSET_X, TOUCH_OFFSET_Y, DISPLAY_RESX,
                       DISPLAY_RESY};
  } else {
    return (SDL_FRect){EMULATOR_BORDER, EMULATOR_BORDER, DISPLAY_RESX,
                       DISPLAY_RESY};
  }
}

static void display_refresh_internal(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

#ifdef DISPLAY_MONO
  copy_mono_framebuf(drv);
#endif

  if (drv->background) {
    const SDL_FRect r = {0, 0, WINDOW_WIDTH, WINDOW_HEIGHT};
    SDL_RenderTexture(drv->renderer, drv->background, NULL, &r);
  } else {
    SDL_RenderClear(drv->renderer);
  }
  // Show the display buffer
  SDL_UpdateTexture(drv->texture, NULL, drv->buffer->pixels,
                    drv->buffer->pitch);
#define BACKLIGHT_NORMAL 150
  SDL_SetTextureAlphaMod(
      drv->texture, MIN(255, 255 * drv->backlight_level / BACKLIGHT_NORMAL));
  const SDL_FRect r = screen_rect();
  SDL_RenderTextureRotated(drv->renderer, drv->texture, NULL, &r,
                           drv->orientation_angle, NULL, 0);

  if (drv->foreground) {
    const SDL_FRect fr = {0, 0, WINDOW_WIDTH, WINDOW_HEIGHT};
    SDL_RenderTexture(drv->renderer, drv->foreground, NULL, &fr);
  }

#ifdef USE_RGB_LED
  draw_rgb_led();
#endif

  SDL_RenderPresent(drv->renderer);
}

static void display_refresh_trampoline(uintptr_t arg1, uintptr_t arg2,
                                       uintptr_t arg3) {
  display_refresh_internal();
  systask_yield_to((systask_t *)arg1);
}

void display_refresh(void) {
  // Call SDL drawing function in the context of the kernel task
  if (systask_active() == systask_kernel()) {
    display_refresh_internal();
  } else {
    systask_push_call(systask_kernel(), (void *)display_refresh_trampoline,
                      (uintptr_t)systask_active(), 0, 0);
    systask_yield_to(systask_kernel());
  }
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
  SDL_Surface *crop = SDL_CreateSurface(rect.w, rect.h, drv->buffer->format);
  if (crop == NULL) {
    LOG_ERR("SDL_CreateSurface failed: %s", SDL_GetError());
    return;
  }
  SDL_BlitSurface(drv->buffer, &rect, crop, NULL);
  // compare with previous screen, skip if equal
  if (drv->prev_saved != NULL) {
    if (memcmp(drv->prev_saved->pixels, crop->pixels, crop->pitch * crop->h) ==
        0) {
      SDL_DestroySurface(crop);
      return;
    }
    SDL_DestroySurface(drv->prev_saved);
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

  SDL_DestroySurface(drv->prev_saved);
  drv->prev_saved = NULL;
}

#ifdef USE_POWER_MANAGER
static void display_draw_suspend_overlay_internal(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  SDL_FRect screen = screen_rect();
  // create a blue texture
  SDL_Texture *overlay =
      SDL_CreateTexture(drv->renderer, SDL_PIXELFORMAT_RGBA8888,
                        SDL_TEXTUREACCESS_STATIC, (int)screen.w, (int)screen.h);
  SDL_SetTextureBlendMode(overlay, SDL_BLENDMODE_BLEND);
  SDL_SetRenderTarget(drv->renderer, overlay);

  // set texture to all blue
  SDL_SetRenderDrawColor(drv->renderer, 0, 0, 255, 255);
  SDL_RenderClear(drv->renderer);

  // draw the suspend overlay png in the middle of the texture
  SDL_Texture *suspend_text = IMG_LoadTexture_IO(
      drv->renderer,
      SDL_IOFromMem(_suspend_overlay_text_data, _suspend_overlay_text_len),
      true);
  if (suspend_text == NULL) {
    LOG_ERR("Failed to load suspend overlay texture: %s", SDL_GetError());
    goto cleanup;
  }
  float text_width = 0.0f, text_height = 0.0f;
  if (!SDL_GetTextureSize(suspend_text, &text_width, &text_height)) {
    LOG_ERR("SDL_GetTextureSize failed: %s", SDL_GetError());
    goto cleanup;
  }
  SDL_FRect middle = {(screen.w - text_width) / 2, (screen.h - text_height) / 2,
                      text_width, text_height};
  SDL_RenderTexture(drv->renderer, suspend_text, NULL, &middle);
  SDL_RenderPresent(drv->renderer);

  // render to the screen
  SDL_SetRenderTarget(drv->renderer, NULL);
  SDL_RenderTexture(drv->renderer, overlay, NULL, &screen);
  SDL_RenderPresent(drv->renderer);

cleanup:
  SDL_DestroyTexture(suspend_text);
  SDL_DestroyTexture(overlay);
  SDL_SetRenderTarget(drv->renderer, NULL);
  SDL_SetRenderDrawColor(drv->renderer, 0, 0, 0, 255);
}

static void display_draw_suspend_overlay_trampoline(uintptr_t arg1,
                                                    uintptr_t arg2,
                                                    uintptr_t arg3) {
  display_draw_suspend_overlay_internal();
  systask_yield_to((systask_t *)arg1);
}

void display_draw_suspend_overlay(void) {
  // Call SDL drawing function in the context of the kernel task
  if (systask_active() == systask_kernel()) {
    display_draw_suspend_overlay_internal();
  } else {
    systask_push_call(systask_kernel(),
                      (void *)display_draw_suspend_overlay_trampoline,
                      (uintptr_t)systask_active(), 0, 0);
    systask_yield_to(systask_kernel());
  }
}

#endif
