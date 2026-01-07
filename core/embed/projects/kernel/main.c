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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <gfx/gfx_bitblt.h>
#include <io/display.h>
#include <sec/random_delays.h>
#include <sec/secret.h>
#include <sec/secure_aes.h>
#include <sys/bootutils.h>
#include <sys/coreapp.h>
#include <sys/mpu.h>
#include <sys/syscall_ipc.h>
#include <sys/sysevent.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <util/board_capabilities.h>
#include <util/boot_image.h>
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

#ifdef USE_HASH_PROCESSOR
#include <sec/hash_processor.h>
#endif

#ifdef USE_OPTIGA
#include <sec/optiga_init.h>
#endif

#ifdef USE_BACKUP_RAM
#include <sys/backup_ram.h>
#endif

#ifdef USE_TROPIC
#include <sec/tropic.h>
#endif

#ifdef USE_POWER_MANAGER
#include <sys/power_manager.h>
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

#ifdef USE_RTC
#include <sys/rtc.h>
#endif

#ifdef USE_TAMPER
#include <sys/tamper.h>
#endif

#ifdef USE_TOUCH
#include <io/touch.h>
#endif

#ifdef USE_USB
#include <io/usb.h>
#include <io/usb_config.h>
#endif

void drivers_init() {
#ifdef SECURE_MODE
  parse_boardloader_capabilities();
  unit_properties_init();
#ifdef USE_STORAGE_HWKEY
  secure_aes_init();
#endif
#ifdef USE_TAMPER
  tamper_init();
#if PRODUCTION
  tamper_external_enable();
#endif
#endif
  random_delays_init();
#ifdef RDI
  random_delays_start_rdi();
#endif
#ifdef USE_BACKUP_RAM
  backup_ram_init();
#endif
#ifdef USE_HASH_PROCESSOR
  hash_processor_init();
#endif
#endif  // SECURE_MODE

#ifdef USE_RTC
  rtc_init();
#endif

#ifdef USE_CONSUMPTION_MASK
  consumption_mask_init();
#endif

#ifdef USE_POWER_MANAGER
  pm_init(true);
#endif

#ifdef USE_PVD
  pvd_init();
#endif

  display_init(DISPLAY_JUMP_BEHAVIOR);

#ifdef SECURE_MODE
#ifdef USE_OEM_KEYS_CHECK
  check_oem_keys();
#endif

#endif

#ifdef USE_BUTTON
  button_init();
#endif

#ifdef USE_RGB_LED
  rgb_led_init();
#endif

#ifdef USE_TOUCH
  touch_init();
#endif

#ifdef USE_SD_CARD
  sdcard_init();
#endif

#ifdef USE_HAPTIC
  ts_t status = haptic_init();
  ensure_ok(status, "haptic driver initialization failed");
#endif

#ifdef USE_BLE
  ble_init();
#endif

#ifdef SECURE_MODE
#ifdef USE_OPTIGA
  optiga_init_and_configure();
#endif
#ifdef USE_TROPIC
  tropic_init();
#endif
#endif  // SECURE_MODE

#ifdef USE_USB
  usb_configure(NULL);
#endif
}

// Kernel task main loop
//
// Returns when the coreapp task is terminated
static void kernel_loop(applet_t *coreapp) {
#if SECURE_MODE && USE_STORAGE_HWKEY
  secure_aes_set_applet(coreapp);
#endif

  do {
    sysevents_t awaited = {
        .read_ready = 1 << SYSHANDLE_SYSCALL,
        .write_ready = 0,
    };

    sysevents_t signalled = {0};

    sysevents_poll(&awaited, &signalled, ticks_timeout(100));

    if (signalled.read_ready & (1 << SYSHANDLE_SYSCALL)) {
      syscall_ipc_dequeue();
    }

  } while (applet_is_alive(coreapp));
}

#ifndef USE_BOOTARGS_RSOD

// Shows RSOD (Red Screen of Death)
static void show_rsod(const systask_postmortem_t *pminfo) {
#ifdef RSOD_IN_COREAPP
  applet_t coreapp;
  coreapp_init(&coreapp);

  // Reset and run the coreapp in RSOD mode
  if (coreapp_reset(&coreapp, 1, pminfo, sizeof(systask_postmortem_t))) {
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

#endif  // USE_BOOTARGS_RSOD

// Kernel panic handler
// (may be called from interrupt context)
static void kernel_panic(const systask_postmortem_t *pminfo) {
  // Since the system state is unreliable, enter emergency mode
  // and show the RSOD.
#ifndef USE_BOOTARGS_RSOD
  system_emergency_rescue(&init_and_show_rsod, pminfo);
#else
  reboot_with_rsod(pminfo);
#endif  // USE_BOOTARGS_RSOD
  // We never get here
}

int main(void) {
  // Initialize system's core services
  system_init(&kernel_panic);

  // Initialize hardware drivers
  drivers_init();

  // Initialize coreapp task
  applet_t coreapp;
  coreapp_init(&coreapp);

  // Reset and run the coreapp
  if (!coreapp_reset(&coreapp, 0, NULL, 0)) {
    error_shutdown("Cannot start coreapp");
  }

  // Run the applet
  applet_run(&coreapp);

  // Loop until the coreapp is terminated
  kernel_loop(&coreapp);
  // Release the coreapp resources
  applet_stop(&coreapp);

#ifndef USE_BOOTARGS_RSOD
  // Coreapp crashed, show RSOD
  show_rsod(&coreapp.task.pminfo);
  // Reboots or halts (if RSOD_INFINITE_LOOP is defined)
  reboot_or_halt_after_rsod();
#else
  reboot_with_rsod(&coreapp.task.pminfo);
#endif  // USE_BOOTARGS_RSOD

  return 0;
}
