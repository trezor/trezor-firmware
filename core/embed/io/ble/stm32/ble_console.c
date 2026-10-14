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
#include <io/ble_console.h>
#include <io/nrf.h>
#include <sys/systimer.h>

// Retry period for the console-enable request until the nRF link is up.
#define ENABLE_RETRY_MS 100

typedef struct {
  ble_chan_t chan;

  // Sends MGMT_CMD_CONSOLE_ENABLE once the nRF link accepts messages
  systimer_t *enable_timer;
  bool enable_sent;
} ble_console_driver_t;

static ble_console_driver_t g_ble_console = {0};

// Interrupt context: inter-MCU frame on NRF_SERVICE_CONSOLE
static void ble_console_rx(const uint8_t *data, uint32_t len) {
  ble_chan_rx(&g_ble_console.chan, data, len);
}

// Interrupt context: one-shot, re-armed until the request goes out. The nRF
// currently registers the console service unconditionally and treats the
// request as a no-op; it is sent so that a later nRF version can register the
// service only on request without an STM32 change.
static void ble_console_enable_timer(void *context) {
  ble_console_driver_t *drv = (ble_console_driver_t *)context;

  if (drv->enable_sent) {
    return;
  }

  if (nrf_enable_console()) {
    drv->enable_sent = true;
  } else {
    systimer_set(drv->enable_timer, ENABLE_RETRY_MS);
  }
}

bool ble_console_init(void) {
  ble_console_driver_t *drv = &g_ble_console;

  if (drv->chan.initialized) {
    return true;
  }

  drv->enable_sent = false;
  drv->enable_timer = systimer_create(ble_console_enable_timer, drv);
  if (drv->enable_timer == NULL) {
    return false;
  }

  if (!ble_chan_init(&drv->chan, NRF_SERVICE_CONSOLE, SYSHANDLE_BLE_CONSOLE,
                     ble_console_rx)) {
    systimer_delete(drv->enable_timer);
    drv->enable_timer = NULL;
    return false;
  }

  systimer_set(drv->enable_timer, ENABLE_RETRY_MS);

  return true;
}

void ble_console_deinit(void) {
  ble_console_driver_t *drv = &g_ble_console;

  if (!drv->chan.initialized) {
    return;
  }

  ble_chan_deinit(&drv->chan);
  systimer_delete(drv->enable_timer);
  drv->enable_timer = NULL;
  drv->enable_sent = false;
}

void ble_console_set_intr(uint8_t byte, ble_console_intr_cb_t callback) {
  ble_chan_set_intr(&g_ble_console.chan, byte, callback);
}

bool ble_console_can_read(void) {
  return ble_chan_can_read(&g_ble_console.chan);
}

uint32_t ble_console_read(uint8_t *data, uint16_t max_len) {
  return ble_chan_read(&g_ble_console.chan, data, max_len);
}

bool ble_console_can_write(void) {
  return ble_chan_can_write(&g_ble_console.chan);
}

bool ble_console_write(const uint8_t *data, uint16_t len) {
  return ble_chan_write(&g_ble_console.chan, data, len);
}

void ble_console_get_stats(ble_console_stats_t *stats) {
  ble_chan_get_stats(&g_ble_console.chan, stats);
}

#endif  // KERNEL_MODE
