
#include "../boot_args.h"
#include <common.h>
#include <string.h>

// The 'g_boot_command_shadow' shadows a real boot command passed
// to the bootloader.
// 1. In the bootloader, its value is set in the startup code.
// 2. In the firmware it holds command for the next boot and it is used
//    when svc_reboot_to_bootloader() is called
boot_command_t g_boot_command_shadow;

#ifdef STM32U5
// The 'g_boot_command' is persistent variable that holds the 'command'
// for the next reboot/jump to the bootloader. Its value is set to
// g_boot_command_shadow when 'svc_reboot_to_bootloader()' is called.
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
