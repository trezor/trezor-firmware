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

#ifdef USE_SD_CARD

#include <trezor_rtl.h>

#include <io/sdcard.h>
#include <rtl/cli.h>
#include <sys/systick.h>

static void prodtest_sdcard_test(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

#define BLOCK_SIZE (32 * 1024)
  static uint32_t buf1[BLOCK_SIZE / sizeof(uint32_t)];
  static uint32_t buf2[BLOCK_SIZE / sizeof(uint32_t)];

  bool low_speed = false;

#ifndef TREZOR_MODEL_T3T1
  if (sectrue != sdcard_is_present()) {
    cli_trace(cli, "The inserted SD card is required.");
    cli_error(cli, "no-card", "");
    return;
  }
#else
  low_speed = true;
#endif

  cli_trace(cli, "Powering on the SD card...");

  if (sectrue != sdcard_power_on_unchecked(low_speed)) {
    cli_error(cli, CLI_ERROR, "SD card power on sequence failed.");
    return;
  }

  cli_trace(cli, "Reading data from the SD card...");

  if (sectrue != sdcard_read_blocks(buf1, 0, BLOCK_SIZE / SDCARD_BLOCK_SIZE)) {
    cli_error(cli, CLI_ERROR, "Failed to read data from SD card.");
    goto power_off;
  }

  for (int j = 1; j <= 2; j++) {
    cli_trace(cli, "Writing data to the SD card (attempt #%d)...", j);

    for (int i = 0; i < BLOCK_SIZE / sizeof(uint32_t); i++) {
      buf1[i] ^= 0xFFFFFFFF;
    }

    if (sectrue !=
        sdcard_write_blocks(buf1, 0, BLOCK_SIZE / SDCARD_BLOCK_SIZE)) {
      cli_error(cli, CLI_ERROR, "Failed to write data from the SD card.");
      goto power_off;
    }

    systick_delay_ms(1000);

    if (sectrue !=
        sdcard_read_blocks(buf2, 0, BLOCK_SIZE / SDCARD_BLOCK_SIZE)) {
      cli_error(cli, CLI_ERROR, "Failed to read data from SD card.");
      goto power_off;
    }

    if (0 != memcmp(buf1, buf2, sizeof(buf1))) {
      cli_error(cli, CLI_ERROR, "Data mismatch after writing to SD card.");
      goto power_off;
    }
  }

  cli_ok(cli, "");

power_off:
  sdcard_power_off();
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "sdcard-test",
  .func = prodtest_sdcard_test,
  .info = "Test the SD card interface",
  .args = ""
);

#endif  // USE_SD_CARD
