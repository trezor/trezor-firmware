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

#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#include TREZOR_BOARD
#include STM32_HAL_H

#include "display_fb.h"
#include "display_internal.h"
#include "display_io.h"
#include "display_panel.h"
#include "xdisplay.h"

#include "gfx_bitblt.h"
#include "irq.h"
#include "supervise.h"

#ifndef BOARDLOADER
#include "bg_copy.h"
#endif

#ifndef STM32U5
#error Framebuffer only supported on STM32U5 for now
#endif

// The following code supports only 1 or 2 frame buffers
_Static_assert(FRAME_BUFFER_COUNT == 1 || FRAME_BUFFER_COUNT == 2);

// Size of the physical frame buffer in bytes
#define PHYSICAL_FRAME_BUFFER_SIZE (DISPLAY_RESX * DISPLAY_RESY * 2)

// Physical frame buffers in internal SRAM memory.
// Both frame buffers layes in the fixed addresses that
// are shared between bootloaders and the firmware.
static __attribute__((section(".fb1")))
ALIGN_32BYTES(uint8_t physical_frame_buffer_0[PHYSICAL_FRAME_BUFFER_SIZE]);

#if (FRAME_BUFFER_COUNT > 1)
static __attribute__((section(".fb2")))
ALIGN_32BYTES(uint8_t physical_frame_buffer_1[PHYSICAL_FRAME_BUFFER_SIZE]);
#endif

// Returns the pointer to the physical frame buffer (0.. FRAME_BUFFER_COUNT-1)
// Returns NULL if the framebuffer index is out of range.
static uint8_t *get_fb_ptr(uint32_t index) {
  if (index == 0) {
    return physical_frame_buffer_0;
#if (FRAME_BUFFER_COUNT > 1)
  } else if (index == 1) {
    return physical_frame_buffer_1;
#endif
  } else {
    return NULL;
  }
}

void display_physical_fb_clear(void) {
  for (int i = 0; i < FRAME_BUFFER_COUNT; i++) {
    memset(get_fb_ptr(i), 0, PHYSICAL_FRAME_BUFFER_SIZE);
  }
}

#ifndef BOARDLOADER

// Callback called when the background copying is done
// It's called from the IRQ context
static void bg_copy_callback(void) {
  display_driver_t *drv = &g_display_driver;

  if (drv->queue.rix >= FRAME_BUFFER_COUNT) {
    // This is an invalid state and we should never get here
    return;
  }

  drv->queue.entry[drv->queue.rix] = FB_STATE_EMPTY;
  drv->queue.rix = (drv->queue.rix + 1) % FRAME_BUFFER_COUNT;
}

// Interrupt routing handling TE signal
void DISPLAY_TE_INTERRUPT_HANDLER(void) {
  display_driver_t *drv = &g_display_driver;

  __HAL_GPIO_EXTI_CLEAR_FLAG(DISPLAY_TE_PIN);

  if (drv->queue.rix >= FRAME_BUFFER_COUNT) {
    // This is an invalid state and we should never get here
    return;
  }

  switch (drv->queue.entry[drv->queue.rix]) {
    case FB_STATE_EMPTY:
    case FB_STATE_PREPARING:
      // No new frame queued
      break;

    case FB_STATE_COPYING:
      // Currently we are copying a data to the display.
      // We need to wait for the next TE interrupt.
      break;

    case FB_STATE_READY:
      // Now it's proper time to copy the data to the display
      drv->queue.entry[drv->queue.rix] = FB_STATE_COPYING;
      display_panel_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);
      bg_copy_start_const_out_8(get_fb_ptr(drv->queue.rix),
                                (uint8_t *)DISPLAY_DATA_ADDRESS,
                                PHYSICAL_FRAME_BUFFER_SIZE, bg_copy_callback);

      // NOTE: when copying is done, this queue slot is marked empty
      // (see bg_copy_callback())
      break;

    default:
      // This is an invalid state and we should never get here
      break;
  }
}
#endif

display_fb_info_t display_get_frame_buffer(void) {
  display_driver_t *drv = &g_display_driver;

  frame_buffer_state_t state;

  // We have to wait if the buffer was passed for copying
  // to the interrupt handler
  do {
    state = drv->queue.entry[drv->queue.wix];
  } while (state == FB_STATE_READY || state == FB_STATE_COPYING);

  if (state == FB_STATE_EMPTY) {
    // First use of this buffer, copy the previous buffer into it
#if (FRAME_BUFFER_COUNT > 1)
    uint8_t *src = get_fb_ptr((FRAME_BUFFER_COUNT + drv->queue.wix - 1) %
                              FRAME_BUFFER_COUNT);
    uint8_t *dst = get_fb_ptr(drv->queue.wix);
    memcpy(dst, src, PHYSICAL_FRAME_BUFFER_SIZE);
#endif
  };

  drv->queue.entry[drv->queue.wix] = FB_STATE_PREPARING;

  display_fb_info_t fb = {
      .ptr = get_fb_ptr(drv->queue.wix),
      .stride = DISPLAY_RESX * sizeof(uint16_t),
  };

  return fb;
}

