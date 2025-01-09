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
#include <trezor_rtl.h>

#include <io/display.h>
#include <sys/bootargs.h>
#include <sys/bootutils.h>
#include <sys/irq.h>
#include <sys/mpu.h>
#include <util/image.h>

#ifdef TREZOR_MODEL_T2T1
#include "../stm32f4/startup_init.h"
#endif

#ifdef KERNEL_MODE

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

#ifdef BOOTLOADER
// Contains the current boot command saved during bootloader startup.
boot_command_t g_boot_command_saved;

boot_command_t bootargs_get_command() { return g_boot_command_saved; }

void bootargs_get_args(boot_args_t* dest) {
  mpu_mode_t mode = mpu_reconfig(MPU_MODE_BOOTARGS);

  memcpy(dest, g_boot_args.raw, BOOT_ARGS_MAX_SIZE);

  mpu_restore(mode);
}
#endif

// Deletes all secrets and SRAM2 where stack is located
// to prevent stack smashing error, do not return from function calling this
#ifdef STM32U5
static inline void __attribute__((always_inline)) delete_secrets(void) {
  __disable_irq();

  // Disable SAES peripheral clock, so that we don't get tamper events
  __HAL_RCC_SAES_CLK_DISABLE();

  TAMP->CR2 |= TAMP_CR2_BKERASE;
}
#endif  // STM32U5

#ifdef STM32F4
// Ensure that we are running in privileged thread mode.
//
// This function is used only on STM32F4, where a direct jump to the
// bootloader is performed. It checks if we are in handler mode, and
// if so, it switches to privileged thread mode.
__attribute((naked, no_stack_protector)) static void ensure_thread_mode(void) {
  __asm__ volatile(
      // --------------------------------------------------------------
      // Check if we are in handler mode
      // --------------------------------------------------------------

      "LDR      R1, =0x1FF         \n"  // Get lower 9 bits of IPSR
      "MRS      R0, IPSR           \n"
      "ANDS     R0, R0, R1         \n"
      "CMP      R0, #0             \n"  // == 0 if in thread mode
      "IT       EQ                 \n"
      "BXEQ     LR                 \n"  // return if in thread mode

      // --------------------------------------------------------------
      // Disable FP registers lazy stacking
      // --------------------------------------------------------------

      "LDR     R1, = 0xE000EF34    \n"  // FPU->FPCCR
      "LDR     R0, [R1]            \n"
      "BIC     R0, R0, #1          \n"  // Clear LSPACT to suppress lazy
                                        // stacking
      "STR     R0, [R1]            \n"

      // --------------------------------------------------------------
      // Exit handler mode, enter thread mode
      // --------------------------------------------------------------

      "MOV     R0, SP              \n"  // Align stack pointer to 8 bytes
      "AND     R0, R0, #~7         \n"
      "MOV     SP, R0              \n"
      "SUB     SP, SP, #32         \n"  // Allocate space for the stack frame

      "MOV     R0, #0              \n"
      "STR     R0, [SP, #0]        \n"  // future R0 = 0
      "STR     R0, [SP, #4]        \n"  // future R1 = 0
      "STR     R0, [SP, #8]        \n"  // future R2 = 0
      "STR     R0, [SP, #12]       \n"  // future R3 = 0
      "STR     R12, [SP, #16]      \n"  // future R12 = R12
      "STR     LR, [SP, #20]       \n"  // future LR = LR
      "BIC     LR, LR, #1          \n"
      "STR     LR, [SP, #24]       \n"  // return address = LR
      "LDR     R0, = 0x01000000    \n"  // THUMB bit set
      "STR     R0, [SP, #28]       \n"  // future xPSR

      "MRS     R0, CONTROL         \n"  // Clear SPSEL to use MSP for thread
      "BIC     R0, R0, #3          \n"  // Clear nPRIV to run in privileged mode
      "MSR     CONTROL, R0         \n"

      "LDR     LR, = 0xFFFFFFF9    \n"  // Return to Secure Thread mode, use MSP
      "BX      LR                  \n");
}
#endif  // STM32F4

// Reboots the device with the given boot command and arguments
static void __attribute__((noreturn))
reboot_with_args(boot_command_t command, const void* args, size_t args_size) {
  bootargs_set(command, args, args_size);

#ifdef STM32U5
  delete_secrets();
  NVIC_SystemReset();
#else
  display_deinit(DISPLAY_RESET_CONTENT);
  ensure_compatible_settings();

  mpu_reconfig(MPU_MODE_DISABLED);

  ensure_thread_mode();

  // from util.s
  extern void jump_to_with_flag(uint32_t address, uint32_t reset_flag);
  jump_to_with_flag(BOOTLOADER_START + IMAGE_HEADER_SIZE, g_boot_command);
  for (;;)
    ;
#endif
}

void reboot_to_bootloader(void) {
  reboot_with_args(BOOT_COMMAND_STOP_AND_WAIT, NULL, 0);
}

void reboot_and_upgrade(const uint8_t hash[32]) {
  reboot_with_args(BOOT_COMMAND_INSTALL_UPGRADE, hash, 32);
}

void reboot_device(void) {
  bootargs_set(BOOT_COMMAND_NONE, NULL, 0);

#ifdef STM32U5
  delete_secrets();
#endif

  NVIC_SystemReset();
}

void __attribute__((noreturn)) secure_shutdown(void) {
  display_deinit(DISPLAY_RETAIN_CONTENT);

#ifdef STM32U5
  delete_secrets();
#endif
  // from util.s
  extern void shutdown_privileged(void);
  shutdown_privileged();

  for (;;)
    ;
}

void ensure_compatible_settings(void) {
#ifdef TREZOR_MODEL_T2T1
  // Early version of bootloader on T2T1 expects 168 MHz core clock.
  // So we need to set it here before handover to the bootloader.
  set_core_clock(CLOCK_168_MHZ);
#endif
}

#endif  // KERNEL_MODE
