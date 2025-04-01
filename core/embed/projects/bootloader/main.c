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
#include <sec/random_delays.h>
#include <sec/secret.h>
#include <sys/bootargs.h>
#include <sys/bootutils.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <sys/types.h>
#include <util/flash_otp.h>
#include <util/flash_utils.h>
#include <util/image.h>
#include <util/rsod.h>
#include <util/unit_properties.h>

#ifdef USE_PVD
#include <sys/pvd.h>
#endif
#ifdef USE_OPTIGA
#include <sec/optiga_hal.h>
#endif
#ifdef USE_TOUCH
#include <io/touch.h>
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
#ifdef USE_TAMPER
#include <sys/tamper.h>
#endif

#include "antiglitch.h"
#include "bootui.h"
#include "version_check.h"
#include "workflow/workflow.h"

#ifdef TREZOR_EMULATOR
#include "SDL.h"
#include "emulator.h"
#endif

void failed_jump_to_firmware(void);

CONFIDENTIAL volatile secbool dont_optimize_out_true = sectrue;
CONFIDENTIAL void (*volatile firmware_jump_fn)(void) = failed_jump_to_firmware;

static void drivers_init(secbool *touch_initialized) {
  random_delays_init();
#ifdef USE_PVD
  pvd_init();
#endif
#ifdef USE_HASH_PROCESSOR
  hash_processor_init();
#endif
  display_init(DISPLAY_RESET_CONTENT);
  unit_properties_init();

#if (defined TREZOR_MODEL_T3T1 || defined TREZOR_MODEL_T3W1)
  // on T3T1 and T3W1, tester needs to run without touch and tamper, so making
  // an exception until unit variant is written in OTP
  const secbool manufacturing_mode =
      unit_properties()->locked ? secfalse : sectrue;
#else
  const secbool manufacturing_mode = secfalse;
  (void)manufacturing_mode;  // suppress unused variable warning
#endif

#ifdef USE_TAMPER
  tamper_init();
  if (manufacturing_mode != sectrue) {
    tamper_external_enable();
  }
#endif

#ifdef USE_TOUCH
  *touch_initialized = touch_init();
  if (manufacturing_mode != sectrue) {
    ensure(*touch_initialized, "Touch screen panel was not loaded properly.");
  }
#endif

#ifdef USE_OPTIGA
  optiga_hal_init();
#endif
#ifdef USE_BUTTON
  button_init();
#endif
#ifdef USE_CONSUMPTION_MASK
  consumption_mask_init();
#endif
#ifdef USE_RGB_LED
  rgb_led_init();
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
#endif
  display_deinit(DISPLAY_JUMP_BEHAVIOR);
}

