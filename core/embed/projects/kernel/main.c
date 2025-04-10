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
#include <sys/sysevent.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <util/bl_check.h>
#include <util/board_capabilities.h>
#include <util/image.h>
#include <util/option_bytes.h>
#include <util/rsod.h>
#include <util/unit_properties.h>

#ifdef USE_BUTTON
#include <io/button.h>
#endif

#ifdef USE_BLE
#include <io/ble.h>
#endif

#ifdef USE_CONSUMPTION_MASK
#include <sec/consumption_mask.h>
#endif

#ifdef USE_HAPTIC
#include <io/haptic.h>
#endif

#ifdef USE_OPTIGA
#include <sec/optiga_config.h>
#endif

#ifdef USE_TROPIC
#include <sec/tropic.h>
#endif

#ifdef USE_POWERCTL
#include <sys/powerctl.h>
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

void drivers_init() {
#ifdef USE_POWERCTL
  powerctl_init();
#endif

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

  display_init(DISPLAY_JUMP_BEHAVIOR);

#ifdef USE_OEM_KEYS_CHECK
  check_oem_keys();
#endif

  parse_boardloader_capabilities();

  unit_properties_init();

#ifdef USE_STORAGE_HWKEY
  secure_aes_init();
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

#ifdef USE_BLE
  ble_init();
#endif

#ifdef USE_OPTIGA
  optiga_init_and_configure();
#endif

#ifdef USE_TROPIC
  tropic_init();
#endif
}

// Kernel task main loop
//
// Returns when the coreapp task is terminated
static void kernel_loop(applet_t *coreapp) {
  do {
    sysevents_t awaited = {0};
    sysevents_t signalled = {0};

    sysevents_poll(&awaited, &signalled, ticks_timeout(100));

  } while (applet_is_alive(coreapp));
}

// defined in linker script
extern uint32_t _codelen;

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
      .data1.start = (uint32_t)AUX1_RAM_START,
      .data1.size = (uint32_t)AUX1_RAM_SIZE,
#ifdef AUX2_RAM_START
      .data2.start = (uint32_t)AUX2_RAM_START,
      .data2.size = (uint32_t)AUX2_RAM_SIZE,
#endif
      .code1.start = CODE1_START,
      .code1.size = CODE1_END - CODE1_START,
#ifdef FIRMWARE_P2_START
      .code2.start = FIRMWARE_P2_START,
      .code2.size = FIRMWARE_P2_MAXSIZE,
#endif
  };

  applet_privileges_t coreapp_privileges = {
      .assets_area_access = true,
  };

  applet_init(applet, coreapp_header, &coreapp_layout, &coreapp_privileges);
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
    // Loop until the coreapp is terminated
    kernel_loop(&coreapp);
    // Release the coreapp resources
    applet_stop(&coreapp);

    if (coreapp.task.pminfo.reason == TASK_TERM_REASON_EXIT) {
      // RSOD was shown successfully
      return;
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

  // Reboots or halts (if RSOD_INFINITE_LOOP is defined)
  reboot_or_halt_after_rsod();
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

  // Run the applet
  applet_run(&coreapp);
  // Loop until the coreapp is terminated
  kernel_loop(&coreapp);
  // Release the coreapp resources
  applet_stop(&coreapp);

  // Coreapp crashed, show RSOD
  show_rsod(&coreapp.task.pminfo);

  // Reboots or halts (if RSOD_INFINITE_LOOP is defined)
  reboot_or_halt_after_rsod();

  return 0;
}
