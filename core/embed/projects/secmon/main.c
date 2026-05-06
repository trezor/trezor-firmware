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

#include <trezor_bsp.h>
#include <trezor_model.h>

#include <sec/board_capabilities.h>
#include <sec/boot_image.h>
#include <sec/option_bytes.h>
#include <sec/random_delays.h>
#include <sec/secure_aes.h>
#include <sec/tz_init.h>
#include <sec/unit_properties.h>
#include <sys/bootutils.h>
#include <sys/flash.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <sys/sysutils.h>

#ifdef USE_BACKUP_RAM
#include <sec/backup_ram.h>
#endif

#ifdef USE_OPTIGA
#include <sec/optiga_init.h>
#endif

#ifdef USE_TAMPER
#include <sec/tamper.h>
#endif

#ifdef USE_TROPIC
#include <sec/tropic.h>
#endif

#ifdef USE_HASH_PROCESSOR
#include <sec/hash_processor.h>
#endif

#ifdef USE_SECRET
#include <sec/secret.h>
#endif

// Configure and enable power for USB peripheral
// (need to be called in secure mode since PWR and RCC peripheras are
//  not accessible from non-secure mode)

#if defined(USE_USB_HS) && !defined(USE_USB_HS_IN_FS)
void usb_power_init(void) {
  __HAL_RCC_PWR_CLK_ENABLE();
  // Enable VDDUSB
  HAL_PWREx_EnableVddUSB();
  // Power-on USB PHY
  HAL_PWREx_EnableUSBHSTranceiverSupply();
  __HAL_RCC_PWR_CLK_DISABLE();
}
#elif defined(USE_USB_FS) || defined(USE_USB_HS_IN_FS)
void usb_power_init(void) {
  __HAL_RCC_PWR_CLK_ENABLE();
  // Enable VDDUSB (the full-speed peripheral has no separate HS PHY supply)
  HAL_PWREx_EnableVddUSB();
  __HAL_RCC_PWR_CLK_DISABLE();

  // Configure the HSI48 clock recovery system (CRS). HSI48 (already enabled
  // during the secure clock init) and the CRS configuration live in the
  // secure RCC domain, so they are set up here in the secure monitor rather
  // than in the non-secure kernel. The CRS trims HSI48 against the USB SOF
  // once the (non-secure) kernel starts the USB peripheral.
  __HAL_RCC_CRS_CLK_ENABLE();
  RCC_CRSInitTypeDef crs_init = {0};
  crs_init.Prescaler = RCC_CRS_SYNC_DIV1;
  crs_init.Source = RCC_CRS_SYNC_SOURCE_USB;
  crs_init.Polarity = RCC_CRS_SYNC_POLARITY_RISING;
  crs_init.ReloadValue = __HAL_RCC_CRS_RELOADVALUE_CALCULATE(48000000, 1000);
  crs_init.ErrorLimitValue = RCC_CRS_ERRORLIMIT_DEFAULT;
  crs_init.HSI48CalibrationValue = RCC_CRS_HSI48CALIBRATION_DEFAULT;
  HAL_RCCEx_CRSConfig(&crs_init);
}
#else
#error Not implemented
#endif

static void drivers_init(void) {
  flash_init();

  parse_boardloader_capabilities();
  unit_properties_init();

#ifdef USE_STORAGE_HWKEY
  secure_aes_init();
#endif

#ifdef USE_TAMPER
  tamper_init();
  tamper_external_disable();
#endif

  random_delays_init();
#ifdef RDI
  random_delays_start_rdi();
#endif

#ifdef USE_OEM_KEYS_CHECK
  option_bytes_check_oem_keys();
#endif

#ifdef USE_OPTIGA
  optiga_init_and_configure();
#endif

#ifdef USE_TROPIC
  ensure_true(tropic_init(NULL), "Failed to initialize Tropic driver");
#if defined(USE_SECRET) && defined(LOCKABLE_BOOTLOADER)
  if (secfalse != secret_bootloader_locked()) {
    ensure(tropic_ensure_configuration(), "Tropic configuration check failed");
  }
#else
  ensure(tropic_ensure_configuration(), "Tropic configuration check failed");
#endif  // USE_SECRET && LOCKABLE_BOOTLOADER
#endif  // USE_TROPIC

#ifdef USE_BACKUP_RAM
  backup_ram_init();
#endif

#ifdef USE_HASH_PROCESSOR
  hash_processor_init();
#endif

  usb_power_init();
}

// Secure monitor panic handler
// (may be called from interrupt context)
static void secmon_panic(const systask_postmortem_t* pminfo) {
  // Since the system state is unreliable, enter emergency mode,
  // store the postmortem info into bootargs and reboot.
  system_emergency_rescue(NULL, pminfo);
}

// defined in linker script
extern uint32_t _secmon_size;
#define SECMON_SIZE ((uint32_t)&_secmon_size)
#define KERNEL_START (FIRMWARE_START + SECMON_SIZE)

int main(void) {
  tz_init();

  // Initialize system's core services
  system_init(secmon_panic);

  // Initialize secure monitor drivers
  drivers_init();

  // Jump to the kernel (non-secure world)
  jump_to_vectbl_ns(KERNEL_START);
}
