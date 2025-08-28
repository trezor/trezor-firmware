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

#ifdef KERNEL_MODE

#include <trezor_rtl.h>

#include "math.h"
#include "rgb_led_internal.h"

// RGB_LED_EFFECT_BOOTLOADER_BREATHE constants
#define EF_BB_PHASE1_MS 2000  // Breathe up
#define EF_BB_PHASE2_MS 400   // LED ON pause
#define EF_BB_PHASE3_MS 800   // Breathe down
#define EF_BB_PHASE4_MS 100   // LED OFF pause
#define EF_BB_CYCLE_MS \
  (EF_BB_PHASE1_MS + EF_BB_PHASE2_MS + EF_BB_PHASE3_MS + EF_BB_PHASE4_MS)

// RGB_LED_EFFECT_CHARGING constants
#define EF_CHG_PHASE1_MS 300
#define EF_CHG_PHASE2_MS 800
#define EF_CHG_PHASE3_MS 300
#define EF_CHG_PHASE4_MS 800
#define EF_CHG_CYCLE_MS \
  (EF_CHG_PHASE1_MS + EF_CHG_PHASE2_MS + EF_CHG_PHASE3_MS + EF_CHG_PHASE4_MS)

// Gamma correction factor
#define GAMMA_CF 3.0f
#define GAMMA_CF_INV 1.0f / GAMMA_CF

// Effect callback function prototypes
static void rgb_led_effect_pairing(uint32_t elapsed_ms,
                                   rgb_led_effect_data_t *data,
                                   rgb_led_color_fs_t *color);
static void rgb_led_effect_charging(uint32_t elapsed_ms,
                                    rgb_led_effect_data_t *data,
                                    rgb_led_color_fs_t *color);

// Effect callback functions lookup table
static void (*rgb_led_effects_callbacks[])(uint32_t elapsed_ms,
                                           rgb_led_effect_data_t *data,
                                           rgb_led_color_fs_t *color) = {
    [RGB_LED_EFFECT_PAIRING] = rgb_led_effect_pairing,
    [RGB_LED_EFFECT_CHARGING] = rgb_led_effect_charging,
};

// Single color linear interpolation auxiliary function for floats
static inline float linear_interpolate_f(float y0, float y1, float x,
                                         float x1) {
  return (y0 + ((y1 - y0) * x / x1));
}

// Linear interpolation between two colors based on elapsed time with gamma
// correction
static void rgb_led_linear_gc_effect(uint32_t c0, uint32_t c1,
                                     uint32_t elapsed_ms, uint32_t total_ms,
                                     rgb_led_color_fs_t *interp_color) {
  if (elapsed_ms >= total_ms) {
    interp_color->red = 0;
    interp_color->green = 0;
    interp_color->blue = 0;
    return;
  }
  float r0 = powf(RGB_EXTRACT_RED(c0) / 255.0f, GAMMA_CF_INV);
  float g0 = powf(RGB_EXTRACT_GREEN(c0) / 255.0f, GAMMA_CF_INV);
  float b0 = powf(RGB_EXTRACT_BLUE(c0) / 255.0f, GAMMA_CF_INV);

  float r1 = powf(RGB_EXTRACT_RED(c1) / 255.0f, GAMMA_CF_INV);
  float g1 = powf(RGB_EXTRACT_GREEN(c1) / 255.0f, GAMMA_CF_INV);
  float b1 = powf(RGB_EXTRACT_BLUE(c1) / 255.0f, GAMMA_CF_INV);

  float r = linear_interpolate_f(r0, r1, (float)elapsed_ms, (float)total_ms);
  float g = linear_interpolate_f(g0, g1, (float)elapsed_ms, (float)total_ms);
  float b = linear_interpolate_f(b0, b1, (float)elapsed_ms, (float)total_ms);

  r = powf(r, GAMMA_CF);
  g = powf(g, GAMMA_CF);
  b = powf(b, GAMMA_CF);

  r = fminf(1.0f, fmaxf(r, 0.0f));
  g = fminf(1.0f, fmaxf(g, 0.0f));
  b = fminf(1.0f, fmaxf(b, 0.0f));

  interp_color->red = (uint32_t)(r * RGB_LED_TIMER_PERIOD);
  interp_color->green = (uint32_t)(g * RGB_LED_TIMER_PERIOD);
  interp_color->blue = (uint32_t)(b * RGB_LED_TIMER_PERIOD);
}

// Assign effect callback from the lookup table
bool rgb_led_assign_effect(rgb_led_effect_t *effect,
                           rgb_led_effect_type_t effect_type) {
  if (effect_type >= RGB_LED_NUM_OF_EFFECTS && effect_type < 0) {
    return false;
  }

  // Clear effect structure
  memset(effect, 0, sizeof(rgb_led_effect_t));

  effect->type = effect_type;
  effect->callback = rgb_led_effects_callbacks[effect_type];

  return true;
}

