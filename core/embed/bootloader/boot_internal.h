#ifndef BOOT_INTERNAL_H
#define BOOT_INTERNAL_H

#include <boot_args.h>
#include <stdint.h>

// The 'g_boot_command' variable stores the 'command' passed to the
// function 'svc_reboot_to_bootloader()'. It may be one of the
// 'BOOT_COMMAND_xxx' values defined in the enumeration, or it could
// be any other value that should be treated as a non-special action,
// in which case the bootloader should behave as if the device was
// just powered up. The variable is set before the main() is called.
extern boot_command_t g_boot_command;

// The 'g_boot_args' array stores extra arguments passed
// function 'svc_reboot_to_bootloader()'
extern uint8_t g_boot_args[BOOT_ARGS_SIZE];

#endif  // BOOT_INTERNAL_H
