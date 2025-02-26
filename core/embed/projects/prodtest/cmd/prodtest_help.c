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

#include <trezor_rtl.h>

#include <rtl/cli.h>

static void prodtest_help(cli_t* cli) {
  const char* prefix = cli_arg(cli, "prefix");
  size_t prefix_len = strlen(prefix);

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  if (prefix_len > 0) {
    cli_trace(cli, "Available commands:");
  } else {
    cli_trace(cli, "Available commands (filtered):");
  }

  extern cli_command_t _prodtest_cli_cmd_section_start;
  extern cli_command_t _prodtest_cli_cmd_section_end;

  cli_command_t* cmd = &_prodtest_cli_cmd_section_start;

  while (cmd < &_prodtest_cli_cmd_section_end) {
    if (cmd->name[0] != '$' && strncmp(cmd->name, prefix, prefix_len) == 0) {
      cli_trace(cli, " %s - %s", cmd->name, cmd->info);
    }
    cmd++;
  }

  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "help",
  .func = prodtest_help,
  .info = "Display the list of available commands",
  .args = "[<prefix>]"
);
