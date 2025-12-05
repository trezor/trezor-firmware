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

#include <io/display.h>
#include <io/display_utils.h>
#include <io/usb_config.h>
#include <sec/random_delays.h>
#include <sec/secret.h>
#include <sys/bootargs.h>
#include <sys/bootutils.h>
#include <sys/notify.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <sys/types.h>
#include <util/flash_utils.h>
#include <util/image.h>
#include <util/rsod.h>
#include <util/rsod_special.h>
#include <util/unit_properties.h>

#ifdef USE_BOOT_UCB
#include <util/boot_ucb.h>
#endif

#ifdef USE_PVD
#include <sys/pvd.h>
#endif
#ifdef USE_TOUCH
#include <io/touch.h>
#endif
#ifdef USE_BACKUP_RAM
#include <sys/backup_ram.h>
#endif
#ifdef USE_BUTTON
#include <io/button.h>
#endif
#ifdef USE_CONSUMPTION_MASK
#include <sec/consumption_mask.h>
#endif
#ifdef USE_RGB_LED
#include <io/rgb_led.h>
#endif
#ifdef USE_HASH_PROCESSOR
#include <sec/hash_processor.h>
#endif
#ifdef USE_RTC
#include <sys/rtc.h>
#endif
#ifdef USE_TAMPER
#include <sys/tamper.h>
#endif
#ifdef USE_BLE
#include <io/ble.h>
#endif
#ifdef USE_POWER_MANAGER
#include <sys/power_manager.h>
#endif
#ifdef USE_HAPTIC
#include <io/haptic.h>
#endif
#ifdef USE_IWDG
#include <sec/iwdg.h>
#endif
#ifdef USE_NRF
#include <io/nrf.h>
#endif

#ifdef USE_BLE
#include "wire/wire_iface_ble.h"
#endif

#include "bootui.h"
#include "fw_check.h"
#include "rust_ui_common.h"
#include "ui_helpers.h"
#include "version_check.h"
#include "wire/wire_iface_usb.h"
#include "workflow/workflow.h"

#ifdef TREZOR_EMULATOR
#include "SDL.h"
#include "emulator.h"
#endif

void failed_jump_to_firmware(void);

volatile secbool dont_optimize_out_true = sectrue;
void (*volatile firmware_jump_fn)(void) = failed_jump_to_firmware;

static secbool is_manufacturing_mode(void) {
  unit_properties_init();

  vendor_header vhdr;
  memset(&vhdr, 0, sizeof(vhdr));
  (void)!read_vendor_header((const uint8_t *)FIRMWARE_START, &vhdr);

  if ((vhdr.vtrust & VTRUST_ALLOW_PROVISIONING) != VTRUST_ALLOW_PROVISIONING) {
    return secfalse;
  }

#if (defined TREZOR_MODEL_T3T1 || defined TREZOR_MODEL_T3W1)
  // on T3T1 and T3W1, tester needs to run without touch and tamper, so making
  // an exception until unit variant is written in OTP
  const secbool manufacturing_mode =
      unit_properties()->locked ? secfalse : sectrue;
#else
  const secbool manufacturing_mode = secfalse;
#endif

  return manufacturing_mode;
}

static void display_touch_init(secbool manufacturing_mode,
                               secbool *touch_initialized) {
  display_init(DISPLAY_RESET_CONTENT);

#ifdef USE_TOUCH
  secbool touch_init_ok = secfalse;
  touch_init_ok = touch_init();
  if (manufacturing_mode != sectrue) {
    ensure(touch_init_ok, "Touch screen panel was not loaded properly.");
  }
  if (touch_initialized != NULL) {
    *touch_initialized = touch_init_ok;
  }
#endif
}

