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
#include <sec/board_capabilities.h>
#include <sys/flash.h>
#include <sys/mpu.h>

#include "common.h"

static void prodtest_boardloader_version(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  boardloader_version_t v;
  get_boardloader_version(&v);
  cli_ok(cli, "%d.%d.%d", v.version_major, v.version_minor, v.version_patch);
}

#if !PRODUCTION && !TREZOR_MODEL_T2T1
static bool prodtest_boardloader_update_finalize(uint8_t* data, size_t len) {
  mpu_mode_t mode = mpu_reconfig(MPU_MODE_BOARDLOADER);

  secbool res = flash_area_erase(&BOARDLOADER_AREA, NULL);

  if (res != sectrue) {
    goto cleanup;
  }

  res = flash_unlock_write();

  if (res != sectrue) {
    goto cleanup;
  }

  res = flash_area_write_data_padded(&BOARDLOADER_AREA, 0, data, len, 0xFF,
                                     flash_area_get_size(&BOARDLOADER_AREA));

cleanup:

  (void)!flash_lock_write();

  mpu_restore(mode);

  parse_boardloader_capabilities();

  return res == sectrue;
}

static void prodtest_boardloader_update(cli_t* cli) {
  binary_update(cli, prodtest_boardloader_update_finalize);
}
#endif

// clang-format off

PRODTEST_CLI_CMD(
  .name = "boardloader-version",
  .func = prodtest_boardloader_version,
  .info = "Retrieve the boardloader version",
  .args = ""
);

#if !PRODUCTION && !TREZOR_MODEL_T2T1
PRODTEST_CLI_CMD(
  .name = "boardloader-update",
  .func = prodtest_boardloader_update,
  .info = "Update boardloader",
  .args = "<phase> <hex-data>"
);
#endif
