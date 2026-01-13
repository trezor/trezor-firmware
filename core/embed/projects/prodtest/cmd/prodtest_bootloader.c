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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <sec/board_capabilities.h>
#include <sys/mpu.h>
#include <util/boot_image.h>
#include <util/image.h>

#include "common.h"

#ifdef USE_BOOT_UCB
#include <util/boot_header.h>
#endif

static void prodtest_bootloader_version(cli_t *cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

#ifdef USE_BOOT_UCB

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_BOOTLOADER);

  const boot_header_auth_t *hdr = boot_header_auth_get(BOOTLOADER_START);

  if (hdr == NULL) {
    mpu_restore(mpu_mode);
    cli_error(cli, CLI_ERROR, "No valid bootloader header found.");
    return;
  }

  cli_ok(cli, "%d.%d.%d", hdr->version.major, hdr->version.minor,
         hdr->version.patch);

  mpu_restore(mpu_mode);

#else
  uint32_t v = 0;

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_BOOTLOADER);

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

#endif
}

#ifndef TREZOR_MODEL_T2T1

#if USE_BOOT_UCB
// Writes boot header and bootloader code to the BOOTUPDATE_AREA
static bool write_to_bootupdate_area(const uint8_t *data, size_t size) {
  if (!IS_ALIGNED(size, FLASH_BLOCK_SIZE)) {
    return false;
  }

  if (sectrue != flash_area_erase(&BOOTUPDATE_AREA, NULL)) {
    return false;
  }

  if (sectrue != flash_unlock_write()) {
    return false;
  }

  if (sectrue != flash_area_write_data(&BOOTUPDATE_AREA, 0, data, size)) {
    return false;
  }

  if (sectrue != flash_lock_write()) {
    return false;
  }

  return true;
}
#endif  // USE_BOOT_UCB

static bool prodtest_bootloader_update_finalize(uint8_t *data, size_t len) {
#if USE_BOOT_UCB
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_BOOTUPDATE);

  if (!write_to_bootupdate_area(data, len)) {
    mpu_restore(mpu_mode);
    return false;
  }

  boot_image_t bootloader_image = {
      .image_ptr = (const void *)BOOTUPDATE_START,
      .image_size = len,
  };

  boot_image_replace(&bootloader_image);

  mpu_restore(mpu_mode);

#else
  boot_image_t bootloader_image = {
      .image_ptr = data,
      .image_size = len,
  };

  boot_image_replace(&bootloader_image);
#endif

  return true;
}

static void prodtest_bootloader_update(cli_t *cli) {
  binary_update(cli, prodtest_bootloader_update_finalize);
}
#endif

// clang-format off

PRODTEST_CLI_CMD(
  .name = "bootloader-version",
  .func = prodtest_bootloader_version,
  .info = "Retrieve the bootloader version",
  .args = ""
);

#ifndef TREZOR_MODEL_T2T1
PRODTEST_CLI_CMD(
  .name = "bootloader-update",
  .func = prodtest_bootloader_update,
  .info = "Update bootloader",
  .args = "<phase> <hex-data>"
);
#endif

