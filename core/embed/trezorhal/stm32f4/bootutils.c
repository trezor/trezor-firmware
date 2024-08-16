
#include "../bootutils.h"
#include <common.h>
#include <string.h>

#include "display.h"
#include "irq.h"
#include "mpu.h"

// The 'g_boot_command_shadow' shadows a real boot command passed
// to the bootloader.
// 1. In the bootloader, its value is set in the startup code.
// 2. In the firmware it holds command for the next boot and it is used
//    when reboot_to_bootloader() is called
boot_command_t g_boot_command_shadow;

#ifdef STM32U5
// The 'g_boot_command' is persistent variable that holds the 'command'
// for the next reboot/jump to the bootloader. Its value is set to
// g_boot_command_shadow when 'reboot_to_bootloader()' is called.
boot_command_t __attribute__((section(".boot_command"))) g_boot_command;
#endif

// The 'g_boot_args' is persistent array that stores extra arguments passed
// to the function bootargs_set.
static boot_args_t __attribute__((section(".boot_args"))) g_boot_args;

void bootargs_set(boot_command_t command, const void* args, size_t args_size) {
  // save boot command
  g_boot_command_shadow = command;

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
}

boot_command_t bootargs_get_command() { return g_boot_command_shadow; }

const boot_args_t* bootargs_get_args() { return &g_boot_args; }

void __attribute__((noreturn)) secure_shutdown(void) {
  display_deinit(DISPLAY_RETAIN_CONTENT);

#if defined(STM32U5)
  __HAL_RCC_SAES_CLK_DISABLE();
  // Erase all secrets
  TAMP->CR2 |= TAMP_CR2_BKERASE;
#endif
  // from util.s
  extern void shutdown_privileged(void);
  shutdown_privileged();

  for (;;)
    ;
}

void reboot_to_bootloader(void) {
  boot_command_t boot_command = bootargs_get_command();
  display_deinit(DISPLAY_RESET_CONTENT);
#ifdef ENSURE_COMPATIBLE_SETTINGS
  ensure_compatible_settings();
#endif
#ifdef STM32U5
  // extern uint32_t g_boot_command;
  g_boot_command = boot_command;
  disable_irq();
  delete_secrets();
  NVIC_SystemReset();
#else
  mpu_config_bootloader();
  jump_to_with_flag(BOOTLOADER_START + IMAGE_HEADER_SIZE, boot_command);
  for (;;)
    ;
#endif
}

void reboot(void) { NVIC_SystemReset(); }
