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

#ifdef USE_RGB_LED

#include <trezor_rtl.h>

#include <io/rgb_led.h>
#include <rtl/cli.h>

#include "../prodtest.h"

static void prodtest_rgbled_set(cli_t* cli) {
  uint32_t r = 0;
  uint32_t g = 0;
  uint32_t b = 0;

  if (!cli_arg_uint32(cli, "r", &r) || r > 255) {
    cli_error_arg(cli, "Expecting red value in range 0-255.");
    return;
  }

  if (!cli_arg_uint32(cli, "g", &g) || g > 255) {
    cli_error_arg(cli, "Expecting green value in range 0-255.");
    return;
  }

  if (!cli_arg_uint32(cli, "b", &b) || b > 255) {
    cli_error_arg(cli, "Expecting blue value in range 0-255.");
    return;
  }

  if (cli_arg_count(cli) > 3) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Setting the RGB LED color to [%d, %d, %d]...", r, g, b);

  // Disable automatic control of RGB LED in prodtest main loop
  prodtest_disable_rgbled_control();

  uint32_t rgb = (r << 16) | (g << 8) | b;

  rgb_led_set_color(rgb);

  cli_ok(cli, "");
}

static void prodtest_rgbled_effect_start(cli_t* cli) {
  uint32_t effect_num;
  uint32_t requested_cycles = 0;

  if (!cli_arg_uint32(cli, "effect_num", &effect_num) ||
      effect_num >= RGB_LED_NUM_OF_EFFECTS) {
    cli_error_arg(cli, "Expecting effect number in range 0-%d.",
                  (RGB_LED_NUM_OF_EFFECTS - 1));
    return;
  }

  if (cli_has_arg(cli, "requested_cycles")) {
    if (!cli_arg_uint32(cli, "requested_cycles", &requested_cycles) ||
        requested_cycles == 0) {
      cli_error_arg(cli,
                    "Expecting requested_cycles to be a positive integer.");
      return;
    }
  }

  if (cli_arg_count(cli) > 2) {
    cli_error_arg_count(cli);
    return;
  }

  if (requested_cycles == 0) {
    cli_trace(cli, "Start RGB LED effect #%d for infinite cycles", effect_num);
  } else {
    cli_trace(cli, "Start RGB LED effect #%d for %d cycles", effect_num,
              requested_cycles);
  }

  // Disable automatic control of RGB LED in prodtest main loop
  prodtest_disable_rgbled_control();

  rgb_led_effect_start((rgb_led_effect_type_t)effect_num, requested_cycles);

  cli_ok(cli, "");
}

static void prodtest_rgbled_effect_stop(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Stop ongoing RGB LED effect");

  // Disable automatic control of RGB LED in prodtest main loop
  prodtest_disable_rgbled_control();

  rgb_led_effect_stop();

  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "rgbled-set",
  .func = prodtest_rgbled_set,
  .info = "Set the RGB LED color",
  .args = "<r> <g> <b>"
);

PRODTEST_CLI_CMD(
  .name = "rgbled-effect-start",
  .func = prodtest_rgbled_effect_start,
  .info = "Start rgbled effect",
  .args = "<effect_num> <requested_cycles>"
);

PRODTEST_CLI_CMD(
  .name = "rgbled-effect-stop",
  .func = prodtest_rgbled_effect_stop,
  .info = "Stop rgbled effect",
  .args = ""
);


#endif  // USE_RGB_LED
