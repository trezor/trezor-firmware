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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "bootutils.h"
#include "common.h"
#include "system.h"
#include "systick.h"
#include "systimer.h"

systask_error_handler_t g_error_handler = NULL;

void system_init(systask_error_handler_t error_handler) {
  g_error_handler = error_handler;
  systick_init();
  systimer_init();
}

void system_exit(int exitcode) {
  if (g_error_handler != NULL) {
    systask_postmortem_t pminfo = {0};

    pminfo.reason = TASK_TERM_REASON_EXIT;
    pminfo.exit.code = exitcode;

    if (g_error_handler != NULL) {
      g_error_handler(&pminfo);
    }
  }

  secure_shutdown();
}

void system_exit_error_ex(const char* title, size_t title_len,
                          const char* message, size_t message_len,
                          const char* footer, size_t footer_len) {
  fprintf(stderr, "ERROR: %s\n", message);
  fflush(stderr);

  if (g_error_handler != NULL) {
    systask_postmortem_t pminfo = {0};
    size_t len;

    pminfo.reason = TASK_TERM_REASON_ERROR;

    len = MIN(title_len, sizeof(pminfo.error.title) - 1);
    strncpy(pminfo.error.title, title, len);

    len = MIN(message_len, sizeof(pminfo.error.message) - 1);
    strncpy(pminfo.error.message, message, len);

    len = MIN(footer_len, sizeof(pminfo.error.footer) - 1);
    strncpy(pminfo.error.footer, footer, len);

    if (g_error_handler != NULL) {
      g_error_handler(&pminfo);
    }
  }

  secure_shutdown();
}

void system_exit_error(const char* title, const char* message,
                       const char* footer) {
  size_t title_len = title != NULL ? strlen(title) : 0;
  size_t message_len = message != NULL ? strlen(message) : 0;
  size_t footer_len = footer != NULL ? strlen(footer) : 0;

  system_exit_error_ex(title, title_len, message, message_len, footer,
                       footer_len);
}

void system_exit_fatal_ex(const char* message, size_t message_len,
                          const char* file, size_t file_len, int line) {
  fprintf(stderr, "ERROR: %s\n", message);
  if (file) {
    fprintf(stderr, "FILE: %s:%d\n", file, line);
  }
  fflush(stderr);

  if (g_error_handler != NULL) {
    systask_postmortem_t pminfo = {0};
    size_t len;

    pminfo.reason = TASK_TERM_REASON_FATAL;

    len = MIN(message_len, sizeof(pminfo.fatal.expr) - 1);
    strncpy(pminfo.fatal.file, file, len);

    len = MIN(file_len, sizeof(pminfo.fatal.file) - 1);
    strncpy(pminfo.fatal.expr, message, len);

    pminfo.fatal.line = line;

    if (g_error_handler != NULL) {
      g_error_handler(&pminfo);
    }
  }

  secure_shutdown();
}

void system_exit_fatal(const char* message, const char* file, int line) {
  size_t message_len = message != NULL ? strlen(message) : 0;
  size_t file_len = file != NULL ? strlen(file) : 0;
  system_exit_fatal_ex(message, message_len, file, file_len, line);
}

const char* system_fault_message(const system_fault_t* fault) {
  // Not used in simulator
  return "(FAULT)";
}

void system_emergency_rescue(systask_error_handler_t error_handler,
                             const systask_postmortem_t* pminfo) {
  error_handler(pminfo);

  // We should never reach this point
  exit(0);
}
