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

#include "commands.h"

#ifdef TREZOR_EMULATOR
#include <stdlib.h>
cli_command_t *_cmd_list;
size_t _cmd_count;

void register_cli_command(const cli_command_t *cmd) {
  _cmd_list = realloc(_cmd_list, sizeof(cli_command_t) * (_cmd_count + 1));
  _cmd_list[_cmd_count++] = *cmd;
}

#endif

const cli_command_t *commands_get_ptr(void) {
#ifdef TREZOR_EMULATOR
  return _cmd_list;

#else
  extern cli_command_t _prodtest_cli_cmd_section_start;

  return &_prodtest_cli_cmd_section_start;
#endif
}

size_t commands_count(void) {
#ifdef TREZOR_EMULATOR
  return _cmd_count;

#else
  extern cli_command_t _prodtest_cli_cmd_section_start;
  extern cli_command_t _prodtest_cli_cmd_section_end;

  return &_prodtest_cli_cmd_section_end - &_prodtest_cli_cmd_section_start;
#endif
}
