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
#include <trezor_model.h>
#include <trezor_rtl.h>

#include "wire_iface_null.h"

static bool null_write(uint8_t* data, size_t size) { return sectrue; }

static int null_read(uint8_t* buffer, size_t buffer_size) { return 0; }

static void null_error(void) {
  error_shutdown_ex("INTERNAL ERROR", "Trying to read from NULL interface",
                    NULL);
}

void null_iface_init(wire_iface_t* iface) {
  iface->poll_iface_id = 0;
  iface->tx_packet_size = 32767;
  iface->rx_packet_size = 32767;
  iface->write = &null_write;
  iface->read = &null_read;
  iface->error = &null_error;
}

void null_iface_deinit(wire_iface_t* iface) {
  memset(iface, 0, sizeof(wire_iface_t));
}
