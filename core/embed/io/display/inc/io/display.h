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

#ifndef TREZORHAL_XDISPLAY_H
#define TREZORHAL_XDISPLAY_H

#include <trezor_types.h>

#include <gfx/gfx_bitblt.h>

// This is a universal API for controlling different types of display
// controllers.
//
// Currently, following displays displays are supported
//
// VG-2864KSWEG01  - OLED Mono / 128x64 pixels  / SPI
//                 - Model T2B1
//
// UG-2828SWIG01   - OLED Mono / 128x128 pixels / Parallel
//                 - Early revisions of T2B1
//
// ST7789V         - TFT RGB   / 240x240 pixels / Parallel
//                 - Model T2T1 / Model T3T1
//
// ILI9341         - TFT RGB   / 320x240 pixels / Parallel / LTDC + SPI
//                 - STM32F429I-DISC1 Discovery Board
//
// MIPI            -
//                 - STM32U5A9J-DK Discovery Board

#ifdef KERNEL_MODE

// Specifies how display content should be handled during
// initialization or deinitialization.
typedef enum {
  // Clear the display content
  DISPLAY_RESET_CONTENT,
  // Retain the display content
  DISPLAY_RETAIN_CONTENT
} display_content_mode_t;

// Initializes the display controller.
//
// If `mode` is `DISPLAY_RETAIN_CONTENT`, ensure the driver was previously
// initialized and `display_deinit(DISPLAY_RETAIN_CONTENT)` was called.
//
// Returns `true` if the initialization was successful.
bool display_init(display_content_mode_t mode);

// Deinitializes the display controller.
//
// If `mode` is `DISPLAY_RETAIN_CONTENT`, the function waits for
// background operations to complete and disables interrupts, so the
//  application can safely proceed to the next boot stage and call
// `display_init(DISPLAY_RETAIN_CONTENT)`.
void display_deinit(display_content_mode_t mode);

// Allows unprivileged access to the display framebuffer from
// perspective of the GTZC (Global TrustZone Controller).
void display_set_unpriv_access(bool unpriv);

#endif  // KERNEL_MODE

// Sets display backlight level ranging from 0 (off)..255 (maximum).
//
// The default backligt level is 0. Without settings it
// to some higher value the displayed pixels are not visible.
// Beware that his also applies to the emulator.
//
// Returns the set level (usually the same value or the
// closest value to the `level` argument)
int display_set_backlight(int level);

// Gets current display level ranging from 0 (off)..255 (maximum).
int display_get_backlight(void);

// Sets the display orientation.
//
// May accept one of following values: 0, 90, 180, 270
// but accepted values are model-dependent.
// Default display orientation is always 0.
//
// Returns the set orientation
int display_set_orientation(int angle);

// Gets the display's current orientation
//
// Returned value is one of 0, 90, 180, 270.
int display_get_orientation(void);

#ifdef FRAMEBUFFER

typedef struct {
  // Pointer to the top-left pixel
  void *ptr;
  // Stride in bytes
  size_t stride;

} display_fb_info_t;

// Provides pointer to the inactive (writeable) framebuffer.
//
// If framebuffer is not available yet due to display refreshing etc.,
// the function may block until the buffer is ready to write.
//
// Return `false` if the framebuffer is not available.
bool display_get_frame_buffer(display_fb_info_t *fb);

#else  // FRAMEBUFFER

// Waits for the vertical synchronization pulse.
//
// Used for synchronization with the display refresh cycle
// to achieve tearless UX if possible when not using a frame buffer.
void display_wait_for_sync(void);
#endif

// Swaps the frame buffers
//
// The function waits for vertical synchronization and
// swaps the active (currently displayed) and the inactive frame buffers.
void display_refresh(void);

// Following functions define display's bitblt interface.
//
// These functions draw directly to to display or to the
// currently inactive framebuffer.
//
// bb->dst_row and bb->dst_stride must be 0

// Fills a rectangle with a solid color.
// This function is supported by all types of displays.
void display_fill(const gfx_bitblt_t *bb);
// Copies an RGB565 bitmap.
// This function is supported by RGB displays only.
void display_copy_rgb565(const gfx_bitblt_t *bb);
// Copies a MONO4 bitmap (supported only with RGB displays).
// This function is supported by RGB displays only.
void display_copy_mono4(const gfx_bitblt_t *bb);
// Copies a MONO1P bitmap.
// This function is supported by all types of displays.
void display_copy_mono1p(const gfx_bitblt_t *bb);

#ifdef TREZOR_EMULATOR
// Save the screen content to a file.
// The function is available only on the emulator.
const char *display_save(const char *prefix);
void display_clear_save(void);
#endif

#endif  // TREZORHAL_XDISPLAY_H
