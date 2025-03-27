#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <rtl/mini_printf.h>

#include <ctype.h>
#include <stdarg.h>

#define ESC_COLOR_GREEN "\e[32m"
#define ESC_COLOR_RED "\e[31m"
#define ESC_COLOR_GRAY "\e[37m"
#define ESC_COLOR_RESET "\e[39m"

bool cli_init(cli_t* cli, cli_read_cb_t read, cli_write_cb_t write,
              void* callback_context) {
  memset(cli, 0, sizeof(cli_t));
  cli->read = read;
  cli->write = write;
  cli->callback_context = callback_context;

  return true;
}

void cli_set_commands(cli_t* cli, const cli_command_t* cmd_array,
                      size_t cmd_count) {
  cli->cmd_array = cmd_array;
  cli->cmd_count = cmd_count;
}

static void cli_vprintf(cli_t* cli, const char* format, va_list args) {
  char buffer[CLI_LINE_BUFFER_SIZE];
  mini_vsnprintf(buffer, sizeof(buffer), format, args);
  cli->write(cli->callback_context, buffer, strlen(buffer));
}

static void cli_printf(cli_t* cli, const char* format, ...) {
  va_list args;
  va_start(args, format);
  cli_vprintf(cli, format, args);
  va_end(args);
}

void cli_vtrace(cli_t* cli, const char* format, va_list args) {
  if (cli->interactive) {
    cli_printf(cli, ESC_COLOR_GRAY);
  }

  cli_printf(cli, "#");

  if (cli->interactive) {
    cli_printf(cli, ESC_COLOR_RESET);
  }

  if (format != NULL && format[0] != '\0') {
    // Print the formatted message
    cli_printf(cli, " ");
    cli_vprintf(cli, format, args);
  }

  cli_printf(cli, "\r\n");
}

void cli_trace(cli_t* cli, const char* format, ...) {
  va_list args;
  va_start(args, format);
  cli_vtrace(cli, format, args);
  va_end(args);
}

void cli_ok(cli_t* cli, const char* format, ...) {
  va_list args;

  if (cli->interactive) {
    cli_printf(cli, ESC_COLOR_GREEN);
  }

  cli_printf(cli, "OK");

  if (cli->interactive) {
    cli_printf(cli, ESC_COLOR_RESET);
  }

  if (format != NULL && format[0] != '\0') {
    // Print the formatted message
    cli_printf(cli, " ");
    va_start(args, format);
    cli_vprintf(cli, format, args);
    va_end(args);
  }
  cli_printf(cli, "\r\n");

  cli->final_status = true;
}

// Write OK response with hex-encoded data
void cli_ok_hexdata(cli_t* cli, const void* data, size_t size) {
  if (cli->interactive) {
    cli_printf(cli, ESC_COLOR_GREEN);
  }

  cli_printf(cli, "OK");

  if (cli->interactive) {
    cli_printf(cli, ESC_COLOR_RESET);
  }

  if (size > 0) {
    cli_printf(cli, " ");
    for (size_t i = 0; i < size; i++) {
      cli_printf(cli, "%02X", ((uint8_t*)data)[i]);
    }
  }
  cli_printf(cli, "\r\n");

  cli->final_status = true;
}

static void cli_verror(cli_t* cli, const char* code, const char* format,
                       va_list args) {
  if (cli->interactive) {
    cli_printf(cli, ESC_COLOR_RED);
  }

  cli_printf(cli, "ERROR");

  if (cli->interactive) {
    cli_printf(cli, ESC_COLOR_RESET);
  }

  cli_printf(cli, " %s", code);

  if (format != NULL && format[0] != '\0') {
    cli_printf(cli, " \"");
    // Print the formatted message
    cli_vprintf(cli, format, args);
    cli_printf(cli, "\"");
  }

  cli_printf(cli, "\r\n");

  cli->final_status = true;
}

void cli_error(cli_t* cli, const char* code, const char* format, ...) {
  va_list args;
  va_start(args, format);
  cli_verror(cli, code, format, args);
  va_end(args);
}

