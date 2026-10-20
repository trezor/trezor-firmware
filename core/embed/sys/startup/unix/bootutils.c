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

#include <stdio.h>
#include <stdlib.h>

#include <sys/bootargs.h>
#include <sys/bootutils.h>
#include <sys/logging.h>
#include <sys/profile.h>
#include <sys/systick.h>

LOG_DECLARE(bootutils)

// On exit, the boot command and its arguments are written to
// `trezor.bootargs` in the profile directory, so that a test harness can
// read what the next boot would have done. The file is never read back
// implicitly; the bootloader emulator takes it as explicit input (-B).
typedef struct {
  // boot_command_t, stored as a fixed-width word
  uint64_t command;
  // raw argument block, see boot_args_t
  uint8_t args[BOOT_ARGS_MAX_SIZE];
} bootargs_file_t;

// Holds the 'command' for the next reboot.
static boot_command_t g_boot_command;

// Holds extra arguments for the command passed to the bootloader.
static boot_args_t g_boot_args;

static const char* bootargs_path(void) {
  static char path[1024];
  if (path[0] == '\0') {
    snprintf(path, sizeof(path), "%s/trezor.bootargs", profile_dir());
  }
  return path;
}

bool bootargs_load_file(const char* path) {
  FILE* f = fopen(path, "rb");
  if (f == NULL) {
    LOG_ERR("cannot open bootargs file '%s'", path);
    return false;
  }

  bootargs_file_t file = {0};
  size_t read = fread(&file, 1, sizeof(file), f);
  fclose(f);

  if (read != sizeof(file)) {
    LOG_ERR("malformed bootargs file '%s'", path);
    return false;
  }

  bootargs_set((boot_command_t)file.command, file.args, BOOT_ARGS_MAX_SIZE);
  return true;
}

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

static void bootargs_persist(void) {
  bootargs_file_t file = {.command = (uint64_t)g_boot_command};
  memcpy(file.args, g_boot_args.raw, BOOT_ARGS_MAX_SIZE);

  FILE* f = fopen(bootargs_path(), "wb");
  if (f == NULL) {
    LOG_WARN("failed to write bootargs file");
    return;
  }
  if (fwrite(&file, 1, sizeof(file), f) != sizeof(file)) {
    LOG_WARN("failed to write bootargs file");
  }
  fclose(f);
}

// A test harness sets TREZOR_EMULATOR_FAST_EXIT to skip the delays that
// let a human read the screen before the process ends.
static bool fast_exit(void) {
  const char* value = getenv("TREZOR_EMULATOR_FAST_EXIT");
  return value != NULL && value[0] != '\0' && value[0] != '0';
}

static void exit_delay(void) {
  if (!fast_exit()) {
    systick_delay_ms(3000);
  }
}

void emulator_exit(emulator_exit_code_t code) {
  bootargs_persist();
  exit(code);
}

__attribute__((noreturn)) void reboot_device(void) {
  LOG_WARN("reboot (normal)");

  bootargs_set(BOOT_COMMAND_REBOOT, NULL, 0);
  emulator_exit(EMULATOR_EXIT_REBOOT);
}

__attribute__((noreturn)) void reboot_to_bootloader(void) {
  LOG_WARN("reboot (to bootloader)");

  bootargs_set(BOOT_COMMAND_STOP_AND_WAIT, NULL, 0);
  emulator_exit(EMULATOR_EXIT_REBOOT);
}

__attribute__((noreturn)) void reboot_and_connect(void) {
  LOG_WARN("reboot (to bootloader, connect)");

  bootargs_set(BOOT_COMMAND_STOP_AND_CONNECT, NULL, 0);
  emulator_exit(EMULATOR_EXIT_REBOOT);
}

__attribute__((noreturn)) void reboot_and_upgrade(const uint8_t hash[32]) {
  LOG_WARN("reboot (upgrade)");

  bootargs_set(BOOT_COMMAND_INSTALL_UPGRADE, hash, 32);
  emulator_exit(EMULATOR_EXIT_REBOOT);
}

__attribute__((noreturn)) void reboot_to_off(void) {
  LOG_WARN("reboot (power off)");

  bootargs_set(BOOT_COMMAND_POWER_OFF, NULL, 0);
  emulator_exit(EMULATOR_EXIT_POWER_OFF);
}

// To avoid including higher-layer code, we declare this function here.
// We expect to remove the show_wipe_info() call in the future as soon as
// we are able to test the bootargs content using automated tests.
extern void show_wipe_info(const bootutils_wipe_info_t* info);

__attribute__((noreturn)) void reboot_and_wipe(
    const bootutils_wipe_info_t* info) {
  show_wipe_info(info);

  LOG_WARN("reboot (wipe)");

  bootargs_set(BOOT_COMMAND_WIPE, info, sizeof(*info));
  exit_delay();
  emulator_exit(EMULATOR_EXIT_REBOOT);
}

__attribute__((noreturn)) void reboot_or_halt_after_rsod(void) {
  LOG_WARN("halt after RSOD");

  // Wait some time to let the user see the displayed
  // message before shutting down
  exit_delay();

  // Like halt_device() on hardware, leave a clean command behind
  bootargs_set(BOOT_COMMAND_NONE, NULL, 0);
  emulator_exit(EMULATOR_EXIT_HALT);
}
