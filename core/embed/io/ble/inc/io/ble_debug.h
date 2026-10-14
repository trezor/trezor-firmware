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
 * BLE debuglink interface.
 *
 * The debuglink's own packet channel to a bonded BLE host, the counterpart of
 * the USB debug interface (SYSHANDLE_USB_DEBUG) on boards without USB. It
 * rides the debuglink GATT service on the nRF and its own inter-MCU service
 * id, separate from both the wire protocol and the console. Only debug
 * firmware builds it, and only debug nRF images expose the service.
 *
 * Like the USB debug interface it carries fixed-size packets of
 * BLE_DEBUG_PACKET_SIZE bytes in both directions, the codec v1 report size the
 * debuglink uses over BLE; a shorter inbound packet is dropped. Delivery is
 * flow-controlled with one packet in flight (see `ble_chan.h`): a write that
 * cannot go out now returns false and the handle signals writable once it
 * can, so the codec's write loop never loses a report.
 *
 * Requires `ble_init()`; independent of `ble_start()` and of the wire
 * protocol's accept state. Data flows only while a host is connected.
 *
 * Not available on the emulator: its debuglink is the emulated USB debug
 * interface.
 */

/** Size of every debuglink packet, either direction. */
#define BLE_DEBUG_PACKET_SIZE 244

/**
 * @brief Initializes the debuglink interface
 *
 * Registers the inter-MCU listener and SYSHANDLE_BLE_IFACE_1. Has no effect
 * if already initialized.
 *
 * @return true on success, false otherwise
 */
bool ble_debug_init(void);

/**
 * @brief Deinitializes the debuglink interface
 */
void ble_debug_deinit(void);

/**
 * @brief Checks whether a packet is waiting to be read
 */
bool ble_debug_can_read(void);

/**
 * @brief Reads one debuglink packet
 *
 * @param data Buffer for the packet, at least BLE_DEBUG_PACKET_SIZE bytes
 * @param max_len Size of the buffer
 * @return BLE_DEBUG_PACKET_SIZE, or 0 if no packet was available or the
 *         buffer is too small
 */
uint32_t ble_debug_read(uint8_t *data, uint16_t max_len);

/**
 * @brief Checks whether a packet can be written now
 */
bool ble_debug_can_write(void);

/**
 * @brief Writes one debuglink packet
 *
 * @param data Packet, exactly BLE_DEBUG_PACKET_SIZE bytes
 * @param len Must be BLE_DEBUG_PACKET_SIZE
 * @return true if the packet was handed to the link, false if it cannot go
 *         out now (retry once the handle is writable) or `len` is wrong
 */
bool ble_debug_write(const uint8_t *data, uint16_t len);
