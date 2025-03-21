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

#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <rtl/unit_test.h>
#include <sys/systick.h>

#include <stdlib.h>
#include "../../../sys/powerctl/npm1300/npm1300.h"

static void prodtest_pmic_init(cli_t* cli) {
  cli_trace(cli, "Initializing the NPM1300 driver...");

  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  npm1300_deinit();

  if (!npm1300_init()) {
    cli_error(cli, CLI_ERROR, "Failed to initialize NPM1300 driver.");
    return;
  }

  cli_ok(cli, "");
}

static void prodtest_pmic_charge_enable(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Enabling battery charging @ %dmA...",
            npm1300_get_charging_limit());

  if (!npm1300_set_charging(true)) {
    cli_error(cli, CLI_ERROR, "Failed to enable battery charging.");
    return;
  }

  cli_ok(cli, "");
}

static void prodtest_pmic_charge_disable(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Disabling battery charging...");

  if (!npm1300_set_charging(false)) {
    cli_error(cli, CLI_ERROR, "Failed to disable battery charging.");
    return;
  }

  cli_ok(cli, "");
}

static void prodtest_pmic_charge_set_limit(cli_t* cli) {
  uint32_t i_charge = 0;

  if (!cli_arg_uint32(cli, "limit", &i_charge) ||
      i_charge < NPM1300_CHARGING_LIMIT_MIN ||
      i_charge > NPM1300_CHARGING_LIMIT_MAX) {
    cli_error_arg(cli, "Expecting charging limit in range %d-%d mA.",
                  NPM1300_CHARGING_LIMIT_MIN, NPM1300_CHARGING_LIMIT_MAX);
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Setting battery charging limit to %d mA...", i_charge);

  if (!npm1300_set_charging_limit(i_charge)) {
    cli_error(cli, CLI_ERROR, "Failed to set battery charging limit.");
    return;
  }

  cli_ok(cli, "");
}

static void prodtest_pmic_buck_set_mode(cli_t* cli) {
  npm1300_buck_mode_t buck_mode = NPM1300_BUCK_MODE_AUTO;

  const char* mode = cli_arg(cli, "mode");
  if (strcmp(mode, "pwm") == 0) {
    buck_mode = NPM1300_BUCK_MODE_PWM;
  } else if (strcmp(mode, "pfm") == 0) {
    buck_mode = NPM1300_BUCK_MODE_PFM;
  } else if (strcmp(mode, "auto") == 0) {
    buck_mode = NPM1300_BUCK_MODE_AUTO;
  } else {
    cli_error_arg(cli, "Buck converter mode expected (pwm, pfm or auto).");
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Setting the buck converter mode...");

  if (!npm1300_set_buck_mode(buck_mode)) {
    cli_error(cli, CLI_ERROR, "Failed to set buck converter mode.");
    return;
  }

  cli_ok(cli, "");
}

static void prodtest_pmic_report(cli_t* cli) {
  uint32_t count = 1;
  uint32_t period = 1000;

  if (cli_has_arg(cli, "count") && !cli_arg_uint32(cli, "count", &count)) {
    cli_error_arg(cli, "Expecting count of measurements.");
    return;
  }

  if (cli_has_arg(cli, "period") && !cli_arg_uint32(cli, "period", &period)) {
    cli_error_arg(cli, "Expecting period in milliseconds.");
    return;
  }

  if (cli_arg_count(cli) > 2) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli,
            "      time      vbat  ibat  ntc    vsys  die    bat  buck mode");

  uint32_t ticks = hal_ticks_ms();

  while (count-- > 0) {
    npm1300_report_t report;

    if (!npm1300_measure_sync(&report)) {
      cli_error(cli, CLI_ERROR, "Failed to get NPM1300 report.");
      return;
    }

    const char* state = "IDLE";

    bool ibat_discharging = ((report.ibat_meas_status >> 2) & 0x03) == 1;
    bool ibat_charging = ((report.ibat_meas_status >> 2) & 0x03) == 3;

    if (ibat_discharging) {
      state = "DISCHARGING";
    } else if (ibat_charging) {
      state = "CHARGING";
    }

    cli_progress(
        cli, "%09d %d.%03d %d.%03d %d.%03d %d.%03d %d.%03d 0x%02X 0x%02X %s",
        ticks, (int)report.vbat, (int)(report.vbat * 1000) % 1000,
        (int)report.ibat, (int)abs(report.ibat * 1000) % 1000,
        (int)report.ntc_temp, (int)abs(report.ntc_temp * 1000) % 1000,
        (int)report.vsys, (int)(report.vsys * 1000) % 1000,
        (int)report.die_temp, (int)abs(report.die_temp * 1000) % 1000,
        report.ibat_meas_status, report.buck_status, state);

    if (count > 0) {
      do {
        if (cli_aborted(cli)) {
          return;
        }
      } while (!ticks_expired(ticks + period));
      ticks += period;
    }
  }

  cli_ok(cli, "");
}

// ut-pmic-init-deinit
// This unit test verifies the PMIC driver initialization and deinitialization
// routine could be called repeatably witout failure. It should verify that all
// driver components are properly cleaned by deinit function.
static ut_status_t ut_pmic_init_deinit() {
  ut_status_t ut_result = UT_PASSED;

  for (uint8_t i = 0; i < 5; i++) {
    // deinitilize the pmic driver
    npm1300_deinit();
    if (npm1300_init() == false) {
      ut_result = UT_FAILED;
      break;
    }
  }

  npm1300_deinit();

  return ut_result;
}

// ut-pmic-battery
// This unit test verifies the battery connection to NPM1300 PMIC.
// Firstly it initilize the PMIC driver and request the measurement
// report. From the measurement report it checks, if the battery voltage and
// NTC temperature are within the expeted range. At last, it checks if NTC
// temperature measurement is not too far away from the die temperarture.
static ut_status_t ut_pmic_battery() {
  ut_status_t ut_result = UT_PASSED;
  npm1300_report_t report;

  if (npm1300_init() == false) {
    ut_result = UT_FAILED;
  } else {
    // Request mesaurement report from PMIC
    if (npm1300_measure_sync(&report) == false) {
      ut_result = UT_FAILED;
    } else {
      // Battery voltage outside given range
      if (report.vbat < 3.0 || report.vbat > 3.8) {
        ut_result = UT_FAILED;
      }

      // Battery NTC outside given range
      if (report.ntc_temp < -40.0 || report.ntc_temp > 50.0) {
        ut_result = UT_FAILED;
      }

      // Battery NTC too far from die temp
      if (abs(report.ntc_temp - report.die_temp) > 10.0) {
        ut_result = UT_FAILED;
      }
    }
  }

  npm1300_deinit();
  return ut_result;
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "pmic-init",
  .func = prodtest_pmic_init,
  .info = "Initialize the PMIC driver",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "pmic-charge-enable",
  .func = prodtest_pmic_charge_enable,
  .info = "Enable battery charging",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "pmic-charge-disable",
  .func = prodtest_pmic_charge_disable,
  .info = "Disable battery charging",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "pmic-charge-set-limit",
  .func = prodtest_pmic_charge_set_limit,
  .info = "Set the battery charging limit",
  .args = "<limit>"
);

PRODTEST_CLI_CMD(
  .name = "pmic-buck-set-mode",
  .func = prodtest_pmic_buck_set_mode,
  .info = "Set the buck converter mode",
  .args = "<mode>"
)

PRODTEST_CLI_CMD(
  .name = "pmic-report",
  .func = prodtest_pmic_report,
  .info = "Retrieve PMIC report",
  .args = "[<count>] [<period>]"
);

REGISTER_UNIT_TEST(
  .name = "ut-pmic-init-deinit",
  .func = ut_pmic_init_deinit,
  .info = "Test PMIC driver initialization and deinitialization",
)

REGISTER_UNIT_TEST(
  .name = "ut-pmic-battery",
  .func = ut_pmic_battery,
  .info = "Test PMIC battery connection",
)

#endif  // USE_POWERCTL
