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

#include "rsod.h"
#include "display.h"
#include "mini_printf.h"
#include "system.h"
#include "terminal.h"

#define RSOD_DEFAULT_TITLE "INTERNAL ERROR";
#define RSOD_DEFAULT_MESSAGE "UNSPECIFIED";
#define RSOD_DEFAULT_FOOTER "PLEASE VISIT TREZOR.IO/RSOD";
#define RSOD_EXIT_MESSAGE "EXIT %d"

#ifdef KERNEL_MODE

#define RSOD_FG_COLOR COLOR_WHITE

#ifdef USE_RGB_COLORS
#define RSOD_BG_COLOR RGB16(0x7F, 0x00, 0x00)
#else
#define RSOD_BG_COLOR COLOR_BLACK
#endif

void rsod_terminal(const systask_postmortem_t* info) {
  display_orientation(0);
  term_set_color(RSOD_FG_COLOR, RSOD_BG_COLOR);

  const char* title = RSOD_DEFAULT_TITLE;
  const char* message = RSOD_DEFAULT_MESSAGE;
  const char* footer = RSOD_DEFAULT_FOOTER;
  const char* file = NULL;
  char message_buf[32] = {0};
  int line = 0;

  switch (info->reason) {
    case TASK_TERM_REASON_EXIT:
      mini_snprintf(message_buf, sizeof(message_buf), RSOD_EXIT_MESSAGE,
                    info->exit.code);
      message = message_buf;
      break;
    case TASK_TERM_REASON_ERROR:
      title = info->error.title;
      message = info->error.message;
      footer = info->error.footer;
      break;
    case TASK_TERM_REASON_FATAL:
      message = info->fatal.expr;
      file = info->fatal.file;
      line = info->fatal.line;
      break;
    case TASK_TERM_REASON_FAULT:
      message = system_fault_message(&info->fault);
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

  display_backlight(255);
}

#endif  // KERNEL_MODE

#if defined(FIRMWARE) || defined(BOOTLOADER)

#include "rust_ui.h"

void rsod_gui(const systask_postmortem_t* info) {
  const char* title = RSOD_DEFAULT_TITLE;
  const char* message = RSOD_DEFAULT_MESSAGE;
  const char* footer = RSOD_DEFAULT_FOOTER;
  char message_buf[128] = {0};

  switch (info->reason) {
    case TASK_TERM_REASON_EXIT:
      mini_snprintf(message_buf, sizeof(message_buf), RSOD_EXIT_MESSAGE,
                    info->exit.code);
      message = message_buf;
      break;

    case TASK_TERM_REASON_ERROR:
      title = info->error.title;
      message = info->error.message;
      footer = info->error.footer;
      break;

    case TASK_TERM_REASON_FATAL:
      message = info->fatal.expr;
      if (message[0] == '\0') {
        mini_snprintf(message_buf, sizeof(message_buf), "%s:%u",
                      info->fatal.file, (unsigned int)info->fatal.line);
        message = message_buf;
      }
      break;

    case TASK_TERM_REASON_FAULT:
      message = system_fault_message(&info->fault);
      break;
  }

  // Render the RSOD in Rust
  display_rsod_rust(title, message, footer);
}

#endif
