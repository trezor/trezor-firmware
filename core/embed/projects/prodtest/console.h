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

#pragma once

#include <trezor_types.h>

#include <rtl/cli.h>

/**
 * CLI console transport.
 *
 * The CLI engine (rtl/cli) is a byte stream: it reads one byte at a time and
 * writes many small fragments. This module sits between the engine and the
 * transports the board provides:
 *
 * - USB VCP (USE_USB): a byte stream already; passed through with a blocking
 *   write and an adaptive timeout so an absent host does not stall the loop.
 * - BLE console (USE_BLE_CONSOLE, board declares `[ble_console]`): a packet
 *   channel of up to 244 bytes. Input packets are handed to the engine byte by
 *   byte; output fragments are coalesced into a packet that is flushed on a
 *   newline, when full, or when the main loop calls console_flush().
 *
 * When both are built in, both are listened to until one delivers input; that
 * transport then owns the console, so different stages of testing can use
 * different transports without the two ever interleaving. Ownership ends when
 * the owner's link goes away (USB unplugged, BLE disconnected), or on the
 * `console-release` command; both transports are then listened to again.
 * Meanwhile a line sent on the other transport is discarded and answered
 * there with an error that names the owner.
 */

typedef enum {
  CONSOLE_BACKEND_NONE = 0,  // no input yet, listening on every transport
  CONSOLE_BACKEND_USB,
  CONSOLE_BACKEND_BLE,
} console_backend_t;

/** Sets up the transports and the Ctrl-C abort hooks. */
void console_init(cli_t *cli);

/** Transport that owns the console, NONE until the first input byte. */
console_backend_t console_active(void);

/**
 * Gives the console up after the current command's reply has been flushed,
 * so the other transport can take it with its first input byte.
 */
void console_release(void);

/**
 * Releases the console when the owning transport's link is gone. Call from
 * the main loop on every pass.
 */
void console_tick(void);

#ifdef USE_USB
/** USB VCP interrupt-byte callback, to be passed to usb_configure(). */
void console_usb_intr(void);
#endif

/** Bits of `sysevents_t.read_ready` the main loop should wait on. */
uint32_t console_poll_mask(void);

/**
 * True when bytes from an already received packet are still unread, so the
 * CLI should be serviced without waiting for a new read-ready event.
 */
bool console_input_pending(void);

/** Flushes buffered output. Call after servicing the CLI. */
void console_flush(void);

/** CLI read callback (see cli_read_cb_t). */
ssize_t console_read(void *context, char *buf, size_t size);

/** CLI write callback (see cli_write_cb_t). */
ssize_t console_write(void *context, const char *buf, size_t size);