void cli_error_arg(cli_t* cli, const char* format, ...) {
  if (cli->interactive && cli->current_cmd != NULL) {
    const cli_command_t* cmd = cli->current_cmd;
    if (cmd->args != NULL) {
      cli_trace(cli, "USAGE: %s %s", cmd->name, cmd->args);
    } else {
      cli_trace(cli, "USAGE: %s", cmd->name);
    }
  }

  va_list args;
  va_start(args, format);
  cli_verror(cli, CLI_ERROR_INVALID_ARG, format, args);
  va_end(args);
}

void cli_error_arg_count(cli_t* cli) {
  cli_error_arg(cli, "Unexpected trailing input.");
}

void cli_progress(cli_t* cli, const char* format, ...) {
  va_list args;
  va_start(args, format);

  cli_printf(cli, "PROGRESS");

  if (format != NULL && format[0] != '\0') {
    cli_printf(cli, " ");
    // Print the formatted message
    cli_vprintf(cli, format, args);
  }

  cli_printf(cli, "\r\n");

  va_end(args);
}

void cli_abort(cli_t* cli) { cli->aborted = true; }

bool cli_aborted(cli_t* cli) { return cli->aborted; }

// Finds a command record by name
//
// Returns NULL if the command is not found
static const cli_command_t* cli_find_command(cli_t* cli, const char* cmd) {
  for (size_t i = 0; i < cli->cmd_count; i++) {
    if (strcmp(cmd, cli->cmd_array[i].name) == 0) {
      return &cli->cmd_array[i];
    }
  }

  return NULL;
}

#define INDEX_ADD(index, offset) \
  (((index) + CLI_HISTORY_DEPTH + (offset)) % CLI_HISTORY_DEPTH)

static void cli_history_add(cli_t* cli, const char* line) {
  size_t line_len = strlen(line);
  if (line_len == 0 || line_len >= CLI_HISTORY_LINE_SIZE) {
    // Skip empty or too long lines
    return;
  }
  for (int i = 0; i < CLI_HISTORY_DEPTH; i++) {
    if (strcmp(cli->history[i], line) == 0) {
      // Duplicate line => Move it to the top
      for (; i != INDEX_ADD(cli->history_head, -1); i = INDEX_ADD(i, 1)) {
        strcpy(cli->history[i], cli->history[INDEX_ADD(i, 1)]);
      }
      strcpy(cli->history[i], line);
      return;
    }
  }

  // Add the new line to the history
  strcpy(cli->history[cli->history_head], line);
  cli->history_head = (cli->history_head + 1) % CLI_HISTORY_DEPTH;
}

// Searches the history for the previous command that starts with the prefix
// provided in the `line` buffer.
//
// `idx` is the index of the current command in the history
//
// Returns NULL if there are no more commands
static const char* cli_history_rev(cli_t* cli, int* idx, char* line,
                                   int prefix) {
  for (int i = *idx + 1; i <= CLI_HISTORY_DEPTH; i++) {
    const char* hist_line = cli->history[INDEX_ADD(cli->history_head, -i)];
    if (*hist_line == '\0') break;
    if (strlen(hist_line) >= prefix && strncmp(hist_line, line, prefix) == 0) {
      *idx = i;
      return hist_line;
    }
  }
  return NULL;
}

// Searches the history for the next command that starts with the prefix
// provided in the `line` buffer.
//
// `idx` is the index of the current command in the history
//
// Returns NULL if there are no more commands
static const char* cli_history_fwd(cli_t* cli, int* idx, char* line,
                                   int prefix) {
  for (int i = *idx - 1; i > 0; i--) {
    const char* hist_line = cli->history[INDEX_ADD(cli->history_head, -i)];
    if (strlen(hist_line) >= prefix && strncmp(hist_line, line, prefix) == 0) {
      *idx = i;
      return hist_line;
    }
  }
  *idx = 0;
  return NULL;
}

#define ESC_SEQ(ch) (0x200 + (ch))

