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

// Auxiliary GATT channel: the machinery shared by the services that carry an
// opaque packet stream between the STM32 and a bonded host next to the
// wire-protocol service, each on its own inter-MCU service id: the console
// (console.c) and the debuglink (debug.c).
//
// Both characteristics are variable-length up to AUX_CHAN_PACKET_SIZE. The
// SPI frame stays fixed-size and carries the real length in its header, so
// nothing here pads or strips anything. Unlike the wire-protocol service
// there is no peer-address prefix: there is a single connection and the
// channels have no per-peer semantics.
//
// Flow control: the STM32 keeps one packet per channel in flight and waits
// for a credit before sending the next. The credit is an empty frame on the
// channel's service id, sent once the notification has left (or once the
// packet had to be dropped), so the STM32 can never outrun the air interface
// and fill the heap-backed FIFO. Empty frames therefore never carry data in
// either direction; an empty GATT write is discarded.
//
// Each channel is registered at runtime (bt_gatt_service_register) rather
// than with BT_GATT_SERVICE_DEFINE so that a later version can register it
// only when the STM32 asks for it.

#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/kernel.h>

#include <trz_comm/trz_comm.h>

// Largest payload in either direction. Bounded by the ATT MTU on the air side
// (CONFIG_BT_L2CAP_TX_MTU - 3) and by the inter-MCU frame on the other.
#define AUX_CHAN_PACKET_SIZE BLE_TX_PACKET_SIZE

// A channel instance; the instance file owns the attribute table, the
// service, the thread and the callbacks, and fills this descriptor.
typedef struct {
  const char *name;  // for logs
  nrf_service_id_t service_id;
  struct bt_gatt_service *svc;
  const struct bt_gatt_attr *tx_attr;  // TX characteristic value attribute
  bt_gatt_complete_func_t on_sent;     // instance trampoline to aux_chan_sent
  struct k_sem *ready;                 // given once registered
} aux_chan_t;

// Registers the service and releases the write thread. Not fatal to the
// caller: the wire protocol works without the channel.
int aux_chan_init(const aux_chan_t *chan);

// Host -> STM32: forwards exactly `len` bytes on the channel's service id.
// Returns `len` for the GATT write callback.
ssize_t aux_chan_on_receive(const aux_chan_t *chan, const void *buf,
                            uint16_t len);

// Notification-sent callback body: frees the packet and credits the STM32.
void aux_chan_sent(const aux_chan_t *chan, void *user_data);

// STM32 -> host forwarding loop; never returns. Run it from the instance's
// thread.
void aux_chan_write_thread(const aux_chan_t *chan);
