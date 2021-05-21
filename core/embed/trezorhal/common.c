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

#include STM32_HAL_H

#include <string.h>

#include "common.h"
#include "display.h"
#include "flash.h"
#include "rand.h"

#include "stm32f4xx_ll_utils.h"

// from util.s
extern void shutdown(void);

#define COLOR_FATAL_ERROR RGB16(0x7F, 0x00, 0x00)

void __attribute__((noreturn))
__fatal_error(const char *expr, const char *msg, const char *file, int line,
              const char *func) {
  display_orientation(0);
  display_backlight(255);
  display_print_color(COLOR_WHITE, COLOR_FATAL_ERROR);
  display_printf("\nFATAL ERROR:\n");
  if (expr) {
    display_printf("expr: %s\n", expr);
  }
  if (msg) {
    display_printf("msg : %s\n", msg);
  }
  if (file) {
    display_printf("file: %s:%d\n", file, line);
  }
  if (func) {
    display_printf("func: %s\n", func);
  }
#ifdef SCM_REVISION
  const uint8_t *rev = (const uint8_t *)SCM_REVISION;
  display_printf("rev : %02x%02x%02x%02x%02x\n", rev[0], rev[1], rev[2], rev[3],
                 rev[4]);
#endif
  display_printf("\nPlease contact Trezor support.\n");
  shutdown();
  for (;;)
    ;
}

void __attribute__((noreturn))
error_shutdown(const char *line1, const char *line2, const char *line3,
               const char *line4) {
  display_orientation(0);
#ifdef TREZOR_FONT_NORMAL_ENABLE
  display_clear();
  display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, COLOR_FATAL_ERROR);
  int y = 32;
  if (line1) {
    display_text(8, y, line1, -1, FONT_NORMAL, COLOR_WHITE, COLOR_FATAL_ERROR);
    y += 32;
  }
  if (line2) {
    display_text(8, y, line2, -1, FONT_NORMAL, COLOR_WHITE, COLOR_FATAL_ERROR);
    y += 32;
  }
  if (line3) {
    display_text(8, y, line3, -1, FONT_NORMAL, COLOR_WHITE, COLOR_FATAL_ERROR);
    y += 32;
  }
  if (line4) {
    display_text(8, y, line4, -1, FONT_NORMAL, COLOR_WHITE, COLOR_FATAL_ERROR);
    y += 32;
  }
  y += 32;
  display_text(8, y, "Please unplug the device.", -1, FONT_NORMAL, COLOR_WHITE,
               COLOR_FATAL_ERROR);
#else
  display_print_color(COLOR_WHITE, COLOR_FATAL_ERROR);
  if (line1) {
    display_printf("%s\n", line1);
  }
  if (line2) {
    display_printf("%s\n", line2);
  }
  if (line3) {
    display_printf("%s\n", line3);
  }
  if (line4) {
    display_printf("%s\n", line4);
  }
  display_printf("\nPlease unplug the device.\n");
#endif
  display_backlight(255);
  shutdown();
  for (;;)
    ;
}

#ifndef NDEBUG
void __assert_func(const char *file, int line, const char *func,
                   const char *expr) {
  __fatal_error(expr, "assert failed", file, line, func);
}
#endif

void hal_delay(uint32_t ms) { HAL_Delay(ms); }

// reference RM0090 section 35.12.1 Figure 413
#define USB_OTG_HS_DATA_FIFO_RAM (USB_OTG_HS_PERIPH_BASE + 0x20000U)
#define USB_OTG_HS_DATA_FIFO_SIZE (4096U)

void clear_otg_hs_memory(void) {
  // use the HAL version due to section 2.1.6 of STM32F42xx Errata sheet
  __HAL_RCC_USB_OTG_HS_CLK_ENABLE();  // enable USB_OTG_HS peripheral clock so
                                      // that the peripheral memory is
                                      // accessible
  memset_reg(
      (volatile void *)USB_OTG_HS_DATA_FIFO_RAM,
      (volatile void *)(USB_OTG_HS_DATA_FIFO_RAM + USB_OTG_HS_DATA_FIFO_SIZE),
      0);
  __HAL_RCC_USB_OTG_HS_CLK_DISABLE();  // disable USB OTG_HS peripheral clock as
                                       // the peripheral is not needed right now
}

uint32_t __stack_chk_guard = 0;

void __attribute__((noreturn)) __stack_chk_fail(void) {
  error_shutdown("Internal error", "(SS)", NULL, NULL);
}

uint8_t HW_ENTROPY_DATA[HW_ENTROPY_LEN];

void collect_hw_entropy(void) {
  // collect entropy from UUID
  uint32_t w = LL_GetUID_Word0();
  memcpy(HW_ENTROPY_DATA, &w, 4);
  w = LL_GetUID_Word1();
  memcpy(HW_ENTROPY_DATA + 4, &w, 4);
  w = LL_GetUID_Word2();
  memcpy(HW_ENTROPY_DATA + 8, &w, 4);

  // set entropy in the OTP randomness block
  if (secfalse == flash_otp_is_locked(FLASH_OTP_BLOCK_RANDOMNESS)) {
    uint8_t entropy[FLASH_OTP_BLOCK_SIZE];
    random_buffer(entropy, FLASH_OTP_BLOCK_SIZE);
    ensure(flash_otp_write(FLASH_OTP_BLOCK_RANDOMNESS, 0, entropy,
                           FLASH_OTP_BLOCK_SIZE),
           NULL);
    ensure(flash_otp_lock(FLASH_OTP_BLOCK_RANDOMNESS), NULL);
  }
  // collect entropy from OTP randomness block
  ensure(flash_otp_read(FLASH_OTP_BLOCK_RANDOMNESS, 0, HW_ENTROPY_DATA + 12,
                        FLASH_OTP_BLOCK_SIZE),
         NULL);
}