// Reads a character from the console input and return it.
// Comple escape sequences translates into ESC_SEQ values
//   - ESC[<letter> => ESC_SEQ(letter),   e.g. ESC[A => ESC_SEQ('A')
//   - ESC[<number>~ => ESC_SEQ(number) , e.g. ESC[3~ => ESC_SEQ(3)
static int cli_readch(cli_t* cli) {
  int esc_len = 0;   // >0 if we are in the middle of an escape sequence
  int esc_code = 0;  // numeric code of the escape sequence

  for (;;) {
    char ch;
    size_t len = cli->read(cli->callback_context, &ch, 1);

    if (len != 1) {
      return 0;
    }

    if (ch == '\e') {
      // Escape sequence start
      esc_len = 1;
    } else if (esc_len == 1) {
      if (ch == '\e') {
        return 'e';
      } else if (ch == '[') {
        // Control sequence introducer
        esc_len = 2;
        esc_code = 0;
      } else {
        esc_len = 0;
      }
    } else if (esc_len == 2 && ch >= 'A' && ch <= 'Z') {
      // XTERM sequences - ESC[<letter>
      return ESC_SEQ(ch);
    } else if (esc_len >= 2 && ch >= '0' && ch <= '9') {
      // VT sequences - ESC[<number>~
      esc_code = esc_code * 10 + (ch - '0');
      esc_len++;
    } else if (esc_len >= 3 && ch == '~') {
      // End of VT sequence
      return ESC_SEQ(esc_code);
    } else if (esc_len >= 3) {
      // Invalid VT sequence
      esc_len = 0;
    } else {
      // Non-escape character
      return ch;
    }
  }
}

// Finds the next character that can be used for autocomplete.
// Returns '\0' if there are no more characters.
static char cli_autocomplete(cli_t* cli, const char* prefix) {
  char next_char = '\0';
  size_t prefix_len = strlen(prefix);
  for (size_t i = 0; i < cli->cmd_count; i++) {
    const char* cmd = cli->cmd_array[i].name;
    if (cstr_starts_with(cmd, prefix)) {
      char ch = cmd[prefix_len];
      if (next_char == '\0') {
        next_char = ch;
      } else if (ch != next_char) {
        return '\0';
      }
    }
  }
  return next_char;
}

