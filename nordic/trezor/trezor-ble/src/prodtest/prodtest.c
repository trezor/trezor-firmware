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

#include <stdbool.h>
#include <stdint.h>

#include <zephyr/kernel.h>
#include <zephyr/types.h>

#include <zephyr/logging/log.h>

#include <signals/signals.h>
#include <trz_comm/trz_comm.h>

#define LOG_MODULE_NAME prodtest
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

static K_SEM_DEFINE(prodtest_ok, 0, 1);

typedef enum {
  PRODTEST_CMD_SPI_DATA = 0x00,
  PRODTEST_CMD_UART_DATA = 0x01,
  PRODTEST_CMD_SET_OUTPUT = 0x02,
} prodtest_cmd_t;

typedef enum {
  PRODTEST_RESP_SPI = 0x00,
  PRODTEST_RESP_UART = 0x01,
} prodtest_resp_t;

void prodtest_init(void) { k_sem_give(&prodtest_ok); }

static void process_command(uint8_t *data, uint16_t len) {
  uint8_t resp_data[244] = {0};
  uint8_t cmd = data[0];
  switch (cmd) {
    case PRODTEST_CMD_SPI_DATA:
      resp_data[0] = PRODTEST_RESP_SPI;
      trz_comm_send_msg(NRF_SERVICE_PRODTEST, resp_data, 244);
      break;
    case PRODTEST_CMD_UART_DATA:
      resp_data[0] = PRODTEST_RESP_UART;
      trz_comm_send_msg(NRF_SERVICE_PRODTEST, resp_data, 64);
      break;
    case PRODTEST_CMD_SET_OUTPUT:
      signals_reserved(data[1]);
      break;
    default:
      break;
  }
}

void prodtest_thread(void) {
  /* Don't go any further until module is initialized */
  k_sem_take(&prodtest_ok, K_FOREVER);

  for (;;) {
    trz_packet_t *buf = trz_comm_poll_data(NRF_SERVICE_PRODTEST);
    process_command(buf->data, buf->len);
    k_free(buf);
  }
}

K_THREAD_DEFINE(prodtest_thread_id, CONFIG_DEFAULT_THREAD_STACK_SIZE,
                prodtest_thread, NULL, NULL, NULL, 7, 0, 0);
