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

#ifdef USE_POWERCTL

#include <rust_ui_prodtest.h>
#include <stdlib.h>
#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <rtl/mini_printf.h>
#include <sys/systick.h>

#include "../../../sys/powerctl/fuel_gauge/fuel_gauge.h"
#include "../../../sys/powerctl/npm1300/npm1300.h"

static void prodtest_fuel_gauge(cli_t *cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  char display_text[100];

  fuel_gauge_state_t fg;

  // Fuel gauge noise covariance parameters.
  // These parameters are used in the Kalman filter to adjust the weight
  // given to the measurements versus the model predictions.
  // Parameters are fine-tuned on battery model simulation.
  float Q = 0.001f;
  float R = 3000.0f;
  float R_aggressive = 3000.0f;
  float Q_aggressive = 0.001f;
  float P_init = 0.1;

  cli_trace(cli, "Initialize Fuel gauge.");

  fuel_gauge_init(&fg, R, Q, R_aggressive, Q_aggressive, P_init);

  npm1300_report_t report;
  if (!npm1300_measure_sync(&report)) {
    cli_error(cli, CLI_ERROR, "Failed to get measurement data from PMIC.");
    return;
  }

  fuel_gauge_initial_guess(&fg, report.vbat, report.ibat, report.ntc_temp);
  uint32_t tick = systick_ms();

  systick_delay_ms(1000);

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "Abort fuel gauge test.");
      break;
    }

    if (!npm1300_measure_sync(&report)) {
      cli_error(cli, CLI_ERROR, "Failed to get measurement data from PMIC.");
      break;
    }

    fuel_gauge_update(&fg, systick_ms() - tick, report.vbat, report.ibat,
                      report.ntc_temp);
    tick = systick_ms();

    // Calculate the integer and fractional parts correctly
    int vbat_int = (int)report.vbat;
    int vbat_frac =
        abs((int)((report.vbat - vbat_int) * 1000));  // Only 3 decimal places

    int ibat_int = (int)report.ibat;
    int ibat_frac =
        abs((int)((report.ibat - ibat_int) * 1000));  // Only 3 decimal places

    int soc_int = (int)fg.soc;
    int soc_frac =
        abs((int)((fg.soc - soc_int) * 1000));  // Only 3 decimal places

    const char *charge_state_str;
    if (report.ibat > 0) {
      charge_state_str = "DISCHARGING";
    } else if (report.ibat < 0) {
      charge_state_str = "CHARGING";
    } else {
      charge_state_str = "IDLE";
    }

    cli_progress(cli, "%d.%03d %d.%03d %d.%03d %s", vbat_int, vbat_frac,
                 ibat_int, ibat_frac, soc_int, soc_frac, charge_state_str);

    mini_snprintf(display_text, 100, "V: %d.%03d I: %d.%03d SOC: %d.%03d",
                  vbat_int, vbat_frac, ibat_int, ibat_frac, soc_int, soc_frac);

    screen_prodtest_show_text(display_text, strlen(display_text));

    // Wait a second
    systick_delay_ms(1000);
  }
}

// clang-format off

PRODTEST_CLI_CMD(
    .name = "fuel-gauge",
    .func = prodtest_fuel_gauge,
    .info = "Test fuel gauge",
    .args = ""
);

#endif  // USE_POWERCTL
