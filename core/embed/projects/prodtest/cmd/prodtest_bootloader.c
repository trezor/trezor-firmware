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

#include <rtl/cli.h>
#include <sys/mpu.h>
#include <util/image.h>

static void prodtest_bootloader_version(cli_t *cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint32_t v = 0;

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_BOOTUPDATE);

  cli_trace(cli, "Reading bootloader image header..");

  const image_header *header =
      read_image_header((const uint8_t *)BOOTLOADER_START,
                        BOOTLOADER_IMAGE_MAGIC, BOOTLOADER_MAXSIZE);

  if (header != NULL) {
    v = header->version;
  } else {
    cli_error(cli, CLI_ERROR, "No valid bootloader header found.");
    return;
  }

  mpu_restore(mpu_mode);

  cli_ok(cli, "%d.%d.%d", v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF);
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "bootloader-version",
  .func = prodtest_bootloader_version,
  .info = "Retrieve the bootloader version",
  .args = ""
);
