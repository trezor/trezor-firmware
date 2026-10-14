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

#include <io/nrf.h>
#include <io/tsqueue.h>
#include <sys/sysevent.h>

/**
 * Auxiliary BLE packet channel.
 *
 * The machinery shared by the BLE interfaces that ride their own GATT
 * service on the nRF and their own inter-MCU service id, next to the wire
 * protocol: the console (prodtest CLI, debug logs) and the debuglink. One
 * instance per channel; the channel-specific headers (`ble_console.h`,
 * `ble_debug.h`) wrap an instance and are what consumers include.
 *
 * Packets are 1..BLE_CHAN_PACKET_SIZE bytes and are delivered with their real
 * length. Nothing here blocks: a packet that cannot be queued is dropped and
 * reported through the counters, and a write refused for lack of a credit
 * returns false for the caller to retry once the handle signals writable.
 *
 * Flow control is one packet in flight: a written packet stays pending until
 * the nRF credits it back with an empty frame on the channel's service id
 * (sent once the notification left the air interface, or once the nRF had to
 * drop it), or until BLE_CHAN_TX_CREDIT_TIMEOUT_MS passes. This keeps the
 * STM32 from outrunning the BLE link and from crowding the wire protocol out
 * of the shared inter-MCU transmit queue.
 */

/** Largest payload of one packet, either direction. */
#define BLE_CHAN_PACKET_SIZE 244

/** Inbound packets buffered until the consumer reads them. */
#define BLE_CHAN_RX_QUEUE_LEN 16

/** A packet in flight is given up without a credit after this long. */
#define BLE_CHAN_TX_CREDIT_TIMEOUT_MS 1000

/** Callback invoked from interrupt context when the interrupt byte arrives. */
typedef void (*ble_chan_intr_cb_t)(void);

/** Counters for diagnosing the link; all since init. */
typedef struct {
  uint32_t tx_packets;  /**< packets handed to the inter-MCU link */
  uint32_t tx_credits;  /**< credits received back from the nRF */
  uint32_t tx_timeouts; /**< packets given up without a credit */
  uint32_t tx_failed;   /**< packets the inter-MCU link refused or aborted */
  uint32_t rx_packets;  /**< packets queued for the consumer */
  uint32_t rx_dropped;  /**< packets dropped, receive queue full or oversized */
} ble_chan_stats_t;

/** Channel instance; owned by the wrapping interface, opaque to consumers. */
typedef struct {
  bool initialized;

  nrf_service_id_t service_id;
  syshandle_t handle;

  uint8_t rx_queue_buffers[BLE_CHAN_RX_QUEUE_LEN][BLE_CHAN_PACKET_SIZE];
  tsqueue_entry_t rx_queue_entries[BLE_CHAN_RX_QUEUE_LEN];
  tsqueue_t rx_queue;

  // One packet in flight until the nRF credits it back or the deadline passes
  volatile bool tx_pending;
  uint32_t tx_deadline;

  uint8_t intr_byte;
  ble_chan_intr_cb_t intr_cb;

  // Bring-up diagnostics state (see on_chan_poll)
  bool read_awaited_seen;
  bool read_ready_seen;

  ble_chan_stats_t stats;
} ble_chan_t;

/**
 * @brief Brings a channel up
 *
 * Registers `rx` as the inter-MCU listener for `service_id` (the wrapper
 * passes a trampoline that calls ble_chan_rx() on this instance, since the
 * listener carries no context) and registers `handle` with a generic
 * read/write/poll implementation over the channel.
 *
 * @return true on success, false otherwise (nothing stays registered)
 */
bool ble_chan_init(ble_chan_t *chan, nrf_service_id_t service_id,
                   syshandle_t handle, nrf_rx_callback_t rx);

/** @brief Takes a channel down; no-op if not initialized. */
void ble_chan_deinit(ble_chan_t *chan);

/** @brief Interrupt context: handles an inter-MCU frame for the channel. */
void ble_chan_rx(ble_chan_t *chan, const uint8_t *data, uint32_t len);

/** @brief Sets the out-of-band interrupt byte; `callback` NULL disables. */
void ble_chan_set_intr(ble_chan_t *chan, uint8_t byte,
                       ble_chan_intr_cb_t callback);

/** @brief Reads the link counters. */
void ble_chan_get_stats(const ble_chan_t *chan, ble_chan_stats_t *stats);

/** @brief True when a packet is waiting to be read. */
bool ble_chan_can_read(const ble_chan_t *chan);

/**
 * @brief Reads one packet
 *
 * `max_len` must be at least BLE_CHAN_PACKET_SIZE, otherwise nothing is read
 * and the packet stays queued.
 *
 * @return Number of bytes read, 0 if no packet was available
 */
uint32_t ble_chan_read(ble_chan_t *chan, uint8_t *data, uint16_t max_len);

/**
 * @brief True when a host is connected and no packet is in flight
 *
 * Also retires a packet whose credit never came, counting a timeout.
 */
bool ble_chan_can_write(ble_chan_t *chan);

/**
 * @brief Writes one packet
 *
 * @return true if the packet was handed to the inter-MCU link, false if it
 *         could not be sent now (no host, a packet in flight, link refused)
 */
bool ble_chan_write(ble_chan_t *chan, const uint8_t *data, uint16_t len);