// Processes a received character
//
// Returns 1 if the input line is complete,
// returns 0 if more characters are needed,
// returns negative value if the input line is too long
static int cli_process_char(cli_t* cli, int ch) {
  char* buf = cli->line_buffer;

  switch (ch) {
    case ESC_SEQ('A'):  // ESC[A
      // Up arrow - search history backwards
      if (cli->hist_idx == 0) {
        cli->hist_prefix = cli->line_len;
      }
      const char* hist_line =
          cli_history_rev(cli, &cli->hist_idx, buf, cli->hist_prefix);
      if (hist_line != NULL) {
        if (cli->line_cursor > 0) {
          // Move the cursor to the beginning of the line
          cli_printf(cli, "\e[%dD", cli->line_cursor);
        }
        // Replace original text
        strcpy(buf, hist_line);
        cli->line_len = cli->line_cursor = strlen(buf);
        cli_printf(cli, "%s\e[K", buf);
      }
      return 0;

    case ESC_SEQ('B'):  // ESC[B
      // Down arrow - search history forwards
      if (cli->hist_idx > 0) {
        const char* hist_line =
            cli_history_fwd(cli, &cli->hist_idx, buf, cli->hist_prefix);
        if (hist_line != NULL) {
          if (cli->line_cursor > 0) {
            // Move the cursor to the beginning of the line
            cli_printf(cli, "\e[%dD", cli->line_cursor);
          }
          // Replace original text
          strcpy(buf, hist_line);
          cli->line_len = cli->line_cursor = strlen(buf);
          cli_printf(cli, "%s\e[K", buf);
        } else {
          if (cli->line_cursor > cli->hist_prefix) {
            cli_printf(cli, "\e[%dD", cli->line_cursor - cli->hist_prefix);
          }
          cli_printf(cli, "\e[K");
          cli->line_len = cli->line_cursor = cli->hist_prefix;
          buf[cli->line_len] = '\0';
        }
      }
      return 0;
  }

  // Reset the history index, if the user types something else
  cli->hist_idx = 0;

  switch (ch) {
    case ESC_SEQ('C'):  // ESC[C
      // Right arrow
      if (cli->line_cursor < cli->line_len) {
        if (cli->interactive) {
          cli_printf(cli, "\e[C");
        }
        cli->line_cursor++;
      }
      break;

    case ESC_SEQ('D'):  // ESC[D
      // Left arrow
      if (cli->line_cursor > 0) {
        if (cli->interactive) {
          cli_printf(cli, "\e[D");
        }
        cli->line_cursor--;
      }
      break;

    case '\b':
    case 0x7F:
      // backspace => delete last character
      if (cli->line_cursor == 0) break;
      if (cli->interactive) {
        // Move the cursor left
        cli_printf(cli, "\e[D");
      }
      --cli->line_cursor;
      // do not break, fall through

    case ESC_SEQ(3):  // ESC[3~
      // Delete
      if (cli->line_cursor < cli->line_len) {
        // Delete the character at the cursor
        memmove(&buf[cli->line_cursor], &buf[cli->line_cursor + 1],
                cli->line_len - cli->line_cursor);
        --cli->line_len;
        if (cli->interactive) {
          // Print the rest of the line and move the cursor back
          cli_printf(cli, "%s \b", &buf[cli->line_cursor]);
          if (cli->line_cursor < cli->line_len) {
            cli_printf(cli, "\e[%dD", cli->line_len - cli->line_cursor);
          }
        }
      }
      break;

    case '\r':
    case '\n':
      // end of line
      if (cli->interactive) {
        cli_printf(cli, "\r\n");
      }
      if (cli->line_len < CLI_LINE_BUFFER_SIZE) {
        return 1;
      }
      return -1;

    case '\t':
      // tab => autocomplete
      if (cli->interactive && cli->line_len == cli->line_cursor) {
        char ch;
        while ((ch = cli_autocomplete(cli, buf)) != '\0') {
          if (cli->line_len < CLI_LINE_BUFFER_SIZE - 1) {
            cli_printf(cli, "%c", ch);
            buf[cli->line_len++] = ch;
            buf[cli->line_len] = '\0';
            cli->line_cursor++;
          }
        }
      }
      break;

    default:
      if (ch >= 0x20 && ch <= 0x7E) {
        // Printable character
        if (cli->line_len < CLI_LINE_BUFFER_SIZE - 1) {
          // Insert the character at the cursor
          ++cli->line_len;
          memmove(&buf[cli->line_cursor + 1], &buf[cli->line_cursor],
                  cli->line_len - cli->line_cursor);
          buf[cli->line_cursor] = ch;
          // Print new character and the rest of the line
          if (cli->interactive) {
            cli_printf(cli, "%s", &buf[cli->line_cursor]);
          }
          ++cli->line_cursor;
          if (cli->interactive && cli->line_cursor < cli->line_len) {
            // Move the cursor back
            cli_printf(cli, "\e[%dD", cli->line_len - cli->line_cursor);
          }
        }
      }
  }
  return 0;
}

static void cli_clear_line(cli_t* cli) {
  cli->line_len = 0;
  cli->line_cursor = 0;
  cli->hist_idx = 0;
  cli->hist_prefix = 0;
  memset(cli->line_buffer, 0, sizeof(cli->line_buffer));
}

// Splits the command line into arguments
// Returns false if there are too many arguments
static const char* cstr_token(char** str) {
  char* p = *str;
  // Skip leading whitespace
  p = (char*)cstr_skip_whitespace(p);
  // Start of token
  const char* token = p;
  // Find the end of the token
  while (*p != '\0' && !isspace((unsigned char)*p)) {
    ++p;
  }
  // Terminate the token
  if (*p != '\0') {
    *p++ = '\0';
  }
  *str = p;
  return token;
}

static bool cli_split_args(cli_t* cli) {
  char* buf = cli->line_buffer;

  cli->cmd_name = cstr_token(&buf);
  cli->args_count = 0;

  while (*buf != '\0' && cli->args_count < CLI_MAX_ARGS) {
    const char* arg = cstr_token(&buf);
    if (*arg != '\0') {
      cli->args[cli->args_count++] = arg;
    }
  }

  return *cstr_skip_whitespace(buf) == '\0';
}

static void cli_process_command(cli_t* cli, const cli_command_t* cmd) {
  cli->current_cmd = cmd;
  cli->final_status = false;
  cli->aborted = false;

  // Call the command handler
  cmd->func(cli);

  if (!cli->final_status) {
    // Command handler hasn't sent final status
    if (cli->aborted) {
      cli_error(cli, CLI_ERROR_ABORT, "");
    } else {
      cli_error(cli, CLI_ERROR_FATAL,
                "Command handler didn't finish properly.");
    }
  } else {
    // Finalize the last command with an empty line
    cli_printf(cli, "\r\n");
  }
}

