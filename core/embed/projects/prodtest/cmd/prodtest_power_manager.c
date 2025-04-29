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

#include <rtl/cli.h>
#include <rtl/mini_printf.h>
#include <rtl/unit_test.h>
#include <rust_ui_prodtest.h>
#include <sys/power_manager.h>
#include <sys/systick.h>

#include <trezor_rtl.h>

#include <stdlib.h>

void prodtest_pm_hibernate(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Hibernating the device...");

  if (!pm_hibernate()) {
    cli_error(cli, CLI_ERROR, "Failed to hibernate.");
    return;
  }

  cli_trace(cli, "Device is powered externally, hibernation is not possible.");
  cli_ok(cli, "");
}

void prodtest_pm_suspend(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Suspending the device to low-power mode...");
  cli_trace(cli, "Press the POWER button to resume.");
  systick_delay_ms(1000);

  pm_suspend();

  systick_delay_ms(1500);
  cli_trace(cli, "Resumed to active mode.");

  cli_ok(cli, "");
}

void prodtest_pm_watch(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  char screen_text_buf[100];

  while (1) {
    pm_report_t report;
    pm_status_t status = pm_get_report(&report);
    if (status != PM_OK) {
      cli_error(cli, CLI_ERROR, "Failed to get power manager report");
      return;
    }

    if (cli_aborted(cli)) {
      cli_trace(cli, "aborted");
      break;
    }

    cli_progress(cli, "%d.%03d %d.%03d %d.%03d %d.%02d",
                 (int)report.battery_voltage_v,
                 (int)(report.battery_voltage_v * 1000) % 1000,
                 (int)report.battery_current_ma,
                 abs((int)(report.battery_current_ma * 1000) % 1000),
                 (int)report.battery_temp_c,
                 abs((int)(report.battery_temp_c * 1000) % 1000),
                 (int)(report.battery_soc * 100),
                 (int)(report.battery_soc * 10000) % 100);

    mini_snprintf(screen_text_buf, 100, "%d.%03dV %d.%03dmA %d.%02d ",
                  (int)report.battery_voltage_v,
                  (int)(report.battery_voltage_v * 1000) % 1000,
                  (int)report.battery_current_ma,
                  abs((int)(report.battery_current_ma * 1000) % 1000),
                  (int)(report.battery_soc * 100),
                  (int)(report.battery_soc * 10000) % 100);

    screen_prodtest_show_text(screen_text_buf, strlen(screen_text_buf));

    systick_delay_ms(500);
  }

  cli_ok(cli, "");
}

void prodtest_pm_report(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  pm_report_t report;
  pm_status_t status = pm_get_report(&report);
  if (status != PM_OK) {
    cli_error(cli, CLI_ERROR, "Failed to get power manager report");
    return;
  }
  cli_trace(cli, "Power manager report:");
  cli_trace(cli, "  USB %s",
            report.usb_connected ? "connected" : "disconnected");
  cli_trace(cli, "  WLC %s",
            report.wireless_charger_connected ? "connected" : "disconnected");
  cli_trace(cli, "  Battery voltage: %d.%03d V", (int)report.battery_voltage_v,
            (int)(report.battery_voltage_v * 1000) % 1000);
  cli_trace(cli, "  Battery current: %d.%03d mA",
            (int)report.battery_current_ma,
            abs((int)(report.battery_current_ma * 1000) % 1000));
  cli_trace(cli, "  Battery temperature: %d.%03d C", (int)report.battery_temp_c,
            abs((int)(report.battery_temp_c * 1000) % 1000));
  cli_trace(cli, "  Battery SoC: %d.%02d", (int)(report.battery_soc * 100),
            (int)(report.battery_soc * 10000) % 100);
  cli_trace(cli, "  Battery SoC latched: %d.%02d",
            (int)(report.battery_soc_latched * 100),
            (int)(report.battery_soc_latched * 10000) % 100);
  cli_trace(cli, "  PMIC die temperature: %d.%03d C", (int)report.pmic_temp_c,
            (int)(report.pmic_temp_c * 1000) % 1000);
  cli_trace(cli, "  WLC voltage: %d.%03d V",
            (int)report.wireless_output_voltage_v,
            (int)(report.wireless_output_voltage_v * 1000) % 1000);
  cli_trace(cli, "  WLC current: %d.%03d mA", (int)report.wireless_current_ma,
            (int)(report.wireless_current_ma * 1000) % 1000);
  cli_trace(cli, "  WLC die temperature: %d.%03d C",
            (int)report.wireless_temp_c,
            (int)(report.wireless_temp_c * 1000) % 1000);
  cli_trace(cli, "  System voltage: %d.%03d V", (int)report.system_voltage_v,
            (int)(report.system_voltage_v * 1000) % 1000);

  cli_ok(cli, "");
}

void prodtest_pm_monitor(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  pm_status_t status;
  pm_event_t event_flag;
  pm_state_t state;

  status = pm_get_state(&state);

  // Clear leftover events
  pm_get_events(&event_flag);

  cli_trace(cli, "Start power manager monitor, current state: {%s}",
            pm_get_state_name(state));

  while (true) {
    if (cli_aborted(cli)) {
      cli_trace(cli, "power manager test aborted");
      break;
    }

    status = pm_get_events(&event_flag);
    if (status != PM_OK) {
      cli_error(cli, CLI_ERROR, "Failed to get power manager events");
    }

    if (event_flag & PM_EVENT_STATE_CHANGED) {
      status = pm_get_state(&state);

      cli_trace(cli, "Power manager state changed to {%s}",
                pm_get_state_name(state));
    }

    if (event_flag & PM_EVENT_USB_CONNECTED) {
      cli_trace(cli, "USB connected");
    }

    if (event_flag & PM_EVENT_USB_DISCONNECTED) {
      cli_trace(cli, "USB disconnected");
    }

    if (event_flag & PM_EVENT_WIRELESS_CONNECTED) {
      cli_trace(cli, "WLC connected");
    }

    if (event_flag & PM_EVENT_WIRELESS_DISCONNECTED) {
      cli_trace(cli, "WLC disconnected");
    }

    systick_delay_ms(50);
  }

  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
    .name = "power-manager-monitor",
    .func = prodtest_pm_monitor,
    .info = "Run power manager monitor",
    .args = ""
);

PRODTEST_CLI_CMD(
  .name = "power-manager-watch",
  .func = prodtest_pm_watch,
  .info = "Watch power manager reports",
  .args = ""
);

PRODTEST_CLI_CMD(
    .name = "power-manager-report",
    .func = prodtest_pm_report,
    .info = "Get power manager report",
    .args = ""
);

PRODTEST_CLI_CMD(
    .name = "power-manager-suspend",
    .func = prodtest_pm_suspend,
    .info = "Suspend the device to low-power mode",
    .args = ""
);

PRODTEST_CLI_CMD(
    .name = "power-manager-hibernate",
    .func = prodtest_pm_hibernate,
    .info = "Hibernate the device into a near power-off state",
    .args = ""
);

#endif /* USE POWERCTL */
