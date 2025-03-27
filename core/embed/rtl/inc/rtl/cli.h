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

#include <trezor_types.h>

#include <rtl/strutils.h>

typedef struct cli cli_t;

// Maximum length of command line input (including command, arguments)
#define CLI_LINE_BUFFER_SIZE 4096
// Maximum number of command arguments + 1
#define CLI_MAX_ARGS 64

// Maximum length of command line in history buffer
// (lines longer than this limit are not recorder)
#define CLI_HISTORY_LINE_SIZE 256
// Depth of the history buffer
#define CLI_HISTORY_DEPTH 5

// Error codes
#define CLI_ERROR "error"  // unspecified error
#define CLI_ERROR_INVALID_CMD "invalid-cmd"
#define CLI_ERROR_INVALID_ARG "invalid-arg"
#define CLI_ERROR_ABORT "abort"
#define CLI_ERROR_FATAL "fatal"
#define CLI_ERROR_TIMEOUT "timeout"
#define CLI_ERROR_LOCKED "locked"
#define CLI_ERROR_NODATA "no-data"

// CLI command handler routine prototype
typedef void (*cli_cmd_handler_t)(cli_t* cli);

// Structure describing the registration record for a CLI command handler
typedef struct {
  // Command name
  const char* name;
  // Command handler
  cli_cmd_handler_t func;
  // Single line command description
  const char* info;
  // Arguments definition
  // "<mandatory-arg> [<optional-arg>] [--flag1 | --flag2]"
  // NOTE: optional args must be placed after mandatory args
  const char* args;
} cli_command_t;

#define CONCAT_INDIRECT(x, y) x##y
#define CONCAT(x, y) CONCAT_INDIRECT(x, y)

// Registers a command handler by placing its registration structure
// into a specially designated linker script section
#define PRODTEST_CLI_CMD(...)                                              \
  __attribute__((used,                                                     \
                 section(".prodtest_cli_cmd"))) static const cli_command_t \
      CONCAT(_cli_cmd_handler, __COUNTER__) = {__VA_ARGS__};

// Callback for writing characters to console output
typedef size_t (*cli_write_cb_t)(void* ctx, const char* buf, size_t len);
// Callback for reading characters from console input
typedef size_t (*cli_read_cb_t)(void* ctx, char* buf, size_t len);

struct cli {
  // I/O callbacks
  cli_read_cb_t read;
  cli_write_cb_t write;
  void* callback_context;

  // Registered command handlers
  const cli_command_t* cmd_array;
  size_t cmd_count;

  // Current line buffer
  char line_buffer[CLI_LINE_BUFFER_SIZE];
  // number of characters in the buffer (excluding '\0')
  int line_len;
  // cursor position in the buffer
  int line_cursor;
  // currently selected history entry
  int hist_idx;
  // prefix to search in the history
  int hist_prefix;

  // Command name (pointer to the line buffer)
  const char* cmd_name;
  // Number of parsed arguments
  size_t args_count;
  // Parsed arguments (pointers to the line buffer)
  const char* args[CLI_MAX_ARGS];
  // Currently processed command
  const cli_command_t* current_cmd;

  // Command history
  char history[CLI_HISTORY_DEPTH][CLI_HISTORY_LINE_SIZE];
  // History head index (the most recent command)
  int history_head;

  // Final status (OK/ERROR) was sent by the command handler
  bool final_status;
  // Interactive mode
  bool interactive;
  // Empty line counter
  int empty_lines;
  // Flag set by `cli_abort()` to indicate the command should
  // finish as soon as possible with an CLI_ERROR_ABORT
  volatile bool aborted;
};

// Initializes the command line structure
bool cli_init(cli_t* cli, cli_read_cb_t read, cli_write_cb_t write,
              void* callback_context);

// Registers the command handlers
void cli_set_commands(cli_t* cli, const cli_command_t* cmd_array,
                      size_t cmd_count);

// Process the newly received characters from the console input
void cli_process_io(cli_t* cli);

// Returne the number of arguments in the command line
size_t cli_arg_count(cli_t* cli);

// Returns the n-th argument from the command line.
//
// Indexing starts at 0, meaning the first argument is at index 0.
// Returns an empty string if the argument is not present.
const char* cli_nth_arg(cli_t* cli, int n);

// Returns the argument with the given name from the command line.
//
// Returns an empty string if the argument is not present.
const char* cli_arg(cli_t* cli, const char* name);

// Returns true if the n-th argument is present.
bool cli_has_nth_arg(cli_t* cli, int n);

// Returns true if the argument with the given name is present.
bool cli_has_arg(cli_t* cli, const char* name);

// Parses the argument with the given name as an unsigned 32-bit integer.
//
// The result is set only if the argument is present and can be parsed.
// Otherwise, the function returns false and the result is not modified.
bool cli_arg_uint32(cli_t* cli, const char* name, uint32_t* result);

// Parses the argument with the given name as a hexadecimal string.
//
// (see cstr_parse_hex() for details)
bool cli_arg_hex(cli_t* cli, const char* name, uint8_t* dst, size_t dst_len,
                 size_t* bytes_written);

// Writes a formatted trace string to the console. The formatted string is
// automatically prefixed with the "#" character and terminated with
// CR/LF characters.
void cli_trace(cli_t* cli, const char* format, ...);

// Writes a formatted OK response to the console. The formatted string is
// automatically prefixed with the "OK" string and terminated with CR/LF
// characters.
void cli_ok(cli_t* cli, const char* format, ...);

// Write OK response with hex-encoded data
void cli_ok_hexdata(cli_t* cli, const void* data, size_t size);

// Writes a formatted progress message to the console. The formatted string is
// automatically prefixed with the "PROGRESS" string and terminated with CR/LF
// characters.
void cli_progress(cli_t* cli, const char* format, ...);

// Writes a formatted error message to the console. The formatted string is
// automatically prefixed with the "ERROR" string and terminated with CR/LF
// characters.
void cli_error(cli_t* cli, const char* code, const char* format, ...);

// Writes a invalid argument error message to the console
// and prepends the error message with formatted trace.
void cli_error_arg(cli_t* cli, const char* format, ...);

// Writes an error message to the console indicating that the number of
// arguments is incorrect.
void cli_error_arg_count(cli_t* cli);

// Aborts the current CLI command processing
//
// Can also be called from interrupt context
void cli_abort(cli_t* cli);

// Returns true if `cli_abort()` was called
bool cli_aborted(cli_t* cli);
