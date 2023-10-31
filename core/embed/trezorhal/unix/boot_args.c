
#include "../boot_args.h"
#include <common.h>
#include <string.h>

// The 'g_boot_command_shadow' variable stores the 'command' for the next
// reboot/jumping to the bootloadeer. It may be one of the
// 'BOOT_COMMAND_xxx' values defined in the enumeration, or it could
// be any other value that should be treated as a non-special action,
// in which case the bootloader should behave as if the device was
// just powered up.

static boot_command_t g_boot_command_shadow;

// The 'g_boot_args' array stores extra arguments passed
// function boot_args. It sits at section that persists jump to the bootloader.
static boot_args_t g_boot_args;

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

void bootargs_clear() {
  g_boot_command_shadow = BOOT_COMMAND_NONE;
  memset(&g_boot_args, 0, sizeof(g_boot_args));
}

boot_command_t bootargs_get_command() { return g_boot_command_shadow; }

const boot_args_t* bootargs_get_args() { return &g_boot_args; }
