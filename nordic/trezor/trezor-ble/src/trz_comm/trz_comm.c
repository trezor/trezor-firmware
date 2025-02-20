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
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/settings/settings.h>
#include <zephyr/sys/crc.h>
#include <zephyr/types.h>

#include <trz_comm/trz_comm.h>

#include "trz_comm_internal.h"

#define LOG_MODULE_NAME trz_comm
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

static K_FIFO_DEFINE(fifo_uart_rx_ble);
static K_FIFO_DEFINE(fifo_uart_rx_ble_manager);
static K_FIFO_DEFINE(fifo_uart_rx_management);
static K_FIFO_DEFINE(fifo_uart_rx_prodtest);

void trz_comm_init(void) {
  spi_init();
  uart_init();
}

bool trz_comm_send_msg(nrf_service_id_t service, const uint8_t *data,
                       uint32_t len) {
  if (len == SPI_TX_DATA_LEN) {
    return spi_send(service, data, len);
  } else if (len <= MAX_UART_DATA_SIZE) {
    return uart_send(service, data, len);
  }
  return false;
}

void process_rx_msg(uint8_t service_id, uint8_t *data, uint32_t len) {
  trz_packet_t *buf = k_malloc(sizeof(*buf));

  if (!buf) {
    LOG_WRN("Not able to allocate UART receive buffer");
    return;
  }

  buf->len = len;
  memcpy(buf->data, data, len);

  switch (service_id) {
    case NRF_SERVICE_BLE:
      k_fifo_put(&fifo_uart_rx_ble, buf);
      break;
    case NRF_SERVICE_BLE_MANAGER:
      k_fifo_put(&fifo_uart_rx_ble_manager, buf);
      break;
    case NRF_SERVICE_MANAGEMENT:
      k_fifo_put(&fifo_uart_rx_management, buf);
      break;
    case NRF_SERVICE_PRODTEST:
      k_fifo_put(&fifo_uart_rx_prodtest, buf);
      break;
    default:
      LOG_WRN("UART_RX unknown service");
      k_free(buf);
      break;
  }
}

trz_packet_t *trz_comm_poll_data(nrf_service_id_t service) {
  switch (service) {
    case NRF_SERVICE_BLE:
      return k_fifo_get(&fifo_uart_rx_ble, K_FOREVER);
    case NRF_SERVICE_BLE_MANAGER:
      return k_fifo_get(&fifo_uart_rx_ble_manager, K_FOREVER);
    case NRF_SERVICE_MANAGEMENT:
      return k_fifo_get(&fifo_uart_rx_management, K_FOREVER);
    case NRF_SERVICE_PRODTEST:
      return k_fifo_get(&fifo_uart_rx_prodtest, K_FOREVER);
    default:
      LOG_WRN("UART_RX unknown service");
      return NULL;
  }
}
