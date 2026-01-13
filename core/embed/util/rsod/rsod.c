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

#include <gfx/terminal.h>
#include <io/display.h>
#include <sys/bootutils.h>
#include <sys/system.h>
#include <util/rsod.h>

#include <rtl/strutils.h>

#ifdef SCM_REVISION_INIT
#include <rtl/scm_revision.h>
#endif

#define RSOD_DEFAULT_TITLE "Internal error";
#define RSOD_DEFAULT_MESSAGE "Unspecified";
#define RSOD_DEFAULT_FOOTER "Please visit trezor.io/rsod";
#define RSOD_EXIT_MESSAGE "Exit "  // followed by exit code

#ifdef KERNEL_MODE

#define RSOD_FG_COLOR COLOR_WHITE

#ifdef USE_RGB_COLORS
#define RSOD_BG_COLOR gfx_color_rgb(0x7F, 0x00, 0x00)
#else
#define RSOD_BG_COLOR COLOR_BLACK
#endif

void rsod_terminal(const systask_postmortem_t* pminfo) {
  display_set_orientation(0);
  term_set_color(RSOD_FG_COLOR, RSOD_BG_COLOR);

  const char* title = RSOD_DEFAULT_TITLE;
  const char* message = RSOD_DEFAULT_MESSAGE;
  const char* footer = RSOD_DEFAULT_FOOTER;
  const char* file = NULL;
  char message_buf[32] = "";
  int line = 0;

  switch (pminfo->reason) {
    case TASK_TERM_REASON_EXIT:
      cstr_append(message_buf, sizeof(message_buf), RSOD_EXIT_MESSAGE);
      cstr_append_int32(message_buf, sizeof(message_buf), pminfo->exit.code);
      message = message_buf;
      break;
    case TASK_TERM_REASON_ERROR:
      if (pminfo->error.title[0] != '\0') {
        title = pminfo->error.title;
      }
      if (pminfo->error.message[0] != '\0') {
        message = pminfo->error.message;
      }
      if (pminfo->error.footer[0] != '\0') {
        footer = pminfo->error.footer;
      }
      break;
    case TASK_TERM_REASON_FATAL:
      message = pminfo->fatal.expr;
      file = pminfo->fatal.file;
      line = pminfo->fatal.line;
      break;
    case TASK_TERM_REASON_FAULT:
      message = system_fault_message(&pminfo->fault);
      break;
  }

  if (title != NULL) {
    term_print(title);
    term_print("\n");
  }

  if (message != NULL) {
    term_print("msg : ");
    term_print(message);
    term_print("\n");
  }

  if (file) {
    term_print("file: ");
    term_print(file);
    term_print(":");
    term_print_int32(line);
    term_print("\n");
  }

#ifdef SCM_REVISION_INIT
  char rev[10 + 1];
  cstr_encode_hex(rev, sizeof(rev), SCM_REVISION, (sizeof(rev) - 1) / 2);
  term_print("rev : ");
  term_print(rev);
#endif

  if (footer != NULL) {
    term_print("\n");
    term_print(footer);
    term_print("\n");
  }

  display_set_backlight(255);
}

#endif  // KERNEL_MODE

#ifdef FANCY_FATAL_ERROR

#include "rust_ui_common.h"

void rsod_gui(const systask_postmortem_t* pminfo) {
  const char* title = RSOD_DEFAULT_TITLE;
  const char* message = RSOD_DEFAULT_MESSAGE;
  const char* footer = RSOD_DEFAULT_FOOTER;
  char message_buf[128] = "";

  switch (pminfo->reason) {
    case TASK_TERM_REASON_EXIT:
      cstr_append(message_buf, sizeof(message_buf), RSOD_EXIT_MESSAGE);
      cstr_append_int32(message_buf, sizeof(message_buf), pminfo->exit.code);
      message = message_buf;
      break;

    case TASK_TERM_REASON_ERROR:
      if (pminfo->error.title[0] != '\0') {
        title = pminfo->error.title;
      }
      if (pminfo->error.message[0] != '\0') {
        message = pminfo->error.message;
      }
      if (pminfo->error.footer[0] != '\0') {
        footer = pminfo->error.footer;
      }
      break;

    case TASK_TERM_REASON_FATAL:
      message = pminfo->fatal.expr;
      if (message[0] == '\0') {
        cstr_append(message_buf, sizeof(message_buf), pminfo->fatal.file);
        cstr_append(message_buf, sizeof(message_buf), ":");
        cstr_append_int32(message_buf, sizeof(message_buf), pminfo->fatal.line);
      } else {
        cstr_append(message_buf, sizeof(message_buf), message);
        cstr_append(message_buf, sizeof(message_buf), "\n");
        cstr_append(message_buf, sizeof(message_buf), pminfo->fatal.file);
        cstr_append(message_buf, sizeof(message_buf), ":");
        cstr_append_int32(message_buf, sizeof(message_buf), pminfo->fatal.line);
      }
      message = message_buf;
      break;

    case TASK_TERM_REASON_FAULT:
      message = system_fault_message(&pminfo->fault);
      break;
  }

  // Render the RSOD in Rust
  display_rsod_rust(title, message, footer);
}

#endif  // FANCY_FATAL_ERROR

#ifdef KERNEL_MODE

// Initializes system in emergency mode and shows RSOD
static void init_and_show_rsod(const systask_postmortem_t* pminfo) {
  // Initialize the system's core services
  // Pass NULL as error handler => if the system crashes in this routine
  // we will not try to re-enter emergency mode again and reboot directly.
  system_init(NULL);

  // Initialize necessary drivers
  display_init(DISPLAY_RESET_CONTENT);

#ifdef FANCY_FATAL_ERROR
  // Show the RSOD using Rust GUI
  rsod_gui(pminfo);
#else
  // Show the RSOD using terminal
  rsod_terminal(pminfo);
#endif

  // Reboots or halts (if RSOD_INFINITE_LOOP is defined)
  reboot_or_halt_after_rsod();
}

// Universal panic handler
// (may be called from interrupt context)
void rsod_panic_handler(const systask_postmortem_t* pminfo) {
  // Since the system state is unreliable, enter emergency mode
  // and show the RSOD.
  system_emergency_rescue(&init_and_show_rsod, pminfo);
  // The previous function call never returns
}

#endif  // KERNEL_MODE
