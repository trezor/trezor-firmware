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
#include "model.h"

#include "flash_otp.h"
#include "platform.h"
#include "rand.h"
#include "supervise.h"

#include "stm32f4xx_ll_utils.h"

#ifdef TREZOR_MODEL_T
#include "backlight_pwm.h"
#endif

uint32_t systick_val_copy = 0;

// from util.s
extern void shutdown_privileged(void);

void __attribute__((noreturn)) trezor_shutdown(void) {
  display_finish_actions();
#ifdef USE_SVC_SHUTDOWN
  svc_shutdown();
#else
  // It won't work properly unless called from the privileged mode
  shutdown_privileged();
#endif

  for (;;)
    ;
}

void hal_delay(uint32_t ms) { HAL_Delay(ms); }
uint32_t hal_ticks_ms() { return HAL_GetTick(); }
void hal_delay_us(uint16_t delay_us) {
  uint32_t val = svc_get_systick_val();
  uint32_t t = hal_ticks_ms() * 1000 +
               (((SystemCoreClock / 1000) - val) / (SystemCoreClock / 1000000));
  uint32_t t2 = t;
  do {
    val = svc_get_systick_val();
    t2 = hal_ticks_ms() * 1000 +
         (((SystemCoreClock / 1000) - val) / (SystemCoreClock / 1000000));
  } while ((t2 - t) < delay_us);
}

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
  error_shutdown("(SS)");
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
#ifdef NEW_RENDERING
  display_set_compatible_settings();
#else
  display_set_big_endian();
#endif
  display_orientation(0);
  set_core_clock(CLOCK_168_MHZ);
  backlight_pwm_set_slow();
#endif
}

void invalidate_firmware(void) {
  // erase start of the firmware (metadata) -> invalidate FW
  ensure(flash_unlock_write(), NULL);
  for (int i = 0; i < (1024 / FLASH_BLOCK_SIZE); i += FLASH_BLOCK_SIZE) {
    flash_block_t data = {0};
    ensure(flash_area_write_block(&FIRMWARE_AREA, i * FLASH_BLOCK_SIZE, data),
           NULL);
  }
  ensure(flash_lock_write(), NULL);
}
