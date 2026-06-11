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

#ifdef USE_DBG_CONSOLE

#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <sys/logging.h>
#include <sys/syslog.h>

#include "prodtest_error_codes.h"

static void prodtest_set_log_filter(cli_t* cli) {
  const char* filter = cli_arg(cli, "filter");
  size_t filter_len = strlen(filter);

  if (filter_len == 0) {
    cli_error_arg(cli, "Expecting filter string.");
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  if (!syslog_set_filter(filter, filter_len)) {
    cli_error(cli, PRODTEST_ERR_SYSLOG_FILTER_SET, "Failed to set log filter.");
    return;
  }

  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "log-filter",
  .func = prodtest_set_log_filter,
  .info = "Set logging filter",
  .args = "<filter>"
);

#endif  // USE_DBG_CONSOLE
