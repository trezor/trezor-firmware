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

#include <rtl/printf.h>
#include <rtl/strutils.h>
#include <sys/dbg_console.h>
#include <sys/logging.h>
#include <sys/systick.h>

#ifndef TREZOR_EMULATOR
#include <sys/irq.h>
#endif

#include <stdarg.h>

#ifdef KERNEL_MODE

#define EOL_STRING "\r\n"
#define SYSLOG_MAX_FILTER_LEN 128

#define ESC_COLOR_NORMAL "\e[0m"
#define ESC_COLOR_SOURCE "\e[35m"
#define ESC_COLOR_ERR "\e[31m"
#define ESC_COLOR_WARN "\e[33m"
#define ESC_COLOR_INF "\e[36m"
#define ESC_COLOR_DBG "\e[32m"

typedef struct {
  // Current filter string
  char filter[SYSLOG_MAX_FILTER_LEN];
  // Not ended record
  bool eol_needed;
} syslog_t;

static syslog_t g_syslog;

static bool syslog_filter_match(const log_source_t* source, log_level_t level) {
  syslog_t* syslog = &g_syslog;

  const char* p = syslog->filter;

  // Start with inclusion of everything if the filter is empty
  // or starts with '-';
  bool included = (*p == '-' || *p == '\0');

  while (*p != '\0') {
    // Parse operation
    char op = *p++;
    if (op != '-' && op != '+') {
      // Error in filter format
      break;
    }

    // Parse log level threshold
    log_level_t threshold = op == '-' ? LOG_LEVEL_ERR : LOG_LEVEL_DBG;
    if (*p >= '1' && *p <= '4') {
      threshold = LOG_LEVEL_OFF + (uint8_t)(*p - '0');
      p++;
    }

    const char* s = source->name;
    const char* s_end = s + source->name_len;

    // Parse module name
    while (*p != '\0' && s < s_end && *p == *s) {
      p++;
      s++;
    }

    // Wildcard at the end?
    if (*p == '*') {
      p++;
      s = s_end;
    } else {
      // Skip remaining characters in module name
      while (*p != '\0' && *p != '-' && *p != '+') {
        p++;
      }
    }

    // Skip spaces
    while (*p == ' ') {
      p++;
    }

    // Module name matched?
    if (s == s_end && (*p == '+' || *p == '-' || *p == '\0')) {
      if (op == '-' && level >= threshold) {
        included = false;
      } else if (level <= threshold) {
        included = true;
      }
    }
  }

  return included;
}

static const char* log_level_str(log_level_t level) {
  switch (level) {
    case LOG_LEVEL_ERR:
      return ESC_COLOR_ERR "ERR" ESC_COLOR_NORMAL;
    case LOG_LEVEL_WARN:
      return ESC_COLOR_WARN "WRN" ESC_COLOR_NORMAL;
    case LOG_LEVEL_INF:
      return ESC_COLOR_INF "INF" ESC_COLOR_NORMAL;
    case LOG_LEVEL_DBG:
      return ESC_COLOR_DBG "DBG" ESC_COLOR_NORMAL;
    default:
      return "UNK";
  }
}

bool syslog_start_record(const log_source_t* source, log_level_t level) {
  syslog_t* syslog = &g_syslog;

  if (syslog_filter_match(source, level)) {
    // Prepare a record header
    uint32_t ticks = systick_ms();
    uint32_t seconds = ticks / 1000;
    uint32_t msec = ticks % 1000;
    const char* level_str = log_level_str(level);

#ifndef TREZOR_EMULATOR
    irq_key_t irq_key = irq_lock();
#endif

    const char* eol = syslog->eol_needed ? EOL_STRING : "";
    syslog->eol_needed = true;

#ifndef TREZOR_EMULATOR
    irq_unlock(irq_key);
#endif

    int name_len = (int)MIN(source->name_len, INT32_MAX);

    dbg_console_printf("%s%" PRIu32 ".%03" PRIu32 " " ESC_COLOR_SOURCE
                       "%*s" ESC_COLOR_NORMAL " %s ",
                       eol, seconds, msec, name_len, source->name, level_str);

    return true;
  } else {
    return false;
  }
}

ssize_t syslog_write_chunk(const char* text, size_t text_len, bool end_record) {
  syslog_t* syslog = &g_syslog;

  if (text_len > 0) {
#ifndef TREZOR_EMULATOR
    irq_key_t irq_key = irq_lock();
#endif
    syslog->eol_needed = true;
#ifndef TREZOR_EMULATOR
    irq_unlock(irq_key);
#endif
  }

  // Write text chunk
  ssize_t bytes_written = dbg_console_write(text, text_len);

  if (end_record && bytes_written == (ssize_t)text_len) {
    // Finish the record with a newline
    dbg_console_write(EOL_STRING, strlen(EOL_STRING));

#ifndef TREZOR_EMULATOR
    irq_key_t irq_key = irq_lock();
#endif
    syslog->eol_needed = false;
#ifndef TREZOR_EMULATOR
    irq_unlock(irq_key);
#endif
  }

  return bytes_written;
}

bool syslog_set_filter(const char* filter, size_t filter_len) {
  syslog_t* syslog = &g_syslog;

  // Filter string too long?
  if (filter_len > sizeof(syslog->filter) - 1) {
    return false;
  }

  // Locking interrutps here ensures that `syslog_start_record()`
  // potentially running in interrupt context does not read partial
  // filter string.

#ifndef TREZOR_EMULATOR
  irq_key_t irq_key = irq_lock();
#endif

  strncpy(syslog->filter, filter, filter_len);
  syslog->filter[filter_len] = '\0';

#ifndef TREZOR_EMULATOR
  irq_unlock(irq_key);
#endif

  return true;
}

#endif  // KERNEL_MODE

void syslog_vprintf(const log_source_t* source, log_level_t level,
                    const char* fmt, va_list args) {
  if (syslog_start_record(source, level)) {
    char msg[160];
    size_t msg_len = vsnprintf_(msg, sizeof(msg), fmt, args);
    syslog_write_chunk(msg, msg_len, true);
  }
}

void syslog_printf(const log_source_t* source, log_level_t level,
                   const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  syslog_vprintf(source, level, fmt, args);
  va_end(args);
}

void syslog_print_hex(const log_source_t* source, log_level_t level,
                      const char* prefix, const uint8_t* data,
                      size_t data_size) {
  if (syslog_start_record(source, level)) {
    syslog_write_chunk(prefix, strlen(prefix), data_size == 0);
    if (data_size > 0) {
      syslog_write_chunk(" ", 1, false);
    }
    for (size_t i = 0; i < data_size; i++) {
      char byte_str[3];
      cstr_encode_hex(byte_str, sizeof(byte_str), &data[i], sizeof(uint8_t));
      bool last_chunk = (i == data_size - 1);
      syslog_write_chunk(byte_str, strlen(byte_str), last_chunk);
    }
  }
}

#ifdef TREZOR_PRODTEST

#include <rtl/cli.h>

static void prodtest_set_log_filter(cli_t* cli) {
  const char* filter = cli_arg(cli, "filter");
  size_t filter_len = strlen(filter);

  if (filter_len == 0) {
    cli_error_arg(cli, "Expecting filter string.");
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  if (!syslog_set_filter(filter, filter_len)) {
    cli_error(cli, CLI_ERROR, "Failed to set log filter.");
  }

  cli_ok(cli, "");
}

PRODTEST_CLI_CMD(.name = "log-filter", .func = prodtest_set_log_filter,
                 .info = "Set logging filter", .args = "<filter>");

#endif  // TREZOR_PRODTEST
