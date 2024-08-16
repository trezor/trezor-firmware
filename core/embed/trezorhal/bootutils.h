#ifndef TREZORHAL_BOOTUTILS_H
#define TREZORHAL_BOOTUTILS_H

#include <stddef.h>
#include <stdint.h>

// Defines boot command for 'reboot_to_bootloader()' function
typedef enum {
  // Normal boot sequence
  BOOT_COMMAND_NONE = 0x00000000,
  // Stop and wait for further instructions
  BOOT_COMMAND_STOP_AND_WAIT = 0x0FC35A96,
  // Do not ask anything, install an upgrade
  BOOT_COMMAND_INSTALL_UPGRADE = 0xFA4A5C8D,
} boot_command_t;

// Maximum size boot_args array
#define BOOT_ARGS_MAX_SIZE (256 - 8)

typedef union {
  uint8_t raw[BOOT_ARGS_MAX_SIZE];

  // firmware header hash, BOOT_COMMAND_INSTALL_UPGRADE
  uint8_t hash[32];

} boot_args_t;

// Sets boot command and arguments for the next reboot
// arguments have too respect boot_args_t structure layout
// (function can be called multiple times before reboting)
void bootargs_set(boot_command_t command, const void* args, size_t args_size);

// Returns the last boot command set by bootargs_set_command()
boot_command_t bootargs_get_command();

// Returns the pointer to boot arguments
const boot_args_t* bootargs_get_args();

// Reboots the device into the bootloader.
// The bootloader will read the command set by `bootargs_set()`.
void __attribute__((noreturn)) reboot_to_bootloader(void);

// Causes immediate reset of the device.
void __attribute__((noreturn)) reboot(void);

// Safely shuts down the device (clears secrets, memory, etc.).
// This function is called when the device is in an unrecoverable state.
void __attribute__((noreturn)) secure_shutdown(void);

#endif  // TREZORHAL_BOOTUTILS_H
