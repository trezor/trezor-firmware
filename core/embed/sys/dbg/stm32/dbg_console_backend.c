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

#include <trezor_rtl.h>

#include <sys/irq.h>

#include <sys/dbg_console.h>
#include <sys/sysevent.h>
#include <sys/systick.h>
#include <sys/systimer.h>

#ifdef USE_DBG_CONSOLE_SYSTEM_VIEW
#include "SEGGER_RTT.h"
#include "SEGGER_SYSVIEW.h"
#endif

#if defined(USE_DBG_CONSOLE_SYSTEM_VIEW) && !defined(USE_SYSTEM_VIEW)
#error "USE_DBG_CONSOLE_SYSTEM_VIEW requires USE_SYSTEM_VIEW"
#endif

#ifdef USE_DBG_CONSOLE_BLE
// Log bytes wait here until the BLE console can take a packet. The console
// is lossy and one packet is in flight at a time, so a burst of logs (or logs
// while no host is connected) must not block the writer: the newest bytes are
// kept and the oldest dropped. Sized for a few screens of log lines.
#define BLE_LOG_RING_SIZE 4096
// One packet on the BLE console interface (io/ble_console.h, not visible from
// this library; the handle's write takes at most this much per call).
#define BLE_LOG_PACKET_SIZE 244
// How often queued bytes are offered to the link
#define BLE_LOG_FLUSH_MS 20

typedef struct {
  uint8_t buf[BLE_LOG_RING_SIZE];
  size_t head;  // next write position
  size_t count;
  systimer_t *timer;
} ble_log_t;

static ble_log_t g_ble_log;

// Interrupt context (systimer). The console interface signals when it can
// take a packet through its handle; a write that returns 0 means not yet.
static void ble_log_flush(void *context) {
  ble_log_t *log = (ble_log_t *)context;
  uint8_t packet[BLE_LOG_PACKET_SIZE];

  for (;;) {
    irq_key_t key = irq_lock();
    size_t n = MIN(log->count, sizeof(packet));
    size_t tail =
        (log->head + BLE_LOG_RING_SIZE - log->count) % BLE_LOG_RING_SIZE;
    for (size_t i = 0; i < n; i++) {
      packet[i] = log->buf[(tail + i) % BLE_LOG_RING_SIZE];
    }
    irq_unlock(key);

    if (n == 0) {
      return;
    }

    ssize_t written = syshandle_write(SYSHANDLE_BLE_CONSOLE, packet, n);
    if (written <= 0) {
      return;  // link busy or no host; try again on the next tick
    }

    key = irq_lock();
    log->count -= MIN((size_t)written, log->count);
    irq_unlock(key);
  }
}

static ssize_t ble_log_write(const void *data, size_t data_size) {
  ble_log_t *log = &g_ble_log;
  const uint8_t *bytes = (const uint8_t *)data;

  irq_key_t key = irq_lock();
  for (size_t i = 0; i < data_size; i++) {
    log->buf[log->head] = bytes[i];
    log->head = (log->head + 1) % BLE_LOG_RING_SIZE;
    if (log->count < BLE_LOG_RING_SIZE) {
      log->count++;
    }
    // else the oldest byte was just overwritten; the console is lossy
  }
  irq_unlock(key);

  return data_size;
}
#endif  // USE_DBG_CONSOLE_BLE

void dbg_console_init(void) {
#ifdef USE_DBG_CONSOLE_SYSTEM_VIEW
  SEGGER_SYSVIEW_Conf();
  SEGGER_SYSVIEW_Start();
#endif
#ifdef USE_DBG_CONSOLE_BLE
  // Buffering starts now so early boot logs are kept; they go out once the
  // BLE console interface is initialized and a host is connected.
  memset(&g_ble_log, 0, sizeof(g_ble_log));
  g_ble_log.timer = systimer_create(ble_log_flush, &g_ble_log);
  if (g_ble_log.timer != NULL) {
    systimer_set_periodic(g_ble_log.timer, BLE_LOG_FLUSH_MS);
  }
#endif
}

ssize_t dbg_console_read(void *buffer, size_t buffer_size) { return 0; }

#ifdef USE_DBG_CONSOLE_SWO
static ssize_t itm_swo_write(const void *data, size_t data_size) {
  irq_key_t irq_key = irq_lock();

  for (size_t i = 0; i < data_size; i++) {
    ITM_SendChar(((const char *)data)[i]);
  }

  irq_unlock(irq_key);
  return data_size;
}
#endif

#ifdef USE_DBG_CONSOLE_SYSTEM_VIEW
static ssize_t sysview_write(const void *data, size_t data_size) {
  static char str[SEGGER_SYSVIEW_MAX_STRING_LEN + 1];

  size_t copy_size = MIN(data_size, sizeof(str) - 1);
  memcpy(str, data, copy_size);
  str[copy_size] = 0;

  SEGGER_SYSVIEW_Print(str);

  return copy_size;
}
#endif

#ifdef USE_DBG_CONSOLE_VCP
static ssize_t usb_vcp_write(const void *data, size_t data_size) {
#ifdef BLOCK_ON_VCP
  // In thread mode, we can wait for the VCP to be ready.
  // In interrupt context, we must not block.
  uint32_t ipsr = __get_IPSR();
  bool thread_mode = (ipsr == 0 || ipsr == 11);  // Thread mode or SVCall
  uint32_t deadline = ticks_timeout(thread_mode ? 1000 : 0);

  const uint8_t *ptr = (const uint8_t *)data;
  size_t remaining = data_size;

  while (remaining > 0) {
    ssize_t written = syshandle_write(SYSHANDLE_USB_VCP, ptr, remaining);

    if (written < 0) {
      break;
    }

    ptr += written;
    remaining -= written;

    if (ticks_expired(deadline)) {
      break;
    } else if (remaining > 0) {
      systick_delay_ms(1);
    }
  }

  return data_size - remaining;
#else
  return syshandle_write(SYSHANDLE_USB_VCP, data, data_size);
#endif
}
#endif

ssize_t dbg_console_write(const void *data, size_t data_size) {
#ifdef USE_DBG_CONSOLE_SWO
  return itm_swo_write(data, data_size);
#endif
#ifdef USE_DBG_CONSOLE_SYSTEM_VIEW
  return sysview_write(data, data_size);
#endif
#ifdef USE_DBG_CONSOLE_VCP
  return usb_vcp_write(data, data_size);
#endif
#ifdef USE_DBG_CONSOLE_BLE
  return ble_log_write(data, data_size);
#endif
  return -1;
}

#endif  // KERNEL_MODE