static secbool boot_sequence(void) {
  secbool stay_in_bootloader = secfalse;

#ifdef USE_BACKUP_RAM
  backup_ram_init();
#endif

#ifdef USE_BUTTON
  button_init();
#endif

#ifdef USE_RGB_LED
  rgb_led_init();
#endif

#ifdef USE_HAPTIC
  haptic_init();
#endif

#ifdef USE_RTC
  rtc_init();
#endif

#ifdef USE_POWER_MANAGER
  pm_init(false);

  boot_command_t cmd = bootargs_get_command();

  bool turn_on =
      (cmd == BOOT_COMMAND_INSTALL_UPGRADE || cmd == BOOT_COMMAND_REBOOT ||
       cmd == BOOT_COMMAND_SHOW_RSOD || cmd == BOOT_COMMAND_WIPE ||
       cmd == BOOT_COMMAND_STOP_AND_WAIT);

  if (cmd != BOOT_COMMAND_POWER_OFF) {
    turn_on = true;
  }

  if (button_is_down(BTN_POWER)) {
    turn_on = false;
  }

  if (cmd == BOOT_COMMAND_POWER_OFF) {
#ifdef USE_BLE
    ble_init();
    ble_wait_until_ready();
    ble_switch_off();
#endif
  }

  uint32_t press_start = 0;
  bool turn_on_locked = false;
  bool bld_locked = false;
#ifdef USE_HAPTIC
  bool haptic_played = false;
#endif

  while (!turn_on) {
    bool btn_down = button_is_down(BTN_POWER);
    if (btn_down) {
      if (press_start == 0) {
        press_start = systick_ms();
        turn_on_locked = true;
        bld_locked = false;
      }

      uint32_t elapsed = systick_ms() - press_start;
      if (elapsed >= 2000) {
        bld_locked = true;
        break;
      }
#ifdef USE_HAPTIC
      if (elapsed >= 500 && !haptic_played) {
        haptic_play(HAPTIC_POWER_ON);
        haptic_played = true;
      }
#endif
    } else if (press_start != 0) {
      // Button just released
      if (turn_on_locked) {
        break;
      }
      // reset to idle
      press_start = 0;
      turn_on_locked = false;
      bld_locked = false;
    }

    pm_state_t state;
    pm_get_state(&state);

    if (pm_is_charging()) {
      // charging indication
#ifdef USE_RGB_LED
      if (!rgb_led_effect_ongoing()) {
        rgb_led_effect_start(RGB_LED_EFFECT_CHARGING, 0);
      }
#endif
    } else {
#ifdef USE_RGB_LED
      rgb_led_set_color(0);
#endif
      if (!btn_down && !state.usb_connected && !state.wireless_connected) {
        // device in just intended to be turned off
        pm_hibernate();
        systick_delay_ms(1000);
        reboot_to_off();
      }
    }
  }

#ifdef USE_RGB_LED
  rgb_led_set_color(0);
#endif

  while (pm_turn_on() != PM_OK) {
#ifdef USE_RGB_LED
    rgb_led_set_color(RGBLED_RED);
    systick_delay_ms(400);
    rgb_led_set_color(0);
    systick_delay_ms(400);
    rgb_led_set_color(RGBLED_RED);
    systick_delay_ms(400);
    rgb_led_set_color(0);
    systick_delay_ms(400);
    rgb_led_set_color(RGBLED_RED);
    systick_delay_ms(400);
    rgb_led_set_color(0);
#endif
    pm_hibernate();
    systick_delay_ms(1000);
    reboot_to_off();
  }

  if (bld_locked) {
#ifdef USE_HAPTIC
    haptic_play(HAPTIC_BOOTLOADER_ENTRY);
#endif

    display_touch_init(secfalse, NULL);
    screen_bootloader_entry_progress(1000, true);

    while (button_is_down(BTN_POWER)) {
    }

    stay_in_bootloader = sectrue;
  }

#endif

  return stay_in_bootloader;
}

static void drivers_init(secbool manufacturing_mode,
                         secbool *touch_initialized) {
  random_delays_init();
#ifdef USE_PVD
  pvd_init();
#endif
#ifdef USE_HASH_PROCESSOR
  hash_processor_init();
#endif

#ifdef USE_TAMPER
  tamper_init();
#endif

#ifndef LAZY_DISPLAY_INIT
  display_touch_init(manufacturing_mode, touch_initialized);
#endif

#ifdef USE_CONSUMPTION_MASK
  consumption_mask_init();
#endif

  usb_configure(NULL);

#ifdef USE_BLE
  ble_init();
  // increase BLE speed for sake of upload speed
  ble_set_high_speed(true);
#endif
}

