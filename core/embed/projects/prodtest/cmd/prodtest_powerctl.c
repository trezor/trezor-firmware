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
#include <sys/powerctl.h>
#include <sys/systick.h>

static void prodtest_powerctl_suspend(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Suspending the device to low-power mode...");
  cli_trace(cli, "Press the POWER button to resume.");
  systick_delay_ms(1000);

  powerctl_suspend();

  systick_delay_ms(1500);
  cli_trace(cli, "Resumed to active mode.");

  cli_ok(cli, "");
}

static void prodtest_powerctl_hibernate(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Hibernating the the device...");

  if (!powerctl_hibernate()) {
    cli_error(cli, CLI_ERROR, "Failed to hibernate.");
    return;
  }

  cli_trace(cli, "Device is powered externally, hibernation is not possible.");
  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "powerctl-suspend",
  .func = prodtest_powerctl_suspend,
  .info = "Suspend the device to low-power mode",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "powerctl-hibernate",
  .func = prodtest_powerctl_hibernate,
  .info = "Hibernate the device into a near power-off state",
  .args = ""
);


#endif  // USE_POWERCTL
