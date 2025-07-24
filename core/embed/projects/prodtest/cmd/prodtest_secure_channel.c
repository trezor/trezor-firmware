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

#include <rtl/cli.h>

#include "secure_channel.h"

static void prodtest_secure_channel_handshake_1(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t output[SECURE_CHANNEL_OUTPUT_SIZE] = {0};

  if (!secure_channel_handshake_1(output)) {
    cli_error(cli, CLI_ERROR, "`secure_channel_handshake_1()` failed.");
    return;
  }

  cli_ok_hexdata(cli, output, sizeof(output));
}

static void prodtest_secure_channel_handshake_2(cli_t* cli) {
  if (cli_arg_count(cli) != 1) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t input[SECURE_CHANNEL_INPUT_SIZE] = {0};
  size_t input_length = 0;
  if (!cli_arg_hex(cli, "hex-data", input, sizeof(input), &input_length)) {
    if (input_length == sizeof(input)) {
      cli_error(cli, CLI_ERROR, "Input too long.");
    } else {
      cli_error(cli, CLI_ERROR, "Hexadecimal decoding error.");
    }
    return;
  }
  if (input_length != SECURE_CHANNEL_INPUT_SIZE) {
    cli_error(cli, CLI_ERROR, "Unexpected input length. Expecting %d bytes.",
              (int)SECURE_CHANNEL_INPUT_SIZE);
  }

  if (!secure_channel_handshake_2(input)) {
    // Either `secure_channel_handshake_1()` has not been called or the keys do
    // not match.
    cli_error(cli, CLI_ERROR, "`secure_channel_handshake_2()` failed.");
  }

  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "secure-channel-handshake-1",
  .func = prodtest_secure_channel_handshake_1,
  .info = "Create the first message of the secure channel handshake",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "secure-channel-handshake-2",
  .func = prodtest_secure_channel_handshake_2,
  .info = "Handle the second message of the secure channel handshake",
  .args = "<hex-data>"
);
