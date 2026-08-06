#pragma once

#include <trezor_types.h>

// Converts window coordinates, as reported by SDL input events, into emulator
// display coordinates. These differ whenever the emulator window is scaled up,
// because SDL reports input in unscaled window coordinates.
//
// This is only an access shim around `SDL_RenderCoordinatesFromWindow()`, which
// does all the work. The renderer is private to the display driver, so callers
// elsewhere cannot perform the conversion themselves.
void sdl_display_window_to_display(float window_x, float window_y,
                                   int *display_x, int *display_y);

#ifdef USE_RGB_LED
// Update the RGB LED color in the emulator
void display_rgb_led(uint32_t color);
#endif

#ifdef USE_POWER_MANAGER
// Draw a suspend overlay
void display_draw_suspend_overlay(void);
#endif
