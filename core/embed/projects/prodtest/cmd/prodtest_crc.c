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

#include <rtl/cli.h>

static void prodtest_crc_enable(cli_t* cli) {
  cli_enable_crc(cli);
  cli_ok(cli, "");
}

static void prodtest_crc_disable(cli_t* cli) {
  cli_disable_crc(cli);
  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "crc-enable",
  .func = prodtest_crc_enable,
  .info = "Enables CRC check",
  .args = "");

PRODTEST_CLI_CMD(
  .name = "crc-disable",
  .func = prodtest_crc_disable,
  .info = "Disables CRC check",
  .args = "");
