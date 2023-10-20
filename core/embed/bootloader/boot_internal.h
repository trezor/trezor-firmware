#ifndef BOOT_INTERNAL_H
#define BOOT_INTERNAL_H

#include <common.h>

// The 'g_boot_command' variable stores the argument passed to the
// function 'reboot_to_bootloader()'. This argument may be one of the
// 'BOOT_COMMAND_xxx' values defined in the enumeration, or it could
// be any other value that should be treated as a non-special action,
// in which case the bootloader should behave as if the device was
// just powered up. The variable is set before the main() is called.
extern boot_command_t g_boot_command;

#endif  // BOOT_INTERNAL_H
