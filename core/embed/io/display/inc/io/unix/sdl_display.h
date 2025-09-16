#pragma once

#include <trezor_types.h>

#ifdef USE_RGB_LED
// Update the RGB LED color in the emulator
void display_rgb_led(uint32_t color);
#endif

#ifdef USE_POWER_MANAGER
// Draw a suspend overlay
void display_draw_suspend_overlay(void);
#endif
