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

#include <gfx/fonts.h>
#include <gfx/gfx_draw.h>
#include <io/display.h>
#include <rtl/cli.h>
#include <sys/bootutils.h>
#include <sys/mpu.h>
#include <sys/systick.h>
#include <util/fwutils.h>

#include <version.h>

static gfx_text_attr_t bold = {
    .font = FONT_BOLD,
    .fg_color = COLOR_WHITE,
    .bg_color = COLOR_BLACK,
};

static void prodtest_prodtest_intro(cli_t* cli) {
  cli_trace(cli, "Welcome to Trezor %s Production Test Firmware v%d.%d.%d.",
            MODEL_NAME, VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH);
  cli_trace(cli, "");
  cli_trace(cli, "Type 'help' to view all available commands.");
  cli_trace(cli, "");
}

static void prodtest_prodtest_version(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_ok(cli, "%d.%d.%d", VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH);
}

static void prodtest_prodtest_wipe(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Invalidating the production test firmware header...");
  firmware_invalidate_header();

  gfx_clear();
  gfx_offset_t pos = gfx_offset(DISPLAY_RESX / 2, DISPLAY_RESY / 2 + 10);
  gfx_draw_text(pos, "WIPED", -1, &bold, GFX_ALIGN_CENTER);
  display_refresh();

  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "$intro",
  .func = prodtest_prodtest_intro,
  .info = "",
  .args = "",
);

PRODTEST_CLI_CMD(
  .name = "prodtest-version",
  .func = prodtest_prodtest_version,
  .info = "Retrieve the production test firmware version",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "prodtest-wipe",
  .func = prodtest_prodtest_wipe,
  .info = "Wipe the production test firmware",
  .args = ""
);
