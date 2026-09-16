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

#ifdef USE_BLE_CONSOLE
#include <io/ble_console.h>
#endif

// Ctrl-C aborts the running command
#define CONSOLE_INTR_BYTE 0x03

// Blocking-write timeouts: generous while a host is consuming output, short
// once a write has failed so an absent host does not stall the main loop.
#define CONSOLE_WRITE_TIMEOUT_MS 2000
#define CONSOLE_WRITE_RETRY_TIMEOUT_MS 100

typedef struct {
  cli_t *cli;
  uint32_t write_timeout;

#ifdef USE_BLE_CONSOLE
  // Current input packet, consumed byte by byte
  uint8_t rx_buf[BLE_CONSOLE_PACKET_SIZE];
  uint16_t rx_len;
  uint16_t rx_pos;

  // Output coalesced into one packet
  uint8_t tx_buf[BLE_CONSOLE_PACKET_SIZE];
  uint16_t tx_len;
#endif
} console_t;

static console_t g_console = {0};

#ifdef USE_BLE_CONSOLE

// Interrupt context
static void console_intr(void) {
  if (g_console.cli != NULL) {
    cli_abort(g_console.cli);
  }
}

void console_init(cli_t *cli) {
  console_t *con = &g_console;

  memset(con, 0, sizeof(*con));
  con->cli = cli;
  con->write_timeout = CONSOLE_WRITE_TIMEOUT_MS;

  ble_console_set_intr(CONSOLE_INTR_BYTE, console_intr);
}

uint32_t console_poll_mask(void) { return 1 << SYSHANDLE_BLE_CONSOLE; }

bool console_input_pending(void) { return g_console.rx_pos < g_console.rx_len; }

void console_flush(void) {
  console_t *con = &g_console;

  if (con->tx_len == 0) {
    return;
  }

  ssize_t rc = syshandle_write_blocking(SYSHANDLE_BLE_CONSOLE, con->tx_buf,
                                        con->tx_len, con->write_timeout);

  // Lossy by design: whatever did not go out within the timeout is dropped.
  con->write_timeout = (rc < (ssize_t)con->tx_len)
                           ? CONSOLE_WRITE_RETRY_TIMEOUT_MS
                           : CONSOLE_WRITE_TIMEOUT_MS;
  con->tx_len = 0;
}

ssize_t console_read(void *context, char *buf, size_t size) {
  UNUSED(context);
  console_t *con = &g_console;

  if (size == 0) {
    return 0;
  }

  if (con->rx_pos >= con->rx_len && ble_console_can_read()) {
    con->rx_len = ble_console_read(con->rx_buf, sizeof(con->rx_buf));
    con->rx_pos = 0;
  }

  if (con->rx_pos >= con->rx_len) {
    return 0;
  }

  size_t n = MIN(size, (size_t)(con->rx_len - con->rx_pos));
  memcpy(buf, &con->rx_buf[con->rx_pos], n);
  con->rx_pos += n;
  return n;
}

ssize_t console_write(void *context, const char *buf, size_t size) {
  UNUSED(context);
  console_t *con = &g_console;

  size_t written = size;

  while (size > 0) {
    size_t room = sizeof(con->tx_buf) - con->tx_len;
    size_t chunk = MIN(size, room);

    memcpy(&con->tx_buf[con->tx_len], buf, chunk);
    con->tx_len += chunk;
    buf += chunk;
    size -= chunk;

    if (con->tx_len == sizeof(con->tx_buf)) {
      console_flush();
    }
  }

  // Every CLI response line ends with "\r\n" as its own write. When the link
  // is free, flush on the newline so a line goes out at once; while a packet
  // is still in flight, keep batching lines into the packet instead of
  // blocking per line, which makes long outputs (help, hex dumps) several
  // times faster. The main loop flushes whatever is left after the command.
  if (con->tx_len > 0 && con->tx_buf[con->tx_len - 1] == '\n' &&
      ble_console_can_write()) {
    console_flush();
  }

  return written;
}

#else  // USB VCP

void console_init(cli_t *cli) {
  console_t *con = &g_console;

  memset(con, 0, sizeof(*con));
  con->cli = cli;
  con->write_timeout = CONSOLE_WRITE_TIMEOUT_MS;
  // Ctrl-C is delivered by the VCP interrupt byte, see usb_config.c
}

uint32_t console_poll_mask(void) { return 1 << SYSHANDLE_USB_VCP; }

bool console_input_pending(void) { return false; }

void console_flush(void) {}

ssize_t console_read(void *context, char *buf, size_t size) {
  UNUSED(context);
  return syshandle_read(SYSHANDLE_USB_VCP, buf, size);
}

ssize_t console_write(void *context, const char *buf, size_t size) {
  UNUSED(context);
  console_t *con = &g_console;

  ssize_t rc = syshandle_write_blocking(SYSHANDLE_USB_VCP, buf, size,
                                        con->write_timeout);
  // Do not wait too long if the host is not connected.
  con->write_timeout = (rc < (ssize_t)size) ? CONSOLE_WRITE_RETRY_TIMEOUT_MS
                                            : CONSOLE_WRITE_TIMEOUT_MS;
  return rc;
}

#endif  // USE_BLE_CONSOLE
