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

#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/ble_chan.h>
#include <io/ble_debug.h>
#include <io/nrf.h>
#include <sys/logging.h>

LOG_DECLARE(ble_debug)

_Static_assert(BLE_DEBUG_PACKET_SIZE == BLE_CHAN_PACKET_SIZE,
               "debuglink packets fill the channel packet exactly");

static ble_chan_t g_ble_debug = {0};

// Interrupt context: inter-MCU frame on NRF_SERVICE_DEBUG
static void ble_debug_rx(const uint8_t *data, uint32_t len) {
  // Credits (empty frames) pass through; a data frame must be a whole
  // report, as on the USB debug interface, or the codec would misparse it.
  if (len != 0 && len != BLE_DEBUG_PACKET_SIZE) {
    g_ble_debug.stats.rx_dropped++;
    LOG_WARN("frame of %u bytes dropped", (unsigned)len);
    return;
  }
  ble_chan_rx(&g_ble_debug, data, len);
}

bool ble_debug_init(void) {
  bool ok = ble_chan_init(&g_ble_debug, NRF_SERVICE_DEBUG,
                          SYSHANDLE_BLE_IFACE_1, ble_debug_rx);
  if (ok) {
    LOG_INF("debuglink interface ready");
  } else {
    LOG_WARN("debuglink interface unavailable");
  }
  return ok;
}

void ble_debug_deinit(void) { ble_chan_deinit(&g_ble_debug); }

bool ble_debug_can_read(void) { return ble_chan_can_read(&g_ble_debug); }

uint32_t ble_debug_read(uint8_t *data, uint16_t max_len) {
  return ble_chan_read(&g_ble_debug, data, max_len);
}

bool ble_debug_can_write(void) { return ble_chan_can_write(&g_ble_debug); }

bool ble_debug_write(const uint8_t *data, uint16_t len) {
  if (len != BLE_DEBUG_PACKET_SIZE) {
    LOG_WARN("write of %u bytes refused, reports are %u", len,
             BLE_DEBUG_PACKET_SIZE);
    return false;
  }
  return ble_chan_write(&g_ble_debug, data, len);
}

#endif  // KERNEL_MODE
