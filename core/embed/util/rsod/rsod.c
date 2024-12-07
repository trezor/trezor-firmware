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

#include <gfx/terminal.h>
#include <io/display.h>
#include <rtl/mini_printf.h>
#include <sys/bootutils.h>
#include <sys/system.h>
#include <util/rsod.h>

#define RSOD_DEFAULT_TITLE "INTERNAL ERROR";
#define RSOD_DEFAULT_MESSAGE "UNSPECIFIED";
#define RSOD_DEFAULT_FOOTER "PLEASE VISIT TREZOR.IO/RSOD";
#define RSOD_EXIT_MESSAGE "EXIT %d"

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
  char message_buf[32] = {0};
  int line = 0;

  switch (pminfo->reason) {
    case TASK_TERM_REASON_EXIT:
      mini_snprintf(message_buf, sizeof(message_buf), RSOD_EXIT_MESSAGE,
                    pminfo->exit.code);
      message = message_buf;
      break;
    case TASK_TERM_REASON_ERROR:
      title = pminfo->error.title;
      message = pminfo->error.message;
      footer = pminfo->error.footer;
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
    term_printf("%s\n", title);
  }

  if (message != NULL) {
    term_printf("msg : %s\n", message);
  }

  if (file) {
    term_printf("file: %s:%d\n", file, line);
  }

#ifdef SCM_REVISION
  const uint8_t* rev = (const uint8_t*)SCM_REVISION;
  term_printf("rev : %02x%02x%02x%02x%02x\n", rev[0], rev[1], rev[2], rev[3],
              rev[4]);
#endif

  if (footer != NULL) {
    term_printf("\n%s\n", footer);
  }

  display_set_backlight(255);
}

#endif  // KERNEL_MODE

#ifdef FANCY_FATAL_ERROR

#include "rust_ui.h"

void rsod_gui(const systask_postmortem_t* pminfo) {
  const char* title = RSOD_DEFAULT_TITLE;
  const char* message = RSOD_DEFAULT_MESSAGE;
  const char* footer = RSOD_DEFAULT_FOOTER;
  char message_buf[128] = {0};

  switch (pminfo->reason) {
    case TASK_TERM_REASON_EXIT:
      mini_snprintf(message_buf, sizeof(message_buf), RSOD_EXIT_MESSAGE,
                    pminfo->exit.code);
      message = message_buf;
      break;

    case TASK_TERM_REASON_ERROR:
      title = pminfo->error.title;
      message = pminfo->error.message;
      footer = pminfo->error.footer;
      break;

    case TASK_TERM_REASON_FATAL:
      message = pminfo->fatal.expr;
      if (message[0] == '\0') {
        mini_snprintf(message_buf, sizeof(message_buf), "%s:%u",
                      pminfo->fatal.file, (unsigned int)pminfo->fatal.line);
        message = message_buf;
      }
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
  // (If the kernel crashes in emergency mode, we are out of options
  // and show the RSOD without attempting to re-enter emergency mode)
  system_init(&rsod_terminal);

  // Initialize necessary drivers
  display_init(DISPLAY_RESET_CONTENT);

#ifdef FANCY_FATAL_ERROR
  // Show the RSOD using Rust GUI
  rsod_gui(pminfo);
#else
  // Show the RSOD using terminal
  rsod_terminal(pminfo);
#endif

  // Wait for the user to manually power off the device
  secure_shutdown();
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
