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

#ifdef USE_BUTTON

#include <trezor_rtl.h>

#include <io/button.h>
#include <rtl/cli.h>
#include <sys/systick.h>

static void test_single_button(cli_t* cli, uint32_t timeout, button_t btn) {
  uint32_t expire_time = ticks_timeout(timeout);

  cli_trace(cli, "Waiting for the button press...");

  button_event_t btn_event = {0};
  while (!button_get_event(&btn_event) || (btn_event.button != btn) ||
         (btn_event.event_type != BTN_EVENT_DOWN)) {
    if (ticks_expired(expire_time)) {
      cli_error(cli, CLI_ERROR_TIMEOUT, "");
      return;
    }

    if (cli_aborted(cli)) {
      return;
    }
  }

  cli_trace(cli, "Waiting for the button release...");

  while (!button_get_event(&btn_event) || (btn_event.button != btn) ||
         (btn_event.event_type != BTN_EVENT_UP)) {
    if (ticks_expired(expire_time)) {
      cli_error(cli, CLI_ERROR_TIMEOUT, "");
      return;
    }

    if (cli_aborted(cli)) {
      return;
    }
  }

  cli_ok(cli, "");
}

static void test_button_combination(cli_t* cli, uint32_t timeout, button_t btn1,
                                    button_t btn2) {
  uint32_t expire_time = ticks_timeout(timeout);

  cli_trace(cli, "Waiting for button combination to be pressed...");

  while (true) {
    if (button_is_down(btn1) && button_is_down(btn2)) {
      break;
    } else if (ticks_expired(expire_time)) {
      cli_error(cli, CLI_ERROR_TIMEOUT, "");
      return;
    } else if (cli_aborted(cli)) {
      return;
    }
  }

  cli_trace(cli, "Waiting for buttons to be released...");

  while (true) {
    if (!button_is_down(btn1) && !button_is_down(btn2)) {
      break;
    } else if (ticks_expired(expire_time)) {
      cli_error(cli, CLI_ERROR_TIMEOUT, "");
      return;
    } else if (cli_aborted(cli)) {
      return;
    }
  }

  cli_ok(cli, "");
}

static void prodtest_button_test(cli_t* cli) {
  const char* button = cli_arg(cli, "button");
  int btn1 = -1;
  int btn2 = -1;

  if (strcmp(button, "left") == 0) {
    btn1 = BTN_LEFT;
  } else if (strcmp(button, "right") == 0) {
    btn1 = BTN_RIGHT;
  } else if (strcmp(button, "left+right") == 0) {
    btn1 = BTN_LEFT;
    btn2 = BTN_RIGHT;
  } else if (strcmp(button, "power") == 0) {
    btn1 = BTN_POWER;
  } else {
    cli_error_arg(cli,
                  "Expecting button name - left, right, left+right or power.");
    return;
  }

  uint32_t timeout = 0;

  if (!cli_arg_uint32(cli, "timeout", &timeout)) {
    cli_error_arg(cli, "Expecting timeout in milliseconds.");
    return;
  }

  if (cli_arg_count(cli) > 2) {
    cli_error_arg_count(cli);
    return;
  }

  if (btn2 >= 0) {
    test_button_combination(cli, timeout, btn1, btn2);
  } else {
    test_single_button(cli, timeout, btn1);
  }
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "button-test",
  .func = prodtest_button_test,
  .info = "Test the hardware buttons",
  .args = "<button> <timeout>"
);

#endif  // USE_BUTTON
