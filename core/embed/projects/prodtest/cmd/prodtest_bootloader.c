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
#include <sys/mpu.h>
#include <util/board_capabilities.h>
#include <util/boot_image.h>
#include <util/image.h>

#ifdef USE_BOOT_UCB
#include <util/boot_header.h>
#endif

static void prodtest_bootloader_version(cli_t *cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

#ifdef USE_BOOT_UCB

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_BOOTUPDATE);

  const boot_header_t *hdr = boot_header_check_integrity(BOOTLOADER_START);

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

#endif
}

#ifndef TREZOR_MODEL_T2T1
__attribute__((
    section(".buf"))) static uint8_t bootloader_buffer[BOOTLOADER_MAXSIZE];
static size_t bootloader_len = 0;

static void prodtest_bootloader_update(cli_t *cli) {
  if (cli_arg_count(cli) < 1) {
    cli_error_arg_count(cli);
    return;
  }

  const char *phase = cli_arg(cli, "phase");

  if (phase == NULL) {
    cli_error_arg(cli, "Expecting phase (begin|chunk|end).");
  }

  if (0 == strcmp(phase, "begin")) {
    if (cli_arg_count(cli) != 1) {
      cli_error_arg_count(cli);
      return;
    }

    // Reset our state
    bootloader_len = 0;
    cli_trace(cli, "Begin");
    cli_ok(cli, "");

  } else if (0 == strcmp(phase, "chunk")) {
    if (cli_arg_count(cli) < 2) {
      cli_error_arg_count(cli);
      return;
    }

    // Receive next piece of the image
    size_t chunk_len = 0;
    // Temporary buffer for this chunk; tweak max if you like
    uint8_t chunk_buf[1024];

    if (!cli_arg_hex(cli, "hex-data", chunk_buf, sizeof(chunk_buf),
                     &chunk_len)) {
      cli_error_arg(cli, "Expecting hex data for chunk.");
      return;
    }

    if (bootloader_len + chunk_len > BOOTLOADER_MAXSIZE) {
      cli_error(cli, CLI_ERROR, "Buffer overflow (have %u, %u more)",
                (unsigned)bootloader_len, (unsigned)chunk_len);
      return;
    }

    memcpy(&bootloader_buffer[bootloader_len], chunk_buf, chunk_len);
    bootloader_len += chunk_len;

    cli_ok(cli, "%u %u", (unsigned)chunk_len, (unsigned)bootloader_len);

  } else if (0 == strcmp(phase, "end")) {
    if (cli_arg_count(cli) != 1) {
      cli_error_arg_count(cli);
      return;
    }

    if (bootloader_len == 0) {
      cli_error(cli, CLI_ERROR, "No data received");
      return;
    }

    boot_image_t bootloader_image = {
        .image_ptr = bootloader_buffer,
        .image_size = bootloader_len,
    };

    boot_image_replace(&bootloader_image);

    // Reset state so next begin must come before chunks
    bootloader_len = 0;

    cli_trace(cli, "Update successful (%u bytes)", (unsigned)bootloader_len);
    cli_ok(cli, "");

  } else {
    cli_error(cli, CLI_ERROR, "Unknown phase '%s' (begin|chunk|end)", phase);
  }
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

