#pragma once

#ifdef USE_HAPTIC
#include <io/haptic.h>
#endif /* USE_HAPTIC */
#include <trezor_types.h>

#ifdef USE_RGB_LED
// Update the RGB LED color in the emulator
void display_rgb_led(uint32_t color);
#endif

#ifdef USE_HAPTIC
// Update the haptic color in the emulator
void display_haptic_effect(haptic_effect_t effect);
void display_custom_effect(uint32_t duration_ms);
#endif /* USE_HAPTIC */