/**
 * Pairing effect
 * Slow Linear transition effect from RGBLED_OFF to RGBLED_BLUE and back to
 * RGBLED_OFF
 */
static void rgb_led_effect_pairing(uint32_t elapsed_ms,
                                   rgb_led_effect_data_t *data,
                                   rgb_led_color_fs_t *ef_color) {
  data->cycles = elapsed_ms / EF_BB_CYCLE_MS;
  uint32_t ef_time = elapsed_ms % EF_BB_CYCLE_MS;

  if (ef_time < EF_BB_PHASE1_MS) {
    // PHASE 1: linear transition to RGBLED_BLUE
    rgb_led_linear_gc_effect(RGBLED_OFF, RGBLED_BLUE, ef_time, EF_BB_PHASE1_MS,
                             ef_color);
  } else if (ef_time < EF_BB_PHASE1_MS + EF_BB_PHASE2_MS) {
    // PHASE 2: hold RGBLED_BLUE color
    ef_color->red = (RGB_EXTRACT_RED(RGBLED_BLUE) * RGB_LED_TIMER_PERIOD) / 255;
    ef_color->green =
        (RGB_EXTRACT_GREEN(RGBLED_BLUE) * RGB_LED_TIMER_PERIOD) / 255;
    ef_color->blue =
        (RGB_EXTRACT_BLUE(RGBLED_BLUE) * RGB_LED_TIMER_PERIOD) / 255;
  } else if (ef_time < EF_BB_PHASE1_MS + EF_BB_PHASE2_MS + EF_BB_PHASE3_MS) {
    // PHASE 3: linear transition to RGBLED_OFF
    rgb_led_linear_gc_effect(RGBLED_BLUE, RGBLED_OFF,
                             ef_time - EF_BB_PHASE1_MS - EF_BB_PHASE2_MS,
                             EF_BB_PHASE3_MS, ef_color);
  } else if (ef_time < EF_BB_CYCLE_MS) {
    // PHASE 4: hold the off state
    ef_color->red = 0;
    ef_color->green = 0;
    ef_color->blue = 0;
  } else {
    // Should not happen
    ef_color->red = 0;
    ef_color->green = 0;
    ef_color->blue = 0;
  }
}

/**
 * Charging effect
 * Faster linear transition effect from RGBLED_OFF to RGBLED_YELLOW and back to
 * RGBLED_OFF
 */
static void rgb_led_effect_charging(uint32_t elapsed_ms,
                                    rgb_led_effect_data_t *data,
                                    rgb_led_color_fs_t *ef_color) {
  data->cycles = elapsed_ms / EF_CHG_CYCLE_MS;
  uint32_t ef_time = elapsed_ms % EF_CHG_CYCLE_MS;

  if (ef_time < EF_CHG_PHASE1_MS) {
    // PHASE 1: linear transition to RGBLED_YELLOW
    rgb_led_linear_gc_effect(RGBLED_OFF, RGBLED_YELLOW, ef_time,
                             EF_CHG_PHASE1_MS, ef_color);
  } else if (ef_time < EF_CHG_PHASE1_MS + EF_CHG_PHASE2_MS) {
    // PHASE 2: hold RGBLED_YELLOW color
    ef_color->red =
        (RGB_EXTRACT_RED(RGBLED_YELLOW) * RGB_LED_TIMER_PERIOD) / 255;
    ef_color->green =
        (RGB_EXTRACT_GREEN(RGBLED_YELLOW) * RGB_LED_TIMER_PERIOD) / 255;
    ef_color->blue =
        (RGB_EXTRACT_BLUE(RGBLED_YELLOW) * RGB_LED_TIMER_PERIOD) / 255;
  } else if (ef_time < EF_CHG_PHASE1_MS + EF_CHG_PHASE2_MS + EF_CHG_PHASE3_MS) {
    // PHASE 3: linear transition to RGBLED_OFF
    rgb_led_linear_gc_effect(RGBLED_YELLOW, RGBLED_OFF,
                             ef_time - EF_CHG_PHASE1_MS - EF_CHG_PHASE2_MS,
                             EF_CHG_PHASE3_MS, ef_color);
  } else if (ef_time < EF_CHG_CYCLE_MS) {
    // PHASE 4: hold the off state
    ef_color->red = 0;
    ef_color->green = 0;
    ef_color->blue = 0;
  } else {
    // Should not happen
    ef_color->red = 0;
    ef_color->green = 0;
    ef_color->blue = 0;
  }
}

#endif
