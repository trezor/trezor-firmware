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

#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/pm/device.h>
#include <zephyr/settings/settings.h>
#include <zephyr/sys/crc.h>
#include <zephyr/types.h>

#include <trz_comm/trz_comm.h>

#include "trz_comm_internal.h"

#define LOG_MODULE_NAME trz_comm_uart
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

#define UART_WAIT_FOR_BUF_DELAY K_MSEC(50)
#define UART_WAIT_FOR_RX CONFIG_BT_NUS_UART_RX_WAIT_TIME

static const struct device *uart = DEVICE_DT_GET(DT_CHOSEN(trezor_trz_uart));

static K_FIFO_DEFINE(fifo_uart_tx_data);

#define COMM_HEADER_SIZE (2)
#define COMM_FOOTER_SIZE (1)
#define OVERHEAD_SIZE (COMM_HEADER_SIZE + COMM_FOOTER_SIZE)

static struct k_work_delayable uart_work;

static volatile bool g_uart_rx_running = false;

static void uart_cb(const struct device *dev, struct uart_event *evt,
                    void *user_data) {
  ARG_UNUSED(dev);

  static size_t aborted_len;
  trz_packet_t *buf;
  static uint8_t *aborted_buf;
  static bool disable_req;
  static uint8_t rx_data = 0;

  switch (evt->type) {
    case UART_TX_DONE:
      LOG_DBG("UART_TX_DONE");

      if (evt->data.tx.buf == NULL) {
        return;
      }

      if (evt->data.tx.len == 0) {
        buf = CONTAINER_OF(evt->data.tx.buf, trz_packet_t, data[0]);

        LOG_DBG("Free uart data");
        k_free(buf);
        return;
      }

      if (aborted_buf) {
        buf = CONTAINER_OF(aborted_buf, trz_packet_t, data[0]);
        aborted_buf = NULL;
        aborted_len = 0;
      } else {
        buf = CONTAINER_OF(evt->data.tx.buf, trz_packet_t, data[0]);
      }

      LOG_DBG("Free uart data");
      k_free(buf);

      buf = k_fifo_get(&fifo_uart_tx_data, K_NO_WAIT);
      if (!buf) {
        return;
      }

      if (!uart_tx(uart, buf->data, buf->len, SYS_FOREVER_MS)) {
        LOG_WRN("FREE: Failed to send data over UART");
      }

      break;

    case UART_RX_RDY:
      //      LOG_WRN("UART_RX_RDY");
      buf = CONTAINER_OF(evt->data.rx.buf, trz_packet_t, data[0]);
      buf->len += evt->data.rx.len;
      rx_data = buf->data[0];

      trz_packet_t *tx = k_malloc(sizeof(*tx));

      if (tx == NULL) {
        LOG_WRN("Not able to allocate UART send data buffer");
        return;
      }
      tx->len = 1;
      tx->data[0] = rx_data;

      uart_tx(uart, tx->data, tx->len, SYS_FOREVER_MS);
      break;

    case UART_RX_DISABLED:
      LOG_DBG("UART_RX_DISABLED");
      disable_req = false;

      LOG_DBG("UART_RX_MALLOC");
      buf = k_malloc(sizeof(*buf));

      if (g_uart_rx_running) {
        if (buf) {
          uart_rx_enable(uart, buf->data, 1, SYS_FOREVER_US);
        } else {
          LOG_WRN("Not able to allocate UART receive buffer");
          k_work_reschedule(&uart_work, UART_WAIT_FOR_BUF_DELAY);
          g_uart_rx_running = false;
        }
      } else {
        uart_power_down();
      }
      break;

    case UART_RX_BUF_RELEASED:
      LOG_DBG("UART_RX_BUF_RELEASED");
      buf = CONTAINER_OF(evt->data.rx_buf.buf, trz_packet_t, data[0]);
      k_free(buf);

      break;
    case UART_RX_STOPPED:
      LOG_DBG("UART_RX_STOPPED");
      g_uart_rx_running = false;
      k_work_reschedule(&uart_work, UART_WAIT_FOR_BUF_DELAY);
      break;

    case UART_TX_ABORTED:
      LOG_DBG("UART_TX_ABORTED");
      if (!aborted_buf) {
        aborted_buf = (uint8_t *)evt->data.tx.buf;
      }

      aborted_len += evt->data.tx.len;
      buf = CONTAINER_OF(aborted_buf, trz_packet_t, data[0]);

      uart_tx(uart, &buf->data[aborted_len], buf->len - aborted_len,
              SYS_FOREVER_MS);

      break;

    default:
      break;
  }
}

