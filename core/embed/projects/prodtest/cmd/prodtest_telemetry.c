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

#ifdef USE_TELEMETRY

#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <sec/telemetry.h>
#include <sec/unit_properties.h>

static void prodtest_telemetry(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  telemetry_data_t data;

  if (!telemetry_get(&data)) {
    cli_error(cli, CLI_ERROR_NODATA, "Telemetry data not available");
    return;
  }

  int32_t min_temp = (int32_t)(data.min_temp_c * 1000.0f);
  int32_t max_temp = (int32_t)(data.max_temp_c * 1000.0f);
  int32_t battery_cycles = (int32_t)(data.battery_cycles * 1000.0f);
  uint32_t tropic_alarms = data.tropic_alarms;

  cli_ok(cli, "%d %d 0x%02X %d %02X%02X%02X%02X%02X %u", min_temp, max_temp,
         data.battery_errors.all, battery_cycles,
         (unsigned)data.tropic_batch[0], (unsigned)data.tropic_batch[1],
         (unsigned)data.tropic_batch[2], (unsigned)data.tropic_batch[3],
         (unsigned)data.tropic_batch[4], (unsigned)tropic_alarms);
}

static void prodtest_telemetry_reset(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

#if PRODUCTION
  unit_properties_t props = {0};
  unit_properties_get(&props);
  if (props.locked) {
    cli_error(cli, CLI_ERROR, "Device is not in manufacturing mode.");
    return;
  }
#endif

  telemetry_reset();
  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "telemetry-read",
  .func = prodtest_telemetry,
  .info = "Read telemetry data",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "telemetry-reset",
  .func = prodtest_telemetry_reset,
  .info = "Reset telemetry data",
  .args = ""
);

#endif  // USE_TELEMETRY
