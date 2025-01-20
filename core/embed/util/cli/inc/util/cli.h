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

#pragma once

typedef struct cli cli_t;

// Maximum length of command line input (including command, arguments, and CRLF)
#define CLI_LINE_BUFFER_SIZE 2048

typedef enum {
  // Success
  CLI_OK,
  // Command in progress
  CLI_PROGRESS,
  // Test error (detail in formatted string)
  CLI_ERROR,
  // Invalid input arguments
  CLI_ERROR_ARG,
  // Fatal/unexpected error
  CLI_ERROR_FATAL,
  // Aborted by user
  CLI_ERROR_ABORTED

} cli_status_t;

// CLI command handler routine prototype
typedef void (*cli_command_handler_t)(cli_t* cli);

// Structure describing the registration record for a CLI command handler
typedef struct {
  const char* name;
  cli_command_handler_t func;
  const char* info;
} cli_command_record_t;

// Registers a command handler by placing its registration structure
// into a specially designated linker script section
#define PRODTEST_CLI_CMD(args)                                              \
  __attribute__((section(".mfgtest_handlers"))) static cli_command_record_t \
      cli_handler #__LINE__ = {args};

// Callback for writing characters to console output
typedef size_t (*cli_write_cb_t)(void* ctx, const uint8_t* buf, size_t len);
// Callback for reading characters from console input
typedef size_t (*cli_read_cb_t)(void* ctx, uint8_t* buf, size_t len);

struct cli {
  // I/O callbbacks
  cli_read_cb_t read;
  cli_write_cb_t write;
  void* callback_context;

  // Current line buffer
  char line[CLI_LINE_BUFFER_SIZE];
  // Arguments slice parsed from the current line
  slice_t args;

  // Last command status
  cli_status_t status;

  // Flag set by `cli_abort()` to indicate the command should
  // finish as soon as possible with an CLI_ERROR_ABORT
  bool aborted;
};

// Initializes the command line structure
bool cli_init(cli_t* cli, cli_read_cb_t read, cli_write_cb_t write,
              void* callback_context);

// Runs the CLI command loop with the given command handlers
void cli_loop(cli_t* cli, const cli_command_record_t* commands, size_t count);

// Reads the next line from the console
// (blocks until the LF character is received)
// void cli_readln(cli_t* cli);

// Returns a slice containing all command line arguments.
//
// Trailing CR/LF characters are removed.
slice_t cli_args(void);

// Returns the n-th argument from the command line.
//
// Arguments are separated by spaces. The first argument is at index 0.
// Returns an empty slice if the argument is not present.
slice_t cli_arg(int n);

// Writes a formatted trace string to the console. The formatted string is
// automatically prefixed with the "#" character and terminated with
// CR/LF characters.
void cli_trace(cli_t* cli, const char* format, ...);

// Writes a command response to the console. The formatted string is
// automatically prefixed with the status string and terminated
// with CR/LF characters.
void cli_write(cli_t* cli, cli_status_t status, const char* format, ...);

// Aborts the current CLI command processing
//
// Can also be called from interrupt context
void cli_abort(cli_t* cli);

// Returns true if `cli_abort()` was called
bool cli_aborted(cli_t* cli);
