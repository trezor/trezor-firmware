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

#include <sec/random_delays.h>
#include <sec/secure_aes.h>
#include <sec/unit_properties.h>
#include <sys/bootutils.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <sys/sysutils.h>
#include <util/board_capabilities.h>
#include <util/boot_image.h>
#include <util/flash.h>
#include <util/option_bytes.h>

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
  check_oem_keys();
#endif

#ifdef USE_OPTIGA
  optiga_init_and_configure();
#endif

#ifdef USE_TROPIC
  tropic_init();
#endif

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
static void secmon_panic(const systask_postmortem_t *pminfo) {
  // Since the system state is unreliable, enter emergency mode,
  // store the postmortem info into bootargs and reboot.
  system_emergency_rescue(NULL, pminfo);
}

// defined in linker script
extern uint32_t _secmon_size;
#define SECMON_SIZE ((uint32_t) & _secmon_size)
#define KERNEL_START (FIRMWARE_START + SECMON_SIZE)

int main(void) {
  // Initialize system's core services
  system_init(secmon_panic);

  // Initialize secure monitor drivers
  drivers_init();

  // Jump to the kernel (non-secure world)
  jump_to_vectbl_ns(KERNEL_START);
}
