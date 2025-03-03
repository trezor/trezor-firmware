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

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <gfx/gfx_bitblt.h>
#include <io/display.h>
#include <sys/irq.h>
#include <sys/mpu.h>

#include "display_fb.h"
#include "display_internal.h"
#include "display_io.h"
#include "display_panel.h"

#include <rtl/sizedefs.h>

#ifdef USE_TRUSTZONE
#include <sys/trustzone.h>
#endif

#ifndef BOARDLOADER
#include "../bg_copy/bg_copy.h"
#endif

#ifndef STM32U5
#error Framebuffer only supported on STM32U5 for now
#endif

#ifdef KERNEL_MODE

// The following code supports only 1 or 2 frame buffers
_Static_assert(FRAME_BUFFER_COUNT == 1 || FRAME_BUFFER_COUNT == 2);

// Hardware requires physical frame buffer alignment
#ifdef USE_TRUSTZONE
#define PHYSICAL_FRAME_BUFFER_ALIGNMENT TZ_SRAM_ALIGNMENT
#else
#define PHYSICAL_FRAME_BUFFER_ALIGNMENT 32
#endif

// Size of the physical frame buffer in bytes
#define PHYSICAL_FRAME_BUFFER_SIZE               \
  ALIGN_UP_CONST(DISPLAY_RESX *DISPLAY_RESY * 2, \
                 PHYSICAL_FRAME_BUFFER_ALIGNMENT)

// Physical frame buffers in internal SRAM memory.
// Both frame buffers layers in the fixed addresses that
// are shared between bootloaders and the firmware.
static
    __attribute__((section(".fb1"), aligned(PHYSICAL_FRAME_BUFFER_ALIGNMENT)))
    uint8_t physical_frame_buffer_0[PHYSICAL_FRAME_BUFFER_SIZE];

#if (FRAME_BUFFER_COUNT > 1)
static
    __attribute__((section(".fb2"), aligned(PHYSICAL_FRAME_BUFFER_ALIGNMENT)))
    uint8_t physical_frame_buffer_1[PHYSICAL_FRAME_BUFFER_SIZE];
#endif

#ifdef USE_TRUSTZONE
void display_set_unpriv_access(bool unpriv) {
  tz_set_sram_unpriv((uint32_t)physical_frame_buffer_0,
                     PHYSICAL_FRAME_BUFFER_SIZE, unpriv);

#if (FRAME_BUFFER_COUNT > 1)
  tz_set_sram_unpriv((uint32_t)physical_frame_buffer_1,
                     PHYSICAL_FRAME_BUFFER_SIZE, unpriv);
#endif
}
#endif  // USE_TRUSTZONE

void display_fb_init(void) {
  display_driver_t *drv = &g_display_driver;

  if (drv->initialized) {
    return;
  }

  fb_queue_reset(&drv->empty_frames);
  fb_queue_reset(&drv->ready_frames);

  for (int16_t i = 0; i < FRAME_BUFFER_COUNT; i++) {
    fb_queue_put(&drv->empty_frames, i);
  }
}

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

void display_fb_clear(void) {
  for (int i = 0; i < FRAME_BUFFER_COUNT; i++) {
    mpu_set_active_fb(get_fb_ptr(i), PHYSICAL_FRAME_BUFFER_SIZE);
    memset(get_fb_ptr(i), 0, PHYSICAL_FRAME_BUFFER_SIZE);
  }
  mpu_set_active_fb(NULL, 0);
}

#ifndef BOARDLOADER

// Callback called when the background copying is done
// It's called from the IRQ context
static void bg_copy_callback(void) {
  display_driver_t *drv = &g_display_driver;

  drv->update_pending = 2;

  fb_queue_put(&drv->empty_frames, fb_queue_take(&drv->ready_frames));
}

// Interrupt routing handling TE signal
static void display_te_interrupt_handler(void) {
  display_driver_t *drv = &g_display_driver;

  __HAL_GPIO_EXTI_CLEAR_FLAG(DISPLAY_TE_PIN);

  if (drv->update_pending > 0) {
    drv->update_pending--;
  }

  if (!fb_queue_peeked(&drv->ready_frames)) {
    int16_t fb_idx = fb_queue_peek(&drv->ready_frames);

    if (fb_idx >= 0) {
      display_panel_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);
      bg_copy_start_const_out_8(get_fb_ptr(fb_idx),
                                (uint8_t *)DISPLAY_DATA_ADDRESS,
                                PHYSICAL_FRAME_BUFFER_SIZE, bg_copy_callback);
    }
  }
}