int uart_start_rx(void) {
  int err;
  trz_packet_t *rx = k_malloc(sizeof(*rx));
  if (rx) {
    rx->len = 0;
  } else {
    return -ENOMEM;
  }

  // receive message type
  err = uart_rx_enable(uart, rx->data, 1, SYS_FOREVER_US);
  if (err) {
    LOG_ERR("Cannot enable uart reception (err: %d)", err);
    /* Free the rx buffer only because the tx buffer will be handled in the
     * callback */
    k_free(rx);
  } else {
    g_uart_rx_running = true;
  }

  return err;
}

static void uart_work_handler(struct k_work *item) {
  trz_packet_t *buf;

  if (!g_uart_rx_running) {
    uart_power_down();
    return;
  }
  buf = k_malloc(sizeof(*buf));
  if (buf) {
    buf->len = 0;
  } else {
    LOG_WRN("Not able to allocate UART receive buffer");
    k_work_reschedule(&uart_work, UART_WAIT_FOR_BUF_DELAY);
    return;
  }

  uart_rx_enable(uart, buf->data, 1, SYS_FOREVER_US);
}

int uart_init(void) {
  int err;

  pm_device_action_run(uart, PM_DEVICE_ACTION_RESUME);

  if (!device_is_ready(uart)) {
    return -ENODEV;
  }

  k_work_init_delayable(&uart_work, uart_work_handler);

  struct uart_config cfg = {
      .baudrate = 1000000,
      .parity = UART_CFG_PARITY_NONE,
      .stop_bits = UART_CFG_STOP_BITS_1,
      .data_bits = UART_CFG_DATA_BITS_8,
      .flow_ctrl = UART_CFG_FLOW_CTRL_RTS_CTS,

  };

  uart_configure(uart, &cfg);

  err = uart_callback_set(uart, uart_cb, NULL);
  if (err) {
    LOG_ERR("Cannot initialize UART callback");
    return err;
  }

  return uart_start_rx();
}

void uart_deinit(void) {
  int err;

  if (!g_uart_rx_running) {
    return;
  }

  g_uart_rx_running = false;

  err = uart_rx_disable(uart);
  if (err) {
    LOG_ERR("Cannot disable UART RX (err: %d)", err);
  }

  err = uart_tx_abort(uart);
  if (err) {
    LOG_ERR("Cannot abort UART TX (err: %d)", err);
  }
}

bool uart_send(uint8_t service_id, const uint8_t *tx_data, uint8_t len) {
  trz_packet_t *tx = k_malloc(sizeof(*tx));

  if (tx == NULL) {
    LOG_WRN("Not able to allocate UART send data buffer");
    return false;
  }

  LOG_DBG("ALLOC: Sending UART data");

  tx->len = len + OVERHEAD_SIZE;

  tx->data[0] = 0xA0 | service_id;
  tx->data[1] = tx->len;
  memcpy(&tx->data[COMM_HEADER_SIZE], tx_data, len);

  uint8_t crc = crc8(tx->data, tx->len - 1, 0x07, 0x00, false);

  tx->data[tx->len - 1] = crc;

  int err = uart_tx(uart, tx->data, tx->len, SYS_FOREVER_MS);
  if (err) {
    k_fifo_put(&fifo_uart_tx_data, tx);
  }
  return true;
}

void uart_power_down(void) {
  int err;

  uart_callback_set(uart, NULL, NULL);

  /* Power down the UART device */
  err = pm_device_action_run(uart, PM_DEVICE_ACTION_SUSPEND);
  if (err) {
    printk("pm_device_action_run() failed (%d)\n", err);
  }
}
