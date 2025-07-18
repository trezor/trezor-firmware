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
#include <zephyr/settings/settings.h>
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
  PRODTEST_CMD_PAIR = 0x03,
} prodtest_cmd_t;

typedef enum {
  PRODTEST_RESP_SPI = 0x00,
  PRODTEST_RESP_UART = 0x01,
  PRODTEST_RESP_SUCCESS = 0x02,
  PRODTEST_RESP_FAILURE = 0x03,
} prodtest_resp_t;

void prodtest_init(void) { k_sem_give(&prodtest_ok); }

#define PAIRING_SECRET_SIZE 32

static uint8_t pairing_secret[PAIRING_SECRET_SIZE] = {0};

static int prodtest_set(const char *key, size_t len, settings_read_cb read_cb,
                        void *cb_arg) {
  if (strcmp(key, "pairing_secret") == 0) {
    ssize_t rc = read_cb(cb_arg, pairing_secret, sizeof(pairing_secret));
    return rc < 0 ? (int)rc : 0;
  }
  return -ENOENT;
}

SETTINGS_STATIC_HANDLER_DEFINE(prodtest, "prodtest", NULL, prodtest_set, NULL,
                               NULL);

bool prodtest_pair(uint8_t *data, uint16_t len) {
  if (len != PAIRING_SECRET_SIZE) {
    LOG_ERR("Invalid pairing data length: %d", len);
    return false;
  }

  // Save pairing data to settings
  int rc = settings_save_one("prodtest/pairing_secret", data, len);

  if (rc != 0) {
    LOG_ERR("Failed to save pairing secret: %d", rc);
    return false;
  }

  settings_commit();  // Commit settings to persistent storage

  return true;
}

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
      signals_set_reserved(data[1]);
      break;
    case PRODTEST_CMD_PAIR:
      if (len < 1 + PAIRING_SECRET_SIZE) {
        LOG_ERR("Pairing data too short: %d", len);
        return;
      }
      bool ok = prodtest_pair(&data[1], PAIRING_SECRET_SIZE);

      if (!ok) {
        resp_data[0] = PRODTEST_RESP_FAILURE;
        LOG_ERR("Failed to pair");
        trz_comm_send_msg(NRF_SERVICE_PRODTEST, resp_data, 1);
        return;
      }

      resp_data[0] = PRODTEST_RESP_SUCCESS;
      trz_comm_send_msg(NRF_SERVICE_PRODTEST, resp_data, 1);
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
