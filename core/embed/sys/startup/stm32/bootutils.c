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

#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sys/bootargs.h>
#include <sys/bootutils.h>
#include <sys/irq.h>
#include <sys/linker_utils.h>
#include <sys/mpu.h>
#include <sys/stack_utils.h>
#include <sys/systick.h>
#include <sys/sysutils.h>

#ifdef STM32F4
#include <io/display.h>
#endif

// Battery powered devices (USE_POWER_MANAGER) should not stall
// after showing RSOD, as it would drain the battery.
#ifdef USE_POWER_MANAGER
#ifdef RSOD_INFINITE_LOOP
#error "RSOD_INFINITE_LOOP is not supported on battery powered devices"
#endif
#endif

#ifdef SECURE_MODE

#ifdef STM32U5
// Persistent variable that holds the 'command' for the next reboot.
boot_command_t __attribute__((section(".boot_command"))) g_boot_command;
#else
// Holds the 'command' for the next jump to the bootloader.
static boot_command_t g_boot_command = BOOT_COMMAND_NONE;
#endif

// Persistent array that holds extra arguments for the command passed
// to the bootloader.
static boot_args_t __attribute__((section(".boot_args"))) g_boot_args;

void bootargs_set(boot_command_t command, const void* args, size_t args_size) {
  mpu_mode_t mode = mpu_reconfig(MPU_MODE_BOOTARGS);

  // save boot command
  g_boot_command = command;

  size_t copy_size = 0;
  // copy arguments up to BOOT_ARGS_MAX_SIZE
  if (args != NULL && args_size > 0) {
    copy_size = MIN(args_size, BOOT_ARGS_MAX_SIZE);
    memcpy(&g_boot_args.raw[0], args, copy_size);
  }

  // clear rest of boot_args array
  size_t clear_size = BOOT_ARGS_MAX_SIZE - copy_size;
  if (clear_size > 0) {
    memset(&g_boot_args.raw[copy_size], 0, clear_size);
  }

  mpu_restore(mode);
}

void bootargs_get_args(boot_args_t* dest) {
  mpu_mode_t mode = mpu_reconfig(MPU_MODE_BOOTARGS);

  memcpy(dest, g_boot_args.raw, BOOT_ARGS_MAX_SIZE);

  mpu_restore(mode);
}

#ifdef BOOTLOADER
// Contains the current boot command saved during bootloader startup.
boot_command_t g_boot_command_saved;

boot_command_t bootargs_get_command() { return g_boot_command_saved; }

void bootargs_init(uint32_t r11_register) {
#ifdef STM32U5
  g_boot_command_saved = g_boot_command;
  g_boot_command = BOOT_COMMAND_NONE;
#else
  g_boot_command_saved = r11_register;
#endif
}
#endif

#ifdef RSOD_INFINITE_LOOP
// Continuation of `reboot_with_args`
static void halt_device_phase_2(uint32_t arg1, uint32_t arg2) {
  // We are now running on a new stack. We cannot be sure about
  // any variables in the .bss and .data sections, so we must
  // be careful and avoid using them altogether.

  // Reset peripherals (so we are sure that no DMA is pending)
  // and disable all interrupts and clear all pending ones
  reset_peripherals_and_interrupts();

  // Clear unused part of stack
  clear_unused_stack();

  // Clear all memory except stack and bootargs
  memregion_t region = MEMREGION_ALL_RUNTIME_RAM;
  MEMREGION_DEL_SECTION(&region, _stack_section);
  MEMREGION_DEL_SECTION(&region, _bootargs_ram);
  memregion_fill(&region, 0);

#ifdef STM32F4
  clear_otg_hs_memory();
#endif

  while (true)
    ;  // Infinite loop
}

__attribute__((noreturn)) static void halt_device(void) {
  // Clear bootargs to prevent the bootloader doing anything
  // unexpected when if the device is reset during the halt.
  bootargs_set(BOOT_COMMAND_NONE, NULL, 0);

  // Disable interrupts, MPU, clear all registers and set up a new stack
  // (on STM32U5 it also clear all CPU secrets and SRAM2).
  call_with_new_stack(0, 0, true, halt_device_phase_2);
}
#endif  // RSOD_INFINITE_LOOP

