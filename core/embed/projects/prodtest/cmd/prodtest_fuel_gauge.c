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

  cli_trace(cli, "Initializing the PMIC driver ...");
  if (!npm1300_init()) {
    cli_error(cli, CLI_ERROR, "Failed to initialize PMIC driver.");
    return;
  }

  char display_text[100];

  fuel_gauge_state_t fg;

  float Q = 0.001f;
  float R = 3000.0f;
  float R_agressive = 3000.0f;
  float Q_agressive = 0.001f;
  float P_init = 0.1;

  cli_trace(cli, "Initialize Fuel gauge.");

  void fuel_gauge_init(fuel_gauge_state_t * state, float R, float Q,
                       float R_aggressive, float Q_aggressive, float P_init);

  fuel_gauge_init(&fg, R, Q, R_agressive, Q_agressive, P_init);

  npm1300_report_t report;
  if (!npm1300_measure_sync(&report)) {
    cli_error(cli, CLI_ERROR, "Failed to measure PMIC.");
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
      cli_error(cli, CLI_ERROR, "Failed to measure PMIC.");
      break;
    }

    fuel_gauge_update(&fg, systick_ms() - tick, report.vbat, report.ibat,
                      report.ntc_temp);
    tick = systick_ms();

    cli_progress(cli, "V: %d.%02d I: %d.%02d SOC: %d.%02d", (int)report.vbat,
                 (int)(report.vbat * 1000) % 1000, (int)report.ibat,
                 (int)(report.ibat * 1000) % 1000, (int)fg.soc,
                 (int)(fg.soc * 1000) % 1000);

    mini_snprintf(display_text, 100, "V: %d.%02d I: %d.%02d SOC: %d.%02d",
                  (int)report.vbat, (int)(report.vbat * 1000) % 1000,
                  (int)report.ibat, (int)(report.ibat * 1000) % 1000,
                  (int)fg.soc, (int)(fg.soc * 1000) % 1000);
    screen_prodtest_show_text(display_text, strlen(display_text));

    // Wait a second
    systick_delay_ms(1000);
  }

  cli_trace(cli, "Cleanup PMIC driver.");
  npm1300_deinit();
}

// clang-format off

PRODTEST_CLI_CMD(
    .name = "fuel-gauge",
    .func = prodtest_fuel_gauge,
    .info = "Test fuel gauge",
    .args = ""
);

#endif  // USE_POWERCTL