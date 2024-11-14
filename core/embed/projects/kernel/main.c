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

#include <trezor_rtl.h>

#include <gfx/gfx_bitblt.h>
#include <io/display.h>
#include <sec/entropy.h>
#include <sec/random_delays.h>
#include <sec/secret.h>
#include <sec/secure_aes.h>
#include <sys/applet.h>
#include <sys/bootutils.h>
#include <sys/mpu.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <util/bl_check.h>
#include <util/board_capabilities.h>
#include <util/image.h>
#include <util/option_bytes.h>
#include <util/rsod.h>
#include <util/unit_properties.h>
#include "memzero.h"

#ifdef USE_BUTTON
#include <io/button.h>
#endif

#ifdef USE_CONSUMPTION_MASK
#include <sec/consumption_mask.h>
#endif

#ifdef USE_HAPTIC
#include <io/haptic.h>
#endif

#ifdef USE_OPTIGA
#include <sec/optiga_commands.h>
#include <sec/optiga_transport.h>
#endif

#ifdef USE_PVD
#include <sys/pvd.h>
#endif

#ifdef USE_SD_CARD
#include <io/sdcard.h>
#endif

#ifdef USE_RGB_LED
#include <io/rgb_led.h>
#endif

#ifdef SYSTEM_VIEW
#include <sys/systemview.h>
#endif

#ifdef USE_TAMPER
#include <sys/tamper.h>
#endif

#ifdef USE_TOUCH
#include <io/touch.h>
#endif

#ifdef USE_TRUSTZONE
#include <sys/trustzone.h>
#endif

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
#ifdef USE_TAMPER
  tamper_init();
#endif

  random_delays_init();

#ifdef USE_PVD
  pvd_init();
#endif

#ifdef RDI
  random_delays_start_rdi();
#endif

#ifdef SYSTEM_VIEW
  enable_systemview();
#endif

#ifdef USE_HASH_PROCESSOR
  hash_processor_init();
#endif

  gfx_bitblt_init();

  display_init(DISPLAY_JUMP_BEHAVIOR);

#ifdef USE_OEM_KEYS_CHECK
  check_oem_keys();
#endif

  parse_boardloader_capabilities();

  unit_properties_init();

#ifdef USE_STORAGE_HWKEY
  secure_aes_init();
#endif

#ifdef USE_OPTIGA
  uint8_t secret[SECRET_OPTIGA_KEY_LEN] = {0};
  secbool secret_ok = secret_optiga_get(secret);
#endif

  entropy_init();

#if PRODUCTION || BOOTLOADER_QA
  check_and_replace_bootloader();
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

// defined in linker script
extern uint32_t _codelen;
extern uint32_t _coreapp_clear_ram_0_start;
extern uint32_t _coreapp_clear_ram_0_size;
extern uint32_t _coreapp_clear_ram_1_start;
extern uint32_t _coreapp_clear_ram_1_size;
#define KERNEL_SIZE (uint32_t) & _codelen

// Initializes coreapp applet
static void coreapp_init(applet_t *applet) {
  const uint32_t CODE1_START = COREAPP_CODE_ALIGN(KERNEL_START + KERNEL_SIZE);

#ifdef FIRMWARE_P1_START
  const uint32_t CODE1_END = FIRMWARE_P1_START + FIRMWARE_P1_MAXSIZE;
#else
  const uint32_t CODE1_END = FIRMWARE_START + FIRMWARE_MAXSIZE;
#endif

  applet_header_t *coreapp_header = (applet_header_t *)CODE1_START;

  applet_layout_t coreapp_layout = {
      .data1.start = (uint32_t)&_coreapp_clear_ram_0_start,
      .data1.size = (uint32_t)&_coreapp_clear_ram_0_size,
      .data2.start = (uint32_t)&_coreapp_clear_ram_1_start,
      .data2.size = (uint32_t)&_coreapp_clear_ram_1_size,
      .code1.start = CODE1_START,
      .code1.size = CODE1_END - CODE1_START,
#ifdef FIRMWARE_P2_START
      .code2.start = FIRMWARE_P2_START,
      .code2.size = FIRMWARE_P2_MAXSIZE,
#endif
  };

  applet_init(applet, coreapp_header, &coreapp_layout);
}

// Shows RSOD (Red Screen of Death)
static void show_rsod(const systask_postmortem_t *pminfo) {
#ifdef RSOD_IN_COREAPP
  applet_t coreapp;
  coreapp_init(&coreapp);

  // Reset and run the coreapp in RSOD mode
  if (applet_reset(&coreapp, 1, pminfo, sizeof(systask_postmortem_t))) {
    // Run the applet & wait for it to finish
    applet_run(&coreapp);

    if (coreapp.task.pminfo.reason == TASK_TERM_REASON_EXIT) {
      // If the RSOD was shown successfully, proceed to shutdown
      secure_shutdown();
    }
  }
#endif

  // If coreapp crashed, fallback to showing the error using a terminal
  rsod_terminal(pminfo);
}

// Initializes system in emergency mode and shows RSOD
static void init_and_show_rsod(const systask_postmortem_t *pminfo) {
  // Initialize the system's core services
  // (If the kernel crashes in emergency mode, we are out of options
  // and show the RSOD without attempting to re-enter emergency mode)
  system_init(&rsod_terminal);

  // Initialize necessary drivers
  display_init(DISPLAY_RESET_CONTENT);

  // Show RSOD
  show_rsod(pminfo);

  // Wait for the user to manually power off the device
  secure_shutdown();
}

// Kernel panic handler
// (may be called from interrupt context)
static void kernel_panic(const systask_postmortem_t *pminfo) {
  // Since the system state is unreliable, enter emergency mode
  // and show the RSOD.
  system_emergency_rescue(&init_and_show_rsod, pminfo);
  // The previous function call never returns
}

int main(void) {
  // Initialize system's core services
  system_init(&kernel_panic);

#ifdef USE_TRUSTZONE
  // Configure unprivileged access for the coreapp
  tz_init_kernel();
#endif

  // Initialize hardware drivers
  drivers_init();

  // Initialize coreapp task
  applet_t coreapp;
  coreapp_init(&coreapp);

  // Reset and run the coreapp
  if (!applet_reset(&coreapp, 0, NULL, 0)) {
    error_shutdown("Cannot start coreapp");
  }

  // Run the applet & wait for it to finish
  applet_run(&coreapp);

  // Coreapp crashed, show RSOD
  show_rsod(&coreapp.task.pminfo);

  // Wait for the user to manually power off the device
  secure_shutdown();

  return 0;
}
