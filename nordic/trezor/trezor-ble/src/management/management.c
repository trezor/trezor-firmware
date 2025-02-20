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

#include <app_version.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/crc.h>
#include <zephyr/sys/poweroff.h>

#include <signals/signals.h>
#include <trz_comm/trz_comm.h>

#define LOG_MODULE_NAME manangement
LOG_MODULE_REGISTER(LOG_MODULE_NAME);

static K_SEM_DEFINE(management_ok, 0, 1);

typedef enum {
  MGMT_CMD_SYSTEM_OFF = 0x00,
  MGMT_CMD_INFO = 0x01,
} management_cmd_t;

typedef enum {
  MGMT_RESP_INFO = 0,
} management_resp_t;

void management_init(void) { k_sem_give(&management_ok); }

static void send_info(void) {
  uint8_t data[9] = {0};

  data[0] = MGMT_RESP_INFO;
  data[1] = APP_VERSION_MAJOR;
  data[2] = APP_VERSION_MINOR;
  data[3] = APP_PATCHLEVEL;
  data[4] = APP_TWEAK;
  data[5] = signals_is_trz_ready();
  data[6] = signals_is_stay_in_bootloader();
  data[7] = signals_out_get_nrf_ready();
  data[8] = signals_out_get_reserved();

  trz_comm_send_msg(NRF_SERVICE_MANAGEMENT, data, sizeof(data));
}

static void process_command(uint8_t *data, uint16_t len) {
  uint8_t cmd = data[0];
  switch (cmd) {
    case MGMT_CMD_SYSTEM_OFF:
      LOG_INF("System off");
      sys_poweroff();
      break;
    case MGMT_CMD_INFO:
      LOG_INF("Info command");
      send_info();
      break;
    default:
      break;
  }
}

void management_thread(void) {
  /* Don't go any further until BLE is initialized */
  k_sem_take(&management_ok, K_FOREVER);

  for (;;) {
    trz_packet_t *buf = trz_comm_poll_data(NRF_SERVICE_MANAGEMENT);
    process_command(buf->data, buf->len);
    k_free(buf);
  }
}

K_THREAD_DEFINE(management_thread_id, CONFIG_DEFAULT_THREAD_STACK_SIZE,
                management_thread, NULL, NULL, NULL, 7, 0, 0);