void DISPLAY_TE_INTERRUPT_HANDLER(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  display_te_interrupt_handler();
  mpu_restore(mpu_mode);
  IRQ_LOG_EXIT();
}
#endif

bool display_get_frame_buffer(display_fb_info_t *fb) {
  display_driver_t *drv = &g_display_driver;

  memset(fb, 0, sizeof(display_fb_info_t));

  if (!drv->initialized) {
    return false;
  }

  fb_queue_wait(&drv->empty_frames);
  uint8_t fb_idx = fb_queue_peek(&drv->empty_frames);

  fb->ptr = get_fb_ptr(fb_idx);
  fb->stride = DISPLAY_RESX * sizeof(uint16_t);
  fb->size = PHYSICAL_FRAME_BUFFER_SIZE;
  // Enable access to the frame buffer from the unprivileged code
  mpu_set_active_fb(fb->ptr, fb->size);

  return true;
}

#ifdef BOARDLOADER
// Copies the frame buffer with the given index to the display
static void copy_fb_to_display(uint8_t index) {
  uint16_t *fb = (uint16_t *)get_fb_ptr(index);

  if (fb != NULL) {
    mpu_set_active_fb(fb, PHYSICAL_FRAME_BUFFER_SIZE);
    display_panel_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);
    for (int i = 0; i < DISPLAY_RESX * DISPLAY_RESY; i++) {
      // 2 bytes per pixel because we're using RGB 5-6-5 format
      ISSUE_PIXEL_DATA(fb[i]);
    }
  }

  mpu_set_active_fb(NULL, 0);
}

static void wait_for_te_signal(void) {
  // sync with the panel refresh
  while (GPIO_PIN_SET == HAL_GPIO_ReadPin(DISPLAY_TE_PORT, DISPLAY_TE_PIN)) {
  }
  while (GPIO_PIN_RESET == HAL_GPIO_ReadPin(DISPLAY_TE_PORT, DISPLAY_TE_PIN)) {
  }
}
#endif

void display_refresh(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  if (!fb_queue_peeked(&drv->empty_frames)) {
    // No refresh needed as the frame buffer is not in
    // the state to be copied to the display
    return;
  }

  // Disable access to the frame buffer from the unprivileged code
  mpu_set_active_fb(NULL, 0);

#ifndef BOARDLOADER
  // Mark the buffer ready to switch to
  fb_queue_put(&drv->ready_frames, fb_queue_take(&drv->empty_frames));

#else  // BOARDLOADER
  wait_for_te_signal();
  int16_t fb_idx = fb_queue_take(&drv->empty_frames);
  if (fb_idx >= 0) {
    copy_fb_to_display(fb_idx);
    fb_queue_put(&drv->empty_frames, fb_idx);
  }
#endif
}

void display_ensure_refreshed(void) {
#ifndef BOARDLOADER
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  if (!is_mode_exception()) {
    bool copy_pending;

    // Wait until all frame buffers are written to the display
    //  so we can be sure there's not scheduled or pending
    // background copying
    do {
      irq_key_t irq_key = irq_lock();
      copy_pending = !fb_queue_empty(&drv->ready_frames) || drv->update_pending;
      irq_unlock(irq_key);
      __WFI();
    } while (copy_pending);
  }
#endif
}

void display_fill(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint16_t *)((uintptr_t)fb.ptr + fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  if (!gfx_bitblt_check_dst_x(&bb_new, 16) ||
      !gfx_bitblt_check_dst_y(&bb_new, fb.size)) {
    return;
  }

  gfx_rgb565_fill(&bb_new);
}

void display_copy_rgb565(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint16_t *)((uintptr_t)fb.ptr + fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  if (!gfx_bitblt_check_dst_x(&bb_new, 16) ||
      !gfx_bitblt_check_src_x(&bb_new, 16) ||
      !gfx_bitblt_check_dst_y(&bb_new, fb.size)) {
    return;
  }

  gfx_rgb565_copy_rgb565(&bb_new);
}

void display_copy_mono1p(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint16_t *)((uintptr_t)fb.ptr + fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  if (!gfx_bitblt_check_dst_x(&bb_new, 16) ||
      !gfx_bitblt_check_src_x(&bb_new, 1) ||
      !gfx_bitblt_check_dst_y(&bb_new, fb.size)) {
    return;
  }

  gfx_rgb565_copy_mono1p(&bb_new);
}

#endif  // KERNEL_MODE
