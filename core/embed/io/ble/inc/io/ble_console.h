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

/**
 * BLE console interface.
 *
 * A packet channel to a bonded BLE host that is separate from the wire
 * protocol interface (`ble_read`/`ble_write`). It rides the console GATT
 * service on the nRF and its own inter-MCU service id, so console traffic and
 * wire-protocol traffic never mix. Consumers are the prodtest CLI and the
 * debug console backend; production firmware never routes it.
 *
 * Packets are variable-length, 1..BLE_CONSOLE_PACKET_SIZE bytes, and are
 * delivered with their real length. The console is lossy by design: packets
 * that cannot be queued are dropped, and nothing here blocks.
 *
 * The interface requires `ble_init()` to have been called first (it shares the
 * nRF link) and works without `ble_start()`: it is independent of the wire
 * protocol's accept state. Data flows only while a host is connected.
 *
 * Not available on the emulator (USE_BLE_CONSOLE is not defined there): its
 * console is the UDP-backed USB VCP.
 */

/** Largest payload of one console packet, either direction. */
#define BLE_CONSOLE_PACKET_SIZE 244

/** Callback invoked from interrupt context when the interrupt byte arrives. */
typedef void (*ble_console_intr_cb_t)(void);

/** Counters for diagnosing the link; all since init. */
typedef struct {
  uint32_t tx_packets;  /**< packets handed to the inter-MCU link */
  uint32_t tx_credits;  /**< credits received back from the nRF */
  uint32_t tx_timeouts; /**< packets given up without a credit */
  uint32_t tx_failed;   /**< packets the inter-MCU link refused or aborted */
  uint32_t rx_packets;  /**< packets queued for the consumer */
  uint32_t rx_dropped;  /**< packets dropped, receive queue full or oversized */
} ble_console_stats_t;

/**
 * @brief Initializes the console interface
 *
 * Registers the inter-MCU listener and SYSHANDLE_BLE_CONSOLE, and asks the nRF
 * to expose the console service once the link is up. Has no effect if already
 * initialized.
 *
 * @return true on success, false otherwise
 */
bool ble_console_init(void);

/**
 * @brief Deinitializes the console interface
 */
void ble_console_deinit(void);

/**
 * @brief Sets an out-of-band interrupt byte
 *
 * When `byte` is seen anywhere in incoming console data, `callback` is invoked
 * from interrupt context before the data is queued. The byte itself stays in
 * the stream. Used by the prodtest CLI to abort a running command on Ctrl-C,
 * mirroring the USB VCP interrupt byte. Pass NULL to disable.
 */
void ble_console_set_intr(uint8_t byte, ble_console_intr_cb_t callback);

/**
 * @brief Reads the link counters
 */
void ble_console_get_stats(ble_console_stats_t *stats);

/**
 * @brief Checks whether a packet is waiting to be read
 */
bool ble_console_can_read(void);

/**
 * @brief Reads one console packet
 *
 * `max_len` must be at least BLE_CONSOLE_PACKET_SIZE, otherwise nothing is
 * read and the packet stays queued.
 *
 * @param data Buffer for the packet
 * @param max_len Size of the buffer
 * @return Number of bytes read, 0 if no packet was available
 */
uint32_t ble_console_read(uint8_t *data, uint16_t max_len);

/**
 * @brief Checks whether a packet can be written now
 *
 * True when a host is connected and no console packet is in flight. A packet
 * stays in flight until the nRF reports that its notification left the air
 * interface (an empty frame on the console service id), or until a timeout
 * assumes it lost. This keeps the STM32 from outrunning the BLE link and
 * from crowding the wire protocol out of the shared transmit queue.
 */
bool ble_console_can_write(void);

/**
 * @brief Writes one console packet
 *
 * @param data Packet payload
 * @param len Payload length, 1..BLE_CONSOLE_PACKET_SIZE
 * @return true if the packet was queued for transmission, false otherwise
 */
bool ble_console_write(const uint8_t *data, uint16_t len);
