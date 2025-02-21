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

#include <rust_ui_prodtest.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <rtl/unit_test.h>

static void prodtest_unit_test_list(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "List of all registered unit tests:");

  unit_test_t* ut = unit_test_get_records();

  for (size_t i = 0; i < ut->unit_test_count; i++) {
    cli_trace(cli, " %s - %s ", ut->unit_test_array[i].name,
              ut->unit_test_array[i].info);
  }

  cli_ok(cli, "");
}

static void prodtest_unit_test_run(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  bool ut_passed = true;

  cli_trace(cli, "Running all unit tests...");

  unit_test_t* ut = unit_test_get_records();

  for (size_t i = 0; i < ut->unit_test_count; i++) {
    ut_status_t test_result = ut->unit_test_array[i].func(cli);

    cli_trace(cli, "%s: %s", ut->unit_test_array[i].name,
              test_result == UT_PASSED ? "PASSED" : "FAILED");

    if (test_result == UT_FAILED) {
      ut_passed = false;
    }
  }

  if (ut_passed) {
    cli_ok(cli, "");
  } else {
    cli_error(cli, CLI_ERROR, "Some of the unit test failed");
  }
}

// clang-format off

PRODTEST_CLI_CMD(
    .name = "unit-test-list",
    .func = prodtest_unit_test_list,
    .info = "Print list of all registered unit tests",
    .args = ""
)

PRODTEST_CLI_CMD(
    .name = "unit-test-run",
    .func = prodtest_unit_test_run,
    .info = "Run all registerd unit tests",
    .args = ""
  )
