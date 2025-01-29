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

#include <trezor_rtl.h>

#include <stdlib.h>

#include <sys/bootargs.h>
#include <sys/bootutils.h>
#include <sys/systick.h>

// Holds the 'command' for the next reboot.
static boot_command_t g_boot_command;

// Holds extra arguments for the command passed to the bootloader.
static boot_args_t g_boot_args;

void bootargs_set(boot_command_t command, const void* args, size_t args_size) {
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
}

boot_command_t bootargs_get_command() { return g_boot_command; }

void bootargs_get_args(boot_args_t* dest) {
  memcpy(dest, &g_boot_args, sizeof(boot_args_t));
}

__attribute__((noreturn)) void reboot_device(void) {
  printf("reboot (normal)\n");

  exit(3);
}

__attribute__((noreturn)) void reboot_or_halt_after_rsod(void) {
  printf("reboot (with timeout)\n");

  // Wait some time to let the user see the displayed
  // message before shutting down
  systick_delay_ms(3000);

  exit(3);
}
