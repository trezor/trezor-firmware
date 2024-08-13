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

#include "image.h"
#include "irq.h"
#include "syscall.h"

#include "board_capabilities.h"
#include "display.h"
#include "dma2d.h"
#include "entropy.h"
#include "fault_handlers.h"
#include "haptic.h"
#include "i2c.h"
#include "memzero.h"
#include "mpu.h"
#include "optiga_commands.h"
#include "optiga_transport.h"
#include "random_delays.h"
#include "sdcard.h"
#include "secret.h"
#include "secure_aes.h"
#include "systick.h"
#include "systimer.h"
#include "tamper.h"
#include "touch.h"
#include "unit_variant.h"

#ifdef USE_OPTIGA
#if !PYOPT
#include <inttypes.h>
#if 1  // color log
#define OPTIGA_LOG_FORMAT \
  "%" PRIu32 " \x1b[35moptiga\x1b[0m \x1b[32mDEBUG\x1b[0m %s: "
#else
#define OPTIGA_LOG_FORMAT "%" PRIu32 " optiga DEBUG %s: "
#endif
static void optiga_log_hex(const char *prefix, const uint8_t *data,
                           size_t data_size) {
  printf(OPTIGA_LOG_FORMAT, hal_ticks_ms() * 1000, prefix);
  for (size_t i = 0; i < data_size; i++) {
    printf("%02x", data[i]);
  }
  printf("\n");
}
#endif
#endif

void drivers_init() {
  syscall_init();

  systick_init();
  systimer_init();

  fault_handlers_init();

  systick_delay_ms(10);

#if defined TREZOR_MODEL_T
  set_core_clock(CLOCK_180_MHZ);
#endif

#ifdef STM32U5
  tamper_init();
#endif

  rdi_init();

#ifdef RDI
  rdi_start();
#endif

#ifdef SYSTEM_VIEW
  enable_systemview();
#endif

#ifdef USE_HASH_PROCESSOR
  hash_processor_init();
#endif

#ifdef USE_DMA2D
  dma2d_init();
#endif

  display_init(DISPLAY_RETAIN_CONTENT);

#ifdef STM32U5
  check_oem_keys();
#endif

  parse_boardloader_capabilities();

  unit_variant_init();

#ifdef STM32U5
  secure_aes_init();
#endif

#ifdef USE_OPTIGA
  uint8_t secret[SECRET_OPTIGA_KEY_LEN] = {0};
  secbool secret_ok = secret_optiga_get(secret);
#endif

  entropy_init();

#if PRODUCTION || BOOTLOADER_QA
  // check_and_replace_bootloader();
#endif

#ifdef USE_BUTTON
  button_init();
#endif

#ifdef USE_RGB_LED
  rgb_led_init();
#endif

#ifdef USE_CONSUMPTION_MASK
  consumption_mask_init();
#endif

#ifdef USE_I2C
  i2c_init();
#endif

#ifdef USE_TOUCH
  touch_init();
#endif

#ifdef USE_SD_CARD
  sdcard_init();
#endif

#ifdef USE_HAPTIC
  haptic_init();
#endif

#ifdef USE_OPTIGA

#if !PYOPT
  // command log is relatively quiet so we enable it in debug builds
  optiga_command_set_log_hex(optiga_log_hex);
  // transport log can be spammy, uncomment if you want it:
  // optiga_transport_set_log_hex(optiga_log_hex);
#endif

  optiga_init();
  if (sectrue == secret_ok) {
    // If the shielded connection cannot be established, reset Optiga and
    // continue without it. In this case, OID_KEY_FIDO and OID_KEY_DEV cannot be
    // used, which means device and FIDO attestation will not work.
    if (optiga_sec_chan_handshake(secret, sizeof(secret)) != OPTIGA_SUCCESS) {
      optiga_soft_reset();
    }
  }
  memzero(secret, sizeof(secret));
  ensure(sectrue * (optiga_open_application() == OPTIGA_SUCCESS),
         "Cannot initialize optiga.");

#endif
}

int main(void) {
  mpu_init();

  // Initialize hardware drivers
  drivers_init();

  // Start unprivileged application
  start_unprivileged_app();

  return 0;
}
