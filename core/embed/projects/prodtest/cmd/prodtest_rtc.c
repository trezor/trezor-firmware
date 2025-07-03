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

static void prodtest_rtc_set(cli_t* cli) {
  if (cli_arg_count(cli) != 6) {
    cli_error_arg_count(cli);
    return;
  }

  uint32_t year, month, day, hour, minute, second;
  if (!cli_arg_uint32(cli, "year", &year) ||
      !cli_arg_uint32(cli, "month", &month) ||
      !cli_arg_uint32(cli, "day", &day) ||
      !cli_arg_uint32(cli, "hour", &hour) ||
      !cli_arg_uint32(cli, "minute", &minute) ||
      !cli_arg_uint32(cli, "second", &second)) {
    cli_error_arg(cli, "Invalid date/time values");
    return;
  }

  if (!rtc_set(year, month, day, hour, minute, second)) {
    cli_error(cli, CLI_ERROR, "Failed to set RTC time");
    return;
  }
  cli_ok(cli, "");
}

static void prodtest_rtc_get(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  rtc_datetime_t datetime;
  if (!rtc_get(&datetime)) {
    cli_error(cli, CLI_ERROR, "Failed to get RTC time");
    return;
  }

  cli_ok(cli, "%04u %02u %02u %02u %02u %02u %02u", datetime.year,
         datetime.month, datetime.day, datetime.hour, datetime.minute,
         datetime.second, datetime.weekday);
}

// clang-format off
PRODTEST_CLI_CMD(
  .name = "rtc-timestamp",
  .func = prodtest_rtc_timestamp,
  .info = "Read the RTC timestamp",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "rtc-set",
  .func = prodtest_rtc_set,
  .info = "Set RTC date/time",
  .args = "<year> <month> <day> <hour> <minute> <second>",
);


PRODTEST_CLI_CMD(
  .name = "rtc-get",
  .func = prodtest_rtc_get,
  .info = "Get RTC date/time",
  .args = "",
);


#endif