// Copies the frame buffer with the given index to the display
static void copy_fb_to_display(uint8_t index) {
  uint16_t *fb = (uint16_t *)get_fb_ptr(index);

  if (fb != NULL) {
    display_panel_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);
    for (int i = 0; i < DISPLAY_RESX * DISPLAY_RESY; i++) {
      // 2 bytes per pixel because we're using RGB 5-6-5 format
      ISSUE_PIXEL_DATA(fb[i]);
    }
  }
}

static void wait_for_te_signal(void) {
  // sync with the panel refresh
  while (GPIO_PIN_SET == HAL_GPIO_ReadPin(DISPLAY_TE_PORT, DISPLAY_TE_PIN)) {
  }
  while (GPIO_PIN_RESET == HAL_GPIO_ReadPin(DISPLAY_TE_PORT, DISPLAY_TE_PIN)) {
  }
}

void display_refresh(void) {
  display_driver_t *drv = &g_display_driver;

  if (drv->queue.entry[drv->queue.wix] != FB_STATE_PREPARING) {
    // No refresh needed as the frame buffer is not in
    // the state to be copied to the display
    return;
  }

#ifndef BOARDLOADER
  if (is_mode_handler()) {
    // Disable scheduling of any new background copying
    HAL_NVIC_DisableIRQ(DISPLAY_TE_INTERRUPT_NUM);
    // Wait for next TE signal. During this time the
    // display might be updated in the background
    wait_for_te_signal();
    // Stop any background copying even if it is not finished yet
    bg_copy_abort();
    // Copy the frame buffer to the display manually
    copy_fb_to_display(drv->queue.wix);
    // Reset the buffer queue so we can eventually continue
    // safely in thread mode
    drv->queue.wix = 0;
    drv->queue.rix = 0;
    for (int i = 0; i < FRAME_BUFFER_COUNT; i++) {
      drv->queue.entry[i] = FB_STATE_EMPTY;
    }
    // Enable normal processing again
    HAL_NVIC_EnableIRQ(DISPLAY_TE_INTERRUPT_NUM);
  } else {
    // Mark the buffer ready to switch to
    drv->queue.entry[drv->queue.wix] = FB_STATE_READY;
    drv->queue.wix = (drv->queue.wix + 1) % FRAME_BUFFER_COUNT;
  }

#else  // BOARDLOADER
  wait_for_te_signal();
  copy_fb_to_display(drv->queue.wix);
  drv->queue.entry[drv->queue.wix] = FB_STATE_EMPTY;
#endif
}

void display_ensure_refreshed(void) {
#ifndef BOARDLOADER
  display_driver_t *drv = &g_display_driver;

  if (!is_mode_handler()) {
    bool copy_pending;

    // Wait until all frame buffers are written to the display
    //  so we can be sure there's not scheduled or pending
    // background copying
    do {
      copy_pending = false;
      for (int i = 0; i < FRAME_BUFFER_COUNT; i++) {
        frame_buffer_state_t state = drv->queue.entry[i];
        if (state == FB_STATE_READY || state == FB_STATE_COPYING) {
          copy_pending = true;
          break;
        }
      }
      __WFI();
    } while (copy_pending);

    // Wait until the display is fully refreshed
    // (TE signal is low when the display is updating)
    while (GPIO_PIN_RESET ==
           HAL_GPIO_ReadPin(DISPLAY_TE_PORT, DISPLAY_TE_PIN)) {
      __WFI();
    }
  }
#endif
}

void display_fill(const gfx_bitblt_t *bb) {
  display_fb_info_t fb = display_get_frame_buffer();

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint16_t *)((uintptr_t)fb.ptr + fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  gfx_rgb565_fill(&bb_new);
}

void display_copy_rgb565(const gfx_bitblt_t *bb) {
  display_fb_info_t fb = display_get_frame_buffer();

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint16_t *)((uintptr_t)fb.ptr + fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  gfx_rgb565_copy_rgb565(&bb_new);
}

void display_copy_mono1p(const gfx_bitblt_t *bb) {
  display_fb_info_t fb = display_get_frame_buffer();

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint16_t *)((uintptr_t)fb.ptr + fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  gfx_rgb565_copy_mono1p(&bb_new);
}

void display_copy_mono4(const gfx_bitblt_t *bb) {
  display_fb_info_t fb = display_get_frame_buffer();

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint16_t *)((uintptr_t)fb.ptr + fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  gfx_rgb565_copy_mono4(&bb_new);
}