static void drivers_deinit(void) {
#ifdef FIXED_HW_DEINIT
#ifdef USE_BUTTON
  button_deinit();
#endif
#ifdef USE_RGB_LED
  rgb_led_deinit();
#endif
#ifdef USE_BLE
  ble_deinit();
#endif
#endif
  display_deinit(DISPLAY_JUMP_BEHAVIOR);
#ifdef USE_POWER_MANAGER
  pm_deinit();
#endif
#ifdef USE_BACKUP_RAM
  backup_ram_deinit();
#endif
#ifdef USE_HAPTIC
  haptic_deinit();
#endif
}

void failed_jump_to_firmware(void) { error_shutdown("(glitch)"); }

void real_jump_to_firmware(void) {
  const image_header *hdr = NULL;
  vendor_header vhdr = {0};

  ensure(read_vendor_header((const uint8_t *)FIRMWARE_START, &vhdr),
         "Firmware is corrupted");

  ensure(check_vendor_header_keys(&vhdr), "Firmware is corrupted");

  ensure(check_vendor_header_lock(&vhdr), "Unauthorized vendor keys");

  hdr =
      read_image_header((const uint8_t *)(size_t)(FIRMWARE_START + vhdr.hdrlen),
                        FIRMWARE_IMAGE_MAGIC, FIRMWARE_MAXSIZE);

  ensure(hdr == (const image_header *)(size_t)(FIRMWARE_START + vhdr.hdrlen)
             ? sectrue
             : secfalse,
         "Firmware is corrupted");

  ensure(check_image_model(hdr), "Wrong firmware model");

  ensure(check_image_header_sig(hdr, vhdr.vsig_m, vhdr.vsig_n, vhdr.vpub),
         "Firmware is corrupted");

  ensure(check_firmware_min_version(hdr->monotonic),
         "Firmware downgrade protection");

  ensure(check_image_contents(hdr, IMAGE_HEADER_SIZE + vhdr.hdrlen,
                              &FIRMWARE_AREA),
         "Firmware is corrupted");

  size_t secmon_code_offset = 0;

#ifdef USE_SECMON_VERIFICATION
  size_t secmon_start = (size_t)IMAGE_CODE_ALIGN(FIRMWARE_START + vhdr.hdrlen +
                                                 IMAGE_HEADER_SIZE);
  const secmon_header_t *secmon_hdr =
      read_secmon_header((const uint8_t *)secmon_start, FIRMWARE_MAXSIZE);

  if (secmon_hdr != NULL) {
    secmon_code_offset = IMAGE_CODE_ALIGN(SECMON_HEADER_SIZE);
  }

  ensure((secmon_hdr != NULL) * sectrue, "Secmon header not found");

  ensure(check_secmon_model(secmon_hdr), "Wrong secmon model");

  ensure(check_secmon_header_sig(secmon_hdr), "Invalid secmon signature");

  ensure(check_secmon_min_version(secmon_hdr->monotonic),
         "Secmon downgrade protection");

  ensure(check_secmon_contents(secmon_hdr, secmon_start - FIRMWARE_START,
                               &FIRMWARE_AREA),
         "Secmon is corrupted");
#endif

  // ensure minimal versions are properly stored for both firmware and secmon
  ensure_firmware_min_version(hdr->monotonic);
#ifdef USE_SECMON_VERIFICATION
  ensure_secmon_min_version(secmon_hdr->monotonic);
#endif

  secbool provisioning_access =
      ((vhdr.vtrust & (VTRUST_ALLOW_PROVISIONING | VTRUST_SECRET_MASK)) ==
       (VTRUST_SECRET_ALLOW | VTRUST_ALLOW_PROVISIONING)) *
      sectrue;

  secbool secret_run_access =
      ((vhdr.vtrust & VTRUST_SECRET_MASK) == VTRUST_SECRET_ALLOW) * sectrue;

  secret_prepare_fw(secret_run_access, provisioning_access);

  // if all warnings are disabled in VTRUST flags then skip the procedure
  if ((vhdr.vtrust & VTRUST_NO_WARNING) != VTRUST_NO_WARNING) {
#ifdef LAZY_DISPLAY_INIT
    display_touch_init(secfalse, NULL);
#endif

    ui_fadeout();
    ui_screen_boot(&vhdr, hdr, 0);
    ui_fadein();

    // The delay is encoded in bitwise complement form.
    int delay = (vhdr.vtrust & VTRUST_WAIT_MASK) ^ VTRUST_WAIT_MASK;
    if (delay > 1) {
      while (delay > 0) {
        ui_screen_boot(&vhdr, hdr, delay);
        hal_delay(1000);
        delay--;
      }
    } else if (delay == 1) {
      hal_delay(1000);
    }

    if ((vhdr.vtrust & VTRUST_NO_CLICK) == 0) {
      ui_screen_boot(&vhdr, hdr, -1);
      ui_click();
    }

    ui_screen_boot_stage_1(false);
  }

  if (DISPLAY_JUMP_BEHAVIOR == DISPLAY_RESET_CONTENT) {
    display_fade(display_get_backlight(), 0, 200);
  }

#ifdef USE_IWDG
  secbool allow_unlimited_run = ((vhdr.vtrust & VTRUST_ALLOW_UNLIMITED_RUN) ==
                                 VTRUST_ALLOW_UNLIMITED_RUN) *
                                sectrue;
  if (sectrue != allow_unlimited_run) {
    iwdg_start(60 * 60);  // 1 hour runtime limit
  }
#endif

  drivers_deinit();

  system_deinit();

  jump_to_next_stage(
      IMAGE_CODE_ALIGN(FIRMWARE_START + vhdr.hdrlen + IMAGE_HEADER_SIZE) +
      secmon_code_offset);
}

