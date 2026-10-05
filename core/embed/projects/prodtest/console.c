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
#include <sys/sysevent.h>

#include "console.h"
#include "prodtest_error_codes.h"

#ifdef USE_USB
#include <io/usb.h>
#endif
#ifdef USE_BLE_CONSOLE
#include <io/ble.h>
#include <io/ble_console.h>
#endif

#if !defined(USE_USB) && !defined(USE_BLE_CONSOLE)
#error "prodtest needs a console transport: USB VCP or the BLE console"
#endif

// Ctrl-C aborts the running command
#define CONSOLE_INTR_BYTE 0x03

// Blocking-write timeouts: generous while a host is consuming output, short
// once a write has failed so an absent host does not stall the main loop.
#define CONSOLE_WRITE_TIMEOUT_MS 2000
#define CONSOLE_WRITE_RETRY_TIMEOUT_MS 100

typedef struct {
  cli_t *cli;

  // Transport that delivered the first input byte; owns the CLI until it is
  // released (console-release, or its link going away)
  console_backend_t active;
  // console_release() was called by a command; applied once its reply is out
  bool release_pending;

#ifdef USE_USB
  uint32_t usb_write_timeout;
#endif

#ifdef USE_BLE_CONSOLE
  uint32_t ble_write_timeout;

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

// Interrupt context: Ctrl-C from `source`. Honoured until another transport
// has taken the console; afterwards only from the owner.
static void console_intr(console_backend_t source) {
  console_t *con = &g_console;

  if (con->cli != NULL &&
      (con->active == CONSOLE_BACKEND_NONE || con->active == source)) {
    cli_abort(con->cli);
  }
}

// ----------------------------------------------------------------------
// USB VCP: a byte stream already, passed through

#ifdef USE_USB

void console_usb_intr(void) { console_intr(CONSOLE_BACKEND_USB); }

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

#endif  // USE_USB

// ----------------------------------------------------------------------
// BLE console: packets of up to 244 bytes, split on input, coalesced on
// output

#ifdef USE_BLE_CONSOLE

// Interrupt context
static void ble_con_intr(void) { console_intr(CONSOLE_BACKEND_BLE); }

static bool ble_con_input_pending(void) {
  return g_console.rx_pos < g_console.rx_len;
}

static void ble_con_flush(void) {
  console_t *con = &g_console;

  if (con->tx_len == 0) {
    return;
  }

  ssize_t rc = syshandle_write_blocking(SYSHANDLE_BLE_CONSOLE, con->tx_buf,
                                        con->tx_len, con->ble_write_timeout);

  // Lossy by design: whatever did not go out within the timeout is dropped.
  con->ble_write_timeout = (rc < (ssize_t)con->tx_len)
                               ? CONSOLE_WRITE_RETRY_TIMEOUT_MS
                               : CONSOLE_WRITE_TIMEOUT_MS;
  con->tx_len = 0;
}

static ssize_t ble_con_read(char *buf, size_t size) {
  console_t *con = &g_console;

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

static ssize_t ble_con_write(const char *buf, size_t size) {
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
      ble_con_flush();
    }
  }

  // Every CLI response line ends with "\r\n" as its own write. When the link
  // is free, flush on the newline so a line goes out at once; while a packet
  // is still in flight, keep batching lines into the packet instead of
  // blocking per line, which makes long outputs (help, hex dumps) several
  // times faster. The main loop flushes whatever is left after the command.
  if (con->tx_len > 0 && con->tx_buf[con->tx_len - 1] == '\n' &&
      ble_console_can_write()) {
    ble_con_flush();
  }

  return written;
}

#endif  // USE_BLE_CONSOLE

// ----------------------------------------------------------------------
// Front end: both transports until one of them delivers input, then that one

void console_init(cli_t *cli) {
  console_t *con = &g_console;

  memset(con, 0, sizeof(*con));
  con->cli = cli;
  con->active = CONSOLE_BACKEND_NONE;

#ifdef USE_USB
  con->usb_write_timeout = CONSOLE_WRITE_TIMEOUT_MS;
  // Ctrl-C arrives through console_usb_intr(), installed by usb_configure()
#endif
#ifdef USE_BLE_CONSOLE
  con->ble_write_timeout = CONSOLE_WRITE_TIMEOUT_MS;
  ble_console_set_intr(CONSOLE_INTR_BYTE, ble_con_intr);
#endif
}

console_backend_t console_active(void) { return g_console.active; }

uint32_t console_poll_mask(void) {
  // Both, even with an owner: input on the other transport is answered with
  // an error, see console_reject_foreign().
  uint32_t mask = 0;

#ifdef USE_USB
  mask |= 1 << SYSHANDLE_USB_VCP;
#endif
#ifdef USE_BLE_CONSOLE
  mask |= 1 << SYSHANDLE_BLE_CONSOLE;
#endif
  return mask;
}

