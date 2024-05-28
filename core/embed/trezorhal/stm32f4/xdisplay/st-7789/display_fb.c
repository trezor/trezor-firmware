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

// Size of the physical frame buffer in bytes
#define PHYSICAL_FRAME_BUFFER_SIZE (DISPLAY_RESX * DISPLAY_RESY * 2)

// Physical frame buffers in internal SRAM memory.
// Both frame buffers layes in the fixed addresses that
// are shared between bootloaders and the firmware.
__attribute__((section(".fb1")))
ALIGN_32BYTES(uint8_t physical_frame_buffer_0[PHYSICAL_FRAME_BUFFER_SIZE]);
__attribute__((section(".fb2")))
ALIGN_32BYTES(uint8_t physical_frame_buffer_1[PHYSICAL_FRAME_BUFFER_SIZE]);

// The current frame buffer selector at fixed memory address
// It's shared between bootloaders and the firmware
__attribute__((section(".framebuffer_select"))) uint32_t current_frame_buffer =
    0;

void display_physical_fb_clear(void) {
  memset(physical_frame_buffer_0, 0, sizeof(physical_frame_buffer_0));
  memset(physical_frame_buffer_1, 0, sizeof(physical_frame_buffer_1));
}

#ifndef BOARDLOADER
static volatile uint16_t pending_fb_switch = 0;
static volatile uint32_t last_fb_update_time = 0;
#endif

#ifndef BOARDLOADER
void DISPLAY_TE_INTERRUPT_HANDLER(void) {
  if (pending_fb_switch == 1) {
    if (current_frame_buffer == 1) {
      bg_copy_start_const_out_8((uint8_t *)physical_frame_buffer_1,
                                (uint8_t *)DISPLAY_DATA_ADDRESS,
                                DISPLAY_RESX * DISPLAY_RESY * 2);

    } else {
      bg_copy_start_const_out_8((uint8_t *)physical_frame_buffer_0,
                                (uint8_t *)DISPLAY_DATA_ADDRESS,
                                DISPLAY_RESX * DISPLAY_RESY * 2);
    }
    last_fb_update_time = HAL_GetTick();
    pending_fb_switch = 2;
  } else if (pending_fb_switch == 2) {
    HAL_NVIC_DisableIRQ(DISPLAY_TE_INTERRUPT_NUM);
    pending_fb_switch = 0;
  }
  __HAL_GPIO_EXTI_CLEAR_FLAG(DISPLAY_TE_PIN);
}

static void copy_fb_to_display(const uint16_t *fb) {
  for (int i = 0; i < DISPLAY_RESX * DISPLAY_RESY; i++) {
    // 2 bytes per pixel because we're using RGB 5-6-5 format
    ISSUE_PIXEL_DATA(fb[i]);
  }
}

void wait_for_fb_switch(void) {
  if (is_mode_handler()) {
    if (pending_fb_switch != 0) {
      if (current_frame_buffer == 0) {
        copy_fb_to_display((uint16_t *)physical_frame_buffer_1);
      } else {
        copy_fb_to_display((uint16_t *)physical_frame_buffer_0);
      }
      pending_fb_switch = 0;
    }
  }else {
    while (pending_fb_switch != 0) {
      __WFI();
    }
    bg_copy_wait();
  }
}
#endif


static void switch_fb_manually(void) {
  // sync with the panel refresh
  while (GPIO_PIN_SET == HAL_GPIO_ReadPin(DISPLAY_TE_PORT, DISPLAY_TE_PIN)) {
  }
  while (GPIO_PIN_RESET == HAL_GPIO_ReadPin(DISPLAY_TE_PORT, DISPLAY_TE_PIN)) {
  }

  if (current_frame_buffer == 0) {
    current_frame_buffer = 1;
    copy_fb_to_display((uint16_t *)physical_frame_buffer_1);
    memcpy(physical_frame_buffer_0, physical_frame_buffer_1,
           sizeof(physical_frame_buffer_0));

  } else {
    current_frame_buffer = 0;
    copy_fb_to_display((uint16_t *)physical_frame_buffer_0);
    memcpy(physical_frame_buffer_1, physical_frame_buffer_0,
           sizeof(physical_frame_buffer_1));
  }
}

#ifndef BOARDLOADER
static void switch_fb_in_background(void) {
  if (current_frame_buffer == 0) {
    current_frame_buffer = 1;

    memcpy(physical_frame_buffer_0, physical_frame_buffer_1,
           sizeof(physical_frame_buffer_0));

    pending_fb_switch = 1;
    __HAL_GPIO_EXTI_CLEAR_FLAG(DISPLAY_TE_PIN);
    svc_enableIRQ(DISPLAY_TE_INTERRUPT_NUM);
  } else {
    current_frame_buffer = 0;
    memcpy(physical_frame_buffer_1, physical_frame_buffer_0,
           sizeof(physical_frame_buffer_1));

    pending_fb_switch = 1;
    __HAL_GPIO_EXTI_CLEAR_FLAG(DISPLAY_TE_PIN);
    svc_enableIRQ(DISPLAY_TE_INTERRUPT_NUM);
  }
}
#endif

display_fb_info_t display_get_frame_buffer(void) {
  void *addr;

  if (current_frame_buffer == 0) {
    addr = (void *)physical_frame_buffer_1;
  } else {
    addr = (void *)physical_frame_buffer_0;
  }

  display_fb_info_t fb = {
      .ptr = addr,
      .stride = DISPLAY_RESX * sizeof(uint16_t),
  };

  return fb;
}

void display_refresh(void) {
#ifndef BOARDLOADER

  if (is_mode_handler()) {
    display_panel_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);
    switch_fb_manually();
    //TODO we should abort any ongoing BG copy here
  } else {
    wait_for_fb_switch();
    display_panel_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);
    switch_fb_in_background();
  }
#else
  display_panel_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);
  switch_fb_manually();
#endif
}

void display_ensure_refreshed(void) {
#ifndef BOARDLOADER
  if (!is_mode_handler()) {
    wait_for_fb_switch();
    // the update time is collected after starting the BG copy, then we need to
    // wait: for the bg copy to finish and for at least one full refresh cycle
    // before we can consider the display fully redrawn
    while (HAL_GetTick() - last_fb_update_time < 40) {
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
