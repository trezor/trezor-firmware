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

#ifdef USE_RTC

#include <trezor_bsp.h>

#include <rtl/cli.h>
#include <sys/rtc.h>

static void prodtest_rtc_timestamp(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint32_t timestamp;
  if (!rtc_get_timestamp(&timestamp)) {
    cli_error(cli, CLI_ERROR, "Failed to get RTC timestamp");
    return;
  }
  cli_ok(cli, "%u", timestamp);
}

// clang-format off
PRODTEST_CLI_CMD(
  .name = "rtc-timestamp",
  .func = prodtest_rtc_timestamp,
  .info = "Read the RTC timestamp",
  .args = ""
);

#endif