__attribute__((noreturn)) void reboot_with_fade(void) {
  display_fade(display_get_backlight(), 0, 200);
  reboot_device();
}

#ifndef TREZOR_EMULATOR
int main(void) {
#else
int bootloader_main(void) {
#endif
  secbool touch_initialized = secfalse;

  system_init(&rsod_panic_handler);

#ifdef USE_BOOT_UCB
  // By erasing UCB area we ensure that the boardloader will not repeat
  // the update process if it was already done.
  boot_ucb_erase();
#endif

  secbool manufacturing_mode = is_manufacturing_mode();

  secbool stay_in_bootloader = boot_sequence();

  drivers_init(manufacturing_mode, &touch_initialized);

#ifdef DISABLE_ANIMATION
  disable_animation(true);
#endif

#ifdef USE_BOOTARGS_RSOD
  if (bootargs_get_command() == BOOT_COMMAND_SHOW_RSOD) {
#ifdef LAZY_DISPLAY_INIT
    display_init(DISPLAY_RESET_CONTENT);
#endif
    // post mortem info was left in bootargs
    boot_args_t args;
    bootargs_get_args(&args);
    rsod_gui(&args.pminfo);
    reboot_or_halt_after_rsod();
  }
#endif  // USE_BOOTARGS_RSOD

  if (bootargs_get_command() == BOOT_COMMAND_WIPE) {
#ifdef LAZY_DISPLAY_INIT
    display_init(DISPLAY_RESET_CONTENT);
#endif

    erase_storage(NULL);

#ifdef USE_BLE
    ble_init();
    ble_wait_until_ready();
    wipe_bonds(NULL);
#endif

#ifdef USE_BACKUP_RAM
    backup_ram_erase_protected();
#endif

    // wipe info was left in bootargs
    boot_args_t args;
    bootargs_get_args(&args);

    show_wipe_info(&args.wipeinfo);
    reboot_or_halt_after_rsod();
  }

  ui_screen_boot_stage_1(false);

#ifdef TREZOR_EMULATOR
  // wait a bit so that the empty lock icon is visible
  // (on a real device, we are waiting for touch init which takes longer)
  hal_delay(400);
#endif

  volatile secbool auto_upgrade = secfalse;

  fw_info_t fw;
  fw_check(&fw);

#if PRODUCTION && !defined STM32U5
  // for STM32U5, this check is moved to boardloader
  ensure_bootloader_min_version();
#endif

  switch (bootargs_get_command()) {
    case BOOT_COMMAND_STOP_AND_WAIT:
      // firmware requested to stay in bootloader
      stay_in_bootloader = sectrue;
      break;
    case BOOT_COMMAND_INSTALL_UPGRADE:
      if (fw.firmware_present == sectrue) {
        // continue without user interaction
        auto_upgrade = sectrue;
      }
      break;
    default:
      break;
  }

  ensure(dont_optimize_out_true *
             (fw.firmware_present == fw.firmware_present_backup),
         NULL);

  // delay to detect touch or skip if we know we are staying in bootloader
  // anyway
  uint32_t touched = 0;
#ifndef USE_POWER_MANAGER
#ifdef USE_TOUCH
  if (fw.firmware_present == sectrue && stay_in_bootloader != sectrue) {
    // Wait until the touch controller is ready
    // (on hardware this may take a while)
    if (touch_initialized != secfalse) {
      while (touch_ready() != sectrue) {
        hal_delay(1);
      }
    }
#ifdef TREZOR_EMULATOR
    hal_delay(500);
#endif
    // Give the touch controller time to report events
    // if someone touches the screen
    for (int i = 0; i < 10; i++) {
      if (touch_activity() == sectrue) {
        touched = 1;
        break;
      }
      hal_delay(5);
    }
  }
#elif defined USE_BUTTON
  if (button_is_down(BTN_LEFT)) {
    touched = 1;
  }
#endif
#endif

  ensure(dont_optimize_out_true *
             (fw.firmware_present == fw.firmware_present_backup),
         NULL);

  notify_send(NOTIFY_BOOT);

  // start the bootloader ...
  // ... if user touched the screen on start
  // ... or we have stay_in_bootloader flag to force it
  // ... or strict upgrade was confirmed in the firmware (auto_upgrade flag)
  // ... or there is no valid firmware
  if (touched || stay_in_bootloader == sectrue ||
      fw.firmware_present != sectrue || auto_upgrade == sectrue) {
    workflow_result_t result;

#ifdef LAZY_DISPLAY_INIT
    display_touch_init(secfalse, &touch_initialized);
#endif

    if (fw.header_present == sectrue) {
      if (auto_upgrade == sectrue && fw.firmware_present == sectrue) {
        result = workflow_auto_update(&fw);
      } else {
        result = workflow_bootloader(&fw);
      }
    } else {
      result = workflow_empty_device();
    }

    switch (result) {
      case WF_OK_REBOOT_SELECTED:
#ifdef USE_BLE
        ble_switch_off();
#endif
#ifdef USE_NRF
        nrf_reboot();
#endif
        reboot_with_fade();
        break;
      case WF_OK_FIRMWARE_INSTALLED:
      case WF_OK_DEVICE_WIPED:
      case WF_OK_BOOTLOADER_UNLOCKED:
        reboot_with_fade();
        return 0;
      case WF_ERROR:
        reboot_or_halt_after_rsod();
        break;
      case WF_ERROR_FATAL:
      default: {
        // erase storage if we saw flips randomly flip, most likely due to
        // glitch
#ifdef USE_STORAGE_HWKEY
        secret_bhk_regenerate();
#endif
        ensure(erase_storage(NULL), NULL);
#ifdef USE_BACKUP_RAM
        ensure(backup_ram_erase_protected() * sectrue, NULL);
#endif
        error_shutdown("Bootloader fatal error");
        break;
      }
    }
  } else {
    ensure(dont_optimize_out_true *
               (fw.firmware_present == fw.firmware_present_backup),
           NULL);

    if (sectrue == fw.firmware_present) {
      firmware_jump_fn = real_jump_to_firmware;
    }

    firmware_jump_fn();
  }

  error_shutdown("Unexpected bootloader exit");  // should never happen
}
