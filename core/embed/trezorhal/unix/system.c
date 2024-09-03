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

    g_error_handler(&pminfo);
  }

  secure_shutdown();
}

void system_exit_error(const char* title, const char* message,
                       const char* footer) {
  fprintf(stderr, "ERROR: %s\n", message);
  fflush(stderr);

  if (g_error_handler != NULL) {
    systask_postmortem_t pminfo = {0};

    pminfo.reason = TASK_TERM_REASON_ERROR;

    strncpy(pminfo.error.title, title, sizeof(pminfo.error.title) - 1);
    pminfo.error.title[sizeof(pminfo.error.title) - 1] = '\0';

    strncpy(pminfo.error.message, message, sizeof(pminfo.error.message) - 1);
    pminfo.error.message[sizeof(pminfo.error.message) - 1] = '\0';

    strncpy(pminfo.error.footer, footer, sizeof(pminfo.error.footer) - 1);
    pminfo.error.footer[sizeof(pminfo.error.footer) - 1] = '\0';

    g_error_handler(&pminfo);
  }

  secure_shutdown();
}

void system_exit_fatal(const char* message, const char* file, int line) {
  fprintf(stderr, "ERROR: %s\n", message);
  if (file) {
    fprintf(stderr, "FILE: %s:%d\n", file, line);
  }
  fflush(stderr);

  if (g_error_handler != NULL) {
    systask_postmortem_t pminfo = {0};

    pminfo.reason = TASK_TERM_REASON_FATAL;

    strncpy(pminfo.fatal.file, file, sizeof(pminfo.fatal.file) - 1);
    pminfo.fatal.file[sizeof(pminfo.fatal.file) - 1] = '\0';

    strncpy(pminfo.fatal.expr, message, sizeof(pminfo.fatal.expr) - 1);
    pminfo.fatal.expr[sizeof(pminfo.fatal.expr) - 1] = '\0';

    pminfo.fatal.line = line;

    g_error_handler(&pminfo);
  }

  secure_shutdown();
}

const char* system_fault_message(const system_fault_t* fault) {
  // Not used  in simulator
  return "(FAULT)";
}

void system_emergency_rescue(systask_error_handler_t error_handler,
                             const systask_postmortem_t* pminfo) {
  error_handler(pminfo);

  // We should never reach this point
  exit(0);
}