static secbool check_vendor_header_lock(const vendor_header *const vhdr) {
  uint8_t lock[FLASH_OTP_BLOCK_SIZE];
  ensure(flash_otp_read(FLASH_OTP_BLOCK_VENDOR_HEADER_LOCK, 0, lock,
                        FLASH_OTP_BLOCK_SIZE),
         NULL);
  if (0 ==
      memcmp(lock,
             "\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF"
             "\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF",
             FLASH_OTP_BLOCK_SIZE)) {
    return sectrue;
  }
  uint8_t hash[32];
  vendor_header_hash(vhdr, hash);
  return sectrue * (0 == memcmp(lock, hash, 32));
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
  ensure_firmware_min_version(hdr->monotonic);

  ensure(check_image_contents(hdr, IMAGE_HEADER_SIZE + vhdr.hdrlen,
                              &FIRMWARE_AREA),
         "Firmware is corrupted");

  secret_prepare_fw(
      ((vhdr.vtrust & VTRUST_SECRET_MASK) == VTRUST_SECRET_ALLOW) * sectrue,
      ((vhdr.vtrust & VTRUST_NO_WARNING) == VTRUST_NO_WARNING) * sectrue);

  // if all warnings are disabled in VTRUST flags then skip the procedure
  if ((vhdr.vtrust & VTRUST_NO_WARNING) != VTRUST_NO_WARNING) {
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

  drivers_deinit();

  system_deinit();

  jump_to_next_stage(
      IMAGE_CODE_ALIGN(FIRMWARE_START + vhdr.hdrlen + IMAGE_HEADER_SIZE));
}

__attribute__((noreturn)) void jump_to_fw_through_reset(void) {
  display_fade(display_get_backlight(), 0, 200);
  reboot_device();
}

#ifndef TREZOR_EMULATOR
int main(void) {
#else
int bootloader_main(void) {
#endif
  secbool stay_in_bootloader = secfalse;
  secbool touch_initialized = secfalse;

  system_init(&rsod_panic_handler);

  drivers_init(&touch_initialized);

  ui_screen_boot_stage_1(false);

#ifdef TREZOR_EMULATOR
  // wait a bit so that the empty lock icon is visible
  // (on a real device, we are waiting for touch init which takes longer)
  hal_delay(400);
#endif

  const image_header *hdr = NULL;
  vendor_header vhdr;

  // detect whether the device contains a valid firmware
  volatile secbool vhdr_present = secfalse;
  volatile secbool vhdr_keys_ok = secfalse;
  volatile secbool vhdr_lock_ok = secfalse;
  volatile secbool img_hdr_ok = secfalse;
  volatile secbool model_ok = secfalse;
  volatile secbool signatures_ok = secfalse;
  volatile secbool version_ok = secfalse;
  volatile secbool header_present = secfalse;
  volatile secbool firmware_present = secfalse;
  volatile secbool firmware_present_backup = secfalse;
  volatile secbool auto_upgrade = secfalse;

  vhdr_present = read_vendor_header((const uint8_t *)FIRMWARE_START, &vhdr);

  if (sectrue == vhdr_present) {
    vhdr_keys_ok = check_vendor_header_keys(&vhdr);
  }

  if (sectrue == vhdr_keys_ok) {
    vhdr_lock_ok = check_vendor_header_lock(&vhdr);
  }

  if (sectrue == vhdr_lock_ok) {
    hdr = read_image_header(
        (const uint8_t *)(size_t)(FIRMWARE_START + vhdr.hdrlen),
        FIRMWARE_IMAGE_MAGIC, FIRMWARE_MAXSIZE);
    if (hdr == (const image_header *)(size_t)(FIRMWARE_START + vhdr.hdrlen)) {
      img_hdr_ok = sectrue;
    }
  }
  if (sectrue == img_hdr_ok) {
    model_ok = check_image_model(hdr);
  }

  if (sectrue == model_ok) {
    signatures_ok =
        check_image_header_sig(hdr, vhdr.vsig_m, vhdr.vsig_n, vhdr.vpub);
  }

  if (sectrue == signatures_ok) {
    version_ok = check_firmware_min_version(hdr->monotonic);
  }

  if (sectrue == version_ok) {
    header_present = version_ok;
  }

  if (sectrue == header_present) {
    ensure_firmware_min_version(hdr->monotonic);
    firmware_present = check_image_contents(
        hdr, IMAGE_HEADER_SIZE + vhdr.hdrlen, &FIRMWARE_AREA);
    firmware_present_backup = firmware_present;
  }

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
      if (firmware_present == sectrue) {
        // continue without user interaction
        auto_upgrade = sectrue;
      }
      break;
    default:
      break;
  }

  ensure(dont_optimize_out_true * (firmware_present == firmware_present_backup),
         NULL);

  // delay to detect touch or skip if we know we are staying in bootloader
  // anyway
  uint32_t touched = 0;
#ifdef USE_TOUCH
  if (firmware_present == sectrue && stay_in_bootloader != sectrue) {
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

  ensure(dont_optimize_out_true * (firmware_present == firmware_present_backup),
         NULL);

  // start the bootloader ...
  // ... if user touched the screen on start
  // ... or we have stay_in_bootloader flag to force it
  // ... or strict upgrade was confirmed in the firmware (auto_upgrade flag)
  // ... or there is no valid firmware
  if (touched || stay_in_bootloader == sectrue || firmware_present != sectrue ||
      auto_upgrade == sectrue) {
    workflow_result_t result;

    jump_reset();
    if (header_present == sectrue) {
      if (auto_upgrade == sectrue) {
        result = workflow_auto_update(&vhdr, hdr);
      } else {
        result = workflow_bootloader(&vhdr, hdr, firmware_present);
      }
    } else {
      result = workflow_empty_device();
    }

    switch (result) {
      case WF_OK_FIRMWARE_INSTALLED:
        firmware_present = sectrue;
        firmware_present_backup = sectrue;
      case WF_OK_REBOOT_SELECTED:
        // todo reconsider need for antiglitching
        // see https://github.com/trezor/trezor-firmware/issues/4805
        ensure(dont_optimize_out_true *
                   (jump_is_allowed_1() == jump_is_allowed_2()),
               NULL);

        ensure(dont_optimize_out_true *
                   (firmware_present == firmware_present_backup),
               NULL);
        jump_to_fw_through_reset();
        break;
      case WF_OK_DEVICE_WIPED:
      case WF_OK_BOOTLOADER_UNLOCKED:
      case WF_ERROR:
        reboot_or_halt_after_rsod();
        return 0;
      case WF_ERROR_FATAL:
      default: {
        // erase storage if we saw flips randomly flip, most likely due to
        // glitch
#ifdef USE_STORAGE_HWKEY
        secret_bhk_regenerate();
#endif
        ensure(erase_storage(NULL), NULL);
        error_shutdown("Bootloader fatal error");
      }
    }
  }

  ensure(dont_optimize_out_true * (firmware_present == firmware_present_backup),
         NULL);

  if (sectrue == firmware_present) {
    firmware_jump_fn = real_jump_to_firmware;
  }

  firmware_jump_fn();

  return 0;
}
