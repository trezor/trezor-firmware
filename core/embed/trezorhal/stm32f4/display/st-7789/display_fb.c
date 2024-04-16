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

#include "irq.h"
#include "supervise.h"

#ifndef BOARDLOADER
#include "bg_copy.h"
#endif

#ifdef XFRAMEBUFFER

#ifndef STM32U5
#error Framebuffer only supported on STM32U5 for now
#endif

// Physical frame buffers in internal SRAM memory
__attribute__((section(".fb1")))
ALIGN_32BYTES(uint8_t physical_frame_buffer_0[PHYSICAL_FRAME_BUFFER_SIZE]);

__attribute__((section(".fb2")))
ALIGN_32BYTES(uint8_t physical_frame_buffer_1[PHYSICAL_FRAME_BUFFER_SIZE]);

// The current frame buffer selector at fixed memory address
// It's shared between bootloaders and the firmware
__attribute__((section(".framebuffer_select"))) uint32_t current_frame_buffer =
    0;

#ifndef BOARDLOADER
static bool pending_fb_switch = false;
#endif

#ifndef BOARDLOADER
void DISPLAY_TE_INTERRUPT_HANDLER(void) {
  HAL_NVIC_DisableIRQ(DISPLAY_TE_INTERRUPT_NUM);

  if (current_frame_buffer == 1) {
    bg_copy_start_const_out_8((uint8_t *)physical_frame_buffer_1,
                              (uint8_t *)DISPLAY_DATA_ADDRESS,
                              DISPLAY_RESX * DISPLAY_RESY * 2);

  } else {
    bg_copy_start_const_out_8((uint8_t *)physical_frame_buffer_0,
                              (uint8_t *)DISPLAY_DATA_ADDRESS,
                              DISPLAY_RESX * DISPLAY_RESY * 2);
  }

  pending_fb_switch = false;
  __HAL_GPIO_EXTI_CLEAR_FLAG(DISPLAY_TE_PIN);
}

static void wait_for_fb_switch(void) {
  while (pending_fb_switch) {
    __WFI();
  }
  bg_copy_wait();
}
#endif

static void copy_fb_to_display(uint16_t *fb) {
  for (int i = 0; i < DISPLAY_RESX * DISPLAY_RESY; i++) {
    // 2 bytes per pixel because we're using RGB 5-6-5 format
    ISSUE_PIXEL_DATA(fb[i]);
  }
}

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
static void switch_fb_in_backround(void) {
  if (current_frame_buffer == 0) {
    current_frame_buffer = 1;

    memcpy(physical_frame_buffer_0, physical_frame_buffer_1,
           sizeof(physical_frame_buffer_0));

    pending_fb_switch = true;
    __HAL_GPIO_EXTI_CLEAR_FLAG(DISPLAY_TE_PIN);
    svc_enableIRQ(DISPLAY_TE_INTERRUPT_NUM);
  } else {
    current_frame_buffer = 0;
    memcpy(physical_frame_buffer_1, physical_frame_buffer_0,
           sizeof(physical_frame_buffer_1));

    pending_fb_switch = true;
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
  wait_for_fb_switch();
  display_panel_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);

  if (is_mode_handler()) {
    switch_fb_manually();
  } else {
    switch_fb_in_backround();
  }
#else
  display_panel_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);
  switch_fb_manually();
#endif
}

#endif  // XFRAMEBUFFER