void cli_process_io(cli_t* cli) {
  int res;
  do {
    int ch = cli_readch(cli);
    if (ch == 0) {
      return;
    }
    res = cli_process_char(cli, ch);
  } while (res == 0);

  if (res < 0) {
    cli_error(cli, CLI_ERROR_FATAL, "Input line too long.");
    goto cleanup;
  }

  cli_history_add(cli, cli->line_buffer);

  // Split command line into arguments
  if (!cli_split_args(cli)) {
    cli_error(cli, CLI_ERROR_FATAL, "Too many arguments.");
    goto cleanup;
  }

  // Empty line?
  if (*cli->cmd_name == '\0') {
    // Switch to interactive mode if two empty lines are entered
    if (++cli->empty_lines >= 2 && !cli->interactive) {
      cli->interactive = true;
      // Print the welcome message
      const cli_command_t* cmd = cli_find_command(cli, "$intro");
      if (cmd != NULL) {
        cmd->func(cli);
      }
    }
    goto cleanup;
  }
  cli->empty_lines = 0;

  // Quit interactive mode on `.+ENTER`
  if ((strcmp(cli->cmd_name, ".") == 0)) {
    if (cli->interactive) {
      cli->interactive = false;
      cli_trace(cli, "Exiting interactive mode...");
    }
    goto cleanup;
  }

  // Find the command handler
  const cli_command_t* cmd = cli_find_command(cli, cli->cmd_name);

  if (cmd == NULL) {
    cli_error(cli, CLI_ERROR_INVALID_CMD, "Invalid command '%s', try 'help'.",
              cli->cmd_name);
    goto cleanup;
  }

  cli_process_command(cli, cmd);

cleanup:
  if (cli->interactive) {
    // Print the prompt
    cli_printf(cli, "> ");
  }
  cli_clear_line(cli);
}

// Return position of the argument with the given name in
// the command definition.
//
// Returns -1 if the argument is not present.
static int find_arg(const cli_command_t* cmd, const char* name) {
  if (cmd->args == NULL) {
    return -1;
  }

  const char* p = cmd->args;
  int index = 0;

  while (*p != '\0') {
    // Skip '<' or '[>'
    while (*p != '\0' && (*p == ' ' || *p == '<' || *p == '[')) {
      p++;
    }

    // Extract argument name
    const char* s = p;
    while (*p != '\0' && (*p != '>' && *p != ']')) {
      p++;
    }

    if (strlen(name) == (p - s) && strncmp(s, name, p - s) == 0) {
      return index;
    }

    // Skip ']' or '>'
    while (*p != '\0' && (*p == ']' || *p == '>')) {
      p++;
    }

    index++;
  }

  return -1;
}

size_t cli_arg_count(cli_t* cli) { return cli->args_count; }

bool cli_has_nth_arg(cli_t* cli, int n) {
  return n >= 0 && n < cli->args_count;
}

bool cli_has_arg(cli_t* cli, const char* name) {
  return cli_has_nth_arg(cli, find_arg(cli->current_cmd, name));
}

const char* cli_nth_arg(cli_t* cli, int n) {
  if (n >= 0 && n < cli->args_count) {
    return cli->args[n];
  } else {
    return "";
  }
}

const char* cli_arg(cli_t* cli, const char* name) {
  return cli_nth_arg(cli, find_arg(cli->current_cmd, name));
}

bool cli_nth_arg_uint32(cli_t* cli, int n, uint32_t* result) {
  const char* arg = cli_nth_arg(cli, n);
  return cstr_parse_uint32(arg, 0, result);
}

bool cli_arg_uint32(cli_t* cli, const char* name, uint32_t* result) {
  const char* arg = cli_arg(cli, name);
  return cstr_parse_uint32(arg, 0, result);
}

bool cli_arg_hex(cli_t* cli, const char* name, uint8_t* dst, size_t dst_len,
                 size_t* bytes_written) {
  const char* arg = cli_arg(cli, name);
  return cstr_decode_hex(arg, dst, dst_len, bytes_written);
}
