#ifndef TREZORHAL_BOOT_ARGS_H
#define TREZORHAL_BOOT_ARGS_H

// Defines boot command for 'svc_reboot_to_bootloader()' function
typedef enum {
  // Normal boot sequence
  BOOT_COMMAND_NONE = 0x00000000,
  // Stop and wait for further instructions
  BOOT_COMMAND_STOP_AND_WAIT = 0x0FC35A96,
  // Do not ask anything, install an upgrade
  BOOT_COMMAND_INSTALL_UPGRADE = 0xFA4A5C8D,
} boot_command_t;

// Maximum size of extra arguments passed to
// 'svc_reboot_to_bootloader()' function
#define BOOT_ARGS_SIZE 256

#endif  // TREZORHAL_BOOT_ARGS_H
