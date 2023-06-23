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
#ifdef FANCY_FATAL_ERROR
#include "rust_ui.h"
#endif
#include "flash.h"
#include "rand.h"
#include "stm32.h"
#include "supervise.h"

#include "mini_printf.h"
#include "stm32f4xx_ll_utils.h"

#ifdef TREZOR_MODEL_T
#include "backlight_pwm.h"
#endif

#ifdef RGB16
#define COLOR_FATAL_ERROR RGB16(0x7F, 0x00, 0x00)
#else
#define COLOR_FATAL_ERROR COLOR_BLACK
#endif

// from util.s
extern void shutdown_privileged(void);

void __attribute__((noreturn)) trezor_shutdown(void) {
#ifdef USE_SVC_SHUTDOWN
  svc_shutdown();
#else
  // It won't work properly unless called from the privileged mode
  shutdown_privileged();
#endif

  for (;;)
    ;
}

void __attribute__((noreturn))
error_uni(const char *label, const char *msg, const char *footer) {
  display_orientation(0);

#ifdef FANCY_FATAL_ERROR

  screen_fatal_error_rust(label, msg, "PLEASE VISIT\nTREZOR.IO/RSOD");
  display_refresh();
#else
  display_print_color(COLOR_WHITE, COLOR_FATAL_ERROR);
  if (label) {
    display_printf("%s\n", label);
  }
  if (msg) {
    display_printf("%s\n", msg);
  }
  if (footer) {
    display_printf("\n%s\n", footer);
  }
#endif
  display_backlight(255);
  display_refresh();
  trezor_shutdown();
}

void __attribute__((noreturn))
__fatal_error(const char *expr, const char *msg, const char *file, int line,
              const char *func) {
  display_orientation(0);
  display_backlight(255);

#ifdef FANCY_FATAL_ERROR
  char buf[256] = {0};
  mini_snprintf(buf, sizeof(buf), "%s: %d", file, line);
  screen_fatal_error_rust("INTERNAL ERROR", msg != NULL ? msg : buf,
                          "PLEASE VISIT\nTREZOR.IO/RSOD");
  display_refresh();
#else
  display_print_color(COLOR_WHITE, COLOR_FATAL_ERROR);
  display_printf("\nINTERNAL ERROR:\n");
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
#endif
  trezor_shutdown();
}

void __attribute__((noreturn))
error_shutdown(const char *label, const char *msg) {
  display_orientation(0);

#ifdef FANCY_FATAL_ERROR

  screen_fatal_error_rust(label, msg, "PLEASE VISIT\nTREZOR.IO/RSOD");
  display_refresh();
#else
  display_print_color(COLOR_WHITE, COLOR_FATAL_ERROR);
  if (label) {
    display_printf("%s\n", label);
  }
  if (msg) {
    display_printf("%s\n", msg);
  }
  display_printf("\nPLEASE VISIT TREZOR.IO/RSOD\n");
#endif
  display_backlight(255);
  trezor_shutdown();
}

#ifndef NDEBUG
void __assert_func(const char *file, int line, const char *func,
                   const char *expr) {
  __fatal_error(expr, "assert failed", file, line, func);
}
#endif

void hal_delay(uint32_t ms) { HAL_Delay(ms); }
uint32_t hal_ticks_ms() { return HAL_GetTick(); }

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
  error_shutdown("INTERNAL ERROR", "(SS)");
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

// this function resets settings changed in one layer (bootloader/firmware),
// which might be incompatible with the other layers older versions,
// where this setting might be unknown
void ensure_compatible_settings(void) {
#ifdef TREZOR_MODEL_T
  display_set_big_endian();
  display_orientation(0);
  set_core_clock(CLOCK_168_MHZ);
  backlight_pwm_set_slow();
#endif
}

void show_wipe_code_screen(void) {
  error_uni("WIPE CODE ENTERED", "All data has been erased from the device",
            "PLEASE RECONNECT\nTHE DEVICE");
}
void show_pin_too_many_screen(void) {
  error_uni("TOO MANY PIN ATTEMPTS", "All data has been erased from the device",
            "PLEASE RECONNECT\nTHE DEVICE");
}