#if defined(USE_USB) && defined(USE_BLE_CONSOLE)

static bool has_line_end(const char *buf, size_t len) {
  for (size_t i = 0; i < len; i++) {
    if (buf[i] == '\n' || buf[i] == '\r') {
      return true;
    }
  }
  return false;
}

// Input on the transport that does not own the console: discarded, and each
// line attempted is answered there with an error naming the owner, so the
// operator sees why nothing happens instead of a dead link.
static void console_reject_foreign(void) {
  console_t *con = &g_console;
  char line[96];
  bool answer = false;

  if (con->active == CONSOLE_BACKEND_USB) {
    // rx_buf is free: the BLE packets are not for the CLI
    while (ble_console_can_read()) {
      uint16_t n = ble_console_read(con->rx_buf, sizeof(con->rx_buf));
      answer |= has_line_end((const char *)con->rx_buf, n);
    }
    if (answer) {
      int len = snprintf_(line, sizeof(line),
                          "ERROR %d \"console in use over USB; send "
                          "console-release there or unplug it\"\r\n",
                          PRODTEST_ERR_PRODTEST_CONSOLE_BUSY);
      ble_con_write(line, (size_t)len);
      ble_con_flush();
    }
  } else if (con->active == CONSOLE_BACKEND_BLE) {
    char scratch[64];
    ssize_t n;
    while ((n = usb_con_read(scratch, sizeof(scratch))) > 0) {
      answer |= has_line_end(scratch, (size_t)n);
    }
    if (answer) {
      int len = snprintf_(line, sizeof(line),
                          "ERROR %d \"console in use over BLE; send "
                          "console-release there or disconnect it\"\r\n",
                          PRODTEST_ERR_PRODTEST_CONSOLE_BUSY);
      usb_con_write(line, (size_t)len);
    }
  }
}

#else

static void console_reject_foreign(void) {}

#endif

bool console_input_pending(void) {
#ifdef USE_BLE_CONSOLE
  if (g_console.active != CONSOLE_BACKEND_USB) {
    return ble_con_input_pending();
  }
#endif
  return false;
}

void console_flush(void) {
  console_t *con = &g_console;

#ifdef USE_BLE_CONSOLE
  if (con->active != CONSOLE_BACKEND_USB) {
    ble_con_flush();
  }
#endif

  if (con->release_pending) {
    con->release_pending = false;
    con->active = CONSOLE_BACKEND_NONE;
  }
}

void console_release(void) { g_console.release_pending = true; }

void console_tick(void) {
  console_t *con = &g_console;

  // The owner lost its link: a unit unplugged from a USB station (a charger
  // never configures the VCP) or a BLE host gone. Listen to both again so
  // the next station needs no reboot.
  switch (con->active) {
#ifdef USE_USB
    case CONSOLE_BACKEND_USB: {
      usb_state_t state = {0};
      usb_get_state(&state);
      if (!state.configured) {
        con->active = CONSOLE_BACKEND_NONE;
      }
      break;
    }
#endif
#ifdef USE_BLE_CONSOLE
    case CONSOLE_BACKEND_BLE: {
      ble_state_t state = {0};
      ble_get_state(&state);
      if (state.state_known && !state.connected) {
        con->active = CONSOLE_BACKEND_NONE;
      }
      break;
    }
#endif
    default:
      break;
  }
}

ssize_t console_read(void *context, char *buf, size_t size) {
  UNUSED(context);
  console_t *con = &g_console;

  if (size == 0) {
    return 0;
  }

  console_reject_foreign();

  ssize_t n = 0;

#ifdef USE_BLE_CONSOLE
  if (con->active != CONSOLE_BACKEND_USB) {
    n = ble_con_read(buf, size);
    if (n > 0) {
      con->active = CONSOLE_BACKEND_BLE;
      return n;
    }
  }
#endif
#ifdef USE_USB
  if (con->active != CONSOLE_BACKEND_BLE) {
    n = usb_con_read(buf, size);
    if (n > 0) {
      con->active = CONSOLE_BACKEND_USB;
      return n;
    }
  }
#endif
  return n;
}

ssize_t console_write(void *context, const char *buf, size_t size) {
  UNUSED(context);
  console_t *con = &g_console;

  // Before any input the output has no addressee; it goes to every transport
  // (the CLI writes nothing unprompted, so this is only for completeness).
  ssize_t rc = (ssize_t)size;

#ifdef USE_BLE_CONSOLE
  if (con->active != CONSOLE_BACKEND_USB) {
    rc = ble_con_write(buf, size);
  }
#endif
#ifdef USE_USB
  if (con->active != CONSOLE_BACKEND_BLE) {
    rc = usb_con_write(buf, size);
  }
#endif
  return rc;
}