// Continuation of `reboot_with_args`
static void reboot_with_args_phase_2(uint32_t arg1, uint32_t arg2) {
  // We are now running on a new stack. We cannot be sure about
  // any variables in the .bss and .data sections, so we must
  // be careful and avoid using them altogether.

  // Reset peripherals (so we are sure that no DMA is pending)
  // and disable all interrupts and clear all pending ones
  reset_peripherals_and_interrupts();

  // Clear unused part of stack
  clear_unused_stack();

  // Clear all memory except stack and bootargs
  memregion_t region = MEMREGION_ALL_RUNTIME_RAM;
  MEMREGION_DEL_SECTION(&region, _stack_section);
  MEMREGION_DEL_SECTION(&region, _bootargs_ram);
  memregion_fill(&region, 0);

#if defined STM32U5
  NVIC_SystemReset();
#elif defined STM32F4
  boot_command_t command = arg1;
  clear_otg_hs_memory();
  if (command == BOOT_COMMAND_NONE) {
    NVIC_SystemReset();
  } else {
#ifndef FIXED_HW_DEINIT
    SysTick_Config(HAL_RCC_GetSysClockFreq() / 1000U);
    NVIC_SetPriority(SysTick_IRQn, 0);
#endif
    jump_to_vectbl(BOOTLOADER_START + BOOTLOADER_VECTBL_OFFSET, command);
  }
#else
#error Unsupported platform
#endif
}

// Reboots the device with the given boot command and arguments
__attribute__((noreturn)) static void reboot_with_args(boot_command_t command,
                                                       const void* args,
                                                       size_t args_size) {
  // Set bootargs area to the new command and arguments
  bootargs_set(command, args, args_size);

#ifdef STM32F4
  // We are going to jump directly to the bootloader, so we need to
  // ensure that the device is in a compatible state. Following lines
  // ensure the display is properly deinitialized, CPU frequency is
  // properly set and we are running in privileged thread mode.
  display_deinit(DISPLAY_RESET_CONTENT);
  ensure_compatible_settings();
  ensure_thread_mode();
#endif

  // Disable interrupts, MPU, clear all registers and set up a new stack
  // (on STM32U5 it also clear all CPU secrets and SRAM2).
  call_with_new_stack(command, 0, true, reboot_with_args_phase_2);
}

__attribute__((noreturn)) void reboot_to_bootloader(void) {
  reboot_with_args(BOOT_COMMAND_STOP_AND_WAIT, NULL, 0);
}

__attribute__((noreturn)) void reboot_and_upgrade(const uint8_t hash[32]) {
  reboot_with_args(BOOT_COMMAND_INSTALL_UPGRADE, hash, 32);
}

__attribute__((noreturn)) void reboot_device(void) {
  reboot_with_args(BOOT_COMMAND_REBOOT, NULL, 0);
}

__attribute__((noreturn)) void reboot_to_off(void) {
  reboot_with_args(BOOT_COMMAND_POWER_OFF, NULL, 0);
}

__attribute__((noreturn)) void reboot_with_rsod(
    const systask_postmortem_t* pminfo) {
  // Set bootargs area to the new command and arguments
  reboot_with_args(BOOT_COMMAND_SHOW_RSOD, pminfo, sizeof(*pminfo));
}
__attribute__((noreturn)) void reboot_and_wipe(
    const bootutils_wipe_info_t* info) {
  reboot_with_args(BOOT_COMMAND_WIPE, info, sizeof(*info));
}

__attribute__((noreturn)) void reboot_or_halt_after_rsod(void) {
#ifndef RSOD_INFINITE_LOOP
  systick_delay_ms(10 * 1000);
#endif
#ifdef RSOD_INFINITE_LOOP
  halt_device();
#else
  reboot_device();
#endif
}

#endif  // SECURE_MODE

static void jump_to_next_stage_phase_2(uint32_t arg1, uint32_t arg2) {
  // We are now running on a new stack. We cannot be sure about
  // any variables in the .bss and .data sections, so we must
  // be careful and avoid using them altogether.

  // Reset peripherals (so we are sure that no DMA is pending)
  // and disable all interrupts and clear all pending ones
  reset_peripherals_and_interrupts();

  // Clear unused part of stack
  clear_unused_stack();

  // Clear all memory except stack and bootargs
  memregion_t region = MEMREGION_ALL_RUNTIME_RAM;
  MEMREGION_DEL_SECTION(&region, _stack_section);
  MEMREGION_DEL_SECTION(&region, _bootargs_ram);
  memregion_fill(&region, 0);

  // Jump to reset vector of the next stage
  jump_to_vectbl(arg1, 0);
}

void __attribute__((noreturn)) jump_to_next_stage(uint32_t vectbl_address) {
#ifdef STM32F4
  // Ensure the display is properly deinitialized, CPU frequency is
  // properly set. It's needed for backward compatibility with the older
  // firmware.
  display_deinit(DISPLAY_JUMP_BEHAVIOR);
  ensure_compatible_settings();
#endif

  // Disable interrupts, MPU, clear all registers and set up a new stack
  // (on STM32U5 it also clear all CPU secrets and SRAM2).
  call_with_new_stack(vectbl_address, 0, false, jump_to_next_stage_phase_2);
}

#endif  // KERNEL_MODE
