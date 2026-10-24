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

#include <sys/sysevent.h>

#include "console.h"

// Blocking-write timeouts: generous while a host is consuming output, short
// once a write has failed so an absent host does not stall the main loop.
#define CONSOLE_WRITE_TIMEOUT_MS 2000
#define CONSOLE_WRITE_RETRY_TIMEOUT_MS 100

typedef struct {
  console_abort_cb_t abort_cb;
  void *abort_context;
  uint32_t usb_write_timeout;
} console_t;

static console_t g_console = {0};

// Interrupt context: Ctrl-C
static void console_intr(void) {
  console_t *con = &g_console;

  if (con->abort_cb != NULL) {
    con->abort_cb(con->abort_context);
  }
}

// ----------------------------------------------------------------------
// USB VCP: a byte stream already, passed through

void console_usb_intr(void) { console_intr(); }

static ssize_t usb_con_read(char *buf, size_t size) {
  return syshandle_read(SYSHANDLE_USB_VCP, buf, size);
}

static ssize_t usb_con_write(const char *buf, size_t size) {
  console_t *con = &g_console;

  ssize_t rc = syshandle_write_blocking(SYSHANDLE_USB_VCP, buf, size,
                                        con->usb_write_timeout);
  // Do not wait too long if the host is not connected.
  con->usb_write_timeout = (rc < (ssize_t)size) ? CONSOLE_WRITE_RETRY_TIMEOUT_MS
                                                : CONSOLE_WRITE_TIMEOUT_MS;
  return rc;
}

// ----------------------------------------------------------------------
// Front end

void console_init(console_abort_cb_t abort_cb, void *abort_context) {
  console_t *con = &g_console;

  memset(con, 0, sizeof(*con));
  con->abort_cb = abort_cb;
  con->abort_context = abort_context;
  con->usb_write_timeout = CONSOLE_WRITE_TIMEOUT_MS;
  // Ctrl-C arrives through console_usb_intr(), installed by usb_configure()
}

uint32_t console_poll_mask(void) { return 1 << SYSHANDLE_USB_VCP; }

bool console_input_pending(void) { return false; }

void console_flush(void) {}

ssize_t console_read(void *context, char *buf, size_t size) {
  UNUSED(context);

  if (size == 0) {
    return 0;
  }

  return usb_con_read(buf, size);
}

ssize_t console_write(void *context, const char *buf, size_t size) {
  UNUSED(context);
  return usb_con_write(buf, size);
}
