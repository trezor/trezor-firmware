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
 * transport, today USB VCP: a byte stream already, passed through with a
 * blocking write and an adaptive timeout so an absent host does not stall the
 * main loop. Keeping the transport behind these few calls lets another one be
 * slotted in without touching the main loop.
 */

/** Sets up the transport. */
void console_init(cli_t *cli);

/** Bits of `sysevents_t.read_ready` the main loop should wait on. */
uint32_t console_poll_mask(void);

/**
 * True when input is buffered but not yet consumed, so the CLI should be
 * serviced without waiting for a new read-ready event.
 */
bool console_input_pending(void);

/** Flushes buffered output. Call after servicing the CLI. */
void console_flush(void);

/** CLI read callback (see cli_read_cb_t). */
ssize_t console_read(void *context, char *buf, size_t size);

/** CLI write callback (see cli_write_cb_t). */
ssize_t console_write(void *context, const char *buf, size_t size);
